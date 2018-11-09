# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-11 14:39
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0030_xlssessionsreport_xls_filename'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='xlsreportsupload',
            options={'verbose_name': 'Загрузка XLS отчётов', 'verbose_name_plural': 'Загрузки XLS отчётов'},
        ),
        migrations.AlterModelOptions(
            name='xlssessionsreport',
            options={'verbose_name': 'XLS отчёт', 'verbose_name_plural': 'XLS отчёты'},
        ),
        migrations.AlterField(
            model_name='xlsreportsupload',
            name='errors',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='xlsreportsupload',
            name='is_successful',
            field=models.BooleanField(default=True),
        ),
    ]
