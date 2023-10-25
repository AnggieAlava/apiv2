# Generated by Django 3.2.20 on 2023-09-08 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authenticate', '0043_auto_20230817_0837'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvite',
            name='asset_slug',
            field=models.SlugField(blank=True,
                                   help_text='If set, the user signed up because of an Asset',
                                   max_length=40,
                                   null=True),
        ),
        migrations.AddField(
            model_name='userinvite',
            name='conversion_info',
            field=models.JSONField(blank=True,
                                   default=None,
                                   help_text='UTMs and other conversion information.',
                                   null=True),
        ),
        migrations.AddField(
            model_name='userinvite',
            name='event_slug',
            field=models.SlugField(blank=True,
                                   help_text='If set, the user signed up because of an Event',
                                   max_length=40,
                                   null=True),
        ),
        migrations.AddField(
            model_name='userinvite',
            name='has_marketing_consent',
            field=models.BooleanField(default=False),
        ),
    ]