from datetime import timedelta, date
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.middleware import csrf
from django.template.backends.utils import csrf_input
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_tables2 import A
from django_tables2 import Column
from django_tables2 import tables

from common.models import Cinema, Session, ConfirmedMonthlyReport
from kinomania.utils import get_initial_year_and_month


class IntSeparatorColumnMixin:
    def render(self, value):
        return intcomma(value)


class WithTotalColumn(Column):
    def render_footer(self, bound_column, table):
        field_name = bound_column.accessor
        summary_data = table.context['view'].summary_data
        normalized_data = {k.replace('total_', ''): v for k, v in summary_data.items()}

        if hasattr(table, 'render_' + field_name):
            result = getattr(table, 'render_' + field_name)(normalized_data)
        else:
            result = normalized_data.get(field_name)

        return format_html('<b>{}</b>', intcomma(round(result, 2)))


class TotalWithSeparatorColumn(IntSeparatorColumnMixin, WithTotalColumn):
    pass


class MonthlyReportTable(tables.Table):
    date = Column('Дата')
    session_count = WithTotalColumn('Сеансов')
    sum_viewers_count = WithTotalColumn('Посетителей')
    sum_gross_yield = WithTotalColumn('Валовый доход')
    sum_gross_yield_without_vat = WithTotalColumn('Чистые сборы')
    income = WithTotalColumn('Доход')

    class Meta:
        model = Session
        attrs = {'class': 'paleblue'}
        empty_text = 'Нет сеансов'
        fields = (
            'date',
            'session_count',
            'sum_viewers_count',
            'sum_gross_yield',
            'sum_gross_yield_without_vat',
            'income',
        )

    @staticmethod
    def render_date(record):
        date = record['date']

        a_tag = '<a href="{url}">{date_str}</a>'.format(
                url=reverse('cinema_list',
                            kwargs={'date': date.strftime(settings.DATE_URL_INPUT_FORMAT)}),
                date_str=date_format(date))
        return mark_safe(a_tag)

    @staticmethod
    def render_income(record):
        if record['income']:
            return round(record['income'], 2)


class ReportTable(tables.Table):
    period = Column('Период')
    session_count = WithTotalColumn('Сеансов')
    sum_viewers_count = WithTotalColumn('Посетителей')
    sum_gross_yield = TotalWithSeparatorColumn('Валовый доход')
    sum_gross_yield_without_vat = TotalWithSeparatorColumn('Чистые сборы')
    income = TotalWithSeparatorColumn('Роялти')
    cinema_count = WithTotalColumn('Кинотеатров')
    cinema_hall_count = WithTotalColumn('Экранов')
    sum_seats_count = WithTotalColumn('Мест в зале')
    average_attendance = WithTotalColumn('Средняя посещаемость')
    gross_yield_per_viewer = WithTotalColumn('Валовый сбор на зрителя')

    class Meta:
        model = Session
        attrs = {'class': 'paleblue'}
        empty_text = 'Нет сеансов'
        fields = (
            'period',
            'session_count',
            'cinema_count',
            'cinema_hall_count',
            'sum_seats_count',
            'sum_viewers_count',
            'average_attendance',
            'sum_gross_yield',
            'gross_yield_per_viewer',
            'sum_gross_yield_without_vat',
            'income',
        )

    def render_period(self, record, is_export=False):
        if 'date' in record:
            date = record['date']
            date_str = date_format(date)

            if is_export:
                return date_str

            date_in_url = date.strftime(settings.DATE_URL_INPUT_FORMAT)
            if self.context['request'].user.all_cinemas.count() == 1:
                url = reverse('create_session',
                              kwargs={
                                  'pk': self.context['request'].user.cinemas.first().id,
                                  'date': date_in_url})
            else:
                url = reverse('cinema_list', kwargs={'date': date_in_url})

            a_tag = '<a href="{url}">{date_str}</a>'.format(
                    url=url,
                    date_str=date_str)
            return mark_safe(a_tag)

        elif 'week' in record:
            return '{} - {}'.format(date_format(record['week']),
                                    date_format(record['week'] + timedelta(days=6)))
        else:
            return date_format(record['month'], format='F Y')

    @staticmethod
    def render_average_attendance(record):
        return '{}%'.format(record['average_attendance'])

    @staticmethod
    def render_income(record):
        if record['income']:
            return round(record['income'], 2)


class CinemaWithMonthlyReportsTable(tables.Table):
    id = Column('ID кинотеатра', A('id'))
    filtered_agreements_count = Column('Всего доп соглашений', A('filtered_agreements_count'))
    confirmed_monthly_reports_count = Column('Расчётные бланки', A('confirmed_reports_count'))
    are_all_blanks_confirmed = Column('Сданы все бланки', A('pk'))
    send_monthly_report_email = Column('Послать напоминание', A('pk'), orderable=False)

    class Meta:
        model = Cinema
        attrs = {'class': 'paleblue'}
        empty_text = 'Нет кинотеатров'
        fields = (
            'id',
            'name',
            'city',
        )

    def render_are_all_blanks_confirmed(self, record):

        links = []
        year, month = self.get_year_month()

        for agreement in record.filtered_agreements:
            if not ConfirmedMonthlyReport.objects.filter(
                    cinema=agreement.cinema,
                    film=agreement.film,
                    dimension=agreement.dimension,
                    month=date(int(year), int(month), 1)).exists():

                links.append('<a href="{url}" class="not_confirmed">{one_c_number}</a>'.format(
                    url='/admin/common/additionalagreement/{}/change/'.format(agreement.id),
                    one_c_number=agreement.one_c_number))
            else:

                url_params = dict(year=year, month=month, films=agreement.film.id,
                                  cinemas=record.id, dimensions=agreement.dimension.id)

                url = '{}?{}'.format(
                    reverse('confirm_monthly_report'),
                    urlencode(url_params))

                links.append('<a href="{url}">{agreement_one_c_number}</a>'.format(
                    url=url,
                    agreement_one_c_number=agreement.one_c_number))

        return mark_safe('<br>'.join(links))

    def render_send_monthly_report_email(self, record):

        if (record.all_reports_confirmed or (record.filtered_agreements_count == 0) or
                not record.access_to_reports) or not self.context['request'].user.is_superuser:
            return '-'

        button_html_template = """
        <form method="POST" action={url}>
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"/>
            <input type="hidden" name="cinema" value="{cinema_id}"/>
            <input type="hidden" name="month" value="{month}"/>
            <input type="hidden" name="year" value="{year}"/>
            <button type="submit" class="btn btn-default btn-extra-sm glyphicon glyphicon-send"> 
            </button>
        </form>
        """
        csrf_token = csrf.get_token(self.context['view'].request)

        year, month = self.get_year_month()
        button_html = button_html_template.format(
                url=reverse('send_monthly_report_email'),
                csrf_token=csrf_token,
                cinema_id=record.id,
                month=month,
                year=year,
        )
        return format_html(button_html)

    def get_year_month(self):

        get_params = self.context['request'].GET

        if 'month' in get_params and 'year' in get_params:
            month = get_params['month']
            year = get_params['year']
        else:
            month_and_year = get_initial_year_and_month()
            month = month_and_year['month']
            year = month_and_year['year']

        return year, month


class CinemaTable(tables.Table):
    is_daily_report_finished = Column('Отчёт завершён', A('id'))
    hall_count = Column('Залов')
    send_daily_report_email = Column('Послать напоминание', A('pk'), orderable=False)

    class Meta:
        model = Cinema
        attrs = {'class': 'paleblue'}
        empty_text = 'Нет кинотеатров'
        fields = (
            'id',
            'name',
            'city',
            'is_daily_report_finished',
        )

    def render_send_daily_report_email(self, record):

        if not self.context['request'].user.is_superuser:
            return '-'

        if record.is_daily_report_finished:
            return 'отчёт сдан'

        if not record.responsible_for_daily_reports:
            return 'нет ответственного'

        button_html = """
        <form method="POST" action={url}>
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"/>
            <button type="submit" class="btn btn-default btn-extra-sm glyphicon glyphicon-send"> 
            </button>
        </form>
        """
        create_report_url = reverse('send_daily_report_email',
                                    kwargs={'pk': record.pk, 'date': self.context['view'].date_str})
        csrf_token = csrf.get_token(self.context['view'].request)

        return format_html(button_html.format(url=create_report_url, csrf_token=csrf_token))

    def render_is_daily_report_finished(self, record):
        if record.is_daily_report_finished:
            return 'Да'

        if record.is_daily_report_finished is False:
            return 'Нет'

        return 'Нет активных соглашений'

    def render_name(self, record):
        create_report_url = reverse('create_session',
                                    kwargs={'pk': record.pk, 'date': self.context['view'].date_str})

        return format_html('<a href="{}">{}</a>'.format(create_report_url, record.name))


class SessionTable(tables.Table):
    update_link = Column('Редакт.', A('pk'), orderable=False)
    remove_form = Column('Удалить', A('pk'), orderable=False)
    send_update_request_link = Column('Запросить изменение', A('pk'), orderable=False)
    invitations_count = WithTotalColumn('Пригл.')
    viewers_count = WithTotalColumn('Зрители')
    gross_yield = TotalWithSeparatorColumn('Доход')

    class Meta:
        orderable = False
        model = Session
        attrs = {'class': 'paleblue'}
        empty_text = 'Нет сеансов по этому кинотеатру'
        fields = (
            'date',
            'cinema_hall',
            'film',
            'dimension',
            'time',
            'invitations_count',
            'viewers_count',
            'gross_yield',
            'min_price',
            'max_price',
            'is_original_language',
        )

    def render_date(self, record):
        """This allows to use date format from settings file"""
        return record.date

    def render_update_link(self, record):
        if record.is_daily_report_finished and not self.context['request'].user.is_superuser:
            return '-'

        update_url = reverse(
                'update_session',
                kwargs={
                    'pk': record.cinema_hall.cinema.pk,
                    'session_pk': record.pk,
                    'date': self.context['view'].date_str
                })

        html = ('<a href="{}" '
                'class="btn btn-default btn-extra-sm glyphicon glyphicon-pencil">'
                '</a>').format(update_url)
        return format_html(html)

    def render_remove_form(self, record):
        if record.is_daily_report_finished and not self.context['request'].user.is_superuser:
            return '-'

        url = reverse('delete_session', kwargs={'session_pk': record.pk})
        csrf_token_input = csrf_input(self.context['request'])
        html = """
        <form method="POST" action={url}>
            {csrf_token_input}
            <button type="submit" class="btn btn-extra-sm btn-default">
                <span class="glyphicon glyphicon-remove text-danger"></span>
            </button>
        </form>""".format(csrf_token_input=csrf_token_input, url=url)
        return format_html(html)

    def render_send_update_request_link(self, record):
        if not record.is_daily_report_finished or self.context['request'].user.is_superuser:
            return '-'

        request_update_url = reverse(
                'send_update_session_request',
                kwargs={
                    'pk': record.cinema_hall.cinema.pk,
                    'session_pk': record.pk,
                    'date': self.context['view'].date_str
                })

        html = ('<a href="{}" '
                'class="btn btn-default btn-extra-sm glyphicon glyphicon-send">'
                '</a>').format(request_update_url)
        return format_html(html)


