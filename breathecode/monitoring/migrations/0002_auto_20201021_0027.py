# Generated by Django 3.1.2 on 2020-10-21 00:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0011_auto_20201006_0058'),
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='academy',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='admissions.academy'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='endpoint',
            name='application',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='monitoring.application'),
            preserve_default=False,
        ),
    ]