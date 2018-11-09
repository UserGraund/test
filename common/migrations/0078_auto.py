# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-16 15:00
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0077_auto_20171007_1224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='additionalagreement',
            name='vat',
            field=models.NullBooleanField(
                blank=True, null=True,
                verbose_name='НДС',
                help_text='Если НДС не указано, то будет взято значение из кинотеатра'
            )
        )
    ]