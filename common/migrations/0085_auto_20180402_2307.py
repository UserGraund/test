# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-04-02 20:07
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('common', '0084_auto_20180329_2309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='additionalagreement',
            name='one_c_number',
            field=models.CharField(blank=True, max_length=64, unique=True, verbose_name='номер 1С'),
        ),
        migrations.RemoveField(
            model_name='chain',
            name='access_to_reports',
        ),
        migrations.AddField(
            model_name='chain',
            name='access_to_reports',
            field=models.ManyToManyField(blank=True, related_name='report_chain', to=settings.AUTH_USER_MODEL, verbose_name='Доступ к отчётам'),
        ),
        migrations.RemoveField(
            model_name='chain',
            name='responsible_for_daily_reports',
        ),
        migrations.AddField(
            model_name='chain',
            name='responsible_for_daily_reports',
            field=models.ManyToManyField(blank=True, related_name='chain', to=settings.AUTH_USER_MODEL, verbose_name='Дневные отчёты'),
        ),
    ]
