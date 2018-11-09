from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.actions import delete_selected
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Case, BooleanField, CharField
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from common.models import Cinema, FinishedCinemaReportDate, Chain, ContactInformation, \
    AdditionalAgreement
from kinomania.admin_utils import ChangeLinkMixin
from users.admin_forms import UserTypeChoices, CustomUserCreationForm, CustomUserChangeForm, \
    USER_ACCESS_TYPE_CHOICES
from users.models import User


def send_daily_reports_emails(modeladmin, request, queryset):
    queryset.distinct().send_daily_reports_emails(is_email_async=True)
send_daily_reports_emails.short_description = 'Послать напоминание о незаполненном отчёте'


class DateFilter(admin.SimpleListFilter):
    title = 'Дата (сдан ли отчёт за предыдущую дату)'
    parameter_name = 'date'
    template = 'admin/date_list_filter.html'

    def lookups(self, request, model_admin):
        return [['fake', 'fake']]

    def queryset(self, request, queryset):
        return queryset


class AccessTypeFilter(admin.SimpleListFilter):
    title = 'Тип доступа'
    parameter_name = 'access_type'

    def lookups(self, request, model_admin):
        return [(k, v) for (k, v) in USER_ACCESS_TYPE_CHOICES.items()]

    def queryset(self, request, queryset):
        return queryset


class DailyReportFishedFilter(admin.SimpleListFilter):
    title = 'Дневной отчёт заполнен'
    parameter_name = 'report_finished'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Да'),
            ('false', 'Нет'))

    def queryset(self, request, queryset):
        return queryset


@admin.register(User)
class CustomUserAdmin(ChangeLinkMixin, UserAdmin):
    add_form_template = 'admin/users/user/add_form.html'
    add_form = CustomUserCreationForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', )}),
        (_('Permissions'), {'fields': ('is_active', 'is_superuser', 'view_all_reports')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'access_type',
                'chain',
                'chain_cinema_filter',
                'cinemas',
                'password1',
                'password2'
            )
        }),
    )
    actions = [delete_selected, send_daily_reports_emails]

    form = CustomUserChangeForm

    list_display = ('username', 'email', 'is_superuser', 'cinema_chain', 'cinema_list',
                    'is_daily_report_finished', 'access_type')

    list_filter = (DateFilter, DailyReportFishedFilter, AccessTypeFilter,
                   'is_superuser', 'is_active')

    filter_horizontal = []
    ordering = ('email', )

    def get_search_results(self, request, queryset, search_term):
        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(cinemas__name__icontains=search_term) |
                Q(report_cinemas__name__icontains=search_term)
            ).distinct()
        return queryset, False

    def get_queryset(self, request):
        qs = User.objects.all()

        date = request.GET.get('date')
        if date:
            try:
                date = datetime.strptime(date, settings.DATE_URL_INPUT_FORMAT).date()
            except ValueError:
                pass
        if not date:
            date = now().date()
        date = date - timedelta(days=1)
        self.date = date

        finished_cinemas_ids = FinishedCinemaReportDate.objects.filter(
                date=date).values_list('cinema_id', flat=True)
        users_with_finished_reports_ids = qs.filter(
                cinemas__id__in=finished_cinemas_ids).values_list('id', flat=True)

        qs = qs.annotate(
                is_daily_report_finished=Case(
                    When(id__in=users_with_finished_reports_ids, then=True),
                    default=Value(False),
                    output_field=BooleanField()))

        report_finished = request.GET.get('report_finished')
        if report_finished:
            if report_finished == 'true':
                qs = qs.filter(is_daily_report_finished=True)
            else:
                qs = qs.filter(is_daily_report_finished=False)

        daily_report_users_ids = User.objects.exclude(cinemas=None).values_list('id', flat=True)
        main_report_users_ids = User.objects.exclude(report_cinemas=None).values_list(
                'id', flat=True)
        qs = qs.annotate(
            access_type=Case(
                When(Q(id__in=daily_report_users_ids) & Q(id__in=main_report_users_ids),
                     then=Value(UserTypeChoices.FULL)),
                When(id__in=main_report_users_ids, then=Value(UserTypeChoices.VIEW_REPORT)),
                When(view_all_reports=True, then=Value(UserTypeChoices.VIEW_ALL_REPORTS)),
                default=Value('-'),
                output_field=CharField()))
        access_type = request.GET.get('access_type')
        if access_type:
            if access_type == UserTypeChoices.FULL:
                qs = qs.filter(access_type='full')
            elif access_type == UserTypeChoices.VIEW_ALL_REPORTS:
                qs = qs.filter(view_all_reports=True)
            else:
                qs = qs.filter(
                        access_type__in=(UserTypeChoices.FULL, UserTypeChoices.VIEW_REPORT))

        cinemas = Cinema.objects.annotate_finished_by_date(date)
        cinemas = cinemas.select_related('city').prefetch_related(
                Prefetch(
                    'contacts',
                    queryset=ContactInformation.objects.filter(title='администратор'),
                    to_attr='admin_contacts'))
        qs = qs.prefetch_related(Prefetch('cinemas',
                                          queryset=cinemas,
                                          to_attr='annotated_cinemas'))

        return qs.order_by(self.ordering[0])

    def is_daily_report_finished(self, obj):
        if obj.is_daily_report_finished:
            return 'Да'

        if AdditionalAgreement.objects.filter(
                cinema__in=obj.cinemas.all()).filter_by_date(self.date).exists():
            return 'Нет'

        return '-'  # no active AdditionalAgreement
    is_daily_report_finished.short_description = 'Отчёт сдан'

    def cinema_chain(self, obj):
        chain = Chain.objects.filter(responsible_for_daily_reports=obj).first() or \
                Chain.objects.filter(access_to_reports=obj).first()
        if chain:
            url = reverse('admin:common_chain_change', args=(chain.id, ))
            return '<a href="{}">{}</a>'.format(url, chain.name)
    cinema_chain.short_description = 'Сеть'
    cinema_chain.allow_tags = True

    def access_type(self, obj):
        if obj.access_type in USER_ACCESS_TYPE_CHOICES:
            return USER_ACCESS_TYPE_CHOICES[obj.access_type]
        return '-'
    access_type.short_description = 'Тип доступа'

    def cinema_list(self, obj):
        if obj.is_superuser:
            return '-'

        html = ''
        for cinema in obj.annotated_cinemas:
            url = reverse('admin:common_cinema_change', args=(cinema.id, ))

            if cinema.is_daily_report_finished:
                icon_value = 'yes'
            elif AdditionalAgreement.objects.filter(
                    cinema=cinema).filter_by_date(self.date).exists():
                icon_value = 'no'
            else:
                continue

            icon = '<img src="/static/admin/img/icon-{}.svg">'.format(icon_value)

            html += ('<a href="{cinema_admin_url}">'
                     '{cinema_name} ({city}) {phone} {icon}</a><br>').format(
                    cinema_admin_url=url,
                    cinema_name=cinema.name,
                    city=cinema.city.name,
                    phone=cinema.admin_contacts[0].phone_number if cinema.admin_contacts else '',
                    icon=icon)

        return html

    cinema_list.short_description = 'Кинотеатры'
    cinema_list.allow_tags = True


admin.site.unregister(Group)
