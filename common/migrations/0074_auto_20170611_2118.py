# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-11 18:18
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0073_confirmedmonthlyreport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='month',
            field=models.DateField(default=datetime.date(2017, 6, 11)),
            preserve_default=False,
        ),
    ]
