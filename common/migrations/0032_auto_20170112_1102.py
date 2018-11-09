# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-12 09:02
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0031_auto_20170111_1639'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='xlsreportsupload',
            name='errors',
        ),
        migrations.AddField(
            model_name='xlssessionsreport',
            name='errors',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=256), blank=True, null=True, size=None),
        ),
    ]