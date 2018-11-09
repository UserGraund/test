# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-06 11:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0013_cinema_halls_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='XlsSessionsReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('xls_file', models.FileField(upload_to='xls_reports')),
            ],
            options={
                'verbose_name': 'XLS Отчёт',
                'verbose_name_plural': 'XLS Отчёты',
            },
        ),
        migrations.AlterField(
            model_name='cinema',
            name='halls_count',
            field=models.PositiveSmallIntegerField(verbose_name='Залов'),
        ),
    ]