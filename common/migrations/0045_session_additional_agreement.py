# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-18 18:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0044_auto_20170118_2028'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='additional_agreement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='common.AdditionalAgreement'),
        ),
    ]
