import os
import zipfile
from io import BytesIO

from django.http import HttpResponse
from django.contrib import admin
from django.db.models import Count
from django.templatetags.static import static

from common import models
from common.admin_forms import CinemaAdminForm, CinemaHallInlineForm, CinemaHallInlineFormSet, \
    AdditionalAgreementAdminForm, SessionAdminForm, GeneralContractAdminForm
from kinomania.admin_utils import ChangeLinkMixin


@admin.register(models.City)
class CityAdmin(ChangeLinkMixin, admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', )


@admin.register(models.Dimension)
class DimensionAdmin(ChangeLinkMixin, admin.ModelAdmin):
    list_display = ('id', 'name')


class GeneralContractChainInline(admin.TabularInline):
    model = models.GeneralContract
    extra = 1
    exclude = ['cinema']


@admin.register(models.Chain)
class ChainAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cinema_count', 'contract_count')
    search_fields = ('name', )
    inlines = [GeneralContractChainInline, ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(cinema_count=Count('cinemas'))

    def cinema_count(self, obj):
        return obj.cinema_count

    def contract_count(self, obj):
        return obj.contracts.count()


class CinemaHallInline(admin.TabularInline):
    model = models.CinemaHall
    form = CinemaHallInlineForm
    extra = 1
    formset = CinemaHallInlineFormSet


class GeneralContractCinemaInline(admin.TabularInline):
    model = models.GeneralContract.cinemas.through
    extra = 1
    exclude = ['chain']
    verbose_name = 'Генеральный контракт'
    verbose_name_plural = 'Генеральные контракты'
    raw_id_fields = ['generalcontract', ]


class ContactInformationInline(admin.TabularInline):
    model = models.ContactInformation
    extra = 1


@admin.register(models.Cinema)
class CinemaAdmin(admin.ModelAdmin):
    form = CinemaAdminForm
    list_display = ('id', 'name', 'city', 'chain', 'created', 'vat')
    list_filter = ('chain', 'city', 'vat')
    search_fields = ('id', 'name', 'chain__name')
    fieldsets = (
        (None, {'fields': ('name', 'city', 'chain', 'halls_count')}),
        ('Контракт и пользователи', {'fields': ('chain_contract', 'responsible_for_daily_reports',
                                                'access_to_reports', 'vat')}),
    )
    inlines = [
        GeneralContractCinemaInline, CinemaHallInline, ContactInformationInline
    ]

    class Media:
        css = {
            'all': (static('/admin/css/change_form_inline.css'), )
        }

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('city', 'chain')


@admin.register(models.GeneralContract)
class GeneralContractAdmin(admin.ModelAdmin):
    form = GeneralContractAdminForm
    list_display = ('id', 'SBR_code', 'number', 'active_from', 'chain', 'contractor_full_name')
    search_fields = ('SBR_code', 'number', 'contractor_full_name', 'chain__name', 'cinemas__name')
    list_filter = ('chain', 'active_from')
    raw_id_fields = ('chain', )


@admin.register(models.Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',  'code', 'release_date', 'created')
    list_filter = ('dimensions', )
    search_fields = ('name', 'code')


class CinemaFilter(admin.SimpleListFilter):
    title = 'Кинотеатр'
    parameter_name = 'cinema'

    def lookups(self, request, model_admin):
        cinemas = models.Cinema.objects.select_related('city', 'chain')
        lookups = []
        for cinema in cinemas:
            cinema_repr = '{} ({})'.format(cinema.name, cinema.city.name)
            if cinema.chain:
                cinema_repr = '{}: {}'.format(cinema.chain.name, cinema_repr)
            lookups.append((cinema.id, cinema_repr))
        return lookups

    def queryset(self, request, queryset):
        cinema_id = self.value()
        if cinema_id:
            return queryset.filter(cinema_id=self.value())

        return queryset


@admin.register(models.CinemaHall)
class CinemaHallAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'seats_count', 'cinema', 'cinema_chain')
    list_filter = (CinemaFilter, )
    search_fields = ['name', 'cinema__name', 'cinema__city__name', 'cinema__chain__name']

    def cinema_chain(self, obj):
        if obj.cinema.chain_id:
            return obj.cinema.chain.name
        return '-'
    cinema_chain.short_description = 'Сеть'


@admin.register(models.Session)
class SessionAdmin(ChangeLinkMixin, admin.ModelAdmin):
    form = SessionAdminForm
    list_per_page = 30
    list_display = (
        'film_name',
        'chain_name',
        'cinema_name',
        'cinema_hall_name',
        'date',
        'time',
        'dimension',
        'viewers_count',
        'max_price',
        'gross_yield',
        'created',
        'is_original_language',
        'vat',
        'is_daily_report_finished',
    )
    date_hierarchy = 'date'
    list_filter = ('date', 'dimension', 'vat')
    readonly_fields = (
        'gross_yield_without_vat',
        'week',
        'month',
        'creator',
        'xls_raw_data',
        'xls_session_report',
    )
    raw_id_fields = ('additional_agreement', )

    def cinema_name(self, obj):
        return obj.cinema_name
    cinema_name.short_description = 'кинотеатр'

    def film_name(self, obj):
        film_name = obj.film.name
        return (film_name[:20] + '..') if len(film_name) > 20 else film_name
    film_name.short_description = 'фильм'

    def cinema_hall_name(self, obj):
        cinema_hall_name = obj.cinema_hall.name
        return (cinema_hall_name[:20] + '..') if len(cinema_hall_name) > 20 else cinema_hall_name
    cinema_hall_name.short_description = 'зал'

    def chain_name(self, obj):
        chain = obj.cinema_hall.cinema.chain
        return chain.name if chain else ''
    chain_name.short_description = 'сеть'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cinema_hall__cinema__chain', 'film', 'dimension')


@admin.register(models.AdditionalAgreement)
class AdditionalAgreementAdmin(admin.ModelAdmin):
    list_display = ('one_c_number', 'contract', 'film', 'dimension', 'active_date_range_from',
                    'active_date_range_to', 'vat', 'created', )
    list_filter = ('dimension', 'vat', 'film')
    save_as = True
    form = AdditionalAgreementAdminForm
    search_fields = ('film__name', 'cinema__name', 'contract__SBR_code', 'contract__number',
                     'contract__chain__name', 'one_c_number')

    def active_date_range_from(self, obj):
        return obj.active_date_range_from

    def active_date_range_to(self, obj):
        return obj.active_date_range_to

    active_date_range_from.short_description = 'Активно с'
    active_date_range_to.short_description = 'Активно по'


@admin.register(models.ContactInformation)
class ContactInformationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'cinema', 'email', 'phone_number')
    list_filter = ('cinema__city', 'title', 'cinema__chain')
    search_fields = ('title', 'email', 'cinema__name', 'cinema__chain__name')


@admin.register(models.XlsSessionsReport)
class XlsSessionsReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'xls_filename')


@admin.register(models.XlsReportsUpload)
class XlsReportsUploadAdmin(admin.ModelAdmin):
    change_link_description = 'Просмотреть'
    list_display = ('id', 'created', 'is_successful', 'city')

    def has_add_permission(self, request):
        return False


@admin.register(models.FinishedCinemaReportDate)
class FinishedCinemaReportDateAdmin(admin.ModelAdmin):
    raw_id_fields = ('cinema', )
    list_display = ('id', 'cinema', 'date', 'created', 'cinema_chain')
    search_fields = ('cinema__name', 'cinema__responsible_for_daily_reports__email')

    def cinema_chain(self, obj):
        return obj.cinema.chain
    cinema_chain.short_description = 'Сеть'


@admin.register(models.SessionUpdateRequest)
class SessionUpdateRequestAdmin(admin.ModelAdmin):
    raw_id_fields = ('session', )
    list_display = ('id', 'created', 'session_id')
    fields = ('session', )


@admin.register(models.Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'sender', 'text')


@admin.register(models.ConfirmedMonthlyReport)
class ConfirmedMonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('cinema', 'film', 'dimension', 'month_str')

    def month_str(self, obj):
        return obj.month_str
    month_str.short_description = 'Месяц'

@admin.register(models.BackupFile)
class BackupFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'start', 'end', 'backup_file_path')
    list_display_links = None
    actions = ['export']
    
    def has_add_permission(self, request):
        return False

    def export(self, request, queryset):
        # Files (local path) to put in the .zip
        # FIXME: Change this (get paths from DB etc)
        filenames = queryset.values_list('backup_file_path', flat=True)

        # Folder name in ZIP archive which contains the above files
        # E.g [thearchive.zip]/somefiles/file2.txt
        # FIXME: Set this to something better
        zip_filename = "backups.zip"

        # Open StringIO to grab in-memory ZIP contents
        s = BytesIO()

        # The zip compressor
        zf = zipfile.ZipFile(s, "w")

        for fpath in filenames:
            # Calculate path for file in zip
            fdir, fname = os.path.split(fpath)
            # Add file, at correct path
            zf.write(fpath, fname)

            # Must close zip for all contents to be written
        zf.close()

        # Grab ZIP file from in-memory, make response with correct MIME-type
        resp = HttpResponse(s.getvalue(), content_type="application/x-zip-compressed")
        # ..and correct content-disposition
        resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
        return resp

    export.short_description = "Экспорт выбранных"

class BackupAdmin(admin.ModelAdmin):
    change_list_template = 'smuggler/change_list.html'

admin.register(BackupAdmin)





