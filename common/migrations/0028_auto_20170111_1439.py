# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-11 12:39
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0027_auto_20170111_1434'),
    ]

    operations = [
        migrations.AddField(
            model_name='xlssessionsreport',
            name='report_upload',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='common.XlsReportsUpload'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='xlsreportsupload',
            name='errors',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]