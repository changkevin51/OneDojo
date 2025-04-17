# Generated by Django 4.2.8 on 2025-04-17 00:45

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0022_calendarevent_is_birthday'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendarevent',
            name='visibility_type',
            field=models.CharField(choices=[('all', 'All Students'), ('classes', 'Specific Classes'), ('students', 'Specific Students')], default='all', max_length=10),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='visible_to_classes',
            field=models.ManyToManyField(blank=True, related_name='calendar_events', to='portal.unit'),
        ),
        migrations.AddField(
            model_name='calendarevent',
            name='visible_to_students',
            field=models.ManyToManyField(blank=True, related_name='visible_events', to=settings.AUTH_USER_MODEL),
        ),
    ]
