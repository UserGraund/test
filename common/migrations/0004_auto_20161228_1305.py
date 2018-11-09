# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-28 11:05
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0003_auto_20161228_1227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='gross_yield',
            field=models.DecimalField(decimal_places=2, default=Decimal(0), max_digits=10, verbose_name='Доход'),
            preserve_default=False,
        ),
    ]
