import datetime

from admin_reorder.middleware import ModelAdminReorder
from django.urls import reverse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache

from common.models import TimeBackup


class ExtendedModelAdminReorder(ModelAdminReorder):
    def process_app(self, app_config):
        app = super().process_app(app_config)

        if 'links' in app_config:
            links_config = app_config.get('links')
            links = self.process_links(links_config)
            if app and links:
                app['models'] = links
        return app

    def process_links(self, links_config):
        return [{
            'admin_url': reverse(conf[0]),
            'name': conf[1],
            'perms': {'add': False, 'change': False, 'delete': False}} for conf in links_config]


class CheckBackupTime(MiddlewareMixin):
    def process_request(self, request):
        if (cache.get('BACKUP_IN_PROGRESS') or cache.get('BACKUP_LOAD_IN_PROGRESS')) \
           and not request.path == '/not-available/':
            return redirect(reverse('not_working'))
        
