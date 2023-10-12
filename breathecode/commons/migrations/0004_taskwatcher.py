# Generated by Django 3.2.21 on 2023-10-12 06:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('commons', '0003_taskmanager_attemps'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskWatcher',
            fields=[
                ('id',
                 models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                     verbose_name='ID')),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('on_error', models.BooleanField(default=True)),
                ('on_success', models.BooleanField(default=True)),
                ('watch_progress', models.BooleanField(default=False)),
                ('tasks',
                 models.ManyToManyField(blank=True,
                                        help_text='Notify for the progress of these tasks',
                                        related_name='watchers',
                                        to='commons.TaskManager')),
                ('user',
                 models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                      to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
