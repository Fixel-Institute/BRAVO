# Generated by Django 4.0.6 on 2023-05-31 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Backend', '0003_mobileuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalrecording',
            name='recording_info',
            field=models.JSONField(default=dict, null=True),
        ),
    ]