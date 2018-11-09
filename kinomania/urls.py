from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.conf.urls.static import static
from django.core.urlresolvers import resolve

from users.views import ChangePasswordView

SITE_NAME = 'KinoMania'

admin.site.site_title = SITE_NAME
admin.site.site_header = '{}, административная панель'.format(SITE_NAME)
admin.site.index_title = ''


        
urlpatterns = [
    url(r'^admin/', include('smuggler.urls')),
    url(r'^admin/', admin.site.urls),
    url('^admin/', include('common.admin_urls')),
    url('^', include('common.urls')),
    url(
        r'^change-password/$',
        ChangePasswordView.as_view(),
        name='change_password'),
]

backup_file_changelist_view, args, kwargs = resolve('/admin/common/backupfile/')
urlpatterns += (
    url(r'^admin/backup-system/backup-file', backup_file_changelist_view,
        name='common_backupfile_changelist'),
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
