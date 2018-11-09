from dal import autocomplete
from django import forms
from django.contrib.admin import site
from django.contrib.admin import widgets
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget
from django.contrib.postgres.forms.ranges import RangeWidget
from django.db.models import ManyToOneRel
from django.forms import BaseInlineFormSet
from django.forms.widgets import CheckboxFieldRenderer
from django.contrib.admin import widgets
from django.db.models import Q
from django.conf import settings

from common import models
from common.form_fields import MultipleFileField
from common.models import Cinema, AdditionalAgreement, City, GeneralContract, Session, CinemaHall, \
    Film, TimeBackup
from common.xls_report_parsers import XlsReportParser
from users.models import User


class UploadXLSReportsForm(forms.Form):
    xls_folder_path = MultipleFileField(label='Загрузить файлы')
    city = forms.ModelChoiceField(queryset=City.objects.all(), required=False, label='Город')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = City.objects.filter(
            cinemas__in=Cinema.objects.filter(chain__name=XlsReportParser.CHAIN_NAME)).distinct()


class CinemaAdminForm(forms.ModelForm):
    responsible_for_daily_reports = forms.ModelMultipleChoiceField(
        label='Дневные отчёты', queryset=User.objects.all().exclude(
            Q(is_superuser=True) | Q(view_all_reports=True)), required=False,
        widget=autocomplete.ModelSelect2Multiple(url='user_autocomplete'))

    access_to_reports = forms.ModelMultipleChoiceField(
        label='Доступ к отчётам', queryset=User.objects.all().exclude(
            Q(is_superuser=True) | Q(view_all_reports=True)), required=False,
        widget=autocomplete.ModelSelect2Multiple(url='user_autocomplete'))

    class Meta:
        model = Cinema
        fields = ('name', 'city', 'chain', 'halls_count', 'chain_contract')
        widgets = {
            'city': autocomplete.ModelSelect2(url='city_autocomplete'),
            'chain': autocomplete.ModelSelect2(url='chain_autocomplete'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.chain:
            self.fields['chain_contract'].queryset = GeneralContract.objects.filter(
                    chain=self.instance.chain)
        else:
            self.fields['chain_contract'].queryset = GeneralContract.objects.none()


class AdditionalAgreementAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AdditionalAgreementAdminForm, self).__init__(*args, **kwargs)

        self.fields['cinema'].required = True

    class Meta:
        model = AdditionalAgreement
        fields = ('cinema', 'contract', 'film', 'active_date_range', 'dimension',
                  'is_original_language', 'vat', 'one_c_number')
        widgets = {
            'active_date_range': RangeWidget(base_widget=AdminDateWidget()),
            'cinema': autocomplete.ModelSelect2(url='all_cinemas_autocomplete'),
            'contract': autocomplete.ModelSelect2(url='general_contact_autocomplete'),
            'film': autocomplete.ModelSelect2(url='film_autocomplete'),
        }


class CheckboxFieldRendererInline(CheckboxFieldRenderer):
    outer_html = '<div{id_attr}>{content}</div>'
    inner_html = '{choice_value}{sub_widgets}&emsp;'


class CheckboxSelectMultipleInline(forms.CheckboxSelectMultiple):
    renderer = CheckboxFieldRendererInline


class CinemaHallInlineForm(forms.ModelForm):

    class Meta:
        model = models.CinemaHall
        exclude = []
        widgets = {
            'dimensions': CheckboxSelectMultipleInline()
        }


class CinemaHallInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        if self.instance.halls_count != sum([bool(f.cleaned_data) for f in self.forms]):
            raise forms.ValidationError('Проверьте кол-во кинозалов.')


class SessionAdminForm(forms.ModelForm):
    class Meta:
        exclude = []
        model = Session

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.cinema_hall:
            cinema = self.instance.cinema_hall.cinema
            self.fields['cinema_hall'].queryset = CinemaHall.objects.filter(cinema=cinema)

            self.fields['film'].queryset = Film.objects.filter(
                    agreements__in=cinema.get_agreements().filter_by_date(
                        self.instance.date)).distinct()

        else:
            rel = ManyToOneRel(models.models.ForeignKey, models.CinemaHall, 'id')
            self.fields['cinema_hall'].widget = widgets.ForeignKeyRawIdWidget(rel, site)


class GeneralContractAdminForm(forms.ModelForm):

    cinemas = forms.ModelMultipleChoiceField(
        label='Кинотеатры', queryset=Cinema.objects.all(), required=False,
        widget=autocomplete.ModelSelect2Multiple(url='all_cinemas_autocomplete'))

    class Meta:
        model = GeneralContract
        exclude = []

    def clean(self):
        cinemas = self.cleaned_data['cinemas']
        chain = self.cleaned_data['chain']
        SBR_code = self.cleaned_data['SBR_code']
        number = self.cleaned_data['number']

        if chain and cinemas:
            raise forms.ValidationError('Укажите или сеть, или кинотеатры')

        if not chain and not cinemas:
            raise forms.ValidationError('Укажите сеть или кинотеатры')

        if GeneralContract.objects.filter(SBR_code=SBR_code).exists():
            raise forms.ValidationError('ЕГРПОУ уже существует в базе данных')

        if GeneralContract.objects.filter(number=number).exists():
            raise forms.ValidationError('Number уже существует в базе данных')


class TimeForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(TimeForm, self).__init__(*args, **kwargs)
        self.fields['start'].initial = self.get_initial_start()
        
    def get_initial_start(self):
        try:
            return TimeBackup.objects.first().start
        except:
            return

    start = forms.TimeField(label='Время бекапа', initial=None,
                            widget=AdminTimeWidget(format='%H:%M'))

    class Meta:
        model = TimeBackup
        fields = ('start',)

