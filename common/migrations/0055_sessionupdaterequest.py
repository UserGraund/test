# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-10 16:27
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0054_auto_20170131_1047'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionUpdateRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Session')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
