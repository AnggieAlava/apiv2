# Generated by Django 3.2.23 on 2023-11-28 02:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0038_service_icon_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='is_renewable',
            field=models.BooleanField(
                default=True,
                help_text='Is if true, it will create a renewable subscription instead of a plan financing'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='time_of_life',
            field=models.IntegerField(blank=True,
                                      default=1,
                                      help_text='Plan lifetime (e.g. 1, 2, 3, ...)',
                                      null=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='time_of_life_unit',
            field=models.CharField(blank=True,
                                   choices=[('DAY', 'Day'), ('WEEK', 'Week'), ('MONTH', 'Month'),
                                            ('YEAR', 'Year')],
                                   default='MONTH',
                                   help_text='Lifetime unit (e.g. DAY, WEEK, MONTH or YEAR)',
                                   max_length=10,
                                   null=True),
        ),
        migrations.AlterField(
            model_name='planfinancing',
            name='plans',
            field=models.ManyToManyField(blank=True, help_text='Plans to be supplied', to='payments.Plan'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plans',
            field=models.ManyToManyField(blank=True, help_text='Plans to be supplied', to='payments.Plan'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='service_items',
            field=models.ManyToManyField(blank=True,
                                         help_text='Service items to be supplied',
                                         through='payments.SubscriptionServiceItem',
                                         to='payments.ServiceItem'),
        ),
    ]
