# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-27 16:30
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('common', '0051_auto_20170127_1727'),
    ]

    operations = [
        migrations.AddField(
            model_name='chain',
            name='access_to_reports',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='report_chain', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='chain',
            name='responsible_for_daily_reports',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chain', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cinema',
            name='access_to_reports',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='report_cinemas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cinema',
            name='responsible_for_daily_reports',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cinemas', to=settings.AUTH_USER_MODEL),
        ),
    ]
