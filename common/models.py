import os
from datetime import timedelta, date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.postgres.fields import JSONField, ArrayField, DateRangeField
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db import IntegrityError
from django.db import models
from django.db.models import Count
from django.db.models import F
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import now, local
from django.db.models.signals import post_delete
from django.core.files.storage import FileSystemStorage
from model_utils.models import TimeStampedModel

from celery_tasks import async_mail_admins
from common.managers import CinemaManager, AdditionalAgreementManager
from kinomania.utils import validate_xls_extension, build_full_url, MONTHS

VAT_RATE = 0.166666666666666


class City(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        verbose_name_plural = 'Городa'
        verbose_name = 'Город'
        ordering = ('name', )

    def __str__(self):
        return self.name


class Dimension(TimeStampedModel):
    name = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name_plural = 'Форматы'
        verbose_name = 'Формат'
        ordering = ('name', )

    def __str__(self):
        return self.name


class Chain(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)
    responsible_for_daily_reports = models.ManyToManyField(to='users.User', verbose_name='Дневные отчёты',
                                                           related_name='chain', blank=True)
    access_to_reports = models.ManyToManyField(to='users.User', verbose_name='Доступ к отчётам',
                                               related_name='report_chain', blank=True)

    class Meta:
        verbose_name_plural = 'Сети кинотеатров'
        verbose_name = 'Сеть'
        ordering = ('name', )

    def __str__(self):
        return self.name


class Cinema(TimeStampedModel):
    name = models.CharField(max_length=64, verbose_name='Название', db_index=True)
    city = models.ForeignKey(City, verbose_name='Город', related_name='cinemas')
    chain = models.ForeignKey(Chain, verbose_name='Сеть', related_name='cinemas',
                              blank=True, null=True)
    halls_count = models.PositiveSmallIntegerField('Залов', default=0)
    vat = models.BooleanField(verbose_name='НДС', default=False)
    chain_contract = models.ForeignKey(
        'common.GeneralContract', related_name='halls', blank=True, null=True, help_text=(
            'Выберите один из контактов сети или создайте ниже контракт непосредственно '
            'для кинотеатра'), verbose_name='Контракт сети')
    # TODO:  should in future removed access_to_reports_test and responsible_for_daily_reports_test
    responsible_for_daily_reports_test = models.ForeignKey(
        'users.User', models.SET_NULL, related_name='cinemas_test', blank=True, null=True,
        verbose_name='Дневные отчёты')
    access_to_reports_test = models.ForeignKey('users.User', models.SET_NULL,
                                               related_name='report_cinemas_test', blank=True, null=True,
                                               verbose_name='Доступ к отчётам')

    responsible_for_daily_reports = models.ManyToManyField(
        to='users.User', related_name='cinemas',
        verbose_name='Дневные отчёты', blank=True,)
    access_to_reports = models.ManyToManyField(
        to='users.User',
        related_name='report_cinemas',
        verbose_name='Доступ к отчётам', blank=True,
    )

    objects = CinemaManager()

    class Meta:
        verbose_name_plural = 'Кинотеатры'
        verbose_name = 'Кинотеатр'
        ordering = ('name', )
        unique_together = (('name', 'city', 'chain'), )

    def __str__(self):
        return '{} ({})'.format(self.name, self.city.name)

    def save(self, *args, **kwargs):

        if not self.pk and self.chain:
            if self.chain.responsible_for_daily_reports.count() > 0:
                for user in self.chain.responsible_for_daily_reports.all():
                    self.responsible_for_daily_reports.add(user)
            if self.chain.access_to_reports.count() > 0:
                for user in self.chain.responsible_for_daily_reports.all():
                    self.access_to_reports.add(user)

        super().save(*args, **kwargs)

    def is_report_finished(self, date):
        return self.finished_on_dates.filter(date=date).exists()

    def set_report_finished(self, date):
        Session.objects.filter(
            cinema_hall__cinema=self, date=date).update(is_daily_report_finished=True)

        try:
            FinishedCinemaReportDate.objects.create(cinema=self, date=date)
        except IntegrityError:
            pass

    def get_agreements(self):
        cinemas_agreements = AdditionalAgreement.objects.filter(
                contract__in=self.general_contracts.all())
        if self.chain:
            chains_agreements = AdditionalAgreement.objects.filter(
                    contract__in=self.chain.contracts.all())
        else:
            chains_agreements = AdditionalAgreement.objects.none()

        return cinemas_agreements | chains_agreements


class CinemaHall(TimeStampedModel):
    name = models.CharField(max_length=64)
    seats_count = models.PositiveSmallIntegerField()
    dimensions = models.ManyToManyField(Dimension, related_name='halls')
    cinema = models.ForeignKey(Cinema, related_name='halls')

    class Meta:
        verbose_name_plural = 'Залы'
        verbose_name = 'Кинозал'
        ordering = ('name', )
        unique_together = (('name', 'cinema'), )

    def __str__(self):
        return self.name


class FinishedCinemaReportDate(TimeStampedModel):
    cinema = models.ForeignKey(Cinema, related_name='finished_on_dates')
    date = models.DateField()

    class Meta:
        unique_together = ('cinema', 'date')
        verbose_name_plural = 'Даты завершения отчётов'
        verbose_name = 'Дата завершения отчёта'

    def __str__(self):
        return '{} {}'.format(self.cinema.name, self.date)


class Film(TimeStampedModel):
    name = models.CharField(max_length=128, help_text='На украинском языке', unique=True,
                            db_index=True)
    name_original = models.CharField(max_length=128, help_text='Оригинальное название', blank=True)
    dimensions = models.ManyToManyField(Dimension, related_name='films')
    code = models.CharField(max_length=128, unique=True)
    release_date = models.DateField()

    class Meta:
        verbose_name_plural = 'Фильмы'
        verbose_name = 'Фильм'
        ordering = ('created', )

    def __str__(self):
        return self.name

    def clean(self):
        if self.name_original:
            qs = Film.objects.filter(name_original=self.name_original)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('Фильм с таким оригинальным название уже существует')


class GeneralContract(TimeStampedModel):
    contractor_full_name = models.CharField(max_length=64)
    SBR_code = models.BigIntegerField(verbose_name='ЕГРПОУ', unique=True)
    number = models.CharField(max_length=32, unique=True)
    active_from = models.DateField()
    chain = models.ForeignKey(Chain, related_name='contracts', blank=True, null=True)

    cinemas = models.ManyToManyField(Cinema, related_name='general_contracts', blank=True)

    class Meta:
        verbose_name_plural = 'Генеральные контракты'
        verbose_name = 'Контракт'
        ordering = ('created', )

    def __str__(self):
        return '{} ({})'.format(self.contractor_full_name, self.number)


class AdditionalAgreement(TimeStampedModel):

    cinema = models.ForeignKey(Cinema, related_name='agreements', blank=True, null=True,
                               verbose_name='Кинотеатр')
    contract = models.ForeignKey(GeneralContract, related_name='agreements',
                                 verbose_name='Контракт')
    film = models.ForeignKey(Film, related_name='agreements', verbose_name='Фильм')
    active_date_range = DateRangeField('Активно "с" - "по"')
    dimension = models.ForeignKey(Dimension, related_name='agreements', verbose_name='Форматы')
    vat = models.NullBooleanField(blank=True, null=True,
        verbose_name='НДС', help_text='Если НДС не указано, то будет взято значение из кинотеатра')
    is_original_language = models.BooleanField(
        'Показ на языке оригинала',
        default=False, max_length=10,
        help_text='Показ фильма на языке оригинала?')
    one_c_number = models.CharField('номер 1С', max_length=64, unique=True, blank=True)

    objects = AdditionalAgreementManager()

    class Meta:
        verbose_name_plural = 'Дополнительные соглашения'
        verbose_name = 'Доп. соглашение'
        ordering = ('created', )
        unique_together = (('cinema', 'film', 'dimension', 'is_original_language',
                            'active_date_range'), )

    def __str__(self):
        return '{}: {}'.format(self.cinema.name, self.film.name)

    def clean(self):
        # TODO check if after update of active_date_range there are no sessions without agreement

        if self.cinema:
            invalid_cinema_error = ValidationError(
                    'Выбранный кинотеатр не соответствует генеральному контракту')
            if self.contract_id and self.cinema_id and self.contract.chain and self.cinema not in self.contract.chain.cinemas.all():
                raise invalid_cinema_error

            if self.contract.cinemas.exists() and self.cinema not in self.contract.cinemas.all():
                raise invalid_cinema_error

        if self.film_id and self.active_date_range and \
                        self.active_date_range.lower < self.film.release_date:

            raise ValidationError(
                'Соглашение не может быть активно ранее чем дата релиза фильма')

        if self.dimension_id and self.film_id and self.dimension not in self.film.dimensions.all():
            raise ValidationError('Вы указали формат "{}". Форматы выбранного фильма: "{}"'.format(
                    self.dimension.name, ', '.join([d.name for d in self.film.dimensions.all()])))

        if self.film_id and self.active_date_range and self.dimension_id:
            qs = AdditionalAgreement.objects.filter(
                    cinema=self.cinema, film=self.film, dimension=self.dimension,
                    is_original_language=self.is_original_language,
                    active_date_range__overlap=self.active_date_range)
            if self.pk:
                qs = qs.exclude(id=self.id)

            if qs.exists():
                raise ValidationError(
                    'На этот диапазон дат уже существует доп соглашение с указанными параметрами.')

    def save(self, *args, **kwargs):

        if not self.one_c_number:
            self.one_c_number = '{}/{}'.format(self.contract.number, self.film.code)

        if self.vat is None:
            self.vat = self.cinema.vat

        film = self.film
        if not film.name_original or (film.name == film.name_original):
            self.is_original_language = True

        is_new = self.pk is None

        if not is_new:
            origin = AdditionalAgreement.objects.get(pk=self.pk)
            origin_active_date_range = origin.active_date_range
            origin_vat = origin.vat

        super().save(*args, **kwargs)

        if is_new or (self.active_date_range != origin_active_date_range):
            self.sessions = Session.objects.filter(
                film=self.film,
                is_original_language=self.is_original_language,
                cinema_hall__cinema=self.cinema,
                dimension=self.dimension,
                date__range=[self.active_date_range.lower,
                             self.active_date_range.upper])

            self.sessions.update(additional_agreement=self, vat=self.vat)

        if is_new or (self.vat != origin_vat):
            if self.vat:
                self.sessions.update(
                    gross_yield_without_vat=F('gross_yield') - F('gross_yield') * VAT_RATE,
                    vat=True)
            else:
                self.sessions.update(gross_yield_without_vat=F('gross_yield'), vat=False)

    def get_months(self):
        if not self.active_date_range:
            return None

        date_from = self.active_date_range.lower
        date_to = self.active_date_range.upper or now().date()
        month_from = date(date_from.year, date_from.month, 1)

        month_diff_count = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month

        for i in range(month_diff_count + 1):
            yield month_from + relativedelta(months=i)

    @property
    def active_date_range_from(self) -> str:
        if self.active_date_range and self.active_date_range.lower:
            return date_format(self.active_date_range.lower)
        return ''

    @property
    def active_date_range_to(self) -> str:
        if self.active_date_range and self.active_date_range.upper:
            return date_format(self.active_date_range.upper)
        return ''


class ContactInformation(TimeStampedModel):
    title = models.CharField(max_length=64, default='администратор')
    cinema = models.ForeignKey(Cinema, related_name='contacts')
    email = models.EmailField(blank=True)
    phone_number = models.CharField(blank=True, max_length=255)

    class Meta:
        unique_together = (('cinema', 'title', 'email', 'phone_number'), )
        verbose_name_plural = 'Контакты'
        verbose_name = 'Контакт'

    def __str__(self):
        return '{}, {}'.format(self.title, self.cinema.name)

    def clean(self):
        if not self.email and not self.phone_number:
            raise ValidationError('Укажите почту или номер телефона')


class XlsReportsUpload(TimeStampedModel):

    city = models.ForeignKey(City, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Загрузки XLS отчётов'
        verbose_name = 'Загрузка XLS отчётов'

    def __str__(self):
        return date_format(self.created, format=settings.DATETIME_FORMAT)

    @property
    def is_successful(self):
        return not self.reports.filter(errors__isnull=False).exists()

    def all_reports(self):
        return self.reports.annotate(sessions_count=Count('sessions'))


class XlsSessionsReport(TimeStampedModel):
    xls_file = models.FileField(upload_to='xls_reports/%Y/%m/%d/',
                                validators=[validate_xls_extension])
    xls_filename = models.CharField(max_length=256)
    report_upload = models.ForeignKey(XlsReportsUpload, related_name='reports')
    errors = ArrayField(base_field=models.CharField(max_length=256, blank=True),
                        blank=True, null=True)

    class Meta:
        verbose_name_plural = 'XLS отчёты'
        verbose_name = 'XLS отчёт'

    def __str__(self):
        return self.xls_filename

    def save(self, parse_file=True, *args, **kwargs):
        super().save(*args, **kwargs)

        if parse_file:
            from common.xls_report_parsers import XlsReportParser
            parser = XlsReportParser(path_to_xls=self.xls_file.path, xls_report=self,
                                     city=self.report_upload.city)
            parser.handle()


class Session(TimeStampedModel):
    date = models.DateField('Дата', db_index=True)
    time = models.TimeField('Время начала')
    viewers_count = models.PositiveSmallIntegerField('Зрители',
                                                     help_text='Кол-во зрителей купивших билеты')
    cinema_hall = models.ForeignKey(CinemaHall, verbose_name='Зал', related_name='sessions')
    film = models.ForeignKey(Film, verbose_name='фильм', related_name='sessions')
    min_price = models.DecimalField('Мин цена', max_digits=6, decimal_places=2)
    max_price = models.DecimalField('Макс цена', max_digits=6, decimal_places=2)
    invitations_count = models.PositiveSmallIntegerField('Пригл.', default=0)
    gross_yield = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Доход')
    dimension = models.ForeignKey(Dimension, related_name='sessions', verbose_name='Формат')
    vat = models.BooleanField(verbose_name='НДС', default=False)
    is_daily_report_finished = models.BooleanField(default=False, verbose_name='Отчёт сдан')
    month = models.DateField(blank=True, null=True)
    week = models.DateField(blank=True, null=True)
    creator = models.ForeignKey('users.User', models.SET_NULL,
                                related_name='sessions', null=True, blank=True)
    gross_yield_without_vat = models.DecimalField(max_digits=10, decimal_places=2,
                                                  verbose_name='Доход с вычетом НДС',
                                                  blank=True, null=True)
    xls_raw_data = JSONField(blank=True, null=True)
    xls_session_report = models.ForeignKey(XlsSessionsReport, models.SET_NULL,
                                           related_name='sessions', blank=True, null=True)
    additional_agreement = models.ForeignKey(AdditionalAgreement, models.SET_NULL,
                                             related_name='sessions', blank=True, null=True,
                                             verbose_name='Доп. соглашение')
    is_original_language = models.BooleanField(
        'Ориг. язык', default=False,
        help_text='Указывает на то, был ли показ фильма на языке оригинала')

    class Meta:
        verbose_name_plural = 'Сеансы'
        verbose_name = 'Сеанс'
        unique_together = (('cinema_hall', 'time', 'date', 'dimension'), )

    def __str__(self):
        return 'ID: {}, зал "{}": фильм: "{}", дата: {} время: {}'.format(
                self.id, self.cinema_hall.name, self.film.name, self.date, self.time)

    def clean(self):
        if self.dimension not in self.film.dimensions.all():
            raise ValidationError('Вы указали формат "{}". Форматы выбранного фильма: "{}"'.format(
                    self.dimension.name, ', '.join([d.name for d in self.film.dimensions.all()])))

    def save(self, *args, **kwargs):
        film = self.film
        if not film.name_original or (film.name == film.name_original):
            self.is_original_language = True

        error_subject = None
        try:
            agreement_params = dict(
                    cinema=self.cinema_hall.cinema,
                    dimension=self.dimension,
                    is_original_language=self.is_original_language,
                    film=self.film)
            additional_agreement = AdditionalAgreement.objects.filter_by_date(self.date).get(
                    **agreement_params)
            agreement_params['date'] = self.date
        except AdditionalAgreement.DoesNotExist:
            error_subject = 'Для сеанса нет доп. соглашения'
        except MultipleObjectsReturned:
            error_subject = 'Параметрам сеанса соответствуют нескольким доп. соглашениям'
        else:
            self.additional_agreement = additional_agreement
            if additional_agreement.vat is not None:
                self.vat = additional_agreement.vat

        if self.vat:
            self.gross_yield_without_vat = self.gross_yield - self.gross_yield * Decimal(VAT_RATE)
        else:
            self.gross_yield_without_vat = self.gross_yield

        # movie rental week is from Thursday to Wednesday
        week_day = self.date.weekday()
        if week_day > 2:
            self.week = self.date - timedelta(days=week_day - 3)
        else:
            self.week = self.date - timedelta(days=week_day + 4)

        self.month = self.date - timedelta(days=self.date.day - 1)

        super().save(*args, **kwargs)

        if error_subject:
            session_url = build_full_url(reverse('admin:common_session_change', args=(self.id, )))
            async_mail_admins.delay(
                subject=error_subject,
                message='Невозможно автоматически выбрать доп. соглашение для сеанса {url}.\n'
                        'Параметры поиска доп соглашения: {params}'.format(
                            url=session_url,
                            params=', '.join(['{}={}'.format(
                                    k, v) for k, v in agreement_params.items()])))

    @property
    def cinema_name(self):
        return self.cinema_hall.cinema.name


class SessionUpdateRequest(TimeStampedModel):
    session = models.ForeignKey(Session)
    data = JSONField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Запросы на обновление сеансов'
        verbose_name = 'Запрос на обновление сеанса'

    def __str__(self):
        return '{} {}'.format(self.session.id, self.created)


class ConfirmedMonthlyReport(TimeStampedModel):
    cinema = models.ForeignKey(Cinema, verbose_name='Кинотеатр', related_name='confirmed_reports')
    film = models.ForeignKey(Film, verbose_name='Фильм')
    dimension = models.ForeignKey(Dimension, verbose_name='Формат')
    month = models.DateField('Месяц')
    creator = models.ForeignKey('users.User', verbose_name='Подал отчёт')

    class Meta:
        verbose_name_plural = 'Подтверждённые расчётные бланки'
        verbose_name = 'Подтверждённый расчётный бланк'
        unique_together = (('cinema', 'film', 'dimension', 'month'), )

    def __str__(self):
        return '{} {} {}'.format(self.cinema, self.film.name, self.month_str)

    @property
    def month_str(self):
        return MONTHS[self.month.month - 1]


class Feedback(TimeStampedModel):
    sender = models.ForeignKey('users.User', related_name='feedbacks', verbose_name='Отправитель')
    text = models.TextField('Текст')
    receivers_emails = models.CharField('Почтовые адреса получателей', max_length=256)

    class Meta:
        verbose_name_plural = 'Обратная связь'
        verbose_name = 'Обратная связь'

    def __str__(self):
        return self.text[:100]


class TimeBackup(models.Model):
    start = models.TimeField('Время бекапа')


class BackupFile(models.Model):
    start = models.DateTimeField('Время начала')
    end = models.DateTimeField('Время окончания')
    backup_file_path = models.FilePathField(path=settings.BACKUP_DIR_PATH, match='*.json')

    class Meta:
        verbose_name = 'файл бекапа'
        verbose_name_plural = 'файлы бекапов'

    def __str__(self):
        return self.backup_file_path

class BackupLoadTime(models.Model):
    start = models.DateTimeField('Время начала')
    end = models.DateTimeField('Время окончания')
    
    class Meta:
        verbose_name = 'восстановление из бекапа'
        verbose_name_plural = 'восстановление из бекапа'

    def __str__(self):
        return '{}-{}'.format(self.start.strftime("%Y-%m-%d %H:%M:%S"),
                              self.end.strftime("%Y-%m-%d %H:%M:%S"))

def file_cleanup(sender, **kwargs):
    """
    File cleanup callback used to emulate delete
    behavior using signals.

    Usage:
    >>> from django.db.models.signals import post_delete
    >>> post_delete.connect(file_cleanup, sender=MyModel, dispatch_uid="mymodel.file_cleanup")
    """
    for field in sender._meta.get_fields():
        if field and isinstance(field, models.FilePathField):
            inst = kwargs['instance']
            m = inst.__class__._default_manager
            fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR,
                                                         settings.BACKUP_DIR_PATH))
            name = getattr(inst, field.name).split('/')[-1]
            if fs.exists(name):
                try:
                    fs.delete(name)
                except:
                    pass

post_delete.connect(file_cleanup, sender=BackupFile,
                    dispatch_uid="backupfile.backup_file_path.file_cleanup")

