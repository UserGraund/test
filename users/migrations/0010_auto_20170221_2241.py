# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-21 20:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_auto_20170217_0940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='is_staff',
            field=models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='Админ'),
        ),
        migrations.AlterField(
            model_name='user',
            name='view_all_reports',
            field=models.BooleanField(default=False, help_text='Просмотр и экспорт отчётов по всем кинотеатрам'),
        ),
    ]
