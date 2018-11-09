from datetime import timedelta, datetime
from itertools import chain as chain_tools
import time

from braces.views import FormValidMessageMixin
from braces.views import LoginRequiredMixin
from braces.views._access import SuperuserRequiredMixin
from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import mail_admins, send_mail
from django.db import transaction, IntegrityError
from django.db.models import Case, IntegerField, Avg, CharField, BooleanField, Value, Prefetch
from django.db.models import Count
from django.db.models import F
from django.db.models import Sum
from django.db.models import When
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.formats import date_format
from django.utils.timezone import now
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic.edit import FormMixin, ProcessFormView

from common.forms import FilterReportForm, ExportReportForm, CreateFeedbackForm, \
    ChangeSessionsDateForm, FilterMonthlyReportForm, FilterByMonthForm, \
    SendMonthlyReportEmailForm
from common.models import Session, Cinema, SessionUpdateRequest, CinemaHall, AdditionalAgreement, \
    FinishedCinemaReportDate, ConfirmedMonthlyReport  #, TimeBackup
from common.sessions_export import SessionCsvExporter, MonthlyReportXlsExporter, \
    MonthlyReportPdfExporter
from common.tables import CinemaTable, ReportTable, MonthlyReportTable, \
    CinemaWithMonthlyReportsTable
from common.views_mixins import AccessToReportMixin, CinemaPkMixin, SessionMixin, TableMixin, \
    DateViewMixin
from kinomania.utils import get_create_session_ulr, build_full_url, put_forms_errors_to_messages, \
    MONTHS, get_initial_year_and_month


class MonthlyReportView(LoginRequiredMixin, AccessToReportMixin, TableMixin, ListView):
    template_name = 'dashboard/confirm_monthly_report.html'

    model = Session
    table_class = MonthlyReportTable
    filter_form_class = FilterMonthlyReportForm
    context_object_name = 'report_data'
    group_by = 'date'
    session_xls_exporter_class = MonthlyReportXlsExporter
    session_pdf_exporter_class = MonthlyReportPdfExporter
    filter_params = None

    def get(self, request, *args, **kwargs):

        if len(request.GET):
            self.filter_form = self.filter_form_class(data=request.GET, user=self.request.user)
        else:
            self.filter_form = self.filter_form_class(
                    user=self.request.user,
                    initial=get_initial_year_and_month())

        if not self.filter_form.is_valid():
            prev_path = request.META.get('HTTP_REFERER')
            if not prev_path or request.path in prev_path:
                put_forms_errors_to_messages(request, self.filter_form, only_first=True)

        export_format = self.request.GET.get('export_format')

        queryset = self.get_queryset()

        if export_format:
            summary_data = self.get_summary_data(queryset)
            if export_format == 'xls':
                exporter = self.session_xls_exporter_class(
                        queryset, self.first_session,
                        summary_data=summary_data)
            elif export_format == 'pdf':
                exporter = self.session_pdf_exporter_class(
                        queryset, self.first_session,
                        summary_data=summary_data,
                        full_static_path=self.request.build_absolute_uri(settings.STATIC_URL))
            else:
                return HttpResponse(400, 'invalid export format {}'.format(export_format))

            return exporter.export_to_response()

        self.object_list = queryset
        context = self.get_context_data()
        return self.render_to_response(context)

    def filter_queryset(self, queryset):
        if not self.filter_form.is_valid():
            return queryset.none()

        queryset = queryset.filter(is_daily_report_finished=True)
        filter_params = self.filter_form.cleaned_data

        if not self.request.user.is_superuser:
            if not self.request.user.view_all_reports:
                user_cinemas = set(list(chain_tools(
                    self.request.user.report_cinemas.all(), self.request.user.cinemas.all()
                )))

                list_cinemas = [cinema.id for cinema in user_cinemas]
                queryset = queryset.filter(cinema_hall__cinema__id__in=list_cinemas)

        date_range = filter_params.get('date_range')
        if date_range:
            queryset = queryset.filter(date__range=[date_range[0], date_range[1]])

        films = filter_params.get('films')
        if films:
            queryset = queryset.filter(film=films)

        cinemas = filter_params.get('cinemas')
        if cinemas:
            queryset = queryset.filter(cinema_hall__cinema=cinemas)

        dimensions = filter_params.get('dimensions')
        if dimensions:
            queryset = queryset.filter(dimension=dimensions)

        return queryset

    def get_queryset(self):

        qs = self.model.objects.all()

        qs = self.filter_queryset(qs)

        self.first_session = qs.first()

        qs = qs.values('date').annotate(
            sum_gross_yield=Sum('gross_yield'),
            sum_viewers_count=Sum('viewers_count'),
            sum_gross_yield_without_vat=Sum('gross_yield_without_vat'),
            session_count=Count('id'),
        )

        qs = qs.annotate(income=F('sum_gross_yield_without_vat') * settings.KINOMANIA_INCOME_FEE)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['filter_form'] = self.filter_form

        if self.filter_form.is_valid() and self.__class__.__name__ == 'MonthlyReportView':
            filter_data = self.filter_form.cleaned_data
            context['was_report_confirmed'] = ConfirmedMonthlyReport.objects.filter(
                month=filter_data['date_range'][0],
                cinema=filter_data['cinemas'],
                film=filter_data['films'],
                dimension=filter_data['dimensions'],
            ).exists()

        if not self.request.GET.get('export_group_by'):
            self.summary_data = self.get_summary_data(self.object_list)

        return context

    def get_summary_data(self, queryset):
        return queryset.aggregate(
                total_sum_gross_yield=Sum('sum_gross_yield'),
                total_sum_viewers_count=Sum('sum_viewers_count'),
                total_sum_gross_yield_without_vat=Sum('sum_gross_yield_without_vat'),
                total_session_count=Sum('session_count'),
                total_income=Sum('income'))


class MainReportView(MonthlyReportView):
    template_name = 'dashboard/main_report.html'
    template_name_ajax = 'dashboard/main_report_table.html'

    table_class = ReportTable
    filter_form_class = FilterReportForm
    session_csv_exporter_class = SessionCsvExporter
    export_report_form_class = ExportReportForm
    group_by = 'date'
    paginate_by = 30
    filter_params = None

    def get_template_names(self):
        return [self.template_name_ajax if self.request.is_ajax() else self.template_name]

    def get(self, request, *args, **kwargs):

        self.filter_form = self.filter_form_class(data=request.GET, user=self.request.user)
        if not self.filter_form.is_valid():
            put_forms_errors_to_messages(request, self.filter_form)

        if 'export_format' in self.request.GET:
            export_form = self.export_report_form_class(
                    data=request.GET, table=self.table_class(data=[]))
            if not export_form.is_valid():
                put_forms_errors_to_messages(request, export_form)
                return HttpResponse(status=404, messages='invalid export form')

            self.export_params = export_form.cleaned_data
            is_export = self.export_params.get('export_group_by')
            if is_export:
                queryset = self.get_queryset()
            else:
                queryset = self.filter_queryset(self.model.objects.all())
            exporter = self.session_csv_exporter_class(export_form, queryset)
            return exporter.export_to_response()
        else:
            self.export_form = self.export_report_form_class(table=self.table_class(data=[]))

        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_to_response(context)

    def filter_queryset(self, queryset):

        user = self.request.user

        queryset = queryset.filter(is_daily_report_finished=True)

        if not user.is_superuser:
            if not user.view_all_reports:
                user_cinemas = set(list(chain_tools(
                    self.request.user.report_cinemas.all(), self.request.user.cinemas.all()
                )))

                list_cinemas = [cinema.id for cinema in user_cinemas]
                queryset = queryset.filter(cinema_hall__cinema__id__in=list_cinemas)

        filter_params = self.filter_form.cleaned_data
        date_range = filter_params.get('date_range')

        if date_range:
            if date_range.lower:
                queryset = queryset.filter(date__gte=date_range.lower)
            if date_range.upper:
                queryset = queryset.filter(date__lte=date_range.upper)

        films = filter_params.get('films')
        if films:
            queryset = queryset.filter(film__in=films)

        cities = filter_params.get('cities')
        if cities:
            queryset = queryset.filter(cinema_hall__cinema__city__in=cities)

        cinemas = filter_params.get('cinemas')
        if cinemas:
            queryset = queryset.filter(cinema_hall__cinema__in=cinemas)

        dimensions = filter_params.get('dimensions')
        if dimensions:
            queryset = queryset.filter(dimension__in=dimensions)

        chains = filter_params.get('chains')
        if chains:
            queryset = queryset.filter(cinema_hall__cinema__chain__in=chains)

        group_by = self.request.GET.get('export_group_by') or self.request.GET.get('group_by')
        self.group_by = group_by if group_by else self.group_by

        return queryset

    def get_queryset(self):

        qs = self.model.objects.all()

        self.ungrouped_qs = self.filter_queryset(qs)

        qs = self.ungrouped_qs.values(self.group_by).annotate(
            sum_gross_yield=Sum('gross_yield'),
            sum_seats_count=Sum('cinema_hall__seats_count'),
            sum_viewers_count=Sum('viewers_count'),
            sum_gross_yield_without_vat=Sum('gross_yield_without_vat'),
            cinema_hall_count=Count('cinema_hall', distinct=True),
            cinema_count=Count('cinema_hall__cinema', distinct=True),
            session_count=Count('id'),
            period=F(self.group_by),
        )

        qs = qs.annotate(
            average_attendance=Case(
                When(sum_seats_count=0, then=0),
                default=F(
                    'sum_viewers_count') * 100 / F('sum_seats_count'), output_field=IntegerField()),
            gross_yield_per_viewer=Case(
                When(sum_viewers_count=0, then=0),
                default=F('sum_gross_yield') / F('sum_viewers_count'), output_field=IntegerField()),
            income=F('sum_gross_yield_without_vat') * settings.KINOMANIA_INCOME_FEE,
        )

        return qs.order_by(self.group_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_superuser or self.request.user.view_all_reports:
            context['export_form'] = self.export_form

        return context

    def get_summary_data(self, queryset):
        summary_data = super().get_summary_data(queryset)
        summary_data.update(**queryset.aggregate(
                    total_sum_seats_count=Sum('sum_seats_count'),
                    total_average_attendance=Avg('average_attendance'),
                    total_gross_yield_per_viewer=Avg('gross_yield_per_viewer')))

        summary_data['total_cinema_count'] = Cinema.objects.filter(
                halls__sessions__in=self.ungrouped_qs).distinct().count()
        summary_data['total_cinema_hall_count'] = CinemaHall.objects.filter(
                sessions__in=self.ungrouped_qs).distinct().count()
        return summary_data

    def render_to_response(self, context, **response_kwargs):
        """Set location header to update windows.location.href after AJAX calls"""
        response = super().render_to_response(context, **response_kwargs)
        response['Location'] = self.request.get_full_path()
        return response


class CinemaListWithMonthlyReportsView(LoginRequiredMixin, SuperuserRequiredMixin, TableMixin, ListView):
    model = Cinema
    paginate_by = 200
    template_name = 'dashboard/cinema_list_with_monthly_reports.html'
    filter_form_class = FilterByMonthForm
    table_class = CinemaWithMonthlyReportsTable
    context_object_name = 'cinemas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if len(self.request.GET):
            context['filter_form'] = self.filter_form_class(data=self.request.GET)
        else:
            context['filter_form'] = self.filter_form_class(
                    initial=get_initial_year_and_month())

        return context

    def get_queryset(self):
        qs = super().get_queryset()

        filter_form = self.filter_form_class(data=self.request.GET)
        if filter_form.is_valid():
            date_range = filter_form.cleaned_data['date_range']
        else:
            date_range = self.filter_form_class.get_date_range_static(
                **get_initial_year_and_month())

        filtered_agreements = AdditionalAgreement.objects.filter(
                active_date_range__overlap=date_range)

        filtered_agreements_ids = filtered_agreements.values_list('id', flat=True)
        confirmed_reports_ids = ConfirmedMonthlyReport.objects.filter(
                month=date_range[0]).values_list('id', flat=True)

        qs = qs.annotate(
            filtered_agreements_count=Count(
                Case(
                    When(agreements__id__in=filtered_agreements_ids, then=F('agreements')),
                    output_field=IntegerField(),
                ),
                distinct=True,

            ),
            confirmed_reports_count=Count(
                Case(
                    When(confirmed_reports__id__in=confirmed_reports_ids,
                         then=F('confirmed_reports')),
                    output_field=CharField(),
                ),
                distinct=True,
            )
        )

        qs = qs.annotate(
            all_reports_confirmed=Case(
                    When(confirmed_reports_count=F('filtered_agreements_count'), then=True),
                    default=Value(False),
                    output_field=BooleanField())
        )

        qs = qs.prefetch_related(Prefetch(
            'agreements',
            queryset=filtered_agreements,
            to_attr='filtered_agreements'))

        return qs.select_related('city').order_by('all_reports_confirmed')


class CinemaListView(DateViewMixin, LoginRequiredMixin, TableMixin, ListView):
    model = Cinema
    paginate_by = 200
    template_name = 'dashboard/cinema_list.html'
    context_object_name = 'cinemas'
    table_class = CinemaTable
    max_days_ago = 90

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and request.user.cinemas.count() == 1:

            if '/main-cinema-list/' in request.META.get('HTTP_REFERER'):  # dirty hack, sorry

                create_session_url = reverse('create_session', kwargs={
                    'pk': request.user.cinemas.first().pk,
                    'date': kwargs['date']
                })
                return redirect(create_session_url)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.request.user.all_cinemas.filter(
                created__lte=self.date + timedelta(days=1)).annotate(hall_count=Count('halls'))
        qs = qs.annotate_finished_by_date(self.date)
        return qs.select_related('city').order_by('is_daily_report_finished')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = now().date()

        users_cinemas = self.request.user.all_cinemas
        unfinished_reports_dates = []
        finished_reports_dates = []
        no_agreements_dates = []
        for days in range(self.max_days_ago + 1):
            date = today - timedelta(days)

            cinemas_filtered_by_date_count = len(set(AdditionalAgreement.objects.filter(
                cinema__in=users_cinemas).filter_by_date(date).values_list('cinema', flat=True)))

            if not cinemas_filtered_by_date_count:
                no_agreements_dates.append(date)
            else:
                finished_reports_count = users_cinemas.filter(finished_on_dates__date=date).count()

                if finished_reports_count != cinemas_filtered_by_date_count:
                    unfinished_reports_dates.append(date)
                else:
                    finished_reports_dates.append(date)

        context['unfinished_reports_dates'] = unfinished_reports_dates
        context['finished_reports_dates'] = finished_reports_dates
        context['no_agreements_dates'] = no_agreements_dates

        return context


class CreateSessionView(SessionMixin, CreateView):
    form_valid_message = 'Сеанс успешно добавлен'
    submit_text = 'Принять данные по сеансу'

    def get_form_action(self):
        return self.get_create_session_url()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.date = self.date
        self.object.creator = self.request.user
        self.object.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cinema_sessions = Session.objects.filter(cinema_hall__cinema__id=self.kwargs['pk'])
        today_sessions_exists = cinema_sessions.filter(date=self.date).exists()
        yesterday_sessions_exists = cinema_sessions.filter(
                date=self.date - timedelta(days=1)).exists()

        if not today_sessions_exists and yesterday_sessions_exists:
            context['copy_yesterday_sessions_form'] = forms.Form()
        return context


class UpdateSessionView(SessionMixin, UpdateView):
    form_valid_message = 'Сеанс успешно обновлен'
    submit_text = 'Обновить сеанс'

    def get_form_action(self):
        return reverse(
                'update_session',
                kwargs={
                    'pk': self.kwargs['pk'],
                    'session_pk': self.kwargs['session_pk'],
                    'date': self.date_str})

    def get_object(self, queryset=None):
        session = get_object_or_404(Session, pk=self.kwargs['session_pk'])
        if session.is_daily_report_finished and not self.request.user.is_superuser:
            raise Http404()
        return session


class SendUpdateSessionRequestView(SessionMixin, UpdateView):

    form_valid_message = ('Администратору КиноМании было отправлено '
                          'электронное письмо об изменении сеанса')
    submit_text = 'Отправить запрос на обновление сеанса'
    email_template = 'emails/request_session_update.html'

    def get_form_action(self):
        return reverse(
                'send_update_session_request',
                kwargs={
                    'pk': self.kwargs['pk'],
                    'session_pk': self.kwargs['session_pk'],
                    'date': self.date_str})

    def get_object(self):
        return get_object_or_404(Session, pk=self.kwargs['session_pk'])

    def session_table_title(self):
        return 'Вы хотите запросить изменение следующего сеанса:'

    def get_queryset(self):
        return super().get_queryset().filter(id=self.object.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table'].exclude = ('update_link', 'remove_form', 'send_update_request_link')
        return context

    def form_valid(self, form):
        # TODO validate if at least one field was changed?
        session = get_object_or_404(Session, pk=self.kwargs['session_pk'])

        SessionUpdateRequest.objects.create(session=self.object, data=form.data)
        self.messages.success(self.get_form_valid_message(), fail_silently=False)

        mail_admins(
            subject='Запрос на обновление сеанса',
            message='Новый запрос на обновление сеанса',
            html_message=self.get_email_html(session=session, form_data=form.cleaned_data))

        return HttpResponseRedirect(self.get_create_session_url())

    def get_email_html(self, session, form_data):

        cinema = session.cinema_hall.cinema
        email_context = dict(
            username=self.request.user.username,
            cinema_name=cinema.name,
            city_name=cinema.city.name,
            comment=form_data.get('update_request_comment'),
        )

        email_context['session_admin_url'] = self.request.build_absolute_uri(
                reverse('admin:common_session_change', args=(session.id, )))

        requested_updates = []
        for field_name, new_value in form_data.items():
            old_value = getattr(session, field_name, None)
            if old_value and new_value != old_value:
                update = dict(
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value)
                requested_updates.append(update)

        email_context['requested_updates'] = requested_updates

        return render_to_string(self.email_template, email_context)


@login_required
@require_http_methods(['POST'])
def delete_session(request, session_pk):
    user = request.user

    session = get_object_or_404(Session, pk=session_pk)
    if not user.is_superuser and session.is_daily_report_finished:
        return HttpResponse(status=403)

    if session.cinema_hall.cinema not in user.all_cinemas:
        return HttpResponse(status=403)

    session.delete()

    messages.success(request, 'Сеанс был удалён')

    return HttpResponseRedirect(get_create_session_ulr(session.cinema_hall.cinema, session.date))


class BaseCinemaActionView(LoginRequiredMixin, DateViewMixin, CinemaPkMixin, View):

    def post(self, request, *args, **kwargs):
        if self.cinema not in request.user.all_cinemas:
            return HttpResponse(status=403)


class SetDailyReportFinishedView(BaseCinemaActionView):

    success_message = 'Отчёт за {} успешно отмечен как завершённый.'
    error_message = ('Нет ни одного сеанса за указанную дату. Необходимо создать минимум один '
                     'сеанс с нулевыми значениями чтобы вы могли завершить подачу отчёта.')

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        cinema = self.cinema

        if not Session.objects.filter(cinema_hall__cinema=cinema, date=self.date).exists():
            messages.error(request, self.error_message)
            return HttpResponseRedirect(get_create_session_ulr(cinema, self.date))

        current_cinema_agreements = AdditionalAgreement.objects.filter_by_date(
            self.date).filter(cinema=cinema)

        agreements_with_sessions_count = len(set(
            Session.objects.filter(additional_agreement__in=current_cinema_agreements,
                                   date=self.date).values_list('additional_agreement', flat=True)))

        if agreements_with_sessions_count < current_cinema_agreements.count():
            messages.error(request, 'Заполнены сеансы не по всем доп соглашениям')
            return HttpResponseRedirect(get_create_session_ulr(cinema, self.date))

        cinema.set_report_finished(date=self.date)
        messages.success(request, self.success_message.format(self.date_str))
        return HttpResponseRedirect(reverse('cinema_list', kwargs=dict(date=self.date_str)))


class SetDailyReportUnfinishedView(BaseCinemaActionView):

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)

        FinishedCinemaReportDate.objects.filter(cinema=self.cinema, date=self.date).delete()

        create_session_url = reverse('create_session', kwargs={
            'pk': self.cinema.id,
            'date': self.date_str})

        return HttpResponseRedirect(create_session_url)


class CreateConfirmedMonthlyReportView(LoginRequiredMixin, FormMixin, ProcessFormView):
    form_class = FilterMonthlyReportForm
    success_message = 'Расчетный бланк за " {}" подтвержден'

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['user'] = self.request.user
        return form_kwargs

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER', '/'))

    def form_valid(self, form):
        cinema = form.cleaned_data['cinemas']
        film = form.cleaned_data['films']
        dimension = form.cleaned_data['dimensions']
        month_date = form.cleaned_data['date_range'][0]

        sessions = Session.objects.filter(
                cinema_hall__cinema=cinema,
                date__year=month_date.year,
                date__month=month_date.month,
                film=film,
                dimension=dimension)

        previous_url = self.request.META.get('HTTP_REFERER', '/')

        if not sessions.exists():
            messages.error(self.request, 'Нет ни одного сеанса за указанный месяц.')
            return HttpResponseRedirect(previous_url)

        if sessions.filter(additional_agreement=None).exists():
            messages.error(self.request, 'Нет доп соглашения соответствующего сеансу {}'.format(
                    sessions.filter(additional_agreement=None).first()))
            return HttpResponseRedirect(previous_url)

        if sessions.filter(is_daily_report_finished=False).exists():
            unfinished_date = sessions.filter(is_daily_report_finished=False).first().date
            error_message = 'Дневной отчёт за {} был создан, но не отмечен как завершённый.'.format(
                    date_format(unfinished_date))
            messages.error(self.request, error_message)
            return HttpResponseRedirect(previous_url)

        try:
            ConfirmedMonthlyReport.objects.create(
                cinema=cinema,
                film=film,
                dimension=dimension,
                month=month_date,
                creator=self.request.user,
            )
        except IntegrityError:
            pass

        messages.success(self.request, self.success_message.format(MONTHS[month_date.month - 1]))
        return HttpResponseRedirect(previous_url)


class CopyYesterdaysSessionsView(DateViewMixin, LoginRequiredMixin, View):

    @transaction.atomic
    def post(self, request, pk, date):
        cinema_pk = self.kwargs['pk']

        yesterday_sessions = Session.objects.filter(
                cinema_hall__cinema__id=cinema_pk, date=self.date-timedelta(days=1))

        for session in yesterday_sessions:
            session.pk = None
            session.date = self.date
            session.viewers_count = 0
            session.invitations_count = 0
            session.gross_yield = 0
            session.is_daily_report_finished = False
            session.save()

        create_session_url = reverse('create_session', kwargs={
            'pk': cinema_pk,
            'date': self.date_str})

        return HttpResponseRedirect(create_session_url)


class CreateFeedbackView(LoginRequiredMixin, FormValidMessageMixin, CreateView):
    template_name = 'dashboard/create_feedback.html'
    form_class = CreateFeedbackForm
    success_url = reverse_lazy('create_feedback')
    form_valid_message = 'Ваш фидбек был отправлен администратору КиноМании'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.sender = self.request.user
        self.object.receivers_emails = ','.join(settings.FEEDBACK_RECEIVERS_EMAILS)[:255]
        self.object.save()

        send_mail(subject='новый фидбек от {}'.format(self.request.user.email),
                  message=form.cleaned_data['text'],
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=settings.FEEDBACK_RECEIVERS_EMAILS)
        return super().form_valid(form)


class SendDailyReportEmailView(SuperuserRequiredMixin, DateViewMixin, View):
    form_valid_message = 'Напоминание было отправлено.'

    def post(self, request, pk, date):
        url = reverse('cinema_list', kwargs=dict(date=self.date_str))

        if self.date > now().date():
            messages.error(self.request, 'Вы не можете послать письмо для будущих дат.')
            return HttpResponseRedirect(self.get_success_url())

        try:
            cinema = Cinema.objects.get(id=pk)
        except Cinema.DoesNotExist:
            messages.error(self.request, 'Нет кинотеатра с указанным pk.')
            return HttpResponseRedirect(self.get_success_url())

        if cinema not in self.request.user.all_cinemas:
            messages.error(self.request, 'Вы не можете послать письмо по этому кинотеатру.')
            return HttpResponseRedirect(self.get_success_url())

        if cinema.responsible_for_daily_reports.count() == 0 and cinema.access_to_reports.count() == 0:
            messages.error(self.request,
                           'Нет ответственного за дневные отчёты для этого кинотеатра.')
            return HttpResponseRedirect(self.get_success_url())

        missing_report_links = {self.date_str: build_full_url(url)}

        user_cinemas = set(list(chain_tools(
            self.request.user.report_cinemas.all(), self.request.user.cinemas.all()
        )))

        users_email = [user.email for user in user_cinemas]
        send_mail(
            subject='КиноМания: незаполненные отчёты по кинотеатрам',
            from_email=settings.DEFAULT_FROM_EMAIL,
            message='',
            recipient_list=users_email,
            html_message=render_to_string('emails/daily_report_notification.html',
                                          dict(missing_report_links=missing_report_links))
        )
        messages.success(self.request, self.form_valid_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('cinema_list', kwargs={'date': self.date_str})


class SendMonthlyReportEmailView(SuperuserRequiredMixin, FormMixin, ProcessFormView):

    form_valid_message = 'Напоминание было отправлено'
    form_class = SendMonthlyReportEmailForm

    def form_valid(self, form):
        cinema = form.cleaned_data['cinema']
        month = form.cleaned_data['month']
        year = form.cleaned_data['year']

        if cinema.access_to_reports.count() > 0:
            month_str = MONTHS[month - 1]
            email_message_html = ('Вы не подтвердили расчётный бланк за {month} {year}. '
                                  'Вы можете подтвердить бланки перейдя по ссылке'
                                  ' {confirm_report_url}')

            confirm_report_url = '{url}?month={month}&year={year}'.format(
                    url=reverse('confirm_monthly_report'),
                    month=month,
                    year=year)

            email_message = email_message_html.format(
                month=month_str,
                year=year,
                confirm_report_url=self.request.build_absolute_uri(confirm_report_url))

            users_email = [user.email for user in cinema.access_to_reports.all()]
            send_mail(
                subject='Киномания: не сданы расчётные бланки за {}'.format(month_str),
                from_email=settings.DEFAULT_FROM_EMAIL,
                message=email_message,
                recipient_list=users_email
            )

        messages.success(self.request, self.form_valid_message)

        return HttpResponseRedirect('{url}?month={month}&year={year}'.format(
                    url=reverse('cinema_list_with_monthly_reports'),
                    month=month,
                    year=year))

    def form_invalid(self, form):
        put_forms_errors_to_messages(self.request, form)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('cinema_list_with_monthly_reports')

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.get_success_url())


class ChangeSessionsDateView(LoginRequiredMixin, FormMixin, CinemaPkMixin,
                             DateViewMixin, ProcessFormView):

    form_class = ChangeSessionsDateForm
    form_valid_message = 'Дата успешно изменена'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER', '/'))

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['cinema'] = self.cinema
        form_kwargs['change_date_from'] = self.date
        return form_kwargs

    def form_valid(self, form):
        self.change_date_to = form.cleaned_data['change_date_to']

        """Method save() must be called to mail admin if additional agreement doesn't exists"""
        for session in Session.objects.filter(cinema_hall__cinema=self.cinema, date=self.date):
            session.date = self.change_date_to
            session.save()

        messages.success(self.request, self.form_valid_message)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        put_forms_errors_to_messages(self.request, form)
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER', '/'))

    def get_success_url(self):
        return reverse(
                'create_session',
                kwargs=dict(
                    pk=self.kwargs['pk'],
                    date=datetime.strftime(self.change_date_to, settings.DATE_URL_INPUT_FORMAT),
                )
            )


class CountDown(ListView):
    template_name = 'admin/not_working_site.html'

    def get_queryset(self):
        return []
