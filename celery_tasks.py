import logging
import sys
import time
import os
import re
from io import StringIO
from datetime import datetime, timedelta
from logging.config import dictConfig

from celery import Celery

from django.conf import settings
from django.core.mail import send_mail, mail_admins
from django.utils.timezone import now, localtime
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django import apps 

from smuggler.utils import load_fixtures

BACKUP_DIR_NAME = settings.BACKUP_DIR_NAME

if settings.LOGGING:
    dictConfig(settings.LOGGING)    

logger = logging.getLogger('celery_tasks')

app = Celery('celery_tasks', broker='amqp://localhost')

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc = False,
)

# should use cache to allow edit value from tasks (multiprocessing dirty trick)
cache.add('BACKUP_IN_PROGRESS', False)
cache.add('BACKUP_LOAD_IN_PROGRESS', False) 
                                       

@app.task
def send_daily_reports_emails():
    try:
        from users.models import User
        from kinomania.utils import is_weekend, get_previous_dates, build_full_url

        today = now().date()
        if is_weekend(today):
            return

        filtered_users = User.objects.filter(cinemas__isnull=False, is_active=True).distinct()
        filtered_users.send_daily_reports_emails(is_email_async=False)

    except Exception:
        logger.error(msg='send_daily_reports_emails error', exc_info=sys.exc_info())


@app.task
def async_send_email(subject, message, recipient_list, from_email=settings.DEFAULT_FROM_EMAIL,
                     html_message=None):
    try:
        send_mail(
            subject=subject,
            message=message,
            recipient_list=recipient_list,
            from_email=from_email,
            html_message=html_message)
    except Exception:
        logger.error(msg='async_send_email error', exc_info=sys.exc_info())


@app.task
def async_mail_admins(subject, message, fail_silently=False, html_message=None):
    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=fail_silently,
            html_message=html_message)
    except Exception:
        logger.error(msg='async_mail_admins error', exc_info=sys.exc_info())


@app.task
def make_dump():
    cache.set('BACKUP_IN_PROGRESS', True)
    try:
        start_time = localtime(now())
        from django.contrib.sessions.models import Session
        for session in Session.objects.all():
            session.delete()
        from common.models import BackupFile
        backup_file_path = '{}/default-{}.json'.format(BACKUP_DIR_NAME, time.strftime("%Y%m%d-%H%M%S"))
        output = open(backup_file_path, 'w')
        call_command('dumpdata', '--natural-primary', '--natural-foreign',
                     format='json', indent=2, stdout=output)
        output.close()
        end_time = localtime(now())
        backup_file = BackupFile(start=start_time, end=end_time,
                                 backup_file_path=backup_file_path)
        backup_file.save()
        # remove outdated backup files
        count_deleted, details = BackupFile.objects.filter(
            start__lte=datetime.now()-timedelta(days=settings.BACKUP_TO_OUTDATED_DAYS)).delete()
        
        message = "Бекап системы был сделан успешно. "
        if count_deleted > 0:
            message += "Удалено {} устаревших бекапов.".format(count_deleted)
        else:
            message += "Устаревших бекапов не обнаружено."
        mail_admins(
            subject="Бекап системы",
            message=message,
            fail_silently=False,
            html_message=None)
        cache.set('BACKUP_IN_PROGRESS', False)
        return backup_file
    except Exception as e:
        logger.error(msg='make dump error', exc_info=sys.exc_info())
        mail_admins(
            subject="Бекап системы",
            message=str(e),
            fail_silently=False,
            html_message=None)
        return False

        
@app.task
def load_dump(fixtures, tmp_fixtures=None):
    cache.set('BACKUP_LOAD_IN_PROGRESS', True)
    from common.models import BackupLoadTime
    from django.contrib.contenttypes.models import ContentType
    
    backup_load = BackupLoadTime()
    backup_load.start = localtime(now())
    reserve_backup_file = make_dump()
    reserve_backup_file.pk = None
    reserve_backup_file_path = reserve_backup_file.backup_file_path
    ContentType.objects.clear_cache() # clear cache is needed for properly run of django commands
    try:
        output = StringIO()
        call_command('flush', format='json', indent=2, stdout=output, interactive=False)
        output.close()
        for app in settings.INSTALLED_APPS:
            label = app.split('.')[-1]
            # Get SQL commands from sqlsequencereset
            output = StringIO()
            call_command('sqlsequencereset', label, stdout=output, interactive=False)
            sql = output.getvalue()
            # Remove terminal color codes from sqlsequencereset output
            ansi_escape = re.compile(r'\x1b[^m]*m')
            sql = ansi_escape.sub('', sql)
            if(sql): 
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                output.close()
        result = load_fixtures(fixtures)
        message = "Восстановление из бекапа было сделано успешно. "
        mail_admins(
            subject="Бекап системы",
            message=message,
            fail_silently=False,
            html_message=None)
        
    except Exception as e:
        output = StringIO()
        call_command('flush', format='json', indent=2, stdout=output, interactive=False)
        output.close()
        for app in settings.INSTALLED_APPS:
            label = app.split('.')[-1]
            # Get SQL commands from sqlsequencereset
            output = StringIO()
            call_command('sqlsequencereset', label, stdout=output, interactive=False)
            sql = output.getvalue()
            # Remove terminal color codes from sqlsequencereset output
            ansi_escape = re.compile(r'\x1b[^m]*m')
            sql = ansi_escape.sub('', sql)
            if(sql): 
                with connection.cursor() as cursor:
                    cursor.execute(sql)
            output.close()
        load_fixtures((reserve_backup_file_path,))
        message = 'Восстановление из бекапа не удалось'
        logger.exception(message)
        mail_admins(
            subject="Бекап системы",
            message=message,
            fail_silently=False,
            html_message=None)

    reserve_backup_file.save()
    if tmp_fixtures:
        for tmp_file in tmp_fixtures:
            os.unlink(tmp_file)
    backup_load.end = localtime(now())
    backup_load.save()
    cache.set('BACKUP_LOAD_IN_PROGRESS', False)

    
