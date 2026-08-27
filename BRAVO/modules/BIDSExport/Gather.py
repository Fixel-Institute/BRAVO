""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under Open Source GPL-3.0 License

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
BIDS Export - Database Adapter
===================================================
Bridges Server/models (Django ORM, encrypted file-backed Recording storage)
to the plain-dict shapes modules.BIDSExport.Convert expects. This is the
only file in BIDSExport that imports Django/Server.models - Convert.py stays
DB-independent and testable without a database.

A BRAVO SourceFile (a decoded Percept JSON upload, identified by
pointer.endswith(".json") after ingestion - NOT by .type, see
export_participant()) is one Percept clinic-visit upload. A BIDS *session*
is one calendar day in the participant's local timezone - a single clinic
visit routinely produces several separate JSON uploads (programming check,
BrainSense survey, a streaming recording, ...) minutes apart, and those all
belong in the same session, not one each (see gather_day()). See
modules/DataCurator.py::MedtronicPerceptJSONDecoder for how this data was
originally persisted - this module is its mirror image.
"""

import datetime
import hashlib
import hmac
import json
import os
import re

from filelock import FileLock

from Server import models
from modules import Database

STREAMING_TYPES = {"MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream"}
SURVEY_TYPES = {"MedtronicElectrodeIdentifier", "MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicStimulationMontages"}


def _electrode_dicts(device):
    electrodes = []
    for electrode in device.electrodes.all():
        # Electrode.hemisphere is never actually populated by Percept
        # ingestion (DataCurator.MedtronicPerceptJSONDecoder only sets
        # type/custom_name/channel_count/channel_names on create) - it's
        # blank for every real electrode. .target always starts with
        # "Left"/"Right" (e.g. "Right STN", "Right Other" - see
        # Session.py::extractPatientInformation's TargetLocation), so
        # derive it from there rather than emit an empty BIDS cell.
        hemisphere = electrode.hemisphere or electrode.target.split(" ")[0]
        electrodes.append({
            "target": electrode.custom_name or electrode.target,
            # Electrode.custom_name: clinician-assigned label (e.g. "Right
            # STN LFP") that already gets folded into "target" above as a
            # fallback-preferred value - kept here too, raw, so the
            # clinician's own naming is traceable in electrodes.tsv even
            # when it happens to equal (or differ from) the anatomical
            # target BRAVO derived from the device's TargetLocation.
            "custom_name": electrode.custom_name,
            "hemisphere": hemisphere,
            "channel_names": electrode.channel_names,
            "channel_coordinates": electrode.channel_coordinates,
        })
    return electrodes


def _device_dict(device):
    """{"model": str, "serial_hash": str} or None. Unconditionally re-hashes
    serial_number with DATASERVER_HASHKEY at export time regardless of
    whether ingestion already hashed it - DataCurator.py only hashes
    conditionally, gated on an upload-time "automatic_deidentification"
    flag, so serial_number can be plaintext in the DB. Hashing again here
    guarantees a BIDS export never carries a plaintext device serial
    independent of that flag - see docs/BIDS_MAPPING.md
    "De-identification"."""
    if device is None or not device.serial_number:
        return None
    hash_key = os.environ.get("DATASERVER_HASHKEY", "")
    serial_hash = hmac.new(hash_key.encode("utf8"), device.serial_number.encode("utf-8"), hashlib.sha256).hexdigest()
    return {"model": device.type or device.get_name(), "serial_hash": serial_hash}


def _impedance_records(source_file, electrodes):
    """Percept impedance checks report both a per-contact "Monopolar" list
    and a full per-contact-pair "Bipolar" matrix, per hemisphere - both
    positional (index 0 = first contact), not keyed by channel name, so
    they're resolved against each electrode's channel_names in order, same
    as Monopolar always was. Bipolar is upper-triangular (BRAVO/Percept
    only ever populates j > i - the diagonal and lower triangle are
    structural zeros, not real 0-Ohm readings) so only that half is walked."""
    records = []
    for recording in models.Recording.find_all(source=source_file, type="MedtronicDeviceImpedance"):
        for electrode in electrodes:
            hemisphere_data = recording.metadata.get(electrode["hemisphere"])
            if not hemisphere_data:
                continue
            names = electrode["channel_names"]
            lead_model = hemisphere_data.get("LeadModel")

            for name, ohms in zip(names, hemisphere_data.get("Monopolar", [])):
                records.append({
                    "date": recording.date, "hemisphere": electrode["hemisphere"],
                    # electrode is already the one matched by hemisphere above -
                    # same clinician-assigned label as electrodes.tsv's CustomName.
                    "custom_name": electrode.get("custom_name"),
                    "source_id": source_file.uid,
                    "measurement_type": "Monopolar", "contact": name,
                    "impedance_ohm": ohms, "lead_model": lead_model,
                })

            bipolar = hemisphere_data.get("Bipolar", [])
            for i, row in enumerate(bipolar):
                if i >= len(names):
                    continue
                for j in range(i + 1, min(len(row), len(names))):
                    ohms = row[j]
                    if not ohms:
                        continue  # structural zero (unmeasured position), not a real reading
                    records.append({
                        "date": recording.date, "hemisphere": electrode["hemisphere"],
                        "custom_name": electrode.get("custom_name"),
                        "source_id": source_file.uid,
                        "measurement_type": "Bipolar", "contact": names[i], "contact_2": names[j],
                        "impedance_ohm": ohms, "lead_model": lead_model,
                    })
    return records


def _therapy_dicts(source_file):
    """Reconstructs the flat per-hemisphere-per-group shape
    Convert.therapy_history_dataframe expects, from the normalized
    Therapy/ElectricalTherapy/ElectricalStimulation/AdaptiveTherapy rows.

    Deliberately does NOT use Therapy.get_info() - that method silently
    returns None for type == "Past Therapy" (only handles "Pre-visit
    Therapy"/"Post-visit Therapy"), which would drop most of a
    participant's actual therapy history. Querying ElectricalTherapy
    directly bypasses that gate."""
    therapies = []
    for group in models.ElectricalTherapy.find_all(therapy__source=source_file):
        info = group.get_info()
        hemisphere = "Unknown"
        if info["StimulationSettings"]:
            electrode_info = info["StimulationSettings"][0]["Electrode"]
            # Electrode.hemisphere is unpopulated (same DB gap as in
            # _electrode_dicts) - fall back to deriving it from Target.
            hemisphere = electrode_info.get("Hemisphere") or electrode_info.get("Target", "").split(" ")[0] or "Unknown"
        therapies.append({
            "hemisphere": hemisphere,
            "source_id": source_file.uid,
            "type": info["Type"],
            "date": info["Date"],
            "group_id": info["GroupId"],
            "group_name": info["GroupName"],
            # "Active" if this group was actually running on the device at
            # this visit, "" otherwise (modules/MedtronicPercept/Therapy.py)
            "group_type": info["GroupType"],
            # clinician-assigned via the UI's "Assign Therapy Label" action
            # (/api/assignTherapyLabel, e.g. "Pre-visit Preferred") - blank
            # ("") if never set.
            "label": info["Label"],
            "stimulation_type": info["StimulationType"],
            "stimulation_settings": info["StimulationSettings"],
            # Kept as the combined {RecordingConfiguration, StimulationConfiguration}
            # AdaptiveTherapy.get_info() shape - Convert.therapy_adaptive_dataframe
            # needs both halves together per entry, not split into two
            # separately-indexed lists (they're the same adaptive program).
            "adaptive_settings": info["AdaptiveSettings"],
        })
    return therapies


def _event_dicts(source_file):
    """Patient-triggered events plus therapy group/status changes, merged
    into one chronologically-meaningful list - Convert.patient_events_dataframe
    needs {previous, new, type, date} per entry. `previous`/`new` match
    TherapyModification.get_info()'s own key spelling ("Previous"/"New") -
    a real before/after pair (previous_state -> new_state), kept as two
    separate values rather than pre-joined into one string, so a consumer
    can read either side without re-splitting text. A plain `DBSEvent` has
    no such pair - its single label goes in `previous`, `new` stays "n/a"
    rather than repeating or fabricating a second value."""
    events = []
    for event in models.DBSEvent.find_all(source=source_file):
        if event.type == "MedtronicDeviceImpedance":
            continue  # its own Impedance beh.tsv instead, see _impedance_records()
        events.append({"previous": event.name or "n/a", "new": "n/a", "type": event.type, "date": event.date, "source_id": source_file.uid})
    for mod in models.TherapyModification.find_all(source=source_file):
        events.append({"previous": mod.previous_state or "n/a", "new": mod.new_state or "n/a", "type": mod.type, "date": mod.date, "source_id": source_file.uid})
    return events


def gather_session(source_file):
    """source_file: a Server.models.SourceFile row for a decoded Percept
    JSON upload. Returns kwargs ready for Convert.convert_participant(), covering exactly
    this one session/upload."""
    person = source_file.owner
    device_uid = source_file.metadata.get("Device")
    device = models.DBSDevice.find(uid=device_uid) if device_uid else None
    electrodes = _electrode_dicts(device) if device else []
    # Electrode.get_info()-shaped (Target/CustomName), NOT the BIDS-shaped
    # `electrodes` above (whose "target" is already custom_name-or-target
    # merged) - modules.MedtronicPercept.BrainSenseStream.reformatChannelName
    # needs the real, unmerged Target to hemisphere-match against, same
    # shape DataAnalysis.queryAllRecordings() already uses as the platform's
    # canonical channel-naming reference. See Convert.write_ieeg_recording's
    # ClinicalName column / chronic_lfp_dataframe()'s renamed columns.
    electrode_info = device.get_info()["Electrodes"] if device else []

    participant = {
        "sex": person.sex,
        "diagnosis": person.diagnosis,
        "dob": person.date_of_birth or None,
        "session_date": source_file.date,
    }

    streaming_recordings, survey_recordings = [], []
    for recording in models.Recording.find_all(source=source_file):
        if not recording.pointer:
            continue  # e.g. MedtronicDeviceImpedance - metadata-only, no file on disk
        data = Database.loadSourceFile(recording.pointer, recording.hashed)
        # Recording.adjusted_alignment: manual clock-drift correction set via
        # the UI's "Time Shift" tool (/api/setRecordingTimeShift) - 0 unless
        # a user has explicitly corrected this recording. DataAnalysis.py
        # applies it the same way (StartTime + adjusted_alignment) everywhere
        # it reads a recording's start time - BIDS export must match, or a
        # user-corrected recording's scans.tsv acq_time silently reverts to
        # the uncorrected device clock.
        if recording.adjusted_alignment and "StartTime" in data:
            data["StartTime"] += recording.adjusted_alignment
        data["AdjustedAlignment"] = recording.adjusted_alignment
        # SourceFile.uid: the specific upload this recording came from - a
        # day-merged session (Gather.gather_day()) concatenates recordings
        # from several separate uploads, so unlike device_id (constant for
        # the whole day) this can differ row-to-row/run-to-run within one
        # session. See Convert.write_ieeg_recording's scans.tsv SourceId column.
        data["SourceId"] = source_file.uid
        # SourceFile.metadata["Timezone"]: BRAVO's stored UTC-offset string
        # (e.g. "UTC-04:00", see DataCurator.py - SessionOverview.SessionTimezone)
        # for this specific upload - every absolute timestamp this export
        # writes (scans.tsv's acq_time via set_meas_date below, sessions.tsv,
        # Annotations' StartTimestamp/EndTimestamp) is UTC, so without this
        # there's no way to recover the participant's real local time it
        # actually happened at. Per-recording (not session-constant) for the
        # same reason as SourceId - a day-merged session could in principle
        # span uploads with different stored timezones.
        data["Timezone"] = source_file.metadata.get("Timezone") or "n/a"
        # Recording.type/Recording.name - the raw DB fields (e.g. "Type":
        # "MedtronicBaselineMontages"), NOT the same as TaskName (the
        # BIDS-legal task label CONTINUOUS_TYPES maps that type to, e.g.
        # "BaselineMontage") - TaskName can't be swapped for this, it's
        # locked to match the filename's task-<label> entity everywhere
        # BIDS tooling reads it. Same "Type"/"Name" spelling as
        # Recording.get_info() - see Convert.write_ieeg_recording's Type/Name keys.
        data["Type"] = recording.type
        data["Name"] = recording.name or "n/a"
        # Recording.metadata: DB-row-level summary set at ingestion time
        # (e.g. {"ChannelNames": [...], "Duration": ...} - see
        # DataCurator.py) - a lightweight duplicate of fields already inside
        # `data` itself, kept here anyway so it's traceable in the export
        # sidecar (see Convert.write_ieeg_recording's "metadata" key).
        entry = {"type": recording.type, "recording": data, "metadata": recording.metadata}
        if recording.type in STREAMING_TYPES:
            streaming_recordings.append(entry)
        elif recording.type in SURVEY_TYPES:
            survey_recordings.append(entry)
        # MedtronicChronicBrainSense rows aren't bucketed here anymore - see
        # export_participant()'s chronic_activity_by_day. Still the real
        # underlying source data (extractChronicNeuralActivity() reads
        # these Recording rows directly), just not routed through this
        # per-upload streaming/survey path - a chronic segment can span
        # many uploads and isn't tied to any single one the way a TD/Power/
        # Survey recording is.

    return {
        "participant": participant,
        "electrodes": electrodes,
        "streaming_recordings": streaming_recordings,
        "survey_recordings": survey_recordings,
        "therapies": _therapy_dicts(source_file),
        "events": _event_dicts(source_file),
        "impedance_measurements": _impedance_records(source_file, electrodes),
        "device": _device_dict(device),
        "electrode_info": electrode_info,
    }


def _subject_label(bids_root, participant_uid):
    """Maps a BRAVO participant UID to a short sequential BIDS subject label
    (sub-001, sub-002, ...) - the conventional look for a published BIDS
    dataset, vs. the raw 32-char UID. The mapping is kept in a dotfile next
    to the dataset (not part of the BIDS spec - ignored by BIDS parsers) so
    the same participant always lands back on the same number across
    re-exports, and new participants get the next free one. FileLock-guarded
    since AsyncJob exports can run concurrently (same pattern as Database.py)."""
    os.makedirs(bids_root, exist_ok=True)
    map_path = os.path.join(bids_root, ".bravo_subject_ids.json")
    with FileLock(map_path + ".lock", timeout=30):
        mapping = {}
        if os.path.exists(map_path):
            with open(map_path) as fid:
                mapping = json.load(fid)
        if participant_uid not in mapping:
            mapping[participant_uid] = max(mapping.values(), default=0) + 1
            with open(map_path, "w") as fid:
                json.dump(mapping, fid, indent=2)
        return f"{mapping[participant_uid]:03d}"


def gather_and_convert(bids_root, source_file, subject=None, session="01"):
    from modules.BIDSExport.Convert import convert_participant
    kwargs = gather_session(source_file)
    subject = subject or source_file.owner.uid
    return convert_participant(bids_root, subject=subject, session=session, **kwargs)


def _local_date_and_time(timestamp, timezone_offset):
    """timezone_offset: BRAVO's stored offset string, e.g. "UTC-04:00" (see
    DataCurator.py - SessionOverview.SessionTimezone). Falls back to UTC if
    missing/unparseable - a session date is still useful even if the offset
    couldn't be read, and this must never crash the export over a cosmetic
    label. Returns (date_label "YYYYMMDD" for the ses- entity, ISO8601
    local datetime string for sessions.tsv's acq_time)."""
    match = re.match(r"UTC([+-]\d{2}):(\d{2})", timezone_offset or "")
    if match:
        hours, minutes = int(match.group(1)), int(match.group(2))
        offset = datetime.timedelta(minutes=hours * 60 + (minutes if hours >= 0 else -minutes))
    else:
        offset = datetime.timedelta(0)
    local = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc) + offset
    return local.strftime("%Y%m%d"), local.strftime("%Y-%m-%dT%H:%M:%S")


def gather_day(source_files):
    """source_files: every SourceFile upload sharing one local calendar
    date for one participant (see export_participant()), oldest first.
    Merges their individual gather_session() results into one BIDS
    session's worth of kwargs - electrodes/demographics come from the
    earliest upload of the day (implant hardware doesn't change within a
    day), every recording/therapy/event/impedance list is concatenated."""
    source_files = sorted(source_files, key=lambda source_file: source_file.date)
    per_file = [gather_session(source_file) for source_file in source_files]

    merged = {
        "participant": {**per_file[0]["participant"], "session_date": source_files[0].date,
                         "session_end": source_files[-1].date},
        "electrodes": per_file[0]["electrodes"],
        "device": per_file[0]["device"],  # doesn't change within a day, same reasoning as electrodes
        "electrode_info": per_file[0]["electrode_info"],  # same reasoning
        "streaming_recordings": [],
        "survey_recordings": [],
        "therapies": [],
        "events": [],
        "impedance_measurements": [],
    }
    list_keys = ("streaming_recordings", "survey_recordings", "therapies", "events",
                 "impedance_measurements")
    for gathered in per_file:
        for key in list_keys:
            merged[key].extend(gathered[key])
    return merged


def export_participant(participant_uid):
    """Exports every Percept JSON upload for this participant into the
    shared BIDS dataset at DATASERVER_PATH/BIDS - one BIDS session per
    local calendar day (see gather_day() - a single clinic visit is
    usually several separate uploads minutes apart, not one session each),
    ordered chronologically. All of a participant's sessions accumulate
    into the same dataset alongside other participants' - this is one BIDS
    dataset, not one per participant.

    Returns the list of SourceFile uids exported."""
    from modules.BIDSExport.Convert import (
        convert_participant, write_sessions_tsv, write_chronic_neural_activity_derivative, write_subject_devices,
        write_dataset_manifest,
    )

    bids_root = os.path.join(os.environ.get("DATASERVER_PATH"), "BIDS")
    person = models.Participant.find(uid=participant_uid)
    if not person:
        raise Exception("Participant not found")

    # SourceFile.type is NOT a reliable marker here - it's just whatever
    # DataType the upload request specified ("DefaultType" for the generic
    # auto-detect-by-extension path, only "MedtronicJSON" for the explicit
    # upload path - both get decoded by the same MedtronicPerceptJSONDecoder).
    # After ingestion, .pointer always ends in ".json" regardless of which
    # path was used (DataCurator.py moves it under raws/<participant>/*.json)
    # - that's the robust match.
    source_files = models.SourceFile.objects.filter(owner=person, pointer__endswith=".json").order_by("date")
    subject = _subject_label(bids_root, person.uid)

    by_day = {}
    for source_file in source_files:
        date_label, _ = _local_date_and_time(source_file.date, source_file.metadata.get("Timezone"))
        by_day.setdefault(date_label, []).append(source_file)

    # MedtronicChronicNeuralActivity is a single participant-wide Recording
    # (not one per upload) attached to a synthetic "ChronicNeuralActivitySource"
    # SourceFile, rebuilt on every new upload - see DATA_INVENTORY.md. Its
    # segments carry their own TherapyStartTime (one per therapy-change-
    # bounded segment - see ChronicBrainSense.extractChronicNeuralActivity)
    # but no per-segment timezone, so they're bucketed into calendar days
    # using the most recent upload's reported timezone as one fixed offset
    # for the whole participant - a segment near a local-midnight/DST
    # boundary could land in the "wrong" day bucket. Written both as the
    # bravo-chronic-neural-activity derivative (below) and, per segment, as
    # a real ieeg/ task-ChronicLFP recording (see convert_participant()'s
    # chronic_activities) - reassigned onto a real existing session below
    # (real_session_dates) if its own day has no upload/annotation, rather
    # than manufacturing a synthetic session just to hold it.
    chronic_neural_activity_recording = models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=person)
    chronic_activity_by_day = {}
    chronic_device_cache = {}
    if chronic_neural_activity_recording and chronic_neural_activity_recording.pointer:
        fallback_timezone = source_files.last().metadata.get("Timezone") if source_files else None
        for activity in Database.loadSourceFile(chronic_neural_activity_recording.pointer, chronic_neural_activity_recording.hashed):
            date_label, _ = _local_date_and_time(activity["TherapyStartTime"], fallback_timezone)
            # A segment's own recording device (not necessarily this
            # participant's "current" device - a segment can predate a
            # device replacement) - cached since the same device UID
            # repeats across many segments.
            device_uid = activity.get("Device")
            if device_uid not in chronic_device_cache:
                device = models.DBSDevice.find(uid=device_uid) if device_uid else None
                chronic_device_cache[device_uid] = _device_dict(device)
            activity["device"] = chronic_device_cache[device_uid]
            chronic_activity_by_day.setdefault(date_label, []).append(activity)

    # Annotation.source is nullable and the UI's "add event" flow (see
    # modules/Event.py::addAnnotation) never sets it - bucket by the
    # annotation's own .date (like chronic-activity above) rather than by
    # source_file, so manually-added events aren't silently dropped. Same
    # single-fixed-timezone approximation as chronic-activity for the same
    # reason (no per-annotation timezone stored).
    annotations_by_day = {}
    fallback_timezone = source_files.last().metadata.get("Timezone") if source_files else None
    for annotation in models.Annotation.find_all(owner=person):
        date_label, _ = _local_date_and_time(annotation.date, fallback_timezone)
        annotations_by_day.setdefault(date_label, []).append({
            "name": annotation.name, "type": annotation.type,
            "date": annotation.date, "duration": annotation.duration,
        })

    # Chronic-event annotations (seizure logs, etc. - see Reports/ChronicTimeline
    # and Reports/ChronicNeuralActivity's "add event") are routinely logged on
    # days with no device upload at all - unlike chronic-activity above, these
    # are real first-class data, not a redundant convenience join, so a day
    # with annotations but no upload still gets a real BIDS session: just a
    # beh/Annotations_beh.tsv, no ieeg/ - rather than being silently dropped.
    #
    # Restricted to type=="ChronicCustomEvent" only - that's the only type
    # the UI ever assigns from a view NOT anchored to one specific recording
    # (ChronicTimeline/ChronicNeuralActivity's "add event", meant to log
    # something on any calendar day). "RecordingCustomEvent" is only ever
    # set while looking at one specific existing recording's timeline
    # (TimeSeriesAnalysis/TherapeuticEffects/Empatica), so it should always
    # already coincide with a real upload day; one that doesn't is stale/
    # orphaned/test data, not real chronic logging, and manufacturing a
    # session for it would just launder that into the export looking like
    # real data. Found via a real "Test"-named RecordingCustomEvent row
    # sitting in the DB from before this module existed - it doesn't create
    # a session under this rule.
    annotation_only_days = sorted({
        date_label for date_label, annotations in annotations_by_day.items()
        if date_label not in by_day and any(a["type"] == "ChronicCustomEvent" for a in annotations)
    })

    # ChronicLFP is real ieeg/ data, not a special category - it never gets
    # its own synthetic session the way annotation_only_days does. A segment
    # whose own TherapyStartTime doesn't land on a real upload/annotation
    # day is reassigned to the nearest PRECEDING real session instead (that
    # visit is chronologically "when" the device was on this segment's
    # therapy setting, same reasoning TherapyHistory's "Past Therapy"
    # readouts already get retroactively attached to whichever visit
    # captured them) - or the very first real session, for a segment that
    # predates every upload (device was logging before anyone ever
    # uploaded).
    real_session_dates = sorted(set(by_day) | set(annotation_only_days))
    if real_session_dates:
        reassigned_chronic_activity_by_day = {}
        for date_label, activities in chronic_activity_by_day.items():
            if date_label in real_session_dates:
                target = date_label
            else:
                preceding = [d for d in real_session_dates if d <= date_label]
                target = preceding[-1] if preceding else real_session_dates[0]
            reassigned_chronic_activity_by_day.setdefault(target, []).extend(activities)
        chronic_activity_by_day = reassigned_chronic_activity_by_day

    # ScaleRecord (clinical rating scale / questionnaire submissions) isn't
    # tied to a SourceFile either (participant is a direct FK) - grouped by
    # form NAME, not by the specific ScaleForms row: ScaleForms.update_version()
    # creates a new row (new uid) per edit, so the "same" form by name can
    # span several rows over a participant's history - each record still
    # carries its own source (the exact version it was submitted against)
    # for Convert.scale_form_dataframe() to interpret its own answers
    # against. Unlike Annotation, NOT bucketed by its own calendar day -
    # attached to whichever real session's [prev_session_end, session_end]
    # window covers it (see the main loop below), same as how a device
    # upload's "Past Therapy" readouts land in the visit that captured them
    # rather than getting their own session per historical date. Sorted so
    # the main loop can consume them chronologically with a single pass.
    pending_scale_records = sorted((
        {"name": record.source.name, "date": record.date,
         "answers": record.record, "questions": record.source.record}
        for record in models.ScaleRecord.find_all(participant=person)
    ), key=lambda record: record["date"])

    exported = []
    session_rows = []
    device_rows = []
    # Bounds each session's beh.tsv rows to [end of the previous session, end
    # of this session] (see Convert.py's _clamp_onset()) - a device-reported
    # "Past Therapy" readout gets re-included in every visit's upload, so
    # without this a stale duplicate can land with a wildly-negative onset
    # reaching back past the actual previous visit. None on the first
    # iteration - there's no previous session to bound against, so the very
    # first session's rows are left unclamped on the low end.
    prev_session_end = None
    last_date_label, last_participant = None, None
    for date_label in sorted(set(by_day) | set(annotation_only_days)):
        day_chronic_activities = chronic_activity_by_day.get(date_label, [])
        if date_label in by_day:
            day_source_files = by_day[date_label]
            kwargs = gather_day(day_source_files)
            earliest = min(source_file.date for source_file in day_source_files)
            latest = max(source_file.date for source_file in day_source_files)
            timezone = day_source_files[0].metadata.get("Timezone")
            exported.extend(source_file.uid for source_file in day_source_files)
            session_type = "Upload"
        else:
            day_annotations = annotations_by_day.get(date_label, [])
            candidate_dates = [a["date"] for a in day_annotations]
            for activity in day_chronic_activities:
                candidate_dates.append(min(activity["Time"]))
                candidate_dates.append(max(activity["Time"]))
            earliest = min(candidate_dates)
            latest = max(candidate_dates)
            timezone = fallback_timezone
            kwargs = {"participant": {
                "sex": person.sex, "diagnosis": person.diagnosis,
                "dob": person.date_of_birth or None, "session_date": earliest,
                "session_end": latest,
            }}
            session_type = "AnnotationOnly"

        kwargs["participant"]["prev_session_end"] = prev_session_end
        kwargs["participant"]["timezone"] = timezone or "n/a"

        kwargs["annotations"] = annotations_by_day.get(date_label, [])
        kwargs["chronic_activities"] = day_chronic_activities
        # Every pending ScaleRecord up through this session's own session_end
        # belongs here - covers everything back to prev_session_end (nothing
        # else could have claimed it, since pending_scale_records is consumed
        # in chronological order) and, for the very first session, everything
        # before it too (no prev_session_end to bound against, same as
        # onset_bounds' unbounded lower side). Split out via a simple
        # partition rather than a date-range filter for exactly that reason.
        split = next((i for i, record in enumerate(pending_scale_records) if record["date"] > latest), len(pending_scale_records))
        kwargs["scale_records"], pending_scale_records = pending_scale_records[:split], pending_scale_records[split:]

        prev_session_end = latest
        convert_participant(bids_root, subject=subject, session=date_label, **kwargs)
        write_chronic_neural_activity_derivative(
            bids_root, subject, date_label, chronic_activity_by_day.get(date_label, []), kwargs["participant"]["session_date"])

        _, acq_time = _local_date_and_time(earliest, timezone)
        session_rows.append({"session_id": f"ses-{date_label}", "acq_time": acq_time, "timezone": timezone or "n/a", "session_type": session_type})
        device_rows.append({"session_id": f"ses-{date_label}", **(kwargs.get("device") or {})})
        last_date_label, last_participant = date_label, kwargs["participant"]

    # Trailing ScaleRecords submitted after the participant's last known
    # session (no upcoming visit exists to attribute them to yet) go into
    # that last session too, rather than manufacturing a new one - the same
    # task-<FormName>_beh.tsv files, just added into the existing ses-<...>
    # folder (every other kwargs is None here, so convert_participant()'s
    # per-type `if X:` guards mean nothing else in that session gets
    # touched/rewritten). Their `onset` still clamps to that session's own
    # upper bound same as everything else - Convert.scale_form_dataframe()'s
    # Date column is what keeps the real completion date recoverable once
    # multiple real calendar dates share one session this way.
    if pending_scale_records and last_date_label is not None:
        convert_participant(
            bids_root, subject=subject, session=last_date_label,
            participant=last_participant, scale_records=pending_scale_records,
        )
    elif pending_scale_records:
        # No real session exists at all for this participant (device
        # uploads/annotations) - nothing to attach to, so these still need
        # their own session(s) rather than being silently dropped. Bucketed
        # by calendar day, same as every other from-scratch session above.
        trailing_by_day = {}
        for record in pending_scale_records:
            date_label, _ = _local_date_and_time(record["date"], fallback_timezone)
            trailing_by_day.setdefault(date_label, []).append(record)
        for date_label in sorted(trailing_by_day):
            day_scale_records = trailing_by_day[date_label]
            earliest = min(r["date"] for r in day_scale_records)
            latest = max(r["date"] for r in day_scale_records)
            kwargs = {"participant": {
                "sex": person.sex, "diagnosis": person.diagnosis,
                "dob": person.date_of_birth or None, "session_date": earliest,
                "session_end": latest, "prev_session_end": prev_session_end,
                "timezone": fallback_timezone or "n/a",
            }, "scale_records": day_scale_records}
            prev_session_end = latest
            convert_participant(bids_root, subject=subject, session=date_label, **kwargs)
            _, acq_time = _local_date_and_time(earliest, fallback_timezone)
            session_rows.append({"session_id": f"ses-{date_label}", "acq_time": acq_time, "timezone": fallback_timezone or "n/a", "session_type": "ScaleOnly"})
            device_rows.append({"session_id": f"ses-{date_label}"})

    write_sessions_tsv(bids_root, subject, session_rows)
    write_subject_devices(bids_root, subject, device_rows)
    write_dataset_manifest(bids_root, subject)
    return exported
