import os.path
import tempfile

import datetime
from braces.views import SuperuserRequiredMixin
from dal import autocomplete
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView, ListView
from django.db.models import Q
from django.core.cache import cache
from django.contrib import messages
from django.conf import settings
from django.utils.timezone import now, localtime
from django.contrib.admin.helpers import AdminForm
from django.contrib.auth.decorators import user_passes_test
from django.utils.translation import ugettext_lazy as _

from smuggler.forms import ImportForm
from smuggler import settings as smuggler_settings
from smuggler.utils import save_uploaded_file_on_disk

from django_celery_beat.models import PeriodicTask, CrontabSchedule

from common.admin_forms import UploadXLSReportsForm, TimeForm
from common.models import City, Chain, XlsSessionsReport, XlsReportsUpload, Cinema, Film, GeneralContract, TimeBackup, BackupFile
from users.models import User
from celery_tasks import app as celery_app, make_dump, async_mail_admins, load_dump
from celery.schedules import crontab



class UserAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = User.objects.all()
        if self.q:
            qs = qs.filter(email__istartswith=self.q)

        return qs


class FilmAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Film.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class GeneralContractAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = GeneralContract.objects.all()
        if self.q:
            qs = qs.filter(Q(contractor_full_name__istartswith=self.q) |
                           Q(SBR_code__istartswith=self.q) |
                           Q(number__istartswith=self.q))

        return qs


class CityAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = City.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class ChainAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Chain.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class CinemaAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Cinema.objects.all()

        chain_id = self.request.COOKIES.get('chainid') or None
        qs = qs.filter(chain_id=chain_id)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class AllCinemasAutocompleteView(SuperuserRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Cinema.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class UploadXLSReportsView(SuperuserRequiredMixin, FormView):
    form_class = UploadXLSReportsForm
    template_name = 'admin/upload_xls_reports.html'

    def form_valid(self, form):
        report_upload = XlsReportsUpload.objects.create(city=form.cleaned_data.get('city'))

        for _file in form.cleaned_data['xls_folder_path']:
            XlsSessionsReport.objects.create(xls_file=_file,
                                             report_upload=report_upload,
                                             xls_filename=_file.name)
        return HttpResponseRedirect(
                reverse('admin:common_xlsreportsupload_change', args=(report_upload.id, )))


class BackupSystemView(SuperuserRequiredMixin, ListView):
    template_name = 'admin/common/backup/backup_page.html'

    def get_queryset(self):
        return


class TimeView(SuperuserRequiredMixin, FormView):
    form_class = TimeForm
    template_name = 'admin/common/backup/time_page.html'

    def form_valid(self, form):
        if form.is_valid():
            time_back = TimeBackup.objects.first()
            time_back.start = form.cleaned_data['start']
            time_back.save()
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=time_back.start.strftime('%M'),
                hour=time_back.start.strftime('%H'),
                day_of_week='*',
                day_of_month='*',
                month_of_year='*'
                )
            task = PeriodicTask.objects.get(name='make_backup_at')
            task.crontab = schedule
            task.save()
            messages.success(self.request, 'Время обновленно.')
        else:
            messages.error(self.request, 'Время не обновленно.')

        return HttpResponseRedirect(
                reverse('backup_system'))


class BackupFileView(SuperuserRequiredMixin, ListView):
    template_name = 'admin/common/backup/backup_files.html'
    model = BackupFile


class UnplanedBackupLoadView(SuperuserRequiredMixin, ListView):
    def get(self, request, *args, **kwargs):
        try:
            prepare_time = datetime.timedelta(minutes=settings.BACKUP_PREPARE_TIME)
            eta = datetime.datetime.utcnow() + prepare_time
            local_time = localtime(now()) + prepare_time
            make_dump.apply_async(eta=eta)
            cache.add('BACKUP_UNPLANED_TIME', local_time, prepare_time.total_seconds())
        except Exception as e:
            async_mail_admins(
                subject="Бекап системы",
                message="Бекап системы был сделан не успешно.",
                fail_silently=False,
                html_message=None
            )
            messages.error(self.request, 'Внеплановый бекап не был запущен.')

            return HttpResponseRedirect(
                reverse('backup_system'))

        messages.success(self.request, 'Внеплановый бекап успешно запущен.')

        return HttpResponseRedirect(
                reverse('backup_system'))


class LoadBackupView(FormView):
    form_class = ImportForm
    template_name = 'smuggler/load_data_form.html'
    success_url = '.'

    def form_valid(self, form):
        uploads = form.cleaned_data.get('uploads', [])
        store = form.cleaned_data.get('store', False)
        picked_files = form.cleaned_data.get('picked_files', [])
        fixtures = []
        tmp_fixtures = []
        for upload in uploads:
            file_name = upload.name
            if store:  # Store the file in SMUGGLER_FIXTURE_DIR
                destination_path = os.path.join(
                    smuggler_settings.SMUGGLER_FIXTURE_DIR, file_name)
                save_uploaded_file_on_disk(upload, destination_path)
            else:  # Store the file in a tmp file
                prefix, suffix = os.path.splitext(file_name)
                destination_path = tempfile.mkstemp(
                    suffix=suffix, prefix=prefix + '_')[1]
                save_uploaded_file_on_disk(upload, destination_path)
                tmp_fixtures.append(destination_path)
            fixtures.append(destination_path)
        for file_name in picked_files:
            fixtures.append(file_name)
        try:
            prepare_time = datetime.timedelta(minutes=settings.BACKUP_RESTORE_PREPARE_TIME)
            eta = datetime.datetime.utcnow() + prepare_time
            local_time = localtime(now()) + prepare_time
            load_dump.apply_async((fixtures, tmp_fixtures), eta=eta)
            cache.add('BACKUP_RESTORE_TIME', local_time, prepare_time.total_seconds())
            cache.add('BACKUP_FIXTURES', fixtures, prepare_time.total_seconds())
            messages.success(self.request, 'Восстановление из бекапа было запущено')
        except:
            async_mail_admins(
                subject="Бекап системы",
                message="Не удалось запустить восстановление из бекапа.",
                fail_silently=False,
                html_message=None
            )
            messages.error(self.request, 'Не удалось запустить восстановление из бекапа.')

        return super(LoadBackupView, self).form_valid(form)

    def get_admin_form(self, form):
        return AdminForm(form, self.get_fieldsets(form), {})

    def get_context_data(self, **kwargs):
        context = super(LoadBackupView, self).get_context_data(**kwargs)
        context['adminform'] = self.get_admin_form(context['form'])
        return context

    def get_fieldsets(self, form):
        fields = form.fields.keys()
        if 'picked_files' in fields:
            return [
                (_('Upload'), {'fields': ['uploads', 'store']}),
                (_('From fixture directory'), {'fields': ['picked_files']})
            ]
        return [(None, {'fields': fields})]


def is_superuser(u):
    if u.is_authenticated:
        if u.is_superuser:
            return True
        raise PermissionDenied
    return False
load_backup = user_passes_test(is_superuser)(LoadBackupView.as_view())
