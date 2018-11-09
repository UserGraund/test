from datetime import timedelta

from django.db import models
from django.db.models import Case, NullBooleanField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When


class CinemaQuerySet(models.QuerySet):
    def annotate_finished_by_date(self, date):
        from common.models import AdditionalAgreement
        from common.models import FinishedCinemaReportDate

        finished_cinemas_ids = FinishedCinemaReportDate.objects.filter(
                date=date).values_list('cinema_id', flat=True)

        active_agreements_ids = AdditionalAgreement.objects.filter_by_date(
                date).values_list('cinema', flat=True)

        return self.annotate(
            is_daily_report_finished=Case(
                When(id__in=finished_cinemas_ids, then=True),
                When(~Q(id__in=active_agreements_ids), then=None),
                default=Value(False),
                output_field=NullBooleanField()))


class CinemaManager(models.Manager):

    def get_queryset(self):
        return CinemaQuerySet(self.model, using=self._db)

    def annotate_finished_by_date(self, date):
        return self.get_queryset().annotate_finished_by_date(date)


class AdditionalAgreementQuerySet(models.QuerySet):
    def filter_by_date(self, date):
        return self.filter(active_date_range__overlap=[date - timedelta(1), date + timedelta(1)])


class AdditionalAgreementManager(models.Manager):

    def get_queryset(self):
        return AdditionalAgreementQuerySet(self.model, using=self._db)

    def filter_by_date(self, date):
        return self.get_queryset().filter_by_date(date)
