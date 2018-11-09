from datetime import datetime

from braces.views import FormValidMessageMixin
from braces.views._access import LoginRequiredMixin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django_tables2 import RequestConfig

from common.forms import SessionForm, ChangeSessionsDateForm
from common.models import Cinema, Session
from common.tables import SessionTable


class AccessToReportMixin:

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated():
            return self.handle_no_permission(request)

        return super().dispatch(request, *args, **kwargs)


class CinemaPkMixin:
    def dispatch(self, request, *args, **kwargs):

        self.cinema = get_object_or_404(Cinema, pk=self.kwargs['pk'])
        if self.cinema not in request.user.all_cinemas:
            raise Http404('Нет такого кинотеатра')

        return super().dispatch(request, *args, **kwargs)


class TableMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table = self.table_class(data=self.get_queryset(), request=self.request)
        RequestConfig(self.request, paginate={'per_page': self.paginate_by}).configure(table)
        context['table'] = table
        return context


class DateViewMixin:
    def dispatch(self, request, *args, **kwargs):
        try:
            self.date = datetime.strptime(kwargs['date'], settings.DATE_URL_INPUT_FORMAT).date()
        except ValueError:
            raise ValidationError('Invalid date')

        self.date_str = kwargs['date']

        return super().dispatch(request, *args, **kwargs)


class SessionMixin(LoginRequiredMixin, DateViewMixin, CinemaPkMixin,
                   FormValidMessageMixin, TableMixin):
    template_name = 'dashboard/create_or_update_session.html'
    model = Session
    form_class = SessionForm
    table_class = SessionTable
    paginate_by = 20
    context_object_name = 'sessions'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cinema'] = self.cinema
        kwargs['user'] = self.request.user
        kwargs['date'] = self.date
        kwargs['submit_text'] = self.submit_text
        kwargs['form_action'] = self.get_form_action()
        kwargs['create_session_url'] = self.get_create_session_url()
        kwargs['view_name'] = self.request.resolver_match.url_name
        return kwargs

    def get_success_url(self):
        return self.get_create_session_url()

    def get_queryset(self):
        qs = Session.objects.filter(date=self.date)
        qs = qs.filter(cinema_hall__cinema__id=self.kwargs['pk'])

        self.summary_data = qs.aggregate(
                total_invitations_count=Sum('invitations_count'),
                total_viewers_count=Sum('viewers_count'),
                total_gross_yield=Sum('gross_yield'))

        qs = qs.select_related('cinema_hall__cinema', 'film', 'dimension')

        if 'order-by-time' in self.request.GET:
            return qs.order_by('time')

        return qs.order_by('film', 'dimension', 'time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cinema'] = self.cinema
        context['sessions'] = self.get_queryset()
        context['user_is_allowed'] = False
        if self.request.user in self.cinema.access_to_reports.all():
            context['user_is_allowed'] = True
        if self.request.user in self.cinema.responsible_for_daily_reports.all():
            context['user_is_allowed'] = True
        if self.request.user.is_superuser:
            context['user_is_allowed'] = True
        context['table'].exclude = ('date', )
        context['is_daily_report_finished'] = self.cinema.is_report_finished(self.date)
        if not context['is_daily_report_finished']:
            context['last_form'] = self.get_last_form()
            context['change_session_form'] = ChangeSessionsDateForm(
                    change_date_from=self.date, cinema=self.cinema,
                    initial={'change_date_to': self.date})

            if not context['user_is_allowed']:
                context['table'].exclude = ('delete', 'edit')

        return context

    def get_last_form(self):
        from common.views import CreateSessionView

        if isinstance(self, CreateSessionView):
            last_created_session = Session.objects.filter(
                cinema_hall__cinema=self.cinema, creator=self.request.user).order_by(
                    'created').last()

            if last_created_session:
                last_created_session.time = None
                last_created_session.viewers_count = None
                last_created_session.gross_yield = None

                kwargs = self.get_form_kwargs()
                kwargs['instance'] = last_created_session
                return self.form_class(**kwargs)

    def get_create_session_url(self):
        return reverse(
                'create_session',
                kwargs=dict(
                    pk=self.kwargs['pk'],
                    date=self.date_str,
                )
            )

    def session_table_title(self):
        return 'Сеансы в кинотеатре \'{}\' ({})'.format(
                self.cinema.name,
                self.cinema.city.name)
