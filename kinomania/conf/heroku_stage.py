from .base import *

import dj_database_url

from kinomania.conf.base import *

WSGI_APPLICATION = 'kinomania.heroku_wsgi.application'

ALLOWED_HOSTS = ['kinomania.herokuapp.com', '0.0.0.0']

db_from_env = dj_database_url.config(conn_max_age=500)

DATABASES['default'].update(db_from_env)
