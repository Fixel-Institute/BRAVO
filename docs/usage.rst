Usage Documentation
=============================================

The Usage Documentation will provide basic overview on functionality supported by UF BRAVO Platform frontend. 
UF BRAVO Platform is a Python-based Web Application designed to process and analyze Medtronic Percept Neurostimulator data. 
This documentation is intended to provide detail explainations on all functions currently available to the users.

The website you are viewing is a demo version designed for reviewers. 
The demo version contain only "Research" account and deidentified IDs will be used in place of patient identifiers. 
Despite only deidentification IDs are shown, the platform will still retain the data in cloud database to 
demonstrate the capability of long-term data aggregation. It is up to the user to ensure that any data uploaded 
will comply with their institutes' requirement for deidentification. 

Authentication 
---------------------------------------------

Account authentication is done purely on the Python Server. 
In this section, I will describe the primary workflow for account registration and authentication. 

Account Registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Account Registration interface can be seen below.

.. image:: images/Register.png
  :target: images/Register.png
  :width: 400

A basic registration process that require the user to input their first and last name. 
The email address provided by the user will also be used as the Sign In credential (Username). 
All passwords are hashed before storage to ensure securtiy.

Account registered by the user will always default to "Research" account, 
which will remove patient identifications before display in any part of the webpage. 
Promotion of a "Research" account to "Clinician" account can be performed by Admin 
(the local admin at your institute that setup the platform). 
Clinician account will gain access to not only the patient identifiers, 
but also access to all data uploaded by other "Clinician" account within the same institute. 
On contrary, "Research" account's upload will not be added to the "Clinician" account 
nor any other "Research" account, everything will be specific to your account.

As a demo web application, no verification will be used on the registration email. 
Feel free to use made-up email address to register. 
In addition, no "Clinician" nor "Admin" accounts are created for the demo application. 


Account Sign-In
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A user can sign in to their account through the Sign-In interface as shown below. 
Session Cookies are used to store your credentials and further verification within the Web Application. 
If the session idle for more than 60 minutes, the user will be required to login again before continue using the application.

.. image:: images/Login.png
  :target: images/Login.png
  :width: 400

If you enable "Remember me" option, the token requested from the server will have no expiration date and require user to manually 
log out from the account when they are done. This should only be used in local server. 

Patient Table  
---------------------------------------------

Patient Table is the first interface available to the user once logged in. 
A typical patient table containing more than 200 patients is shown below.

The clinician view will display patient's name, diagnosis, device name (and type of neurostimulator), 
and last accessed session file for each patient. A search bar is available to user (top right of the table). 
Filterable keywords include 1) Name, 2) Diagnosis, and 3) Device Name.

In a de-identified "Researcher" account view, fields are mostly leave as blank if user didn't provide any information (Figure 2.2). 
It is up to the researcher to properly label each deidentified patient to avoid confusion. 
Details on how to create a deidentified patient will be discussed in Reference `Upload Deidentified Patient`_ section. 
Details on how to edit an existing patient's information will be discussed in Patient Overview section.

.. _Upload Deidentified Patient:

Upload Deidentified Patient (Research Account)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

User may put in ``Patient Identifier`` and ``Study Identifier`` to better differentiate patients for future references. 
Diagnosis and deidentifiered device name can be left as blank. Once all set, drop or add files to the upload box. 
All files in the upload box will be associated with the specific deidentified patient created. 

.. image:: images/DeidentificationUpload.png
  :target: images/DeidentificationUpload.png
  :width: 400

Once clicking ``Upload``, a new row will be insert to the deidentified patient table. 
If this patient has multiple device, follow instruction in Upload JSON Files (Research Only) to add new devices or additional JSON files. 

User may also opt to use the Batch Upload option (Work In Progress) with identified JSON file. 
The server will deidentify all identified file based on a simple encrypted lookup table upload by the user. 

.. image:: images/BatchDeidentificationUpload.png
  :target: images/BatchDeidentificationUpload.png
  :width: 400

Upload Identified Patient (Clinician Account)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the clinician account view, the patient table will be shown with identifiers. 
Within clinician view, we eliminate the process to manually create patient from the table. 
In contrast, all information are automatically populated when user uploads identified JSON files 
exported from Percept Neurostimulator.

The primary health information extracted are based on 1) Patient First and Last Name, 
and 2) Device Serial Number. Data aggregation is based primarily on Device Serial Number, 
and Patient Identifiers are used to determine if multiple devices belong to the same patient or not. 

Patient Overview 
---------------------------------------------

Patient Overview is detailed interface when a patient is selected from the Patient Table. 
It describes brief information regarding the patient, and the devices currently associated with the specific patient. 
It also serves as the primary navigation to different analysis provided by the platform.

In the device information table, all previous devices associated with the patient will be shown in a table. 
Implant date and estimated battery life may not be accurate in Research Account view if removed as PHI. 
Electrode name and targets are information stored in Percept Device, which will be downloaded along with the JSON file. 
These information will be automatically populated as long as they are not removed from JSON file.

.. image:: images/PatientOverview.png
  :target: images/PatientOverview.png
  :width: 400

.. note:: 

  **Future Updates**:

  Device Type only support Medtronic Percept PC device in Research View. 
  However, the JSON files obtained from Activa SC, PC, or RC are parsible with the platform. Additional supported devices will be included as we obtained more data.

Edit Patient Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

User can edit the patient information through ``Edit Patient Information`` in Patient Overview Page. 
A pop-up dialog will be shown to user with existing patient information. Edit the desire fields 
then click ``UPDATE`` will prompt a database update.

.. image:: images/EditPatientInformation.png
  :target: images/EditPatientInformation.png
  :width: 400

Clicking ``DELETE`` will prompt user to confirm if they want to remove all data associated with this patient ID. 

.. _Upload JSON Files:

Upload JSON Data (Research-Only) [NOT IMPLEMENTED IN 2.0]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is where the Research account should upload their data. 
Unlike Clinician account, the Research account is assumed to be working with deidentified files. 
That means the PHI used to group uploaded JSON into respective Patient ID or Device ID will not be present 
in the uploaded JSON files. This additional process required by the Research account ensure we can properly 
manage the data and organize them in correct group. 

After initial deidentified patient creation in Deidentified Patient Table , the patient overview will be shown 
without any associated device. The user may manually add a Percept PC device via "Add Device" in Red Box 1 of Figure 3.3. 
The fields can all be leave as blank, a fake device ID will be generated in place with most information unavailable to the user. 
Once generated, look at the device table and you will see "Upload" in Red Box 3 of Figure 3.3. 
The user then can upload one or more files associate with that device. If a patient is using bilateral Percept Device, 
the user should create a second blank device and upload files separately. 

Primary Analysis Navigations 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: 
  :widths: 30 70
  :header-rows: 1

  * - Analysis Type
    - Analysis Description
  * - `Therapy History`_
    - Stimulation configurations in all past sessions, and detailed therapy group change trend. 
  * - `BrainSense Survey`_
    - Aggregated BrainSense Survey conducted during each session. 
  * - `BrainSense Streaming`_
    - Realtime Streaming performed during each session. 
  * - `Indefinite Streaming`_
    - Another form of Realtime Streaming, based on simultaneous multi-channel streaming without stimulation. 
  * - `Chronic Brainsense`_
    - Aggregated BrainSense Power recording recorded chronically when patient is using BrainSense-enabled therapy group.  
      
.. _Therapy History:

Therapy History View 
---------------------------------------------

Therapy History provide user an overview of all the past therapy configurations use by the user. 
These information are primarily extracted from ``GroupHistory`` and ``Groups`` JSON Fields in the Session file. 

.. image:: images/TherapyHistory.png
  :target: images/TherapyHistory.png

Therapy Change Log
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Therapy Change Log is a trend generated from Medtronic Session file's ``DiagnosticData.EventLogs`` JSON Field. 
A typical Therapy Change Log looks somewhat like the following code snipet: 

.. code-block:: json

  {
    "DateTime": "2021-10-25T22:35:01Z",
    "ParameterTrendId": "ParameterTrendIdDef.ActiveGroup",
    "NewGroupId": "GroupIdDef.GROUP_B",
    "OldGroupId": "GroupIdDef.GROUP_D"
  }

The datetime field indicate the time of group changes, based on UTC timezone and not patient's local timezone. 
In our platform, all time are presented as the user's local timezone. 

Past Therapy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The therapy configuration extracted from GroupHistory typically contains all information about the stimulation. 
For example, in above figure we present a typical therapy configurations for a patient before their session on December 6th, 2021. 
If you want to view post-session settings, you can toggle the selection to **Post-visit Therapy** to enable display.

The therapy information is displayed in 5 columns: 

  1. Group Name (and Usage percent since last available session)
  2. Therapy active contacts 
  3. Therapy configurations 
  4. BrainSense Configurations
  5. Cycling Stimulation configurations

.. warning::

  BrainSense may show 0.0Hz as sensing frequency in **Past Therapy** tab
  because GroupHistory doesn't always maintain good storage of the BrainSense Frequency. 
  It is typically accurate in Pre-visit Therapy and Post-visit Therapy tab. 

.. _BrainSense Survey:

BrainSense Survey View 
---------------------------------------------

BrainSense Survey are a form of neural signal recording performed by Medtronic's Percept neurostimulator. 
It is stored in the Session JSON file as ``LfpMontageTimeDomain`` JSON Field. 
Each recording contains about 20 seconds time-domain recording recorded at 250Hz sampling rate. 

.. image:: images/BrainSenseSurvey.png
  :target: images/BrainSenseSurvey.png

BrainSense Surveys are snapshots of neural activity at the time of recording. 
We aggregated the Surveys collected over the span of patient's visit at the institute to inform 
changes of brain signal at the target brain region as desease progress (or as therapy delivered).

Power Spectrum across Channels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Power Spectrum are calculated with Welch's Periodogram method. 
The Session JSON files divide one survey into multiple simultaneous recordings of different channels. 
We organize them by performing clustering of timestamp. Recordings perform close to each other are shown side by side for comparison.

The survey displays are interactive and user may selectively choose channels to display or zoom and hover.
A dropdown menu is shown at the top of the page. All surveys are sorted by time.
The user may choose which Survey group to view. Left and right hemisphere are shown in different figure. 
Different channels are colored differently. 

Power Spectrum across Time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BrainSense Survey across time is an analysis perform across time, displayed at the bottom of the webpage.
It present all surveys recorded on the same channel organized by order of acquisition, colored by gradient of colormap. 
A dropdown menu is presented at top-right of the figure block. User may choose which channel to view.

This allow user to visually identify disappearance and emergence of certain brain signals. 
For example, in figure below we can see that an changes in recorded signal between July to October 2021. 

.. image:: images/PSDAcrossTime.png
  :target: images/PSDAcrossTime.png
  :width: 400

.. _BrainSense Streaming:

BrainSense Streaming View 
---------------------------------------------

BrainSense Streaming is one of the most detailed analysis provided by the platform. 
BrainSense Streaming describe the neural recording collected during the real-time streaming of neural signal 
during therapy setup. BrainSense Streaming allow simultaneous bilateral recording if both hemisphere are configured, 
but only one channel at a time. In addition, only Sensing-friendly configuration (E00-E02, E01-E03, E00-E03) are allowed 
to minimize effect of stimulation artifacts. Often time, users may start BrainSense Streaming and adjust stimulation 
parameters to see effect of stimulation on the brain signal.

For multi-channel recordings without stimulation, user may refer to `Indefinite Streaming`_ section.

.. image:: images/BrainSenseStreaming1.png
  :target: images/BrainSenseStreaming1.png
  :width: 800

.. image:: images/BrainSenseStreaming2.png
  :target: images/BrainSenseStreaming2.png
  :width: 800

.. image:: images/BrainSenseStreaming3.png
  :target: images/BrainSenseStreaming3.png
  :width: 800

Select Recording to View
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to BrainSense Survey, BrainSense Streaming data are aggregated for all patients. 
Recordings are organized by date of collection. The platform will also attempt to merge simultaneous 
Left/Right hemisphere recordings into one recording if detected. An example of the selection table is shown in above figures.

If recording contain both Left and Right hemisphere, the table will display information for both in one single row. 
The table provide essential information regarding the recording, such as recording duration and therapy configurations. 

.. note:: 

  The only information require manual update is Stimulation Mode (Ring Stimulation vs Segmented A, B, C) 
  because Percept Session file does not store those information in the recording data. 

Neural Recording Summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once a user selected "View" in Selection Table, data will be processed in the server and transmitted 
to the web application for display. The display for a typical bilateral recording in shown in below figure. 
All figures provided in the graph are interactive with x-axis alignment fixed. 
All time are presented based on user's local timezone. Screenshot taken from Version 1.0 but overall capability has not changed in 2.0.

.. image:: images/BrainSenseStreamingSummary1.png
  :target: images/BrainSenseStreamingSummary1.png
  :width: 800

Time alignemnt with bilataral recording can be easily identified via Red Box 3 in below figure. 
The presence of pathological beta activity is supressed unilaterally when unilateral stimulation is 
turned on for Left and Right separately. The alignment shows that the stimulation artifact align with changes 
in stimulation parameters. 

.. image:: images/BrainSenseStreamingSummary2.png
  :target: images/BrainSenseStreamingSummary2.png
  :width: 800

User may choose to export the raw data. 
The export will generate a CSV file easily loaded in any scientific programming languages. 
The data are aligned if left and right hemisphere both present in the recording. 
Timestamp are provided as UTC timestamp in seconds. 
Aligned stimulation values are provided for identification of stimulation period. 

.. image:: images/BrainSenseStreamingSummary3.png
  :target: images/BrainSenseStreamingSummary3.png
  :width: 800

The basic summary uses default short-time Fourier Transform (Spectrogram) method to generate Time-Frequency Analysis. 
However, user can also choose to use Wavelet Transformation (usually more time-consuming). 
Once method is changed, the processed data are cached on the server and available to user in the future. 

Similarly, user may also choose to use a template matching cardiac filter to remove cardiac artifacts if present. 
below figures show the performance of the cardiac filter. 
It selectively remove signal without altering stimulation artifact spikes. 

.. image:: images/StreamingCardiacOFF.png
  :target: images/StreamingCardiacOFF.png
  :width: 800

.. image:: images/StreamingCardiacON.png
  :target: images/StreamingCardiacON.png
  :width: 800

Effect of Stimulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the effect of stimulation presentation, the platform will automatically segment period with different 
level of stimulation and calculate average power spectrum for different stimulation amplitudes. 
The segments are sorted with increasing amplitude and color gradient indicate a changes of brain signal with 
increasing Stimulation.

.. _Indefinite Streaming:

Indefinite Streaming View 
---------------------------------------------

Indefinite Streaming is similar to BrainSense Streaming, but it doesn't come with stimulation parameters nor other labels. 
In exchange for that, the device allows simultaneous recording up to 6 channels at the same time (Bilateral E00-E02, E01-E03, 
and E00-E03). We align all recordings collected at the same time and perform quick time-frequency analysis display to the user.

.. image:: images/IndefiniteStreaming1.png
  :target: images/IndefiniteStreaming1.png
  :width: 800

The recording selection is performed through toggle buttons. 
Each button indicate the time and duration of the recording. After recordings are selected, 
user can retrieve the data from server, and simple display will be used to allow interactive 
visualization of Indefinite Streaming data.

The toggle selection actually allow multiple selection. User can select multiple recording from the same day 
and visualize them on the same time-axis. Segment without data will be leave as blank.

.. image:: images/IndefiniteStreaming2.png
  :target: images/IndefiniteStreaming2.png
  :width: 800

.. image:: images/IndefiniteStreaming3.png
  :target: images/IndefiniteStreaming3.png
  :width: 800

.. image:: images/IndefiniteStreaming4.png
  :target: images/IndefiniteStreaming4.png
  :width: 800

.. image:: images/IndefiniteStreaming5.png
  :target: images/IndefiniteStreaming5.png
  :width: 800

Since there are no extra label provided by neurostimulator. User may use external label such as biosensors or 
questionaires to indicate events. Data can be exported similar to BrainSense Streaming. 


.. _Chronic BrainSense:

Chronic Brainsense View
---------------------------------------------

Chronic LFP records specific spectral power every 10 minutes when the patient is using a therapy group with 
BrainSense capability enabled. LFPs are collected in a manner similar to the example structure below in ``DiagnosticData.LFPTrendLogs`` 
field. The LFP Trend Log divides recording into Left/Right hemisphere, and groups arrays of samples by date. 
Each sample contains a timestamp, a LFP measurment (integer, arbituary unit), and instananeous stimulation amplitude measurement. 

.. image:: images/Chronic LFP.png
  :target: images/Chronic LFP.png
  :width: 800



.. note::

  It is important to note that ``DiagnosticData.LFPTrendLogs`` doesn't contain any important therapeutic information 
  beside amplitude. The most significant difficulty in interpreting the result is actually assigning proper therapy 
  information to each sample collected. 

.. code-block:: json

  "LFPTrendLogs": {
      "HemisphereLocationDef.Right": {
        "2022-01-11T13:51:24Z": [
          {
            "DateTime": "2022-01-11T16:11:44Z",
            "LFP": 1179,
            "AmplitudeInMilliAmps": 2.5
          },
        ],
      }
    }

In addition to the power sample collected every 10 minutes, there is also another similar Chronic neural 
recording capability available that capture brain signal every time a patient trigger a recording. This is known 
as the Patient Event Power Spectral Density (PSD). The available patient events are stored in ``PatientEvents`` structure. 
The recorded patient events are stored in ``DiagnosticData.LfpFrequencySnapshotEvents`` structure similar to shown below. 

.. code-block::

  "LfpFrequencySnapshotEvents": [
    ...,
    {
      "DateTime": "2021-02-17T19:37:16Z",
      "EventID": 1,
      "EventName": "Dyskinesia",
      "LFP": true,
      "Cycling": false
    },
    {
      "DateTime": "2021-02-18T14:35:23Z",
      "EventID": 4,
      "EventName": "Tremor",
      "LFP": false,
      "Cycling": false
    },
    ...,
    {
      "DateTime": "2021-06-10T19:41:58Z",
      "EventID": 1,
      "EventName": "Dyskinesia",
      "LFP": true,
      "Cycling": false,
      "LfpFrequencySnapshotEvents": {
      "HemisphereLocationDef.Right": {
        "DateTime": "2021-06-10T19:42:28Z",
        "GroupId": "GroupIdDef.GROUP_C",
        "SenseID": "",
        "FFTBinData": [...],
        "Frequency": [...],
      },
      "HemisphereLocationDef.Left": {...}
    },
  ]


Circadian Rhythms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Circadian Rhythm is one of the additional processing examples for Chronic LFP recordings. 
The circadian rhythm calculation divide all Chronic LFP samples based on therapy settings and sensing settings, 
then calculated 24-hour trend of brain signal. This graph demonstrates changes in brain signal between awake state 
and sleep state. In addition, consistent medication cycles will also show up on the graph.

Event-locked Power Trend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Event-locked Power Trend allow user to visualize power 3 hours before and after onset of an event. 
This is especially helpful for understanding changes in power with respect to medications or symptoms. 

Event Power Spectrum
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Patient Events that contains PSDs will be averaged within group and compare to other events. 
The shaded area is one standard-error from mean.
Number of sample is usually different from event-locked power trend because not every recorded event contain PSD snapshot. 
