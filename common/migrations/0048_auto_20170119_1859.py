# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-19 16:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0047_auto_20170119_1119'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='finishedcinemareportdate',
            options={'verbose_name': 'Дата завершенния отчёта', 'verbose_name_plural': 'Даты завершенния отчётов'},
        ),
        migrations.AddField(
            model_name='xlsreportsupload',
            name='city',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='common.City'),
        ),
    ]
