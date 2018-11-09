from .base import *

DEBUG = False


DATABASES['default'].update(
    NAME='kinomania',
    USER='kino_test',
    PASSWORD='54321KINOpass'
)

WSGI_APPLICATION = 'kinomania.heroku_wsgi.application'

ALLOWED_HOSTS = [
    '83.142.234.67',
    'localhost',
    'erp.kinomania.com.ua',
    '192.168.1.74',
]
