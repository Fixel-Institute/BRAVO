BRAVO V2.1.x to V2.2.0 Migration Guide
=========================================

Overview
-----------------------------------------

BRAVO V2.2.0 implemented new data structure for existing data to allow more universal formatting when used with external data. 
The changes are significant that will lead to errors when combining with previous version database. Therefore, 
migration will require re-processing of all data.

Main Modifications
-------------------------------------------

- New Database Table: CombinedRecordingAnalysis
- New Database Table: MobileUser
- New Database Field: ExternalRecording.recording_info

- Data Format Changes for certain third party medical device recordings. 
- Allow External Recordings to be combined with third party medical device recordings for analysis.

Procedure
-------------------------------------------

Due to major database redesign to work with external data and have a common data structure moving forward, 
existing logs must be re-processed again. This approach will run through all session files currently in the database. 

.. danger::

  You must stop the processing queue script in crontab. You can do ``sudo service cron stop`` to stop cron before running the following script. 
  Once the migration is done, you can start cron job again by ``sudo service cron start``. This will avoid processing conflicts. 

.. code-block:: bash 

  # Database Change 
  python3 manage.py migrate

  # Reprocess all existing data
  python3 manage.py MigrateFromV2.1 
