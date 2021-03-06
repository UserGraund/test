# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-12 14:41
from __future__ import unicode_literals

import django.contrib.postgres.fields.ranges
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0068_auto_20170402_1219'),
    ]

    operations = [
        migrations.AddField(
            model_name='generalcontract',
            name='cinemas',
            field=models.ManyToManyField(blank=True, related_name='general_contracts', to='common.Cinema'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='active_date_range',
            field=django.contrib.postgres.fields.ranges.DateRangeField(verbose_name='Активно "с" - "по"'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='cinema',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.Cinema', verbose_name='Кинотеатр'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='contract',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.GeneralContract', verbose_name='Контракт'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='dimension',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.Dimension', verbose_name='Форматы'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='film',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreements', to='common.Film', verbose_name='Фильм'),
        ),
        migrations.AlterField(
            model_name='additionalagreement',
            name='is_original_language',
            field=models.BooleanField(default=False, help_text='Показ фильма на языке оригинала?', max_length=10, verbose_name='Показ на языке оригинала'),
        ),
        migrations.AlterField(
            model_name='session',
            name='additional_agreement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='common.AdditionalAgreement', verbose_name='Доп. соглашение'),
        ),
    ]
