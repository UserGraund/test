from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import UserManager, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from celery_tasks import async_send_email
from common.models import Cinema, AdditionalAgreement, Chain
from kinomania.utils import build_full_url, get_previous_dates


class UserQueryset(models.QuerySet):
    def send_daily_reports_emails(self, is_email_async):

        today = now().date()
        previous_dates = get_previous_dates(today)

        for user in self:
            missing_report_dates = []
            for previous_date in previous_dates:

                if not AdditionalAgreement.objects.filter(
                        cinema__in=user.cinemas.all()).filter_by_date(previous_date).exists():
                    continue

                if Cinema.objects.filter(responsible_for_daily_reports=user,
                                         created__date__lte=previous_date).exclude(
                        finished_on_dates__date=previous_date).exists():
                    missing_report_dates.append(previous_date)

            if not missing_report_dates:
                continue

            missing_report_links = {}
            for date in missing_report_dates:
                date_str = date.strftime(settings.DATE_URL_INPUT_FORMAT)
                url = reverse('cinema_list', kwargs=dict(date=date_str))
                missing_report_links[date_str] = build_full_url(url)

            user.send_daily_reports_email(missing_report_dates=missing_report_dates,
                                          is_email_async=is_email_async)


class CustomUserManager(UserManager):

    def get_queryset(self):
        return UserQueryset(self.model, using=self._db)

    def send_daily_reports_emails(self):
        return self.get_queryset().send_daily_reports_emails(is_email_async=False)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        access_type = extra_fields.pop('access_type', None)
        if email and password and access_type:
            self.send_credentials_email(username, email, password, access_type)
        return self._create_user(username, email, password, **extra_fields)

    @staticmethod
    def send_credentials_email(username, email, password, access_type):

        url = reverse('main_report')
        full_url = build_full_url(url)

        message = ('Уважаемый {username}, ваш аккаунт был создан! \n'
                   'Для входа в систему Вам необходимо пeрейти по ссылке: {full_url} \n '
                   'Для авторизации используйте: \n '
                   'Логин (Имейл): {email} \n '
                   'Пароль: {password}').format(
                username=username,
                full_url=full_url,
                email=email,
                password=password)

        async_send_email.delay(
            subject='КиноМания: ваш новый аккаунт',
            message=message,
            recipient_list=[email])


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_('username'), max_length=150, blank=True,
                                help_text='Required. 150 characters or fewer.')
    email = models.EmailField('Имейл', unique=True)
    phone_number = models.CharField(max_length=256, blank=True)
    is_staff = models.BooleanField(
        'Админ',
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    view_all_reports = models.BooleanField(
        default=False, help_text='Просмотр и экспорт отчётов по всем кинотеатрам')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def get_full_name(self):
        return self.get_short_name()

    def get_short_name(self):
        return self.username if self.username else self.email

    def email_user(self, subject, message, from_email=settings.DEFAULT_FROM_EMAIL, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def all_cinemas(self):
        if self.is_superuser or self.view_all_reports:
            return Cinema.objects.all()

        return self.cinemas.all()

    @property
    def all_chain_cinemas(self):
        if self.is_superuser or self.view_all_reports:
            return Chain.objects.all()

    @property
    def all_report_cinemas(self):
        if self.is_superuser or self.view_all_reports:
            return Cinema.objects.all()

        return self.report_cinemas.all()

    @property
    def all_agreements(self):
        if self.is_superuser or self.view_all_reports:
            return AdditionalAgreement.objects.all()

        return AdditionalAgreement.objects.filter(
                cinema__in=self.cinemas.all() | self.report_cinemas.all())

    @staticmethod
    def make_random_password(length=6):
        allowed_chars = [
            'abcdefghjkmnpqrstuvwxyz',
            'ABCDEFGHJKLMNPQRSTUVWXYZ',
            '23456789',
            '!#$%*+-:;<=>?@\_']

        while True:
            password = get_random_string(length, ''.join(allowed_chars))
            for chars_set in allowed_chars:
                if not set(chars_set) & set(password):
                    continue
            return password

    def async_email_user(self, subject, message, html_message=None):

        async_send_email.delay(subject=subject, message=message,
                               html_message=html_message, recipient_list=[self.email])

    def send_daily_reports_email(self, missing_report_links, is_email_async):
        if not is_email_async:
            send_mail(
                subject='КиноМания: незаполненные отчёты по кинотеатрам',
                from_email=settings.DEFAULT_FROM_EMAIL,
                message='',
                recipient_list=[self.email],
                html_message=render_to_string('emails/daily_report_notification.html',
                                              dict(missing_report_links=missing_report_links))
            )
        else:
            async_send_email.delay(
                    subject='КиноМания: незаполненные отчёты по кинотеатрам',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    message='',
                    recipient_list=[self.email],
                    html_message=render_to_string('emails/daily_report_notification.html',
                                                  dict(missing_report_links=missing_report_links))
                )
