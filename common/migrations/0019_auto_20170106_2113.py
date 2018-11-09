# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-06 19:13
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0018_session_creator'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to=settings.AUTH_USER_MODEL),
        ),
    ]