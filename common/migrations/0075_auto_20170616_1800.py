# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-16 15:00
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0074_auto_20170611_2118'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='confirmedmonthlyreport',
            options={'verbose_name': 'Подтверждённый расчётный бланк', 'verbose_name_plural': 'Подтверждённые расчётный бланки'},
        ),
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='cinema',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Cinema', verbose_name='Кинотеатр'),
        ),
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Подал отчёт'),
        ),
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='dimension',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Dimension', verbose_name='Формат'),
        ),
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='film',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Film', verbose_name='Фильм'),
        ),
        migrations.AlterField(
            model_name='confirmedmonthlyreport',
            name='month',
            field=models.DateField(verbose_name='Месяц'),
        ),
        migrations.AlterUniqueTogether(
            name='confirmedmonthlyreport',
            unique_together=set([('cinema', 'film', 'dimension', 'month')]),
        ),
    ]