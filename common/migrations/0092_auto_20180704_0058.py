# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-07-03 21:58
from __future__ import unicode_literals

from datetime import time

from django.db import migrations


def forward(apps, schema_editor):
    TimeModel = apps.get_model('common', 'TimeBackup')
    TimeModel.objects.create(start=time())


def backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0091_auto_20180704_0057'),
    ]

    operations = [
        migrations.RunPython(forward, backward)
    ]
