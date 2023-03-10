# Generated by Django 3.2.16 on 2023-03-02 06:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0021_auto_20230228_0343'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='plan',
            name='available_event_type_sets',
        ),
        migrations.RemoveField(
            model_name='plan',
            name='available_mentorship_service_sets',
        ),
        migrations.AddField(
            model_name='plan',
            name='event_type_set',
            field=models.ForeignKey(blank=True,
                                    default=None,
                                    help_text='Event type sets to be sold in this service and plan',
                                    null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    to='payments.eventtypeset'),
        ),
        migrations.AddField(
            model_name='plan',
            name='mentorship_service_set',
            field=models.ForeignKey(blank=True,
                                    default=None,
                                    help_text='Mentorship service sets to be sold in this service and plan',
                                    null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    to='payments.mentorshipserviceset'),
        ),
    ]