# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-21 08:41
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0064_auto_20170321_1037'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='contactinformation',
            unique_together=set([('cinema', 'title', 'email', 'phone_number')]),
        ),
    ]
