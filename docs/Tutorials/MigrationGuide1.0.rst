BRAVO_SSR to BRAVO Migration Guide
=========================================

Overview
-----------------------------------------

BRAVO_SSR is the initial public version of BRAVO, written purely in Django. 
Due to expansion of the platform for multiple features not limited to Percept Brain-Sensing recordings, 
the new BRAVO platform utilize a slightly different SQL table setup that is slightly different from the initial BRAVO models.

Main Modifications
-------------------------------------------

- Platform User "user_name" is a combination of "first_name" and "last_name"
- Platform User "uniqueUserID" is renamed to "unique_user_id"
- Platform User may contain "is_mobile" identifier for mobile app authentication. 

- Percept Session file will now have "session_date" column.
- Neural Activity Recording utilize folder that organize recordings.
- Therapy History object will extract more data by providing Adaptive DBS Support.

Database name is also being edited from ``PerceptDashboard`` to ``Backend``. 

Procedure
-------------------------------------------

Changes are mainly minor modifications, and migration is simply extracting existing table
and recreate them in new database. A simple script is available for migration. 
Once new database is completely setup. User can call 

.. code-block:: bash 

  # Primary Migration from SQL Database to new SQL Database 
  python3 manage.py MigrateFromV1 $OLD_DATABASE_PATH

  # Refresh Session to fix an old bug where lead information stored in device object is overwritten by old information.
  python3 manage.py Refresh Sessions All

  # Refresh Therapy History to add aDBS and Cycling Stimulation information.
  python3 manage.py Refresh TherapyHistory All


Where the ``$OLD_DATABASE_PATH`` is the path to your BRAVO_SSR Data Storage folder. Doing the migration
will not delete the old storage folder, but related files will be copied to the new database and 
entries will be added to the SQL Table.