# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-13 14:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0034_auto_20170112_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='additionalagreement',
            name='language',
            field=models.CharField(choices=[('ukrainian', 'ukrainian'), ('russian', 'russian'), ('english', 'english')], default='ukrainian', max_length=10),
        ),
    ]
