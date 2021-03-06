# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-07-26 03:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0093_backupfile'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupLoadTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(verbose_name='Время начала')),
                ('end', models.DateTimeField(verbose_name='Время окончания')),
            ],
            options={
                'verbose_name': 'восстановление из бекапа',
                'verbose_name_plural': 'восстановление из бекапа',
            },
        ),
        migrations.AlterModelOptions(
            name='backupfile',
            options={'verbose_name': 'файл бекапа', 'verbose_name_plural': 'файлы бекапов'},
        ),
    ]
