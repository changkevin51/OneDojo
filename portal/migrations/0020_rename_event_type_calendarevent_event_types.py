# Generated by Django 4.2.8 on 2025-04-05 03:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0019_alter_calendarevent_event_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='calendarevent',
            old_name='event_type',
            new_name='event_types',
        ),
    ]
