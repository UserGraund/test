# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-20 17:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0061_auto_20170320_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalcontract',
            name='number',
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
