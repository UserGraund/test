# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-03 18:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0010_auto_20170103_1359'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='session',
            name='month',
        ),
        migrations.RemoveField(
            model_name='session',
            name='week',
        ),
        migrations.AddField(
            model_name='session',
            name='start_of_month',
            field=models.DateField(blank=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='session',
            name='start_of_week',
            field=models.DateField(blank=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]