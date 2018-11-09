# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-10 10:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0025_auto_20170110_1204'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactInformation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('title', models.CharField(max_length=64)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('cinema', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='common.Cinema')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='contactinformation',
            unique_together=set([('cinema', 'title')]),
        ),
    ]