# Generated by Django 4.0.6 on 2024-04-30 19:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Backend', '0007_customannotations_event_type'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BrainSenseRecording',
            new_name='NeuralActivityRecording',
        ),
    ]
