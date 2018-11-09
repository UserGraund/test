# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-30 08:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_auto_20161229_1855'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='gross_yield_without_vat',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Доход с вычетом ПДВ'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='cinema',
            name='chain',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cinemas', to='common.Chain', verbose_name='Сеть'),
        ),
        migrations.AlterField(
            model_name='cinema',
            name='city',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cinemas', to='common.City', verbose_name='Город'),
        ),
    ]
