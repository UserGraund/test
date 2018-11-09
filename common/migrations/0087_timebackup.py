# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-06-29 14:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0086_auto_20180620_2328'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeBackup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hour', models.IntegerField(default=0, verbose_name='Час')),
                ('minute', models.IntegerField(default=0, verbose_name='Минута')),
            ],
        ),
    ]
