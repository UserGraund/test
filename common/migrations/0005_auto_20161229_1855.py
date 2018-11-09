# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-29 16:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_auto_20161228_1305'),
    ]

    operations = [
        migrations.AddField(
            model_name='additionalagreement',
            name='cinema',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.Cinema'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='chain',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.Chain'),
        ),
    ]