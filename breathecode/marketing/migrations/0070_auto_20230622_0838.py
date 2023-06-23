# Generated by Django 3.2.19 on 2023-06-22 08:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authenticate', '0040_userinvite_is_email_validated'),
        ('marketing', '0069_alter_activecampaignwebhook_run_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='has_waiting_list',
            field=models.BooleanField(default=False, help_text='Has waiting list?'),
        ),
        migrations.AddField(
            model_name='course',
            name='invites',
            field=models.ManyToManyField(blank=True,
                                         help_text="Plan's invites",
                                         related_name='courses',
                                         to='authenticate.UserInvite'),
        ),
    ]
