from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES['default'].update(
    NAME='kinomania',
    USER='usergraund',
    PASSWORD=''
)

ADMINS = (
    ('Mark', 'mark.mishyn@gmail.com'),
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

if DEBUG:
    LOGGING = {}
