# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-07-03 21:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0090_timebackup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timebackup',
            name='start',
            field=models.TimeField(verbose_name='Время бекапа'),
        ),
    ]
