# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-21 21:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0059_additionalagreement_is_original_language'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='additionalagreement',
            unique_together=set([('cinema', 'film', 'dimension', 'is_original_language', 'active_date_range')]),
        ),
    ]
