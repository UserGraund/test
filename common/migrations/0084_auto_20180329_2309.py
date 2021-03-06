# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-03-29 20:09
from __future__ import unicode_literals

from django.db import migrations


def forward(apps, schema_editor):
    Cinema = apps.get_model('common', 'Cinema')

    for cinema in Cinema.objects.all():
        if cinema.access_to_reports_test is not None:
            cinema.access_to_reports.add(cinema.access_to_reports_test)
        if cinema.responsible_for_daily_reports_test is not None:
            cinema.responsible_for_daily_reports.add(cinema.responsible_for_daily_reports_test)
        cinema.save()


def backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0083_auto_20180327_2156'),
    ]

    operations = [
        migrations.RunPython(forward, backward)
    ]
