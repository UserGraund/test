import datetime

from django.utils.timezone import localtime, now
from django.conf import settings
from django.core.cache import cache
from common.models import BackupFile, BackupLoadTime
from django_celery_beat.models import PeriodicTask


def yesterday_date(request):
    return {'yesterday_date': now().date() - datetime.timedelta(1)}


def user_access_in_cinemas(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return {'user_access_in_cinemas': True}
        elif request.user.is_staff:
            return {'user_access_in_cinemas': True}
        elif request.user.view_all_reports:
            return {'user_access_in_cinemas': True}
        elif request.user.cinemas.count() > 0 and request.user.report_cinemas.count() > 0:
            return {'user_access_in_cinemas': True}

    return {'user_access_in_cinemas': False}


def get_working_time(request):
    # regular backup
    schedule = PeriodicTask.objects.get(name='make_backup_at').schedule
    curr_time = localtime(now())
    next_hour = schedule.hour.copy().pop()
    next_minute = schedule.minute.copy().pop()
    next_run_time = curr_time.replace(hour=next_hour, minute=next_minute, second=0)
    if curr_time.hour > next_hour or (curr_time.hour == next_hour and curr_time.minute > next_minute):
        next_run_time = next_run_time.replace(day=next_run_time.day+1)
    time_left = next_run_time-curr_time
    time_unplanned = cache.get('BACKUP_UNPLANED_TIME')
    if time_unplanned:
        time_left_unplanned = time_unplanned - curr_time
        if time_left_unplanned < time_left:
            time_left = time_left_unplanned

    event_type = 'backup'
    
    def get_estimated_update_time(model):
        try:
            last_bp = model.objects.last()
            update_time = last_bp.end - last_bp.start
            update_time = update_time - datetime.timedelta(microseconds=update_time.microseconds)
        except:
            update_time = '[неизвестно]'  
        return update_time
    
    update_time = get_estimated_update_time(BackupFile)
    prepare_time = datetime.timedelta(minutes=settings.BACKUP_PREPARE_TIME)
    
    context = {'time_left': False,
                'time_update': False,
                'event_type': ''}
    
    time_restore = cache.get('BACKUP_RESTORE_TIME')
    if time_restore:
        time_left_restore = time_restore - curr_time
        if time_left_restore < time_left:
            time_left = time_left_restore
            event_type = 'restore'
            prepare_time = datetime.timedelta(minutes=settings.BACKUP_RESTORE_PREPARE_TIME)
            update_time = get_estimated_update_time(BackupLoadTime)
            dates = []
            for fixture in cache.get('BACKUP_FIXTURES'):
                try:
                    filename = fixture.split('/')[-1]
                    date = datetime.datetime.strptime(filename, 'default-%Y%m%d-%H%M%S.json')
                    dates.append(date)
                except:
                    pass
            context.update(dates=dates)
            print(cache.get('BACKUP_FIXTURES'))

    if time_left < prepare_time and time_left.total_seconds() > 0:
        time_left = time_left - datetime.timedelta(microseconds=time_left.microseconds)
        context.update({'time_left': time_left,
                        'time_update': update_time,
                        'event_type': event_type})
    return context
    

