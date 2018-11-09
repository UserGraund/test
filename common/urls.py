from django.conf.urls import url
from django.contrib.auth import views as auth_views

from common.views import MainReportView, CreateSessionView, CinemaListView, UpdateSessionView, \
    delete_session, SetDailyReportFinishedView, CopyYesterdaysSessionsView, \
    SendUpdateSessionRequestView, CreateFeedbackView, SendDailyReportEmailView, \
    ChangeSessionsDateView, SetDailyReportUnfinishedView, MonthlyReportView, \
    CreateConfirmedMonthlyReportView, CinemaListWithMonthlyReportsView, SendMonthlyReportEmailView, \
    CountDown

urlpatterns = [
    url(
        r'^$',
        MainReportView.as_view(),
        name='main_report'),
    url(
        r'^confirm-monthly-report/$',
        MonthlyReportView.as_view(),
        name='confirm_monthly_report'),
    url(
        r'^login/$',
        auth_views.login, {'template_name': 'admin/login.html'},
        name='login'),
    url(
        r'^logout/$',
        auth_views.logout, {'next_page': '/login/'},
        name='logout'),
    url(
        r'^cinemas/(?P<pk>\d+)/create-session/(?P<date>\d{2}-\d{2}-\d{4})/$',
        CreateSessionView.as_view(),
        name='create_session'),
    url(
        r'^cinemas/(?P<pk>\d+)/update-session/(?P<date>\d{2}-\d{2}-\d{4})/(?P<session_pk>\d+)/$',
        UpdateSessionView.as_view(),
        name='update_session'),
    url(
        r'^cinemas/(?P<pk>\d+)/send-update-request/(?P<date>\d{2}-\d{2}-\d{4})/(?P<session_pk>\d+)/$',
        SendUpdateSessionRequestView.as_view(),
        name='send_update_session_request'),
    url(
        r'^delete-session/(?P<session_pk>\d+)/$',
        delete_session,
        name='delete_session'),
    url(
        r'^cinemas/(?P<pk>\d+)/set-report-finished/(?P<date>\d{2}-\d{2}-\d{4})/$',
        SetDailyReportFinishedView.as_view(),
        name='set_daily_report_finished'),
    url(
        r'^cinemas/(?P<pk>\d+)/set-report-unfinished/(?P<date>\d{2}-\d{2}-\d{4})/$',
        SetDailyReportUnfinishedView.as_view(),
        name='set_daily_report_unfinished'),
    url(
        r'^cinemas/(?P<pk>\d+)/copy-yesterday-sessions/(?P<date>\d{2}-\d{2}-\d{4})/$',
        CopyYesterdaysSessionsView.as_view(),
        name='copy_yesterday_sessions'),
    url(
        r'^main-cinema-list/(?P<date>\d{2}-\d{2}-\d{4})/$',
        CinemaListView.as_view(),
        name='cinema_list'),
    url(
        r'^cinema-list-with-monthly-reports/$',
        CinemaListWithMonthlyReportsView.as_view(),
        name='cinema_list_with_monthly_reports'),
    url(
        r'^send-monthly-report-email/$',
        SendMonthlyReportEmailView.as_view(),
        name='send_monthly_report_email'),
    url(
        r'^create-feedback/$',
        CreateFeedbackView.as_view(),
        name='create_feedback'),
    url(
        r'^cinemas/(?P<pk>\d+)/send-daily-report-email/(?P<date>\d{2}-\d{2}-\d{4})/$',
        SendDailyReportEmailView.as_view(),
        name='send_daily_report_email'),
    url(
        r'^cinemas/(?P<pk>\d+)/change-sessions-date/(?P<date>\d{2}-\d{2}-\d{4})/$',
        ChangeSessionsDateView.as_view(),
        name='change_sessions_date'),
    url(
        r'^create-monthly-report/$',
        CreateConfirmedMonthlyReportView.as_view(),
        name='create_monthly_report'),
    url(
        r'not-available/$',
        CountDown.as_view(),
        name='not_working'
    )
]
