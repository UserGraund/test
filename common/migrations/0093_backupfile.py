# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-07-18 18:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0092_auto_20180704_0058'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(verbose_name='Время начала')),
                ('end', models.DateTimeField(verbose_name='Время окончания')),
                ('backup_file_path', models.FilePathField(match='*.json', path='/vagrant/erp-kinomania/backups/')),
            ],
        ),
    ]
