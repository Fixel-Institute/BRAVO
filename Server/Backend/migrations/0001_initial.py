# Generated by Django 4.0.6 on 2023-05-11 12:21

import Backend.models
from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BrainSenseRecording',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recording_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('recording_type', models.CharField(default='', max_length=32)),
                ('recording_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('recording_info', models.JSONField(default=dict, null=True)),
                ('recording_duration', models.FloatField(default=0)),
                ('recording_datapointer', models.CharField(default='', max_length=255)),
                ('source_file', models.CharField(default='', max_length=255)),
            ],
            options={
                'ordering': ['recording_date'],
            },
        ),
        migrations.CreateModel(
            name='CustomAnnotations',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('patient_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('event_name', models.CharField(default='', max_length=255)),
                ('event_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('event_duration', models.FloatField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='CustomizedSurvey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('survey_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('version', models.IntegerField(default=1)),
                ('creator', models.UUIDField(default=uuid.uuid4)),
                ('authorized_users', models.JSONField(default=list)),
                ('name', models.CharField(default='', max_length=64)),
                ('url', models.CharField(default='', max_length=64)),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('contents', models.JSONField(default=list)),
                ('archived', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DeidentifiedPatientID',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('researcher_id', models.UUIDField(default=uuid.uuid1)),
                ('authorized_patient_id', models.UUIDField(default=uuid.uuid4)),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('authorized_time_range', models.JSONField(default=Backend.models.PerceptRecordingDefaultAuthorization, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DeidentifiedPatientTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('researcher_id', models.UUIDField(default=uuid.uuid1)),
                ('lookup_table', models.TextField(default='', max_length=999999)),
            ],
        ),
        migrations.CreateModel(
            name='ExternalRecording',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recording_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('patient_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('recording_type', models.CharField(default='', max_length=32)),
                ('recording_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('recording_duration', models.FloatField(default=0)),
                ('recording_datapointer', models.CharField(default='', max_length=255)),
            ],
            options={
                'ordering': ['recording_date'],
            },
        ),
        migrations.CreateModel(
            name='ExternalSensorPairing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('device_mac', models.CharField(default='', max_length=64)),
                ('device_name', models.CharField(default='', max_length=64)),
                ('pairing_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('pairing_code', models.CharField(default='', max_length=10)),
                ('pairing_password', models.CharField(default='', max_length=64)),
                ('paired', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ImpedanceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('impedance_record', models.JSONField(default=dict, null=True)),
                ('session_date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Institute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(default='', max_length=255)),
                ('last_name', models.CharField(default='', max_length=255)),
                ('diagnosis', models.CharField(default='', max_length=255)),
                ('institute', models.CharField(default='', max_length=255)),
                ('medical_record_number', models.CharField(default='', max_length=255)),
                ('birth_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('tags', models.JSONField(default=list)),
                ('research_study_id', models.JSONField(default=list, null=True)),
                ('device_deidentified_id', models.JSONField(default=list, null=True)),
                ('patient_identifier_hashfield', models.CharField(default='', max_length=255)),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('last_change', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='PatientCustomEvents',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('event_name', models.CharField(default='', max_length=32)),
                ('event_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('sensing_exist', models.BooleanField(default=False)),
                ('brainsense_psd', models.JSONField(default=list, null=True)),
                ('source_file', models.CharField(default='', max_length=256)),
            ],
            options={
                'ordering': ['-event_time'],
            },
        ),
        migrations.CreateModel(
            name='PerceptDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial_number', models.CharField(default='', max_length=512)),
                ('device_name', models.CharField(default='', max_length=32)),
                ('device_type', models.CharField(default='Percept PC', max_length=32)),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('patient_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('implant_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('device_identifier_hashfield', models.CharField(default='', max_length=255)),
                ('device_location', models.CharField(default='', max_length=32)),
                ('device_lead_configurations', models.JSONField(default=list, null=True)),
                ('device_last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('device_eol_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('authority_level', models.CharField(default='Research', max_length=32)),
                ('authority_user', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='PerceptSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deidentified_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('session_file_path', models.CharField(default='', max_length=255)),
                ('session_source_filename', models.CharField(default='', max_length=255)),
                ('session_date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='PredictionModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recording_id', models.UUIDField(default=uuid.uuid4)),
                ('recording_channel', models.CharField(default='', max_length=64)),
                ('recording_contact_type', models.CharField(default='', max_length=64)),
                ('model_details', models.JSONField(default=dict, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProcessingQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner', models.UUIDField(default=uuid.uuid4)),
                ('queue_id', models.UUIDField(default=uuid.uuid4)),
                ('type', models.CharField(default='decodeJSON', max_length=255)),
                ('datetime', models.DateTimeField(default=django.utils.timezone.now)),
                ('state', models.CharField(default='InProgress', max_length=255)),
                ('descriptor', models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='RedcapSurveyLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('linkage_id', models.UUIDField(default=uuid.uuid4)),
                ('survey_id', models.UUIDField(default=uuid.uuid4)),
                ('redcap_server', models.CharField(default='', max_length=255)),
                ('redcap_token', models.CharField(default='', max_length=255)),
                ('redcap_survey_name', models.CharField(default='', max_length=255)),
                ('redcap_record_id', models.CharField(default='', max_length=255)),
                ('owner', models.UUIDField(default=uuid.uuid1)),
            ],
        ),
        migrations.CreateModel(
            name='ResearchAccessShareLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('authorized_patient_list', models.JSONField(default=list)),
                ('share_link', models.CharField(default='', max_length=64)),
                ('expiration_time', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='ResearchAuthorizedAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('researcher_id', models.UUIDField(default=uuid.uuid1)),
                ('authorized_patient_id', models.UUIDField(default=uuid.uuid4)),
                ('authorized_recording_type', models.CharField(default='', max_length=255)),
                ('authorized_recording_id', models.UUIDField(default=uuid.uuid4)),
                ('can_edit', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ScheduledSurveys',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('linkage_id', models.UUIDField(default=uuid.uuid4)),
                ('report_id', models.UUIDField(default=uuid.uuid4)),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='SearchTags',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag_name', models.CharField(default='', max_length=255)),
                ('tag_type', models.CharField(default='Patient', max_length=255)),
                ('institute', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyResults',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('survey_id', models.UUIDField(default=uuid.uuid4)),
                ('version', models.IntegerField(default=1)),
                ('responder', models.CharField(default='', max_length=255)),
                ('values', models.JSONField(default=list)),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='TherapyChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('date_of_change', models.DateTimeField(default=django.utils.timezone.now)),
                ('previous_group', models.CharField(default='', max_length=32)),
                ('new_group', models.CharField(default='', max_length=32)),
                ('source_file', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='TherapyHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('history_log_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('device_deidentified_id', models.UUIDField(default=uuid.uuid4)),
                ('therapy_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('group_name', models.CharField(default='', max_length=32)),
                ('group_id', models.CharField(default='', max_length=32)),
                ('active_group', models.BooleanField(default=False)),
                ('therapy_type', models.CharField(default='', max_length=64)),
                ('therapy_details', models.JSONField(default=dict, null=True)),
                ('source_file', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='TwilioService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_id', models.CharField(default='', max_length=255)),
                ('authToken', models.CharField(default='', max_length=255)),
                ('service_id', models.CharField(default='', max_length=255)),
                ('repeat', models.CharField(default='daily', max_length=255)),
                ('receiver', models.JSONField(default=dict)),
                ('enabled', models.BooleanField(default=False)),
                ('timestamps', models.JSONField(default=list)),
                ('linkage_id', models.UUIDField(default=uuid.uuid4)),
                ('patient_id', models.CharField(default='', max_length=255)),
                ('report_id', models.UUIDField(default=uuid.uuid4)),
            ],
        ),
        migrations.CreateModel(
            name='UserConfigurations',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.UUIDField(default=uuid.uuid1, editable=False)),
                ('configuration', models.JSONField(default=dict, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlatformUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('email', models.EmailField(max_length=255, unique=True, verbose_name='Email Address')),
                ('user_name', models.CharField(default='', max_length=255)),
                ('institute', models.CharField(default='Independent', max_length=255)),
                ('unique_user_id', models.UUIDField(default=uuid.uuid1, editable=False, unique=True)),
                ('register_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('configuration', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('is_mobile', models.BooleanField(default=False)),
                ('is_admin', models.BooleanField(default=False)),
                ('is_clinician', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
