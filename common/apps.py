from datetime import time
from django.utils import timezone
from django.apps import AppConfig, apps
from django.conf import settings
from celery.schedules import crontab


class CommonConfig(AppConfig):
    name = 'common'
    verbose_name = 'Кинотеатры и контракты'

    def ready(self):
        PeriodicTask = apps.get_model(app_label='django_celery_beat', model_name='PeriodicTask')
        try:
            PeriodicTask.objects.get(name='make_backup_at')
        except:
            # if time of backup wasn't set in admin yet.
            TimeBackup = apps.get_model(app_label='common',
                                        model_name='TimeBackup')
            CrontabSchedule = apps.get_model(app_label='django_celery_beat',
                                          model_name='CrontabSchedule')
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=settings.BACKUP_DEFAULT_MINUTE,
                hour=settings.BACKUP_DEFAULT_HOUR, 
                day_of_week='*',
                day_of_month='*',
                month_of_year='*'
                )
            task, _ = PeriodicTask.objects.get_or_create(name='make_backup_at')
            task.crontab = schedule 
            task.save()
            time_back = TimeBackup()
            default_time = time(hour=settings.BACKUP_DEFAULT_HOUR,
                                minute=settings.BACKUP_DEFAULT_MINUTE,
                                tzinfo=timezone.get_current_timezone())
            time_back.start = default_time
            time_back.save()
            










