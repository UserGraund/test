# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-11 18:16
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('common', '0072_auto_20170609_1413'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfirmedMonthlyReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('month', models.DateField(blank=True, null=True)),
                ('cinema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Cinema')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('dimension', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Dimension')),
                ('film', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Film')),
            ],
            options={
                'verbose_name': 'Подтверждённый отчётный бланк',
                'verbose_name_plural': 'Подтверждённые отчётные бланки',
            },
        ),
    ]
