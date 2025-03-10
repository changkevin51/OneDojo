# Generated by Django 4.2.8 on 2025-03-08 00:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0013_alter_assignment_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('late', 'Late')], default='present', max_length=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('marked_by', models.ForeignKey(limit_choices_to={'is_teacher': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marked_attendances', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(limit_choices_to={'is_student': True}, on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to=settings.AUTH_USER_MODEL)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='portal.unit')),
            ],
            options={
                'ordering': ['-date', 'unit'],
                'unique_together': {('student', 'unit', 'date')},
            },
        ),
    ]
