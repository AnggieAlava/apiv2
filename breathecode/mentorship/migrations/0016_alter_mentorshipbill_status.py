# Generated by Django 3.2.15 on 2022-08-31 00:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mentorship', '0015_auto_20220817_0355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mentorshipbill',
            name='status',
            field=models.CharField(choices=[('RECALCULATE', 'Recalculate'), ('DUE', 'Due'),
                                            ('APPROVED', 'Approved'), ('PAID', 'Paid'),
                                            ('IGNORED', 'Ignored')],
                                   default='DUE',
                                   max_length=20),
        ),
    ]