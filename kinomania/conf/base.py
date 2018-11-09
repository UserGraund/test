import os
import django_heroku
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = '%(r)^ed3*bsdvi1fc2d4o%vyd44pay=gf*g9vl*4e!j66+59zi'

DEBUG = True

DJANGO_APPS = [
    # django-autocomplete-light must be before django.contrib.admin

    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',

 ]

THIRD_PARTY_APPS = [
    'django_extensions',
    'debug_toolbar',
    'crispy_forms',
    'django_tables2',
    'django_celery_beat',
    'admin_reorder',
    'dbbackup',
    'smuggler'
]

LOCAL_APPS = [
    'users',
    'common',
]

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'common.middlewares.custom_admin_reorder.ExtendedModelAdminReorder',
    'common.middlewares.custom_admin_reorder.CheckBackupTime',
]

ROOT_URLCONF = 'kinomania.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': True,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'common.context_processors.yesterday_date',
                'common.context_processors.user_access_in_cinemas',
                'common.context_processors.get_working_time',
            ],
        },
    },
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # use host specific settings to indicate database's name and db credentials
    }
}


AUTH_PASSWORD_VALIDATORS = []


LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'Europe/Kiev'
USE_I18N = True
USE_L10N = False
USE_TZ = True

DATE_INPUT_FORMATS = ['%d/%m/%Y']
DATE_FORMAT = DATE_INPUT_FORMATS[0].replace('%', '')

TIME_INPUT_FORMATS = ['%H:%M']
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = '{} {}'.format(DATE_FORMAT, TIME_FORMAT)

DATE_URL_INPUT_FORMAT = DATE_INPUT_FORMATS[0].replace('/', '-')

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'


MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

AUTH_USER_MODEL = 'users.User'

INTERNAL_IPS = ['127.0.0.1']

CRISPY_TEMPLATE_PACK = 'bootstrap3'

REPORT_DATE_LIMITATION_MONTHS = 3

KINOMANIA_INCOME_FEE = 0.5   # 50%

ADMIN_REORDER = (
    'sites',

    {
        'app': 'users',
        'label': 'Пользователи',
        'models': ('users.User', )
    },
    {
        'app': 'common',
        'label': 'Кинотеатры и фильмы',
        'models': (
            'common.Chain',
            'common.Cinema',
            'common.Film',
        )
    },
    {
        'app': 'common',
        'label': 'Сеансы',
        'models': (
            'common.Session',
        )
    },
    {
        'app': 'common',
        'label': 'XLS Отчёты',
        'links': (
            ('upload_xls_reports', 'Загрузить XLS отчёты'),
            ('admin:common_xlsreportsupload_changelist', 'Список XLS отчётов'),
        )
    },
    {
        'app': 'common',
        'label': 'Остальное',
        'models': (
            'common.City',
            'common.Dimension',
            'common.GeneralContract',
            'common.CinemaHall',
            'common.AdditionalAgreement',
            'common.ContactInformation',
            'common.FinishedCinemaReportDate',
            'common.ConfirmedMonthlyReport',
            'common.SessionUpdateRequest',
            'common.Feedback',
        )
    },
    {
    'app': 'common',
    'label': 'Бекап система',
    'links': (
        ('backup_system', 'Зайти в систему'),
     #   ('admin:common_backupfile_changelist', 'Список бекапов'),
    ),
    'models': (
        'common.BackupFile',
    )
    }
)

SITE_ID = 1

SHELL_PLUS_POST_IMPORTS = (
    ('common.models', '*'),
    ('common.factories', '*'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery_tasks': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO'
        }
    }
}

FEEDBACK_RECEIVERS_EMAILS = ['StatisticKino@gmail.com', 'usergraund@gmail.com',
                             'kinomania-admin@protonmail.com']


DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': str(Path(__file__).parents[2])}

BACKUP_DEFAULT_HOUR = 0
BACKUP_DEFAULT_MINUTE = 0
BACKUP_DIR_NAME = 'backups'
BACKUP_DIR_PATH = '{}/{}/'.format(Path(__file__).parents[2],BACKUP_DIR_NAME)
BACKUP_TO_OUTDATED_DAYS = 14
SMUGGLER_FIXTURE_DIR = BACKUP_DIR_PATH

BACKUP_PREPARE_TIME = 15 # time in minutes that allows to user prepare for an update
BACKUP_RESTORE_PREPARE_TIME = 3 # time in minutes that allows to user prepare for an update

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211'

    }
}

django_heroku.settings(locals())
