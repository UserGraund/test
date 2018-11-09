from django.conf.urls import url, include

from common.admin_views import CityAutocompleteView, ChainAutocompleteView, UploadXLSReportsView, \
    CinemaAutocompleteView, AllCinemasAutocompleteView, GeneralContractAutocompleteView, FilmAutocompleteView, \
    UserAutocompleteView, BackupSystemView, TimeView, UnplanedBackupLoadView, BackupFileView, load_backup
from users.admin_views import ImportUsersView

urlpatterns = [

    # autocomplete
    url(
        r'^user-autocomplete/$',
        UserAutocompleteView.as_view(),
        name='user_autocomplete',
    ),
    url(
        r'^city-autocomplete/$',
        CityAutocompleteView.as_view(),
        name='city_autocomplete',
    ),
    url(
        r'^chain-autocomplete/$',
        ChainAutocompleteView.as_view(),
        name='chain_autocomplete',
    ),
    url(
        r'^cinema-autocomplete/$',
        CinemaAutocompleteView.as_view(),
        name='cinema_autocomplete',
    ),
    url(
        r'^all-cinemas-autocomplete/$',
        AllCinemasAutocompleteView.as_view(),
        name='all_cinemas_autocomplete',
    ),
    url(
        r'^film-autocomplete/$',
        FilmAutocompleteView.as_view(),
        name='film_autocomplete',
    ),
    url(
        r'^general-contact-autocomplete/$',
        GeneralContractAutocompleteView.as_view(),
        name='general_contact_autocomplete',
    ),

    # other
    url(
        r'^upload-xls-reports/$',
        UploadXLSReportsView.as_view(),
        name='upload_xls_reports',
    ),
    url(
        r'^import-users/$',
        ImportUsersView.as_view(),
        name='import_users',
    ),
    url(
        r'backup-system/$',
        BackupSystemView.as_view(),
        name='backup_system'
    ),
    url(
        r'backup-system/backup-time/$',
        TimeView.as_view(),
        name="time_system"
    ),
    url(
        r'backup-system/unplaned-backup/$',
        UnplanedBackupLoadView.as_view(),
        name="unplaned_backup"
    ),
    url(
        r'backup-system/backup-load/$',
        load_backup,
        name='backup_load'
    ),

]

