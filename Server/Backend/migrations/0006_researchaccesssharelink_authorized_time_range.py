# Generated by Django 4.0.6 on 2023-11-14 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Backend', '0005_patient_gender_patient_patient_info_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchaccesssharelink',
            name='authorized_time_range',
            field=models.JSONField(default=dict, null=True),
        ),
    ]
