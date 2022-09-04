# Generated by Django 3.2.15 on 2022-08-25 05:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0010_auto_20220812_2033'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assetkeyword',
            name='optimization_rating',
        ),
        migrations.AddField(
            model_name='asset',
            name='last_seo_scan_at',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='optimization_rating',
            field=models.FloatField(blank=True,
                                    default=None,
                                    help_text='Automatically filled (1 to 100)',
                                    null=True),
        ),
        migrations.AddField(
            model_name='asset',
            name='seo_json_status',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='asset',
            name='slug',
            field=models.SlugField(
                help_text=
                'Asset must be unique within the entire database because they could be published into 4geeks.com (shared among all academies)',
                max_length=200,
                unique=True),
        ),
        migrations.AlterField(
            model_name='assetcategory',
            name='slug',
            field=models.SlugField(max_length=200),
        ),
        migrations.AlterField(
            model_name='assetkeyword',
            name='slug',
            field=models.SlugField(max_length=200),
        ),
        migrations.AlterField(
            model_name='assettechnology',
            name='slug',
            field=models.SlugField(help_text='Technologies are unified within all 4geeks.com',
                                   max_length=200,
                                   unique=True),
        ),
        migrations.AlterField(
            model_name='keywordcluster',
            name='slug',
            field=models.SlugField(max_length=200),
        ),
        migrations.CreateModel(
            name='SEOReport',
            fields=[
                ('id',
                 models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type',
                 models.CharField(help_text='Must be one of the services.seo.action script names',
                                  max_length=40)),
                ('status',
                 models.CharField(choices=[('PENDING', 'Pending'), ('ERROR', 'Error'), ('OK', 'Ok'),
                                           ('WARNING', 'Warning')],
                                  default='PENDING',
                                  help_text='Internal state automatically set by the system',
                                  max_length=20)),
                ('log', models.TextField(blank=True, default=None, null=True)),
                ('rating',
                 models.FloatField(blank=True,
                                   default=None,
                                   help_text='Automatically filled (1 to 100)',
                                   null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            to='registry.asset')),
            ],
        ),
    ]
