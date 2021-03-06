# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-17 07:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0055_sessionupdaterequest'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sessionupdaterequest',
            options={'verbose_name': 'Запрос на обновление сеанса', 'verbose_name_plural': 'Запросы на обновление сеансов'},
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='language',
            field=models.CharField(choices=[('ukrainian', 'ukrainian'), ('russian', 'russian'), ('english', 'english')], default='ukrainian', help_text='Язык показа', max_length=10),
        ),
    ]
