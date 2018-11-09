from collections import OrderedDict
from datetime import date, datetime, time, timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms
from django.conf import settings
from django.contrib.postgres.forms.ranges import DateRangeField
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.utils.timezone import now

from common.models import Session, Film, CinemaHall, Dimension, Chain, City, Cinema, Feedback, \
    AdditionalAgreement, FinishedCinemaReportDate
from kinomania.utils import MONTHS

GROUP_BY_CHOICES = (
    ('date', 'День'),
    ('week', 'Неделя'),
    ('month', 'Месяц'),
)


class ExportReportForm(forms.Form):

    FLAT_EXPORT_COLUMNS = (
        # information for DBF table: ('column_name', 'label', 'column_type')
        ('id', 'ID', 'N(10, 0)'),
        ('hall', 'Зал', 'C(64)'),
        ('cinema', 'Кинотеатр', 'C(64)'),
        ('chain', 'Сеть', 'C(64)'),
        ('film', 'Фильм', 'C(128)'),
        ('film_code', 'Код фильма', 'C(128)'),
        ('date', 'Дата', 'D'),
        ('time', 'Время', 'C(8)'),
        ('min_price', 'Мин. цена', 'N(6, 2)'),
        ('max_price', 'Макс. цена', 'N(6, 2)'),
        ('viewers', 'Зрителей', 'N(4, 0)'),
        ('invitation', 'Приглашений', 'N(4, 0)'),
        ('yield', 'Валовый доход', 'N(10, 2)'),
        ('income', 'Роялти', 'N(10, 2)'),
        ('dimension', 'Формат', 'C(3)'),
        ('vat', 'НДС', 'L'),
        ('contr_num', 'Номер ген. договора', 'C(32)'),
        ('contr_code', 'ЕГРПОУ ген. договора', 'N(10, 0)'),
        ('agr_date_s', 'Доп. соглашение активно с', 'D'),
        ('agr_date_e', 'Доп. соглашение активно по', 'D'),
        ('language', 'Язык показа', 'C(12)'),
        ('created', 'Создан', 'D'),
        ('modified', 'Обновлен', 'D'),
    )

    GROUPED_EXPORT_COLUMNS = OrderedDict([
        ('period', ('period', 'C(32)')),
        ('session_count', ('sessions', 'N(8, 0)')),
        ('cinema_count', ('cinemas', 'N(8, 0)')),
        ('cinema_hall_count', ('halls', 'N(8, 0)')),
        ('sum_seats_count', ('seats', 'N(8, 0)')),
        ('sum_viewers_count', ('viewers', 'N(8, 0)')),
        ('sum_gross_yield', ('yield', 'N(12, 2)')),
        ('average_attendance', ('attendance', 'C(6)')),
        ('gross_yield_per_viewer', ('yiel_per_v', 'N(10, 2)')),
        ('sum_gross_yield_without_vat', ('clean_yiel', 'N(12, 2)')),
        ('income', ('income', 'N(12, 2)')),
    ])

    export_format = forms.ChoiceField(label='Формат', choices=(('csv', 'csv'), ('dbf', 'dbf')))
    export_group_by = forms.ChoiceField(choices=(('', 'Не группировать'), ) + GROUP_BY_CHOICES,
                                        label='Группировать по дню/неделе/мес', required=False)
    grouped_columns = forms.MultipleChoiceField(
            label='Столбцы', widget=forms.CheckboxSelectMultiple(attrs={'checked': ''}))
    flat_columns = forms.MultipleChoiceField(
            label='Столбцы', choices=((col[0], col[1]) for col in FLAT_EXPORT_COLUMNS),
            widget=forms.CheckboxSelectMultiple(attrs={'checked': ''}))

    def __init__(self, *args, **kwargs):
        self.table = kwargs.pop('table')
        super().__init__(*args, **kwargs)

        self.fields['grouped_columns'].initial = [col.name for col in self.table.columns]

        self.fields['grouped_columns'].choices = [
                (col.name, col.header) for col in self.table.columns]

        self.fields['export_format'].widget.attrs['class'] = 'form-control'
        self.fields['export_group_by'].widget.attrs['class'] = 'form-control'


class BaseFilterReportForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        not_filterable_fields = ['date_range', 'group_by', 'dimensions', 'chains', 'year', 'month']
        for field_name in self.fields:
            if field_name not in not_filterable_fields:
                self.fields[field_name].widget.attrs['filterable'] = 'filterable'

        filtered_agreements = self.get_filtered_agreements()

        filtered_films = Film.objects.filter(agreements__in=filtered_agreements)
        self.fields['films'].queryset = filtered_films.distinct()

        self.fields['dimensions'].queryset = Dimension.objects.filter(
                agreements__in=filtered_agreements).distinct()

        filtered_cinemas = self.user.all_report_cinemas.filter(
                agreements__in=filtered_agreements)
        self.fields['cinemas'].queryset = filtered_cinemas.select_related('city').distinct()

        if self.fields.get('cities'):
            self.fields['cities'].queryset = City.objects.filter(
                cinemas__in=filtered_cinemas).distinct()

    def get_filtered_agreements(self):

        date_range_from, date_range_to = self.get_date_range()

        first_agreement = AdditionalAgreement.objects.order_by('created').first()

        if not first_agreement:
            return AdditionalAgreement.objects.none()

        date_range_from = date_range_from or first_agreement.created.date()

        date_range_to = date_range_to or now().date()
        return self.user.all_agreements.filter(
                active_date_range__overlap=[date_range_from, date_range_to])


class FilterByMonthForm(forms.Form):
    current_year = now().date().year
    year = forms.TypedChoiceField(
            label='Год', coerce=int, required=False,
            choices=[(y, str(y)) for y in range(current_year - 5, current_year + 1)])
    month = forms.TypedChoiceField(
            label='Месяц', coerce=int,required=False,
            choices=[m for m in enumerate(MONTHS, start=1)])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year'].widget.attrs['class'] = 'form-control'
        self.fields['month'].widget.attrs['class'] = 'form-control'
        self.values = self.get_values()

    def get_values(self):
        try:
            month = self.initial.get('month') or self.data.get('month')
            return {'month': MONTHS[int(month) - 1]}
        except (ValueError, TypeError):
            return {}

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['date_range'] = self.get_date_range()
        return cleaned_data

    def get_date_range(self):
        now_ = now()
        try:
            year = int(self.data.get('year', now_.year))
            month = int(self.data.get('month', now_.month))
        except (TypeError, ValueError):
            return None, None
        else:
            if not year or not month:
                return None, None

        return self.get_date_range_static(year, month)

    @staticmethod
    def get_date_range_static(year, month):
        date_from = date(year, month, 1)
        date_to = date(year if month != 12 else year + 1,
                       month + 1 if month != 12 else 1,
                       1)
        return [date_from, date_to]


class FilterMonthlyReportForm(FilterByMonthForm, BaseFilterReportForm):
    films = forms.ModelChoiceField(label='Фильм', queryset=Film.objects.all(),
                                   widget=forms.RadioSelect(), required=False)
    dimensions = forms.ModelChoiceField(label='Формат',
                                        queryset=Dimension.objects.all(),
                                        widget=forms.RadioSelect(), required=False)
    cinemas = forms.ModelChoiceField(label='Кинотеатр',
                                     queryset=Cinema.objects.all(),
                                     widget=forms.RadioSelect(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['films'].choices = [
            (film.id, film.name) for film in self.fields['films'].queryset]
        self.fields['cinemas'].choices = [
            (c.id, '{} ({})'.format(c.name, c.city.name)) for c in self.fields['cinemas'].queryset]
        self.fields['dimensions'].choices = [
                (c.id, c.name) for c in self.fields['dimensions'].queryset]

    def get_values(self):
        try:
            return dict(
                    month=MONTHS[int(self.data['month']) - 1],
                    film=Film.objects.get(id=self.data['films']).name,
                    cinema=Cinema.objects.get(id=self.data['cinemas']).name,
                    dimension=Dimension.objects.get(id=self.data['dimensions']).name)
        except (ValueError, TypeError, ObjectDoesNotExist, KeyError):
            return {}


class FilterReportForm(BaseFilterReportForm):

    group_by = forms.ChoiceField(label='Группировать по дню/неделе/мес', choices=GROUP_BY_CHOICES,
                                 required=False)
    date_range = DateRangeField(label='Дата', required=False, require_all_fields=False)
    films = forms.ModelMultipleChoiceField(label='Фильм', queryset=Film.objects.all(),
                                           widget=forms.CheckboxSelectMultiple, required=False)
    chains = forms.ModelMultipleChoiceField(
                    label='Сеть', queryset=Chain.objects.all(),
                    widget=forms.CheckboxSelectMultiple, required=False)
    cities = forms.ModelMultipleChoiceField(label='Город', queryset=City.objects.all(),
                                            widget=forms.CheckboxSelectMultiple, required=False)
    cinemas = forms.ModelMultipleChoiceField(label='Кинотеатр', queryset=Cinema.objects.all(),
                                             widget=forms.CheckboxSelectMultiple, required=False)
    dimensions = forms.ModelMultipleChoiceField(label='Формат', queryset=Dimension.objects.all(),
                                                widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['date_range'].widget.attrs['class'] = 'form-control'
        self.fields['group_by'].widget.attrs['class'] = 'form-control'

        if not self.user.is_superuser or not self.user.view_all_reports:
            self.fields.pop('chains')
        else:
            self.fields['chains'].queryset = Chain.objects.filter(
                  cinemas__in=self.fields['cinemas'].queryset).distinct()

    def get_date_range(self):
        date_from = self.data.get('date_range_0')
        date_to = self.data.get('date_range_1')
        date_format = settings.DATE_INPUT_FORMATS[0]
        try:
            date_from = datetime.strptime(date_from, date_format).date() if date_from else None
            date_to = datetime.strptime(date_to, date_format).date() if date_to else None
        except ValueError:
            date_from, date_to = None, None

        """
        It is required to fix error 
        "range lower bound must be less than or equal to range upper bound"
        """
        if date_from and not date_to:
            current_date = now().date()
            date_to = (current_date if current_date > date_from else date_from) + timedelta(days=31)

        return date_from, date_to


class SessionForm(forms.ModelForm):

    time = forms.TimeField(required=False)
    time_hours = forms.ChoiceField(choices=[("", "час")] + [
            (i, '{0:02d}'.format(i)) for i in range(24)])
    time_minutes = forms.ChoiceField(choices=[("", "мин")] + [
            (i, '{0:02d}'.format(i)) for i in range(0, 56, 5)])
    update_request_comment = forms.CharField(widget=forms.Textarea, required=False,
                                             label='Добавьте комментарий (опционально)')

    class Meta:
        model = Session
        fields = (
            'date',
            'time',
            'viewers_count',
            'film',
            'min_price',
            'max_price',
            'invitations_count',
            'dimension',
            'time_minutes',
            'time_hours',
            'cinema_hall',
            'gross_yield',
            'is_original_language',
        )
        widgets = {
            'dimension': forms.RadioSelect(),
            'time': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.cinema = kwargs.pop('cinema')
        self.date = kwargs.pop('date')
        self.submit_text = kwargs.pop('submit_text')
        self.form_action = kwargs.pop('form_action')
        self.view_name = kwargs.pop('view_name')
        self.create_session_url = kwargs.pop('create_session_url')

        super().__init__(*args, **kwargs)

        self.fields['dimension'].empty_label = None
        self.fields['date'].required = False

        for field_name, field in self.fields.items():
            if field_name not in ('dimension', 'is_original_language'):
                field.widget.attrs['class'] = 'form-control'

        current_cinemas_agreements = self.cinema.get_agreements().filter_by_date(self.date)
        self.fields['film'].queryset = self.get_initial_films(current_cinemas_agreements)
        self.fields['cinema_hall'].queryset = CinemaHall.objects.filter(cinema=self.cinema)
        self.fields['dimension'].queryset = Dimension.objects.filter(
                agreements__in=current_cinemas_agreements).distinct()

        if self.instance.pk:
            session_time = self.instance.time
            if session_time:
                self.fields['time_hours'].initial = session_time.hour
                self.fields['time_minutes'].initial = session_time.minute

        if self.view_name != 'send_update_session_request':
            del self.fields['update_request_comment']

    def get_initial_films(self, agreements):

        return Film.objects.filter(agreements__in=agreements).prefetch_related(
                Prefetch(
                    'dimensions',
                    queryset=Dimension.objects.filter(agreements__in=agreements).only('id'),
                    to_attr='dimensions_ids')).distinct()

    def has_changed(self):
        if bool(set(self.changed_data) - {'date', 'time', 'time_minutes', 'time_hours'}):
            return True

        for field_name in ['date', 'time']:
            if self.cleaned_data[field_name] != self.initial[field_name]:
                return True

        return False

    def clean_time(self):
        return time(
            int(self.data['time_hours']),
            int(self.data['time_minutes']))

    def clean_gross_yield(self):
        gross_yield = self.cleaned_data['gross_yield']
        viewers_count = self.cleaned_data['viewers_count']
        min_price = self.cleaned_data['min_price']
        max_price = self.cleaned_data['max_price']

        error_message = ('{min_or_max} доход с учётом введённого кол-ва '
                         'зрителей и цены составляет {gross_yield_value} грн')

        min_gross_yield = viewers_count * min_price
        if gross_yield < min_gross_yield:
            raise forms.ValidationError(error_message.format(
                min_or_max='Минимальный',
                gross_yield_value=min_gross_yield))

        max_gross_yield = viewers_count * max_price
        if gross_yield > max_gross_yield:
            raise forms.ValidationError(error_message.format(
                min_or_max='Максимальный',
                gross_yield_value=max_gross_yield))

        return gross_yield

    def clean_date(self):
        return self.cleaned_data.get('date') or self.initial.get('date')

    def clean(self):
        cleaned_data = super().clean()

        if not self.has_changed() and (self.view_name == 'send_update_session_request'):
            raise forms.ValidationError('Вы не обновили сеанс')

        cinema_hall = cleaned_data.get('cinema_hall')

        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        time = cleaned_data.get('time')
        viewers_count = cleaned_data.get('viewers_count')
        invitations_count = self.cleaned_data.get('invitations_count')
        dimension = self.cleaned_data.get('dimension')
        film = self.cleaned_data.get('film')

        if film and (not film.name_original or (film.name == film.name_original)):
            self.cleaned_data['is_original_language'] = True

        is_original_language = self.cleaned_data.get('is_original_language')

        if film and dimension and cinema_hall:
            filtered_agreements = film.agreements.filter_by_date(self.date).filter(
                    dimension=dimension, cinema=cinema_hall.cinema)

            if not filtered_agreements.exists():
                raise forms.ValidationError(
                    'На формат "{}" нет дополнительного соглашения для фильма "{}".'.format(
                            dimension.name, film.name))

            if is_original_language is not None:
                if not filtered_agreements.filter(
                        is_original_language=is_original_language).exists():
                    raise forms.ValidationError('У фильма нет активного дополнительного соглашения '
                                                'на выбранный формат c этим языком')

        if cinema_hall and time and Session.objects.filter(
                cinema_hall=cinema_hall, time=time, date=self.date).exclude(id=self.instance.pk):
            raise forms.ValidationError('Сеанс с такой датой, временем и кинозалом уже существует.')

        if cinema_hall:
            seats_count = cinema_hall.seats_count

            viewers_count_error = forms.ValidationError(
                        'Максимальное количество зрителей в этом зале %(seats_count)s',
                        params={'seats_count': seats_count})

            if viewers_count is not None and (viewers_count > seats_count):
                raise viewers_count_error

            if invitations_count is not None and (invitations_count > seats_count):
                raise viewers_count_error

            if invitations_count is not None and viewers_count is not None and (
                        (invitations_count + viewers_count) > seats_count):
                raise viewers_count_error

        if (min_price and max_price) and (min_price > max_price):
            raise forms.ValidationError('Минимальная цена не может быть больше максимальной')

        # TODO remove it if unnecessary
        # if viewers_count is not None and invitations_count is not None and (
        #             viewers_count + invitations_count) == 0:
        #     raise forms.ValidationError(
        #             'Если на сеансе не было ни одного человека вы не должны создавать сеанс')

        return cleaned_data


class CreateFeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ('text', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.form_show_errors = True

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-1'
        self.helper.field_class = 'col-lg-11'
        self.helper.layout = Layout(
            'text',
            Submit('create_feedback', 'Отправить фидбек', css_class='btn-primary btn-primary')
        )


class ChangeSessionsDateForm(forms.Form):

    change_date_to = forms.DateField(label='Дата')

    def __init__(self, *args, **kwargs):
        self.cinema = kwargs.pop('cinema')
        self.change_date_from = kwargs.pop('change_date_from')
        super().__init__(*args, **kwargs)

    def clean_change_date_to(self):
        change_date_to = self.cleaned_data['change_date_to']

        if change_date_to == self.change_date_from:
            raise forms.ValidationError('Указана такая же дата.')

        if change_date_to > now().date():
            raise forms.ValidationError('Нельзя изменить дату на дату в будущем.')

        if FinishedCinemaReportDate.objects.filter(
                cinema=self.cinema, date=change_date_to).exists():
            raise forms.ValidationError('За выбранную дату уже сдан отчёт для этого кинотеатра.')

        for session in Session.objects.filter(cinema_hall__cinema=self.cinema, date=change_date_to):
            if Session.objects.filter(
                    cinema_hall=session.cinema_hall,
                    time=session.time,
                    date=self.change_date_from,
                    dimension=session.dimension).exists():
                raise forms.ValidationError(
                    'Сеанс "{film_name} {dimension}" ({time}) в зале "{cinema_hall}" '
                    'уже существует для {date}'.format(
                        film_name=session.film.name,
                        cinema_hall=session.cinema_hall,
                        dimension=session.dimension,
                        time=session.time,
                        date=change_date_to))

        return change_date_to


class SendMonthlyReportEmailForm(FilterByMonthForm):
    cinema = forms.ModelChoiceField(queryset=Cinema.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['month'].required = False
        self.fields['year'].required = False

    def clean(self):
        cleaned_data = super().clean()
        cinema = cleaned_data['cinema']
        if cinema.access_to_reports.count() == 0:
            raise forms.ValidationError('Нет ответственного за расчётные бланки')
        return cleaned_data

