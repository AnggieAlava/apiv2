# Generated by Django 3.2.15 on 2022-08-17 03:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mentorship', '0014_auto_20220719_0759'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentorprofile',
            name='one_line_bio',
            field=models.TextField(blank=True,
                                   default=None,
                                   help_text='Will be shown to showcase the mentor',
                                   max_length=60,
                                   null=True),
        ),
        migrations.AddField(
            model_name='mentorprofile',
            name='rating',
            field=models.FloatField(
                blank=True,
                default=None,
                help_text='Automatically filled when new survey responses are collected about this mentor',
                null=True),
        ),
    ]