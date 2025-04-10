# Generated by Django 4.2.8 on 2025-03-09 22:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0014_attendance'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeedbackTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('content', models.TextField()),
                ('category', models.CharField(choices=[('positive', 'Positive Feedback'), ('improvement', 'Needs Improvement'), ('technical', 'Technical Skills'), ('behavioral', 'Behavioral Skills'), ('general', 'General Comments')], default='general', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['category', 'title'],
            },
        ),
    ]
