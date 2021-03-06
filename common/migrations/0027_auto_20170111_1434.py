# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-11 12:34
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0026_auto_20170110_1231'),
    ]

    operations = [
        migrations.CreateModel(
            name='XlsReportsUpload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_successful', models.BooleanField()),
                ('errors', django.contrib.postgres.fields.jsonb.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='contactinformation',
            options={'verbose_name': 'Контакт', 'verbose_name_plural': 'Контакты'},
        ),
        migrations.AddField(
            model_name='session',
            name='xls_session_report',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='common.XlsSessionsReport'),
        ),
        migrations.AlterField(
            model_name='contactinformation',
            name='title',
            field=models.CharField(default='администратор', max_length=64),
        ),
    ]
