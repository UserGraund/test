# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-06-20 20:28
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0085_auto_20180402_2307'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionupdaterequest',
            name='data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]