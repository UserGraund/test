# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-10 10:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0023_auto_20170110_1141'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='additionalagreement',
            name='chain',
        ),
        migrations.AlterUniqueTogether(
            name='additionalagreement',
            unique_together=set([('cinema', 'film', 'active_from', 'dimension')]),
        ),
    ]
