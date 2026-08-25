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
BIDS Export - Conversion Core
===================================================
Takes plain-Python-shaped BRAVO/Percept data (as produced by
modules.MedtronicPercept.Session.decodeMedtronicJSON, or equivalently
reconstructed from Recording/Participant/Electrode DB rows) and writes a
BIDS-validator-passing dataset. No Django import here on purpose - this
module only ever sees plain dicts/lists/numpy arrays, so it can be tested
without a running database. See docs/BIDS_MAPPING.md in this same directory
for the full per-type design and the open items flagged below.
"""

import datetime
import glob
import os
import json
import re
import warnings

import numpy as np
import pandas as pd
import mne
from mne_bids import BIDSPath, write_raw_bids
from edfio import Edf, EdfSignal, EdfAnnotation, Recording as EdfRecording
from filelock import FileLock

from modules.MedtronicPercept import BrainSenseStream

BIDS_VERSION = "1.10.0"

# ---------------------------------------------------------------------------
# CONFIRM before using on real participant data for publication - see
# docs/BIDS_MAPPING.md "Open items". Not verified against Medtronic's
# technical documentation, just the commonly assumed values.
TD_UNITS_UV = True          # BrainSense TD assumed microvolt-scale
POWER_LINE_FREQUENCY_HZ = 60  # US clinical site assumption (UF)
# ---------------------------------------------------------------------------

# BRAVO Recording `type` -> BIDS ieeg destination. Anything not listed here
# is skipped rather than guessed at - see convert_participant().
#
# ch_type "power_stim" is a special case: mne-bids requires at least one
# ieeg-family channel (dbs/seeg/ecog/eeg) to accept datatype="ieeg" - an
# all-"misc" recording gets rejected outright. We type ALL channels in a
# power_stim recording "dbs" uniformly - verified empirically that mixing
# dbs+misc channel types in one multi-channel EDF export silently corrupts
# the scaling of some channels inside mne/edfio (a real bug, not a BIDS
# requirement). The true semantic distinction (Power = arbitrary units,
# Stimulation = mA current) is recorded honestly in channels.tsv's "units"
# column via _channel_units_for() instead of via the mne channel type.
CONTINUOUS_TYPES = {
    "MedtronicBrainSenseTimeDomain": {"task": "BrainSenseStream", "acq": "TD", "ch_type": "dbs"},
    "MedtronicBrainSensePowerDomain": {"task": "BrainSenseStream", "acq": "Power", "ch_type": "power_stim"},
    "MedtronicIndefiniteStream": {"task": "IndefiniteStream", "acq": None, "ch_type": "dbs"},
    "MedtronicElectrodeIdentifier": {"task": "ElectrodeIdentifier", "acq": None, "ch_type": "dbs"},
    "MedtronicBrainSenseSurvey": {"task": "BrainSenseSurvey", "acq": None, "ch_type": "dbs"},
    "MedtronicBaselineMontages": {"task": "BaselineMontage", "acq": None, "ch_type": "dbs"},
    "MedtronicStimulationMontages": {"task": "StimulationMontage", "acq": None, "ch_type": "dbs"},
}


def _channel_types_for(ch_type, ch_names):
    if ch_type == "power_stim":
        return ["dbs"] * len(ch_names)
    return [ch_type] * len(ch_names)


def _channel_units_for(ch_type, ch_names):
    """None means: leave whatever mne-bids inferred from channel type alone."""
    if ch_type == "power_stim":
        return {name: ("n/a" if name.endswith(" Power") else "mA") for name in ch_names}
    if ch_type == "chronic":
        return {name: ("n/a" if name.endswith(" LFP") else "mA") for name in ch_names}
    return None


def write_dataset_description(bids_root, name="BRAVO BIDS Export", dataset_type="raw"):
    """Unconditional overwrite, not "write once" - see convert_participant()'s
    docstring on why this has to win over whatever mne-bids's own
    write_raw_bids() left behind."""
    os.makedirs(bids_root, exist_ok=True)
    path = os.path.join(bids_root, "dataset_description.json")
    description = {
        "Name": name,
        "BIDSVersion": BIDS_VERSION,
        "DatasetType": dataset_type,
        "GeneratedBy": [{"Name": "BRAVO BIDSExport", "Version": "0.1.0"}],
    }
    if dataset_type == "derivative":
        description["GeneratedBy"][0]["Description"] = "See dataset_description.json's top-level directory for the raw dataset this was derived from."
    with open(path, "w") as fid:
        json.dump(description, fid, indent=2)


def write_readme(bids_root):
    """Unconditional overwrite, same reasoning as write_dataset_description()
    - without this, README is pure mne-bids boilerplate (its own citation
    text, nothing BRAVO- or Percept-specific)."""
    path = os.path.join(bids_root, "README")
    with open(path, "w") as fid:
        fid.write(
            "BRAVO BIDS Export\n"
            "=================\n\n"
            "Medtronic Percept DBS data (BrainSense streaming/survey recordings, "
            "chronic LFP trends, therapy history, impedance checks) exported from "
            "the UF BRAVO Platform (Brain Recording Analysis and Visualization "
            "Online). One session per local calendar day of clinic-visit uploads.\n\n"
            "Electrode positions are not registered to a known imaging space - see "
            "each session's *_coordsystem.json.\n"
        )


_PARTICIPANTS_COLUMNS = ["participant_id", "age", "sex", "diagnosis"]


def upsert_participant(bids_root, subject, age, sex, diagnosis):
    """One row per subject in participants.tsv. Never writes name/MRN/DOB -
    BIDS participants.tsv is not the place for direct identifiers regardless
    of any upstream deidentification flag.

    Enforces _PARTICIPANTS_COLUMNS as the canonical schema on every call
    (drops anything else) rather than trusting whatever columns already
    exist - mne-bids's own write_raw_bids() writes its own participants.tsv
    with irrelevant columns (hand/weight/height, neither BRAVO nor a DBS
    Percept dataset has any of); reindexing only DROPS columns outside this
    list, it never touches other subjects' real values in age/sex/diagnosis,
    so this is safe to run unconditionally. Same reasoning for the .json
    sidecar - see write_dataset_description().

    FileLock-guarded: this is a read-modify-write on ONE file shared across
    every participant in the dataset, called once per session - two
    participants' exports (or two AsyncJob runs for the same one) racing
    here without a lock corrupts the file mid-write (found via a real
    production export: a garbled row and a doubled-up row from two
    interleaved writes), and every subsequent convert_participant() call in
    that export's loop then dies on the now-unparseable file, silently
    truncating the whole session list. Same pattern as
    Gather._subject_label()'s dotfile lock."""
    path = os.path.join(bids_root, "participants.tsv")
    row = {
        "participant_id": f"sub-{subject}",
        "age": age if age is not None else "n/a",
        "sex": sex or "n/a",
        "diagnosis": diagnosis or "n/a",
    }
    with FileLock(path + ".lock", timeout=30):
        if os.path.exists(path):
            df = pd.read_csv(path, sep="\t", dtype=str)
            df = df[df["participant_id"] != row["participant_id"]]
            df = df.reindex(columns=_PARTICIPANTS_COLUMNS)
        else:
            df = pd.DataFrame(columns=_PARTICIPANTS_COLUMNS)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(path, sep="\t", index=False, na_rep="n/a")

    json_path = path.replace(".tsv", ".json")
    with open(json_path, "w") as fid:
        json.dump({
            "age": {"Description": "Age at session, derived from date of birth - raw DOB is never written", "Units": "years"},
            "sex": {"Description": "Sex as recorded by the device programmer"},
            "diagnosis": {"Description": "Primary diagnosis"},
        }, fid, indent=2)


def write_sessions_tsv(bids_root, subject, sessions):
    """sessions: list of {"session_id": "ses-<label>", "acq_time": ISO8601
    local datetime string, "timezone": BRAVO-stored UTC-offset string}. One
    row per BIDS session for this subject, written to
    sub-<subject>/sub-<subject>_sessions.tsv - the spec-native place to
    carry a real timestamp per session (session_id itself can't contain the
    date directly: BIDS labels can't have "-" or ":" in them, so it's a
    compact ses-YYYYMMDD instead; acq_time is where the actual ISO8601
    date/time lives)."""
    subject_dir = os.path.join(bids_root, f"sub-{subject}")
    os.makedirs(subject_dir, exist_ok=True)
    path = os.path.join(subject_dir, f"sub-{subject}_sessions.tsv")

    df = pd.DataFrame(sessions).rename(columns={"timezone": "Timezone", "session_type": "SessionType"}).sort_values("acq_time").reset_index(drop=True)
    df.to_csv(path, sep="\t", index=False, na_rep="n/a")

    json_path = path.replace(".tsv", ".json")
    with open(json_path, "w") as fid:
        json.dump({
            "acq_time": {"Description": "Local calendar date/time of the earliest clinic-visit upload merged into this session"},
            "Timezone": {"Description": "BRAVO-stored UTC offset (e.g. 'UTC-04:00') acq_time was localized with"},
            "SessionType": {"Description": "Why this session exists in the export - not a claim about everything it contains (e.g. an AnnotationOnly session can still carry a ChronicLFP recording for the same date)", "Levels": {
                "Upload": "A real device JSON upload landed on this calendar day",
                "AnnotationOnly": "No device upload, but a ChronicCustomEvent annotation exists for this date",
                "ChronicOnly": "No upload or annotation - exists only because a chronic segment's TherapyStartTime falls on this date",
                "ScaleOnly": "No upload/annotation/chronic activity - exists only for a trailing ScaleRecord submitted after the participant's last known session",
            }},
        }, fid, indent=2)


def write_subject_devices(bids_root, subject, device_rows):
    """device_rows: list of {"session_id": "ses-<label>", "model": str,
    "serial_hash": str}. Optional (only written when at least one session
    has device info) subject-root summary of which physical implant
    recorded each session, e.g. across a device replacement - the same
    de-identified info already repeated in every session's ieeg.json
    (ManufacturersModelName/DeviceSerialNumber) and in TherapyHistory/
    Impedance/PatientEvents' per-row DeviceId (see convert_participant()),
    collected here so it doesn't require cross-referencing every session by
    hand. Not a BIDS-recognized filename - flagged NOT_INCLUDED by
    bids-validator unless excluded via .bidsignore, so this adds itself
    there (idempotent - only appends the line once)."""
    device_rows = [row for row in device_rows if row.get("model") or row.get("serial_hash")]
    if not device_rows:
        return
    bidsignore_path = os.path.join(bids_root, ".bidsignore")
    ignore_line = "sub-*/sub-*_devices.json"
    existing = open(bidsignore_path).read().splitlines() if os.path.exists(bidsignore_path) else []
    if ignore_line not in existing:
        with open(bidsignore_path, "a") as fid:
            fid.write(ignore_line + "\n")

    subject_dir = os.path.join(bids_root, f"sub-{subject}")
    os.makedirs(subject_dir, exist_ok=True)
    path = os.path.join(subject_dir, f"sub-{subject}_devices.json")
    with open(path, "w") as fid:
        json.dump({
            row["session_id"]: {
                "Model": row.get("model") or "n/a",
                "DeviceSerialNumber": row.get("serial_hash") or "n/a",
            } for row in device_rows
        }, fid, indent=2)


def write_dataset_manifest(bids_root, subject):
    """Rebuilds sub-{subject}/sub-{subject}_manifest.json - every real data
    file (every ieeg/*_ieeg.edf, every beh/*_beh.tsv) across every session
    for this one participant, so a consumer can see what that participant's
    export contains without opening every session folder individually.

    Rebuilt from scratch by rescanning this subject's directory on every
    call, not updated incrementally - always reflects whatever's actually
    on disk. FileLock-guarded on the subject's own manifest path (same
    reasoning as upsert_participant() - concurrent AsyncJob exports of
    other participants never contend on this lock, and a rescan of one
    subject never touches another's file). Reads each file's own
    already-written sidecars (ieeg.json, channels.tsv, scans.tsv,
    sessions.tsv, devices.json) rather than recomputing anything - this is
    an index/join over data that already exists, not a new source of
    truth. Not a BIDS-recognized filename - self-registers in .bidsignore,
    same as write_subject_devices()."""
    subject_label = f"sub-{subject}"
    subject_dir = os.path.join(bids_root, subject_label)
    manifest_path = os.path.join(subject_dir, f"{subject_label}_manifest.json")
    with FileLock(manifest_path + ".lock", timeout=60):
        ignore_line = "sub-*/sub-*_manifest.json"
        bidsignore_path = os.path.join(bids_root, ".bidsignore")
        existing_ignores = open(bidsignore_path).read().splitlines() if os.path.exists(bidsignore_path) else []
        if ignore_line not in existing_ignores:
            with open(bidsignore_path, "a") as fid:
                fid.write(ignore_line + "\n")

        sessions_by_id = {}
        sessions_tsv = os.path.join(subject_dir, f"{subject_label}_sessions.tsv")
        if os.path.exists(sessions_tsv):
            for row in pd.read_csv(sessions_tsv, sep="\t", dtype=str, keep_default_na=False).to_dict("records"):
                sessions_by_id[row["session_id"]] = row

        devices_by_session = {}
        devices_json = os.path.join(subject_dir, f"{subject_label}_devices.json")
        if os.path.exists(devices_json):
            with open(devices_json) as fid:
                devices_by_session = json.load(fid)

        sessions = []
        file_count = 0
        for session_dir in sorted(glob.glob(os.path.join(subject_dir, "ses-*"))):
            session_label = os.path.basename(session_dir)  # "ses-20220908"
            session_info = sessions_by_id.get(session_label, {})
            device_info = devices_by_session.get(session_label, {})

            scans_by_filename = {}
            scans_tsv = os.path.join(session_dir, f"{subject_label}_{session_label}_scans.tsv")
            if os.path.exists(scans_tsv):
                for row in pd.read_csv(scans_tsv, sep="\t", dtype=str, keep_default_na=False).to_dict("records"):
                    scans_by_filename[row["filename"]] = row

            # Keyed by datatype folder name (ieeg, beh, ...) rather than
            # one flat list - mirrors the real on-disk layout. ieeg/beh
            # get full specialized parsing; any OTHER datatype folder
            # (e.g. a future "imaging") still gets picked up generically
            # rather than silently dropped, just without the type-
            # specific detail those two have.
            datatypes = {}
            session_file_count = 0

            ieeg_files = []
            for edf_path in sorted(glob.glob(os.path.join(session_dir, "ieeg", "*_ieeg.edf"))):
                basename = os.path.basename(edf_path)
                sidecar_path = edf_path[:-len("edf")] + "json"
                sidecar = {}
                if os.path.exists(sidecar_path):
                    with open(sidecar_path) as fid:
                        sidecar = json.load(fid)
                channels_path = edf_path.replace("_ieeg.edf", "_channels.tsv")
                channel_names = (
                    pd.read_csv(channels_path, sep="\t")["name"].tolist()
                    if os.path.exists(channels_path) else []
                )
                scan_row = scans_by_filename.get(f"ieeg/{basename}", {})
                ieeg_files.append({
                    "Filename": f"{subject_label}/{session_label}/ieeg/{basename}",
                    "Task": sidecar.get("TaskName", "n/a"),
                    "RecordingType": sidecar.get("RecordingType", "n/a"),
                    "SamplingFrequency": sidecar.get("SamplingFrequency", "n/a"),
                    "RecordingDuration": sidecar.get("RecordingDuration", "n/a"),
                    "ChannelCount": len(channel_names), "ChannelNames": channel_names,
                    "DeviceSerialNumber": sidecar.get("DeviceSerialNumber", device_info.get("DeviceSerialNumber", "n/a")),
                    "AcqTime": scan_row.get("acq_time", "n/a"),
                    "SourceId": scan_row.get("SourceId", "n/a"),
                    "AdjustedAlignment": scan_row.get("AdjustedAlignment", "n/a"),
                    "Timezone": scan_row.get("Timezone", session_info.get("Timezone", "n/a")),
                })
            if ieeg_files:
                datatypes["ieeg"] = ieeg_files
                session_file_count += len(ieeg_files)

            beh_files = []
            for beh_path in sorted(glob.glob(os.path.join(session_dir, "beh", "*_beh.tsv"))):
                basename = os.path.basename(beh_path)
                columns = pd.read_csv(beh_path, sep="\t", nrows=0).columns.tolist()
                with open(beh_path) as fid:
                    row_count = sum(1 for _ in fid) - 1
                task = basename.split("_task-")[1].split("_beh")[0] if "_task-" in basename else "n/a"
                beh_files.append({
                    "Filename": f"{subject_label}/{session_label}/beh/{basename}",
                    "Task": task, "RowCount": row_count, "Columns": columns,
                    "Timezone": session_info.get("Timezone", "n/a"),
                })
            if beh_files:
                datatypes["beh"] = beh_files
                session_file_count += len(beh_files)

            known_datatype_dirs = {"ieeg", "beh"}
            for datatype_dir in sorted(glob.glob(os.path.join(session_dir, "*"))):
                datatype = os.path.basename(datatype_dir)
                if not os.path.isdir(datatype_dir) or datatype in known_datatype_dirs:
                    continue
                other_files = [
                    {"Filename": f"{subject_label}/{session_label}/{datatype}/{os.path.basename(p)}"}
                    for p in sorted(glob.glob(os.path.join(datatype_dir, "*"))) if os.path.isfile(p)
                ]
                if other_files:
                    datatypes[datatype] = other_files
                    session_file_count += len(other_files)

            file_count += session_file_count
            sessions.append({
                "Session": session_label,
                "SessionType": session_info.get("SessionType", "n/a"),
                "AcqTime": session_info.get("acq_time", "n/a"),
                "Timezone": session_info.get("Timezone", "n/a"),
                **datatypes,
            })

        with open(manifest_path, "w") as fid:
            json.dump({
                "GeneratedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Subject": subject_label,
                "FileCount": file_count,
                "Sessions": sessions,
            }, fid, indent=2)


def write_electrodes(bids_root, subject, session, electrodes, coordinate_system="Other"):
    """electrodes: list of BRAVO Electrode-shaped dicts (target, hemisphere,
    channel_names, channel_coordinates). Coordinates are written as n/a when
    BRAVO has none on file - never fabricated.

    No impedance column here on purpose - see write_impedance_beh(). BRAVO
    records both a per-contact Monopolar value AND a full per-contact-pair
    Bipolar matrix per visit; electrodes.tsv's spec-native "impedance"
    column only has room for one scalar per contact (and BIDS expects
    electrodes.tsv to stay static unless electrodes are repositioned, not
    to carry a value that changes every visit) - both measurement types
    live together in one place instead of splitting Monopolar into this
    file and Bipolar into another."""
    ieeg_dir = os.path.join(bids_root, f"sub-{subject}", f"ses-{session}", "ieeg")
    os.makedirs(ieeg_dir, exist_ok=True)

    rows = []
    for lead in electrodes:
        coords = lead.get("channel_coordinates") or []
        for i, name in enumerate(lead["channel_names"]):
            xyz = coords[i] if i < len(coords) and coords[i] else [None, None, None]
            rows.append({
                "name": name,
                "x": xyz[0] if len(xyz) > 0 and xyz[0] is not None else "n/a",
                "y": xyz[1] if len(xyz) > 1 and xyz[1] is not None else "n/a",
                "z": xyz[2] if len(xyz) > 2 and xyz[2] is not None else "n/a",
                "size": "n/a",
                "manufacturer": "Medtronic",
                "group": lead["target"],
                "hemisphere": lead["hemisphere"],
                "type": "DBS",
                "CustomName": lead.get("custom_name") or "n/a",
            })

    base = os.path.join(ieeg_dir, f"sub-{subject}_ses-{session}_space-{coordinate_system}")
    # "" is a real value some upstream fields can carry (e.g. Electrode.hemisphere
    # is unpopulated for some ingestion paths) - BIDS wants n/a, not a blank cell.
    pd.DataFrame(rows).replace("", "n/a").to_csv(base + "_electrodes.tsv", sep="\t", index=False, na_rep="n/a")
    with open(base + "_coordsystem.json", "w") as fid:
        json.dump({
            "iEEGCoordinateSystem": coordinate_system,
            "iEEGCoordinateSystemDescription": "Electrode positions are not registered to a known imaging space in BRAVO - x/y/z are n/a unless a lead reconstruction (e.g. Lead-DBS) has been imported.",
            "iEEGCoordinateUnits": "mm",
        }, fid, indent=2)
    electrodes_descriptions = {
        "name": {"Description": "Channel/contact label"},
        "x": {"Description": "n/a unless a lead reconstruction (e.g. Lead-DBS) has been imported - see coordsystem.json"},
        "y": {"Description": "n/a unless a lead reconstruction (e.g. Lead-DBS) has been imported - see coordsystem.json"},
        "z": {"Description": "n/a unless a lead reconstruction (e.g. Lead-DBS) has been imported - see coordsystem.json"},
        "size": {"Description": "Contact surface area - not tracked by BRAVO, always n/a"},
        "manufacturer": {"Description": "Lead manufacturer"},
        "group": {"Description": "Which physical lead this contact belongs to - Electrode.custom_name if set, else the anatomical target (e.g. 'Right STN')"},
        "hemisphere": {"Description": "Implant hemisphere"},
        "type": {"Description": "Electrode type"},
        "CustomName": {"Description": "Clinician-assigned lead label (Electrode.custom_name), e.g. 'Right STN LFP' - already folded into the spec 'group' column above as a fallback-preferred value; kept here too, raw"},
    }
    with open(base + "_electrodes.json", "w") as fid:
        json.dump({col: electrodes_descriptions.get(col, {"Description": col}) for col in pd.DataFrame(rows).columns}, fid, indent=2)


def _missing_annotations(any_missing, sfreq):
    """Turn a per-sample missing/invalid row mask into mne Annotations so
    the discontinuity survives into the BIDS sidecar (RecordingType)
    instead of silently presenting gappy data as continuous."""
    if any_missing is None or not np.any(any_missing):
        return None

    onsets, durations = [], []
    in_gap = False
    start = 0
    for i, flag in enumerate(any_missing):
        if flag and not in_gap:
            start, in_gap = i, True
        elif not flag and in_gap:
            onsets.append(start / sfreq)
            durations.append((i - start) / sfreq)
            in_gap = False
    if in_gap:
        onsets.append(start / sfreq)
        durations.append((len(any_missing) - start) / sfreq)

    return mne.Annotations(onset=onsets, duration=durations, description=["BAD_missing"] * len(onsets))


# Medtronic Percept devices occasionally emit a garbage large-magnitude
# reading in place of a real BrainSense sample - NOT flagged by BRAVO's own
# per-sample `Missing` mask (verified against real participant data: every
# occurrence found had Missing == 0 at that exact index). First found as
# the exact uint32 sentinel 4294967295 (2**32 - 1); further real exports
# turned up other large values with no shared bit pattern (e.g.
# 3435973945, 3436029627) - there's no single fixed constant to match
# against, just "implausibly large for this device". Real Power/TD/Stim
# readings top out in the low 10000s (observed max ~10831 across every
# clean recording checked) - INVALID_VALUE_THRESHOLD is set two orders of
# magnitude above that, comfortably clear of any legitimate reading. Left
# as-is, one of these poisons an EDF channel's whole physical range (EDF's
# physical min/max header field is a fixed 8 ASCII characters) and would
# otherwise crash the export outright, the same way the Power-domain 1e6
# scaling bug above did. Treated the same way as a real device Missing
# gap: annotated as BAD_missing and held at the nearest valid sample rather
# than fabricating a value or leaving the garbage reading in the written
# signal.
INVALID_VALUE_THRESHOLD = 1_000_000


def _mask_invalid_samples(data):
    """Returns (cleaned_data, any_invalid_row_mask). Rows containing an
    implausibly large reading in any channel are forward/back-filled per
    channel from the nearest valid sample - see INVALID_VALUE_THRESHOLD."""
    invalid = np.abs(data) >= INVALID_VALUE_THRESHOLD
    any_invalid = invalid.any(axis=1)
    if not any_invalid.any():
        return data, any_invalid

    cleaned = data.copy()
    cleaned[invalid] = np.nan
    cleaned = pd.DataFrame(cleaned).ffill().bfill().to_numpy()
    return cleaned, any_invalid


# EDF signal labels are hard-capped at 16 characters. BRAVO's raw Medtronic
# channel codes (e.g. "ZERO_AND_THREE_LEFT_RING") routinely blow past that,
# so we abbreviate deterministically and keep the full name recoverable via
# an added "OriginalName" column in channels.tsv rather than losing it.
_CHANNEL_ABBREVIATIONS = {
    "ZERO": "0", "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4",
    "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9",
    "TEN": "10", "ELEVEN": "11", "AND": "-", "LEFT": "L", "RIGHT": "R",
    "RING": "RG", "SEGMENT": "SG", "REFERENCE": "REF", "STIMULATION": "STIM",
    # BrainSense Power-domain channel names carry a mixed-case " Stimulation"
    # suffix (e.g. "0_2_L Stimulation") - the all-caps STIMULATION entry
    # above only matches raw Medtronic-code names, not this one.
    "Stimulation": "Stim",
    # ChronicLFP channel names (ChronicBrainSense.py) are mixed-case
    # "RightHemisphere"/"LeftHemisphere" + " LFP"/" Amplitude" - none of the
    # all-caps entries above match these, so without this they fell back to
    # a blind 16-char truncation (e.g. "RightHemispher~1"), unreadable.
    "RightHemisphere": "RH", "LeftHemisphere": "LH", "Amplitude": "Amp",
}


def _shorten_channel_names(names):
    """Returns (short_names, {short: original}) - short_names <=16 chars,
    unique within this call."""
    seen = set()
    mapping = {}
    short_names = []
    for name in names:
        short = name
        for word, abbr in _CHANNEL_ABBREVIATIONS.items():
            short = short.replace(word, abbr)
        short = short.strip("_").replace("__", "_")
        if len(short) > 16:
            short = short[:16]
        base, n = short, 1
        while short in seen:
            suffix = f"~{n}"
            short = base[: 16 - len(suffix)] + suffix
            n += 1
        seen.add(short)
        mapping[short] = name
        short_names.append(short)
    return short_names, mapping


def write_ieeg_recording(bids_root, subject, session, task, recording, acquisition=None, run=1, ch_type="dbs", device=None, metadata=None, electrode_info=None):
    """recording: BRAVO recording dict - Data (n_samples, n_channels),
    SamplingRate, ChannelNames, optional Missing mask. Writes EDF + the
    channels.tsv/ieeg.json sidecars mne-bids generates, then patches in the
    fields mne-bids doesn't know about (RecordingType, Manufacturer).

    mne/edfio always treat a "dbs"-typed channel's RawArray values as Volts
    internally and multiply by 1e6 when computing the EDF physical
    min/max, regardless of what the data actually represents. So every
    "dbs"-typed channel - including arbitrary-unit BrainSense Power-domain
    output, which is NOT voltage - must be pre-divided by 1e6 here, purely
    to cancel that internal mne/edfio conversion back out and preserve the
    real magnitude in the written file. Skipping this for a "not really
    voltage" channel doesn't avoid a scale - it just leaves the wrong one
    in place: real Power values (up to ~10000s) then get written as
    physical_max ~1e10, which overflows EDF's 8-ASCII-character physical
    min/max header field and crashes the export outright. Verified via
    modules/BIDSExport/tests.py's round-trip check on a real Power-domain
    recording (participant sub-001/ses-18 hit this in production before the
    fix - values up to ~10831 were being written as ~1.08e10)."""
    data = np.asarray(recording["Data"], dtype=float)
    sfreq = float(recording["SamplingRate"])
    # Type inference (Power vs Stimulation suffix) must run on the original
    # names - shortening can truncate the very suffix it looks for.
    ch_types = _channel_types_for(ch_type, recording["ChannelNames"])
    ch_names, original_names = _shorten_channel_names(recording["ChannelNames"])

    data, sentinel_missing = _mask_invalid_samples(data)
    missing = recording.get("Missing")
    any_missing = np.any(np.asarray(missing) > 0, axis=1) if missing is not None else None
    any_missing = sentinel_missing if any_missing is None else (any_missing | sentinel_missing)

    scale = 1e-6  # see docstring - unconditional, not just for real voltage channels
    info = mne.create_info(ch_names, sfreq, ch_types=ch_types)
    info["line_freq"] = POWER_LINE_FREQUENCY_HZ
    raw = mne.io.RawArray((data * scale).T, info, verbose=False)
    # Every real BRAVO recording type sets StartTime at ingestion (see
    # BrainSenseStream.py/IndefiniteStream.py/BrainSenseSurvey.py) - without
    # this, RawArray's meas_date stays None and mne-bids writes "n/a" into
    # every row of scans.tsv's acq_time instead of the recording's real
    # start time.
    if recording.get("StartTime") is not None:
        raw.set_meas_date(datetime.datetime.fromtimestamp(float(recording["StartTime"]), tz=datetime.timezone.utc))

    annotations = _missing_annotations(any_missing, sfreq)
    if annotations is not None:
        raw.set_annotations(annotations)

    bids_path = BIDSPath(subject=subject, session=session, task=task,
                          acquisition=acquisition, run=run, datatype="ieeg", root=bids_root)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        write_raw_bids(raw, bids_path, format="EDF", allow_preload=True, overwrite=True, verbose=False)

    # mne-bids always writes a placeholder electrodes.tsv/coordsystem.json per
    # acquisition (all-n/a coordinates, no hemisphere/impedance/etc) even with
    # no montage set. We write our own authoritative one in write_electrodes()
    # - remove mne-bids's so the two don't coexist under different filenames.
    for suffix, extension in (("electrodes", ".tsv"), ("electrodes", ".json"), ("coordsystem", ".json")):
        stale = bids_path.copy().update(task=None, run=None, suffix=suffix, extension=extension).fpath
        if os.path.exists(stale):
            os.remove(stale)

    sidecar_path = bids_path.copy().update(suffix="ieeg", extension=".json").fpath
    with open(sidecar_path) as fid:
        sidecar = json.load(fid)
    sidecar["RecordingType"] = "discontinuous" if annotations is not None else "continuous"
    sidecar["Manufacturer"] = "Medtronic"
    if ch_type == "power_stim":
        # BrainSense Power-domain channels are forced to mne's "dbs" type
        # purely for the Volts pre-scale workaround above (see this
        # function's docstring) - they aren't real SEEG contacts, so
        # mne-bids's auto-computed SEEGChannelCount is wrong for this run.
        # Reclassify the count itself (not the mne channel type - that
        # would undo the scaling workaround and reintroduce the physical
        # min/max overflow crash it fixes).
        sidecar["MiscChannelCount"] = sidecar.get("MiscChannelCount", 0) + sidecar.get("SEEGChannelCount", 0)
        sidecar["SEEGChannelCount"] = 0
    # device: {"model": DBSDevice.type, "serial_hash": HMAC-hashed serial_number}
    # - see Gather._device_dict(). Battery %/estimated EOL/implant date have no
    # BIDS-recognized sidecar field, so they're deliberately not written here -
    # see docs/BIDS_MAPPING.md "Known gaps".
    if device and device.get("model"):
        sidecar["ManufacturersModelName"] = device["model"]
    if device and device.get("serial_hash"):
        sidecar["DeviceSerialNumber"] = device["serial_hash"]
    if metadata:
        # Recording.metadata (DB-row-level summary set at ingestion, e.g.
        # {"ChannelNames": [...], "Duration": ...}) - fails strict
        # bids-validator schema check (JSON_SCHEMA_VALIDATION_ERROR:
        # ieeg.json rejects unrecognized top-level keys, same as
        # AdjustedAlignment hit before it moved to scans.tsv) - kept here
        # anyway per explicit instruction to put it directly in the sidecar.
        # ChannelNames here is raw/original (set at ingestion) - remap to the
        # shortened channels.tsv "name" values so metadata cross-references
        # the same names the rest of the file uses.
        metadata = dict(metadata)
        if "ChannelNames" in metadata:
            short_by_original = {orig: short for short, orig in original_names.items()}
            metadata["ChannelNames"] = [short_by_original.get(n, n) for n in metadata["ChannelNames"]]
        sidecar["metadata"] = metadata
    # Recording.type/Recording.name, raw - NOT the same as TaskName (BIDS-
    # legal, filename-locked) or RecordingType (spec-controlled vocabulary,
    # continuous/discontinuous only - verified a non-enum value here fails
    # bids-validator's "should be equal to one of the allowed values"
    # check). Same schema-rejection tradeoff as metadata above. Reordered to
    # the front (Name first, Type right after, ahead of RecordingType) per
    # explicit instruction - everything else keeps its existing order.
    sidecar = {"Name": recording.get("Name", "n/a"), "Type": recording.get("Type", "n/a"), **sidecar}
    with open(sidecar_path, "w") as fid:
        json.dump(sidecar, fid, indent=2)

    channels_path = bids_path.copy().update(suffix="channels", extension=".tsv").fpath
    channels_df = pd.read_csv(channels_path, sep="\t")
    channels_df["OriginalName"] = channels_df["name"].map(original_names)

    units_by_original_name = _channel_units_for(ch_type, recording["ChannelNames"])
    if units_by_original_name is not None:
        channels_df["units"] = channels_df["OriginalName"].map(units_by_original_name)

    if electrode_info:
        # Same platform-canonical channel-naming reference
        # DataAnalysis.queryAllRecordings() already uses (hemisphere-prefix
        # -> Electrode.custom_name substitution) - see Gather.gather_session's
        # electrode_info. Guarded per-channel: Percept.reformatChannelName can
        # raise on a shape it doesn't recognize (e.g. ElectrodeIdentifier/
        # StimulationMontages aren't in queryAllRecordings's own filter, so
        # they're not vetted against real platform behavior the way the
        # other types are) - falls back to the raw name rather than failing
        # the whole export over a decorative label.
        clinical_names = {}
        for orig_name in recording["ChannelNames"]:
            try:
                clinical_names[orig_name] = BrainSenseStream.reformatChannelName(orig_name, electrode_info)
            except Exception:
                clinical_names[orig_name] = orig_name
            if ch_type == "power_stim":
                # Mirrors queryAllRecordings' MedtronicBrainSensePowerDomain
                # branch exactly - unconditional suffix regardless of
                # whether a real electrode match was found above.
                clinical_names[orig_name] += " Stimulation" if orig_name.endswith("Stimulation") else " Recording"
        channels_df["ClinicalName"] = channels_df["OriginalName"].map(clinical_names)

    channels_df.to_csv(channels_path, sep="\t", index=False, na_rep="n/a")

    channels_json_path = bids_path.copy().update(suffix="channels", extension=".json").fpath
    channels_descriptions = {
        "name": {"Description": "Shortened technical label, <=16 characters to fit the EDF signal label limit - not the channel's real name, see OriginalName"},
        "type": {"Description": "BIDS channel type"},
        "units": {"Description": "Physical unit of the channel's values"},
        "low_cutoff": {"Description": "Hardware/software high-pass filter cutoff applied to this channel, n/a if unknown", "Units": "Hz"},
        "high_cutoff": {"Description": "Hardware/software low-pass filter cutoff applied to this channel, n/a if unknown", "Units": "Hz"},
        "description": {"Description": "Brief free-text description of the channel"},
        "sampling_frequency": {"Description": "Sampling rate of this channel", "Units": "Hz"},
        "status": {"Description": "Data quality of this channel", "Levels": {"good": "Included, no known quality issue", "bad": "Known quality issue"}},
        "status_description": {"Description": "Free-text explanation for status, n/a if good"},
        "OriginalName": {"Description": "The channel's real name (full Medtronic channel code) - name above is only the shortened EDF-safe label"},
        "ClinicalName": {"Description": "Clinician-facing channel name (Electrode.custom_name substituted for the hemisphere prefix, e.g. 'Right STN LFP E00-E03') - same reformatting DataAnalysis.queryAllRecordings() uses platform-wide, falls back to OriginalName if no electrode matched"},
    }
    with open(channels_json_path, "w") as fid:
        json.dump({col: channels_descriptions.get(col, {"Description": col}) for col in channels_df.columns}, fid, indent=2)

    # AdjustedAlignment doesn't fit the ieeg.json sidecar (schema rejects
    # unrecognized top-level keys there - see Recording.adjusted_alignment in
    # Gather.gather_session) so it's recorded per-run in scans.tsv instead,
    # same custom-column pattern as channels.tsv's OriginalName above.
    edf_path = bids_path.copy().update(suffix="ieeg", extension=".edf")
    scans_path = edf_path.copy().update(
        datatype=None, task=None, acquisition=None, run=None, suffix="scans", extension=".tsv"
    ).fpath
    # dtype=str/keep_default_na=False: without this, pandas' default NA-string
    # list (which includes literal "n/a") reinterprets our own na_rep="n/a"
    # placeholder as real NaN on the next read - coercing a column like
    # SourceId to float64 the moment every row in it happens to be "n/a",
    # then crashing the next run's string assignment into it.
    scans_df = pd.read_csv(scans_path, sep="\t", dtype=str, keep_default_na=False)
    row_filename = f"{edf_path.datatype}/{edf_path.basename}"
    row_mask = scans_df["filename"] == row_filename
    scans_df.loc[row_mask, "AdjustedAlignment"] = str(recording.get("AdjustedAlignment", 0))
    # SourceFile.uid this run's data came from - a day-merged session can
    # concatenate runs from several separate uploads (see Gather.gather_day()),
    # so this can differ row-to-row even within one scans.tsv.
    scans_df.loc[row_mask, "SourceId"] = recording.get("SourceId", "n/a")
    # acq_time (set via set_meas_date above) is always UTC - Timezone is the
    # BRAVO-stored UTC-offset for this specific upload, so the participant's
    # real local time is recoverable without guessing.
    scans_df.loc[row_mask, "Timezone"] = recording.get("Timezone", "n/a")
    scans_df.replace("", "n/a").to_csv(scans_path, sep="\t", index=False, na_rep="n/a")

    scans_json_path = str(scans_path)[:-len(".tsv")] + ".json"
    with open(scans_json_path, "w") as fid:
        json.dump({
            "AdjustedAlignment": {"Description": "Manual clock-drift correction (Recording.adjusted_alignment) already folded into acq_time - recorded here so the correction itself stays traceable", "Units": "s"},
            "SourceId": {"Description": "SourceFile.uid of the specific upload this run's data came from"},
            "Timezone": {"Description": "BRAVO-stored UTC offset (e.g. 'UTC-04:00') for the upload this run came from - acq_time is UTC, so this is needed to recover local time"},
        }, fid, indent=2)

    return bids_path


def write_beh_tsv(bids_root, subject, session, task, dataframe, column_descriptions, acquisition=None):
    """column_descriptions: {column_name: {"Description": ...}}. Any dataframe
    column missing from it gets a bare fallback so the validator never flags
    an undescribed custom column, even for dynamically-named ones (e.g. the
    per-hemisphere chronic LFP channels). acquisition: optional acq-<label>
    entity - e.g. distinguishing ScaleRecord forms under one shared
    task-PatientSurvey rather than encoding the form name into task itself
    (BIDS task labels are alphanumeric-only, verified - no separator survives
    to keep "PatientSurvey" and the form name visually apart within one)."""
    beh_dir = os.path.join(bids_root, f"sub-{subject}", f"ses-{session}", "beh")
    os.makedirs(beh_dir, exist_ok=True)
    acq_part = f"_acq-{acquisition}" if acquisition else ""
    base = os.path.join(beh_dir, f"sub-{subject}_ses-{session}_task-{task}{acq_part}")

    # "" is a real value some Percept fields can carry (e.g. an unnamed
    # therapy group) - BIDS wants that written as n/a, not a blank cell.
    dataframe.replace("", "n/a").to_csv(base + "_beh.tsv", sep="\t", index=False, na_rep="n/a")

    full_descriptions = {col: column_descriptions.get(col, {"Description": col}) for col in dataframe.columns}
    with open(base + "_beh.json", "w") as fid:
        json.dump(full_descriptions, fid, indent=2)


CHRONIC_SAMPLING_INTERVAL = 600.0  # seconds - see _chronic_recording()


def _chronic_recording(activity):
    """activity: one therapy-change-bounded segment, as built by
    modules.MedtronicPercept.ChronicBrainSense.extractChronicNeuralActivity()
    - {Time (list of real unix-second timestamps, irregular only in the
    sense that some ~600s slots are missing), Data ((n_channels, n_samples)
    - channel-major, unlike every other BRAVO recording), ChannelNamesFix
    (already CustomName-substituted, see that function's own hemisphere-
    prefix swap - same substitution Gather._chronic_dicts() used to redo
    independently)}.

    Reindexes onto a strict CHRONIC_SAMPLING_INTERVAL grid spanning this
    segment's own first-to-last real sample. Verified empirically (8 real
    chronic recordings, up to 8523 samples each) that the device already
    logs on almost exactly this grid whenever it's actually logging - the
    observed "irregularity" is real missed polls (device off/not worn), not
    jitter (median/min interval was exactly 600.0s in every recording
    checked). So this is a grid *alignment*, not resampling/interpolation -
    every real sample keeps its own real value, snapped to its nearest
    slot; only genuinely missing slots get a placeholder, and those are
    flagged via the same Missing-mask -> BAD_missing annotation mechanism
    write_ieeg_recording() already uses for real device Missing gaps, so a
    consumer never mistakes a gap for continuous data."""
    time = np.asarray(activity["Time"], dtype=float)
    data = np.asarray(activity["Data"], dtype=float).T  # -> (n_samples, n_channels), matching every other recording
    # The raw device spelling ("RightHemisphere LFP") - not
    # ChannelNamesFix's CustomName-substituted version.
    channel_names = activity["ChannelNames"]

    start = time[0]
    n_slots = int(round((time[-1] - start) / CHRONIC_SAMPLING_INTERVAL)) + 1
    slot_idx = np.round((time - start) / CHRONIC_SAMPLING_INTERVAL).astype(int)
    slot_idx = np.clip(slot_idx, 0, n_slots - 1)  # guard against float round-trip pushing the last sample one slot past the end

    grid_data = np.full((n_slots, data.shape[1]), np.nan)
    missing = np.ones((n_slots, data.shape[1]))
    grid_data[slot_idx] = data
    missing[slot_idx] = 0

    # Same forward/back-fill treatment _mask_invalid_samples() gives a real
    # device Missing gap - a placeholder value has to be something (EDF
    # can't hold NaN), and the Missing mask (not the value) is what tells a
    # consumer this slot isn't real data.
    grid_data = pd.DataFrame(grid_data).ffill().bfill().to_numpy()

    return {
        "SamplingRate": 1.0 / CHRONIC_SAMPLING_INTERVAL,
        "Data": grid_data,
        "Missing": missing,
        "ChannelNames": channel_names,
        "StartTime": start,
        "Type": "MedtronicChronicBrainSense",
        "Name": "n/a",
    }


_CHRONIC_CHANNELS_DESCRIPTIONS = {
    "name": {"Description": "Abbreviated channel label (e.g. 'RH LFP'), <=16 characters to fit the EDF signal label limit - see OriginalName for the unabbreviated device channel name"},
    "type": {"Description": "BIDS channel type"},
    "OriginalName": {"Description": "Original, unabbreviated device channel name (e.g. 'RightHemisphere LFP')"},
    "units": {"Description": "Physical unit of the channel's values"},
    "low_cutoff": {"Description": "Hardware/software high-pass filter cutoff applied to this channel, n/a if unknown", "Units": "Hz"},
    "high_cutoff": {"Description": "Hardware/software low-pass filter cutoff applied to this channel, n/a if unknown", "Units": "Hz"},
    "description": {"Description": "Brief free-text description of the channel"},
    "sampling_frequency": {"Description": "Sampling rate of this channel", "Units": "Hz"},
    "status": {"Description": "Data quality of this channel", "Levels": {"good": "Included, no known quality issue", "bad": "Known quality issue"}},
    "status_description": {"Description": "Free-text explanation for status, n/a if good"},
}


def write_chronic_lfp_recording(bids_root, subject, session, activity, run, device=None):
    """Writes one therapy-change-bounded chronic segment (see
    _chronic_recording()) as a real ieeg/ recording, task-ChronicLFP.

    Bypasses mne/mne-bids entirely for the actual EDF write. mne's EDF
    exporter computes the EDF data-record duration as floor(sfreq)/sfreq;
    at sfreq=1/600 Hz that's floor(0.00167)/0.00167 = 0/0.00167 = NaN - a
    real mne bug/limitation for any sfreq < 1 Hz, reproduced with a bare
    two-line RawArray unrelated to anything BRAVO-specific, not an EDF
    format limitation. Writing directly via edfio instead, with an
    explicit data_record_duration of exactly one sample per channel per
    record, sidesteps it entirely - EDF itself has no problem representing
    a slow-sampled signal this way.

    Also means write_ieeg_recording()'s forced-"dbs"-type + 1e-6 pre-scale
    workaround doesn't apply here - that exists purely to cancel out mne's
    own internal Volts assumption, which this path never goes through.
    Real values are written directly; edfio computes each signal's
    physical_range from the actual data by default, so there's no EDF
    physical-range overflow risk the way Power-domain hit either."""
    recording = _chronic_recording(activity)
    data = recording["Data"]  # (n_samples, n_channels)
    sfreq = recording["SamplingRate"]  # the TRUE rate (1/600 Hz) - see ieeg.json's SamplingFrequency below
    channel_names = recording["ChannelNames"]
    ch_names, original_names = _shorten_channel_names(channel_names)
    units_by_original_name = _channel_units_for("chronic", channel_names) or {}

    # The EDF itself is written at a nominal 1 Hz - NOT the true rate. Every
    # real sample is kept as-is, none padded/held/fabricated; only the
    # declared time unit changes. 1/600 Hz can't be represented exactly in
    # binary floating point, and edfio requires n_samples/sampling_frequency
    # to divide data_record_duration EXACTLY - verified this fails
    # unpredictably (not size-correlated: n=778 and n=100 fail, n=2000 and
    # n=8523 happen to pass) for real segment sizes. 1.0 Hz sidesteps this
    # entirely (n/1.0 is always exact for any integer n). The true interval
    # (CHRONIC_SAMPLING_INTERVAL, 600s/sample) is recorded in ieeg.json's
    # SamplingFrequencyMultiplier so a consumer reading the raw EDF
    # directly (bypassing our sidecar) isn't fooled into thinking this is
    # real 1 Hz data - every declared "1 second" of file time is really
    # CHRONIC_SAMPLING_INTERVAL real seconds.
    edf_sfreq = 1.0
    start = datetime.datetime.fromtimestamp(recording["StartTime"], tz=datetime.timezone.utc)
    signals = []
    for i, short_name in enumerate(ch_names):
        orig_name = original_names[short_name]
        unit = units_by_original_name.get(orig_name, "n/a")
        signals.append(EdfSignal(
            data[:, i], sampling_frequency=edf_sfreq, label=short_name,
            physical_dimension="" if unit == "n/a" else unit,
        ))

    missing = recording["Missing"]
    any_missing = np.any(np.asarray(missing) > 0, axis=1)
    # Annotation onset/duration are positions on the file's OWN declared
    # timeline (nominal seconds, one per sample) - not real seconds, same
    # reasoning as edf_sfreq above.
    gap_annotations = _missing_annotations(any_missing, edf_sfreq)
    edf_annotations = [
        EdfAnnotation(onset, duration, "BAD_missing")
        for onset, duration in zip(gap_annotations.onset, gap_annotations.duration)
    ] if gap_annotations is not None else None

    edf = Edf(
        signals, data_record_duration=1.0 / edf_sfreq, starttime=start.time(),
        recording=EdfRecording(startdate=start.date()), annotations=edf_annotations,
    )

    bids_path = BIDSPath(subject=subject, session=session, task="ChronicLFP",
                          run=run, datatype="ieeg", root=bids_root)
    edf_path = bids_path.copy().update(suffix="ieeg", extension=".edf")
    os.makedirs(os.path.dirname(edf_path.fpath), exist_ok=True)
    edf.write(edf_path.fpath)

    duration_s = (len(data) - 1) / sfreq if len(data) > 1 else 0.0
    sidecar = {
        "Name": recording.get("Name", "n/a"), "Type": recording.get("Type", "n/a"),
        "TaskName": "ChronicLFP",
        "Manufacturer": "Medtronic",
        "PowerLineFrequency": POWER_LINE_FREQUENCY_HZ,
        "SamplingFrequency": sfreq,  # the TRUE rate - the EDF itself is declared at 1 Hz, see below
        # The EDF's own internally-declared rate is a nominal 1 Hz, not this
        # true SamplingFrequency (see write_chronic_lfp_recording's
        # docstring) - multiply any second-based offset read directly off
        # the raw EDF (bypassing this sidecar) by this factor to get real
        # elapsed seconds.
        "SamplingFrequencyMultiplier": CHRONIC_SAMPLING_INTERVAL,
        "SoftwareFilters": "n/a",
        "RecordingDuration": duration_s,
        "RecordingType": "discontinuous" if edf_annotations else "continuous",
        "iEEGReference": "n/a",
        "ECOGChannelCount": 0, "SEEGChannelCount": 0, "EEGChannelCount": 0,
        "EOGChannelCount": 0, "ECGChannelCount": 0, "EMGChannelCount": 0,
        # Not real SEEG contacts (same reasoning as write_ieeg_recording's
        # power_stim SEEG->Misc reclassification) - counted as Misc from
        # the start here rather than reassigned after the fact.
        "MiscChannelCount": len(ch_names), "TriggerChannelCount": 0,
    }
    if device and device.get("model"):
        sidecar["ManufacturersModelName"] = device["model"]
    if device and device.get("serial_hash"):
        sidecar["DeviceSerialNumber"] = device["serial_hash"]
    sidecar_path = bids_path.copy().update(suffix="ieeg", extension=".json").fpath
    with open(sidecar_path, "w") as fid:
        json.dump(sidecar, fid, indent=2)

    nyquist = sfreq / 2
    channels_rows = [{
        "name": ch_names[i], "type": "MISC",
        "units": units_by_original_name.get(original_names[ch_names[i]], "n/a"),
        "low_cutoff": 0.0, "high_cutoff": nyquist,
        "description": "Chronic BrainSense LFP trend", "sampling_frequency": sfreq,
        "status": "good", "status_description": "n/a",
        "OriginalName": original_names[ch_names[i]],
    } for i in range(len(ch_names))]
    channels_path = bids_path.copy().update(suffix="channels", extension=".tsv").fpath
    pd.DataFrame(channels_rows).to_csv(channels_path, sep="\t", index=False, na_rep="n/a")
    channels_json_path = bids_path.copy().update(suffix="channels", extension=".json").fpath
    with open(channels_json_path, "w") as fid:
        json.dump({
            col: _CHRONIC_CHANNELS_DESCRIPTIONS.get(col, {"Description": col})
            for col in channels_rows[0].keys()
        }, fid, indent=2)

    _write_chronic_scans_row(bids_path, edf_path, start, recording)

    return bids_path


def _write_chronic_scans_row(bids_path, edf_path, start, recording):
    """Creates or updates one scans.tsv row for edf_path. Unlike
    write_ieeg_recording()'s scans.tsv patch (which only ever updates a row
    write_raw_bids() already created), write_chronic_lfp_recording() never
    calls write_raw_bids() at all - this has to create the row (and the
    file itself, for a chronic-only session with no other ieeg/ recording)
    from scratch as easily as it updates one."""
    scans_path = edf_path.copy().update(
        datatype=None, task=None, run=None, suffix="scans", extension=".tsv"
    ).fpath
    row_filename = f"{edf_path.datatype}/{edf_path.basename}"
    if os.path.exists(scans_path):
        # Same dtype=str/keep_default_na=False reasoning as
        # write_ieeg_recording's scans.tsv patch - our own na_rep="n/a"
        # would otherwise round-trip back as real NaN and coerce columns.
        scans_df = pd.read_csv(scans_path, sep="\t", dtype=str, keep_default_na=False)
    else:
        os.makedirs(os.path.dirname(scans_path), exist_ok=True)
        scans_df = pd.DataFrame(columns=["filename", "acq_time"])
    if row_filename not in set(scans_df["filename"]):
        scans_df = pd.concat([scans_df, pd.DataFrame([{"filename": row_filename}])], ignore_index=True)
    row_mask = scans_df["filename"] == row_filename
    scans_df.loc[row_mask, "acq_time"] = start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    scans_df.loc[row_mask, "AdjustedAlignment"] = str(recording.get("AdjustedAlignment", 0))
    scans_df.loc[row_mask, "SourceId"] = recording.get("SourceId", "n/a")
    scans_df.loc[row_mask, "Timezone"] = recording.get("Timezone", "n/a")
    scans_df.replace("", "n/a").to_csv(scans_path, sep="\t", index=False, na_rep="n/a")

    scans_json_path = str(scans_path)[:-len(".tsv")] + ".json"
    with open(scans_json_path, "w") as fid:
        json.dump({
            "AdjustedAlignment": {"Description": "Manual clock-drift correction (Recording.adjusted_alignment) already folded into acq_time - recorded here so the correction itself stays traceable", "Units": "s"},
            "SourceId": {"Description": "SourceFile.uid of the specific upload this run's data came from"},
            "Timezone": {"Description": "BRAVO-stored UTC offset (e.g. 'UTC-04:00') for the upload this run came from - acq_time is UTC, so this is needed to recover local time"},
        }, fid, indent=2)


def chronic_neural_activity_dataframe(activities, session_start):
    """activities: list of 'Activity' dict segments as built by
    modules.MedtronicPercept.ChronicBrainSense's chronic-neural-activity
    computation - each is one contiguous therapy-period's worth of chronic
    LFP/Amplitude samples, tagged with a human-readable therapy description
    per channel. Long/tidy format (one row per sample per channel, not one
    column per channel like chronic_lfp_dataframe) since the therapy label
    can differ between channels within the same segment (e.g. only one
    hemisphere got reprogrammed)."""
    rows = []
    for activity in activities:
        time = np.asarray(activity["Time"])
        data = np.asarray(activity["Data"])  # (n_channels, n_samples)
        names = activity.get("ChannelNamesFix") or activity.get("ChannelNames") or []
        therapy_strings = activity.get("TherapyString") or []
        for ch_idx, name in enumerate(names):
            therapy_label = therapy_strings[ch_idx] if ch_idx < len(therapy_strings) else "n/a"
            for sample_idx, t in enumerate(time):
                rows.append({
                    "onset": t - session_start,
                    "Channel": name,
                    "Value": data[ch_idx, sample_idx],
                    "TherapyLabel": therapy_label,
                })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["onset", "Channel"]).reset_index(drop=True)


def write_chronic_neural_activity_derivative(bids_root, subject, session, activities, session_start):
    """Writes MedtronicChronicNeuralActivity - a BRAVO-computed join of data
    already exported raw elsewhere (ChronicLFP + TherapyHistory/Stimulation/
    Adaptive - see docs/BIDS_MAPPING.md "Known gaps") - as a convenience
    pre-joined table under derivatives/, not rawdata/, since it's derived,
    not raw device output. No-op if there's nothing for this session."""
    if not activities:
        return
    derivatives_root = os.path.join(bids_root, "derivatives", "bravo-chronic-neural-activity")
    write_dataset_description(derivatives_root, name="BRAVO Chronic Neural Activity (derived)", dataset_type="derivative")
    df = chronic_neural_activity_dataframe(activities, session_start)
    if not df.empty:
        write_beh_tsv(derivatives_root, subject, session, "ChronicNeuralActivity", df, {
            "onset": {"Description": "Seconds relative to session start", "Units": "s"},
            "Channel": {"Description": "Hemisphere/lead channel name (renamed to the lead's custom name, e.g. 'Right STN LFP'/'Right STN Amplitude')"},
            "Value": {"Description": "Sample value - LFP (arbitrary units) or stimulation Amplitude (mA), per channel"},
            "TherapyLabel": {"Description": "Human-readable therapy/sensing description active for this channel during this sample - a BRAVO-computed summary of the same TherapyHistory/TherapyStimulation/TherapyAdaptive rows already exported in rawdata/"},
        })


def therapy_history_dataframe(therapies, session_start, onset_bounds=None, device_id="n/a"):
    """therapies: the `Therapies` list as returned by Session.py's
    decodeMedtronicJSON - one row per hemisphere per group/session. One row
    per (stimulation program, contact) within that group - fully
    normalized, no packed-list cells. A program (a single ElectricalStimulation
    DB row, i.e. what Server.models.Therapy.ElectricalStimulation.get_info()
    returns) can drive several contacts at once (e.g. a segmented-ring
    combination) plus one or more return contacts - each of those gets its
    own row here, distinguished by `Role` (Active vs Return), rather than
    joining the list into one cell.

    Group-level fields (RecordType/GroupName/GroupType/Label/StimulationType)
    are the same across every row for that group by construction -
    denormalized on purpose, same as a channels.tsv repeating acquisition
    params per channel. This used to be two separate tables
    (TherapyHistory: one summary row per group; TherapyStimulation: one row
    per program/contact, joined back via (onset, hemisphere, group_id)) -
    merged into one because a group's `StimulationType` column
    (ElectricalStimulation.get_info()'s `StimulationType`) is literally
    `self.group.stimulation_type` (see Server/models/Therapy.py) - the exact
    same group-level value the old TherapyHistory table already carried, not
    a distinct per-program concept - so keeping them apart bought nothing
    but an extra join. A group with no stimulation programs at all (should
    not happen for a real Percept-ingested group - modules/MedtronicPercept/
    Therapy.py::extractTherapySettings always appends at least one program -
    but not guaranteed by the model) still gets one row with `Program`-level
    fields "n/a", so a group is never silently dropped."""
    rows = []
    for therapy in therapies:
        shared = {
            "onset": _clamp_onset(therapy["date"] - session_start, onset_bounds),
            "duration": 0,
            "DeviceId": device_id,
            "SourceId": therapy.get("source_id", "n/a"),
            "Hemisphere": therapy["hemisphere"],
            "RecordType": therapy["type"],
            "GroupId": therapy["group_id"],
            "GroupName": therapy["group_name"],
            "GroupType": therapy.get("group_type") or "n/a",
            "Label": therapy.get("label") or "n/a",
            "StimulationType": therapy["stimulation_type"],
        }
        programs = [p for p in (therapy.get("stimulation_settings") or []) if p is not None]
        if not programs:
            rows.append({
                **shared, "ProgramIndex": "n/a", "Contact": "n/a", "Role": "n/a",
                "Amplitude": "n/a", "AmplitudeUnit": "n/a", "FractionalAmplitude": "n/a",
                "Pulsewidth": "n/a", "PulsewidthUnit": "n/a", "Frequency": "n/a",
                "Cycling": "n/a", "CyclingPeriod": "n/a",
            })
            continue
        for i, program in enumerate(programs):
            program_shared = {
                **shared,
                "ProgramIndex": i,
                "Amplitude": program.get("Amplitude", "n/a"),
                "AmplitudeUnit": program.get("AmplitudeUnit", "n/a"),
                "Pulsewidth": program.get("Pulsewidth", "n/a"),
                "PulsewidthUnit": program.get("PulsewidthUnit", "n/a"),
                "Frequency": program.get("Frequency", "n/a"),
                "Cycling": program.get("Cycling", "n/a"),
                "CyclingPeriod": program.get("CyclingPeriod", "n/a"),
            }
            # FractionalAmplitudes (Server.models.Therapy.ElectricalStimulation.amplitude_fraction)
            # is a flat list of per-contact mA values, positionally parallel to
            # Contact (cathodes) only - never Contact.get_info() re-keys it, and
            # ReturnContact never has one. Can be shorter than Contact (or empty)
            # for non-current-steering programs - "n/a" when there's no entry.
            fractional_amplitudes = program.get("FractionalAmplitudes") or []
            for contact_index, contact in enumerate(program.get("Contact", []) or []):
                fraction = fractional_amplitudes[contact_index] if contact_index < len(fractional_amplitudes) else "n/a"
                rows.append({**program_shared, "Contact": contact, "Role": "Active", "FractionalAmplitude": fraction})
            for contact in program.get("ReturnContact", []) or []:
                rows.append({**program_shared, "Contact": contact, "Role": "Return", "FractionalAmplitude": "n/a"})
    columns = ["onset", "duration", "Hemisphere", "RecordType", "GroupId", "GroupName", "GroupType", "Label",
               "StimulationType", "ProgramIndex", "Contact", "Role", "Amplitude", "AmplitudeUnit",
               "FractionalAmplitude", "Pulsewidth", "PulsewidthUnit", "Frequency", "Cycling", "CyclingPeriod"]
    # ProgramIndex is excluded from the sort key: it's "n/a" (str) for a
    # group with no stimulation programs but an int for every real program,
    # and mixing str/int within one column blows up pandas's sort - Role/
    # Contact are enough to order rows deterministically within a group.
    return pd.DataFrame(rows)[columns].sort_values(
        ["onset", "GroupId", "Role", "Contact"]
    ).reset_index(drop=True)


def _pair(values, index, default="n/a"):
    return values[index] if isinstance(values, (list, tuple)) and len(values) > index else default


def _clamp_onset(onset, onset_bounds):
    """onset_bounds: (lower, upper), each independently optional (None =
    unbounded on that side) - see Gather.export_participant()'s
    prev_session_end/session_end. A device-reported "Past Therapy"/
    impedance/event readout gets re-included in every visit's upload, so
    without this a stale duplicate can land with a wildly-off onset
    reaching back (or forward) past the actual adjacent visit. Only
    per-visit point-in-time readouts get clamped (therapy, impedance,
    events, annotations) - continuous device-timestamped trends
    (ChronicLFP) aren't duplicated per-visit the same way, so they're left
    alone."""
    if onset_bounds is None:
        return onset
    lower, upper = onset_bounds
    if upper is not None and onset > upper:
        onset = upper
    if lower is not None and onset < lower:
        onset = lower
    return onset


def _iso(unix_time):
    return datetime.datetime.fromtimestamp(unix_time, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bids_label(text, fallback):
    """BIDS entity/task labels are alphanumeric only (no spaces/punctuation).
    Used for a ScaleForms name -> task-<label> filename - falls back to
    `fallback` (e.g. "Form0") if nothing alphanumeric survives."""
    label = re.sub(r"[^A-Za-z0-9]", "", text or "")
    return label or fallback


def _flatten_scale_answers(questions, answers):
    """questions: one ScaleRecord's own `source.record` (ScaleForms.record) -
    the EXACT form version this record was submitted against, not
    "the form" generically (ScaleForms.update_version() makes a new row per
    edit, so different records of the same form NAME can carry different
    schemas over a participant's history). Shape: list of sections
    {"header": str, "questions": {id: {"text": str, ...}}} (questions can
    also be a plain list - the internal survey builder and the Redcap-CSV
    import path both produce slightly different shapes, see
    Client/src/views/Survey/Editor and Viewer).
    answers: that same record's `record` field - a list of per-section
    answer-value lists, positionally aligned with `questions` (see
    Client/src/views/Survey/Viewer/index.js's submitSurvey()).

    Returns {ColumnLabel: value}. Column label is the question's own `text`
    (its real prompt, e.g. "Do you have difficulty walking?") - deliberately
    NOT forced through PascalCase like BRAVO-invented column names elsewhere
    (see docs/BIDS_MAPPING.md's naming convention) - this is human-authored
    clinical content, not a technical field name, and mangling a full
    sentence into PascalCase would just make it unreadable. Falls back to a
    positional "Section<i>__Question<j>" label if `text` (or the section
    itself) is missing - keeps every answer recoverable even against a
    malformed/unexpected form shape rather than silently dropping it."""
    row = {}
    for i, section in enumerate(questions or []):
        section = section if isinstance(section, dict) else {}
        section_questions = section.get("questions", [])
        items = list(section_questions.items()) if isinstance(section_questions, dict) else list(enumerate(section_questions))
        section_answers = answers[i] if isinstance(answers, list) and i < len(answers) else []
        for j, (_, question) in enumerate(items):
            question = question if isinstance(question, dict) else {}
            text = (question.get("text") or "").strip()
            label = text if text else f"Section{i}__Question{j}"
            value = section_answers[j] if isinstance(section_answers, list) and j < len(section_answers) else None
            row[label] = value if value not in (None, "") else "n/a"
    return row


def scale_form_dataframe(records, session_start, onset_bounds=None):
    """records: this form's ScaleRecord entries (see
    Gather.export_participant() - already filtered to one form NAME by the
    caller) - {"date", "answers", "questions"}. One row per submission.
    Different rows can legitimately have different columns (a form edited
    between two submissions) - pd.DataFrame unions them and fills the gaps
    with NaN, written out as "n/a" like everywhere else, rather than
    requiring every row to match one fixed schema.

    `Date` is the real absolute UTC completion date/time - `onset` is
    clamped to this session's window same as everything else
    (Gather.export_participant() can attribute a form to a session well
    before/after when it was actually completed - between two visits, or
    trailing after the participant's last known session - so unlike
    Annotations, where onset/duration alone place a row within its own
    day, `Date` here is not just a convenience, it's the only way to
    recover when a submission actually happened once its onset has been
    clamped away from its real value)."""
    rows = []
    for record in records:
        row = {"onset": _clamp_onset(record["date"] - session_start, onset_bounds), "duration": 0, "Date": _iso(record["date"])}
        row.update(_flatten_scale_answers(record.get("questions"), record.get("answers")))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("onset").reset_index(drop=True)


def therapy_adaptive_dataframe(therapies, session_start, onset_bounds=None):
    """One row per adaptive/sensing configuration entry attached to a
    therapy group (BrainSense adaptive DBS) - joined back to
    therapy_history via (onset, hemisphere, group_id). Most groups have no
    adaptive config at all (therapy["adaptive_settings"] is [None]); those
    are skipped rather than writing an all-n/a row. Named columns are the
    Medtronic adaptive-DBS fields the BRAVO UI already surfaces (see
    Client TherapyHistory view) - no catch-all JSON column for whatever's
    left over: if a real device turns up a field worth keeping that isn't
    here yet, add it as its own named column rather than falling back to a
    serialized blob."""
    rows = []
    for therapy in therapies:
        for i, entry in enumerate(therapy.get("adaptive_settings") or []):
            if entry is None:
                continue
            recording = entry.get("RecordingConfiguration") or {}
            stimulation = entry.get("StimulationConfiguration") or {}
            sensing_config = recording.get("Config") or {}
            adaptive_config = stimulation.get("Config") or {}
            sensing_setup = sensing_config.get("SensingSetup") or {}
            thresholds = sensing_config.get("Thresholds") or {}

            rows.append({
                "onset": _clamp_onset(therapy["date"] - session_start, onset_bounds),
                "Hemisphere": therapy["hemisphere"],
                "GroupId": therapy["group_id"],
                "ProgramIndex": i,
                "SensingType": recording.get("Type", "n/a"),
                "AdaptiveType": stimulation.get("Type", "n/a"),
                "SensingFrequency": sensing_setup.get("FrequencyInHertz", "n/a"),
                "AveragingDuration": sensing_setup.get("AveragingDurationInMilliSeconds", "n/a"),
                "AmplitudeThreshold__Low": _pair(thresholds.get("AmplitudeThreshold"), 0),
                "AmplitudeThreshold__High": _pair(thresholds.get("AmplitudeThreshold"), 1),
                "CaptureThreshold__Low": _pair(thresholds.get("CaptureAmplitudes"), 0),
                "CaptureThreshold__High": _pair(thresholds.get("CaptureAmplitudes"), 1),
                "LFPAtCaptureThreshold__Low": _pair(thresholds.get("MeasuredLFP"), 0),
                "LFPAtCaptureThreshold__High": _pair(thresholds.get("MeasuredLFP"), 1),
                "LFPThreshold__Low": _pair(thresholds.get("LFPThresholds"), 0),
                "LFPThreshold__High": _pair(thresholds.get("LFPThresholds"), 1),
                "ThresholdMode": adaptive_config.get("Mode", "n/a"),
                "DetectionBlanking": adaptive_config.get("DetectionBlankingDurationInMilliSeconds", "n/a"),
                "ThresholdOnsetLower": adaptive_config.get("LowerThresholdOnsetInMilliSeconds", "n/a"),
                "ThresholdOnsetUpper": adaptive_config.get("UpperThresholdOnsetInMilliSeconds", "n/a"),
                "RampUp": adaptive_config.get("RampUpTime", "n/a"),
                "RampDown": adaptive_config.get("RampDownTime", "n/a"),
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["onset", "GroupId", "ProgramIndex"]).reset_index(drop=True)


def impedance_dataframe(impedance_measurements, session_start, onset_bounds=None, device_id="n/a"):
    """impedance_measurements: list of {date, hemisphere, measurement_type
    ("Monopolar"/"Bipolar"), contact, contact_2 (Bipolar only),
    impedance_ohm, lead_model}. Monopolar and Bipolar share this one table
    (see write_electrodes() docstring for why) - distinguished by
    measurement_type, with contact_2 "n/a" for Monopolar rows."""
    if not impedance_measurements:
        return pd.DataFrame()
    rows = [{
        "onset": _clamp_onset(m["date"] - session_start, onset_bounds),
        "DeviceId": device_id,
        "SourceId": m.get("source_id", "n/a"),
        "Hemisphere": m["hemisphere"],
        "CustomName": m.get("custom_name") or "n/a",
        "MeasurementType": m["measurement_type"],
        "Contact": m["contact"],
        "Contact2": m.get("contact_2", "n/a"),
        "Impedance": m["impedance_ohm"],
        "LeadModel": m.get("lead_model") or "n/a",
    } for m in impedance_measurements]
    return pd.DataFrame(rows).sort_values(["onset", "Hemisphere", "MeasurementType", "Contact"]).reset_index(drop=True)


def patient_events_dataframe(events, session_start, onset_bounds=None, device_id="n/a"):
    """`Previous`/`New`: a real before/after pair for a TherapyModification
    event (e.g. "Off" -> "On"), kept as two columns rather than one joined
    "X -> Y" string - see Gather._event_dicts(). Named to match
    TherapyModification.get_info()'s own key spelling. A plain DBSEvent has
    no such pair - its single label goes in `Previous`, `New` is "n/a"."""
    rows = [{
        "onset": _clamp_onset(event["date"] - session_start, onset_bounds),
        "duration": 0,
        "DeviceId": device_id,
        "SourceId": event.get("source_id", "n/a"),
        "trial_type": event.get("type", "PatientEvent"),
        "Previous": event.get("previous", "n/a"),
        "New": event.get("new", "n/a"),
    } for event in events]
    return pd.DataFrame(rows).sort_values("onset").reset_index(drop=True)


def annotations_dataframe(annotations, session_start, onset_bounds=None, timezone="n/a"):
    """annotations: list of Server.models.Event.Annotation-shaped dicts
    {name, type, date, duration}. Manual/researcher annotations, kept
    separate from patient_events_dataframe (device-generated) even though
    the shape is identical - different provenance, different BIDS task
    name, so a consumer can tell them apart without inspecting trial_type.

    onset_bounds clamps only `onset` (this row's position within this
    session's file) - StartTimestamp/EndTimestamp stay the true absolute
    time regardless, since those are meant to be ground truth, not scoped
    to a session. StartTimestamp/EndTimestamp themselves stay UTC (no
    per-annotation timezone stored, see Gather.py's day-bucketing) -
    `timezone` is the session's own timezone (participant["timezone"], see
    convert_participant()), written alongside as a best-available
    approximation for recovering local time, not claimed as exact."""
    rows = [{
        "onset": _clamp_onset(annotation["date"] - session_start, onset_bounds),
        "duration": annotation.get("duration") or 0,
        "trial_type": annotation.get("type") or "Annotation",
        "value": annotation.get("name") or "n/a",
        # Convenience absolute start/end alongside onset/duration - those
        # alone require doing "sessions.tsv acq_time + onset (+ duration)"
        # math by hand to know the real start and end date/time, which is
        # easy to get wrong scanning a file by eye. UTC, not local - see
        # Timezone column for recovering local time.
        "StartTimestamp": _iso(annotation["date"]),
        "EndTimestamp": _iso(annotation["date"] + (annotation.get("duration") or 0)),
        "Timezone": timezone,
    } for annotation in annotations]
    return pd.DataFrame(rows).sort_values("onset").reset_index(drop=True)


def convert_participant(bids_root, subject, session, participant, electrodes=None,
                         streaming_recordings=None, survey_recordings=None,
                         chronic_activities=None, therapies=None, events=None,
                         impedance_measurements=None, device=None, annotations=None,
                         scale_records=None, electrode_info=None):
    """Orchestrator - writes one participant/session into `bids_root`.
    "Session" here is a calendar day: `session` should already be a
    ses-YYYYMMDD label and every argument should already be merged across
    every clinic-visit upload that landed on that local date (see
    Gather.gather_day()) - this function itself has no day-grouping logic,
    it just writes what it's given.

    participant: {"sex", "diagnosis", "dob" (unix s or None), "session_date"
        (unix s) - earliest upload of the day, used as the onset=0 anchor
        for every *_beh.tsv in this session; "session_end" (unix s,
        optional) - latest upload of the day; "prev_session_end" (unix s or
        None, optional) - latest upload of the immediately preceding
        session, None for a participant's first session. When both
        session_end/prev_session_end are given, every per-visit beh.tsv row
        (therapy, impedance, events, annotations - not ChronicLFP) has its
        onset clamped to [prev_session_end, session_end] relative to
        session_start - see _clamp_onset(). Omitting either leaves that
        side unbounded (e.g. gather_session()'s single-visit callers, which
        have no day-level start/end to give).}
    electrodes: list of BRAVO Electrode-shaped dicts
    streaming_recordings / survey_recordings: list of
        {"type": <BRAVO Recording type str>, "recording": {...}}
    chronic_activities: list of therapy-change-bounded segments (see
        modules.MedtronicPercept.ChronicBrainSense.extractChronicNeuralActivity)
        - written as real ieeg/ recordings (task-ChronicLFP), one per
        segment, via _chronic_recording(). Each carries its own "device"/
        "electrode_info" (see Gather.py) since a segment's recording device
        can differ from this session's main one.
    therapies: the `Therapies` list from decodeMedtronicJSON()
    events: the `EventRecordings` list from decodeMedtronicJSON()
    impedance_measurements: list of {date, hemisphere, measurement_type,
        contact, contact_2, impedance_ohm, lead_model} - see
        impedance_dataframe()
    device: {"model": str, "serial_hash": str} or None - see
        Gather._device_dict(), patched into every ieeg.json sidecar
    annotations: list of {name, type, date, duration} - see
        annotations_dataframe()
    scale_records: list of {name, date, answers, questions} - one entry per
        ScaleRecord submission (any form, any calendar day already merged
        into this session) - see Gather.export_participant() and
        scale_form_dataframe(). Grouped by `name` here into one
        task-<FormName>_beh.tsv per distinct form.

    Returns the list of BIDSPaths written for continuous recordings.
    """
    session_start = participant["session_date"]
    age = None
    if participant.get("dob"):
        age = round((session_start - participant["dob"]) / (365.25 * 24 * 3600), 1)

    session_end = participant.get("session_end")
    prev_session_end = participant.get("prev_session_end")
    onset_bounds = (
        None if prev_session_end is None else min(prev_session_end - session_start, 0),
        None if session_end is None else session_end - session_start,
    )
    # Same de-identified value written into every ieeg.json's DeviceSerialNumber
    # (see Gather._device_dict()) - reused here so a TherapyHistory/Impedance/
    # PatientEvents row can be tied back to the physical device it came from,
    # e.g. across a device replacement between visits.
    device_id = device["serial_hash"] if device else "n/a"
    timezone = participant.get("timezone") or "n/a"

    run_counters = {}
    written_paths = []
    for entry in (streaming_recordings or []) + (survey_recordings or []):
        spec = CONTINUOUS_TYPES.get(entry["type"])
        if spec is None:
            continue  # unmapped BRAVO type - skip rather than guess a destination
        key = (spec["task"], spec["acq"])
        run_counters[key] = run_counters.get(key, 0) + 1
        written_paths.append(write_ieeg_recording(
            bids_root, subject, session, spec["task"], entry["recording"],
            acquisition=spec["acq"], run=run_counters[key], ch_type=spec["ch_type"],
            device=device, metadata=entry.get("metadata"), electrode_info=electrode_info,
        ))

    for i, activity in enumerate(chronic_activities or []):
        written_paths.append(write_chronic_lfp_recording(
            bids_root, subject, session, activity, run=i + 1, device=activity.get("device"),
        ))

    # Runs after every ieeg-writing call above (streaming/survey AND
    # chronic) so it's the last (and only) electrodes.tsv on disk -
    # mne-bids's per-run placeholder is deleted inside write_ieeg_recording.
    if electrodes:
        write_electrodes(bids_root, subject, session, electrodes)

    if therapies:
        df = therapy_history_dataframe(therapies, session_start, onset_bounds, device_id)
        write_beh_tsv(bids_root, subject, session, "TherapyHistory", df, {
            "onset": {"Description": "Seconds relative to session start", "Units": "s"},
            "duration": {"Description": "Always 0 - therapy settings are point-in-time readouts, not intervals", "Units": "s"},
            "DeviceId": {"Description": "De-identified id (hashed serial number) of the implant this row's therapy settings came from - see the corresponding ieeg.json's DeviceSerialNumber"},
            "SourceId": {"Description": "SourceFile.uid of the specific upload this row came from - a session can merge several uploads (see Gather.gather_day()), so this can differ row to row"},
            "Hemisphere": {"Description": "Implant hemisphere this group/setting applies to"},
            "RecordType": {"Description": "Where this setting came from", "Levels": {"Past Therapy": "Historical device readout", "Pre-visit Therapy": "Group active before this session", "Post-visit Therapy": "Group active after this session"}},
            "GroupId": {"Description": "Device-internal therapy group identifier"},
            "GroupName": {"Description": "Clinician-assigned therapy group name, if set"},
            "GroupType": {"Description": "'Active' if this group was actually running on the device at the time of this visit, n/a otherwise (i.e. a stored alternate program, not the one in use)", "Levels": {"Active": "Group was running on the device at this visit"}},
            "Label": {"Description": "Clinician-assigned preference label from the BRAVO UI's therapy timeline (e.g. 'Pre-visit Preferred'/'Post-visit Preferred'), n/a if never set"},
            "StimulationType": {"Description": "Continuous vs Interleaving stimulation program for this group"},
            "ProgramIndex": {"Description": "0-based index within this group's stimulation programs - Interleaving groups have 2, Continuous/Standard groups have 1; n/a if the group has no stimulation programs at all"},
            "Contact": {"Description": "The contact this row describes - 'CAN' means the device case; n/a if the group has no stimulation programs at all"},
            "Role": {"Description": "Whether Contact is Active (cathode) or Return (anode) for this program - a program with multiple Active contacts (e.g. a segmented-ring combination) has one row per contact, all sharing the same ProgramIndex", "Levels": {"Active": "Cathode contact", "Return": "Return/anode contact"}},
            "Amplitude": {"Description": "Stimulation amplitude", "Units": "see AmplitudeUnit"},
            "AmplitudeUnit": {"Description": "Unit of the Amplitude column (mA, or % for fractionalized amplitude)"},
            "FractionalAmplitude": {"Description": "Per-contact current-steering amplitude for this Active (cathode) contact - n/a for Return contacts and for programs with no current-steering configured", "Units": "mA"},
            "Pulsewidth": {"Description": "Pulse width", "Units": "see PulsewidthUnit"},
            "PulsewidthUnit": {"Description": "Unit of the Pulsewidth column (typically uS)"},
            "Frequency": {"Description": "Stimulation frequency", "Units": "Hz"},
            "Cycling": {"Description": "1 if cycling (duty-cycled) stimulation is enabled, else 0"},
            "CyclingPeriod": {"Description": "Cycling on/off period, if cycling is enabled", "Units": "s"},
        })

        adaptive_df = therapy_adaptive_dataframe(therapies, session_start, onset_bounds)
        if not adaptive_df.empty:
            write_beh_tsv(bids_root, subject, session, "TherapyAdaptive", adaptive_df, {
                "onset": {"Description": "Seconds relative to session start - joins back to task-TherapyHistory_beh.tsv", "Units": "s"},
                "Hemisphere": {"Description": "Implant hemisphere this adaptive configuration applies to"},
                "GroupId": {"Description": "Device-internal therapy group identifier"},
                "ProgramIndex": {"Description": "0-based index within this group's adaptive configurations"},
                "SensingType": {"Description": "BrainSense sensing configuration type"},
                "AdaptiveType": {"Description": "Adaptive stimulation control type (e.g. Medtronic Adaptive)"},
                "SensingFrequency": {"Description": "LFP sensing frequency", "Units": "Hz"},
                "AveragingDuration": {"Description": "LFP power averaging window", "Units": "ms"},
                "AmplitudeThreshold__Low": {"Description": "Lower adaptive amplitude bound", "Units": "mA"},
                "AmplitudeThreshold__High": {"Description": "Upper adaptive amplitude bound", "Units": "mA"},
                "CaptureThreshold__Low": {"Description": "Amplitude at which the lower LFP threshold was captured during calibration", "Units": "mA"},
                "CaptureThreshold__High": {"Description": "Amplitude at which the upper LFP threshold was captured during calibration", "Units": "mA"},
                "LFPAtCaptureThreshold__Low": {"Description": "Measured LFP power at the lower capture threshold", "Units": "A.U."},
                "LFPAtCaptureThreshold__High": {"Description": "Measured LFP power at the upper capture threshold", "Units": "A.U."},
                "LFPThreshold__Low": {"Description": "Final lower LFP power threshold used for adaptation", "Units": "A.U."},
                "LFPThreshold__High": {"Description": "Final upper LFP power threshold used for adaptation", "Units": "A.U."},
                "ThresholdMode": {"Description": "Single vs dual LFP threshold adaptive mode"},
                "DetectionBlanking": {"Description": "Blanking duration after a stimulation change before LFP detection resumes", "Units": "ms"},
                "ThresholdOnsetLower": {"Description": "Onset duration below the lower threshold before amplitude ramps down", "Units": "ms"},
                "ThresholdOnsetUpper": {"Description": "Onset duration above the upper threshold before amplitude ramps up", "Units": "ms"},
                "RampUp": {"Description": "Amplitude ramp-up time", "Units": "ms"},
                "RampDown": {"Description": "Amplitude ramp-down time", "Units": "ms"},
            })

    if impedance_measurements:
        df = impedance_dataframe(impedance_measurements, session_start, onset_bounds, device_id)
        if not df.empty:
            write_beh_tsv(bids_root, subject, session, "Impedance", df, {
                "onset": {"Description": "Seconds relative to session start", "Units": "s"},
                "DeviceId": {"Description": "De-identified id (hashed serial number) of the implant this row's measurement came from - see the corresponding ieeg.json's DeviceSerialNumber"},
                "SourceId": {"Description": "SourceFile.uid of the specific upload this row came from - a session can merge several uploads (see Gather.gather_day()), so this can differ row to row"},
                "Hemisphere": {"Description": "Implant hemisphere measured"},
                "CustomName": {"Description": "Clinician-assigned label of the electrode matched by Hemisphere (Electrode.custom_name), e.g. 'Right STN LFP' - same value as electrodes.tsv's CustomName column for that lead, n/a if never set"},
                "MeasurementType": {"Description": "Monopolar (contact to device case) or Bipolar (contact to contact) impedance check", "Levels": {"Monopolar": "Single contact to device case", "Bipolar": "Contact-to-contact pair"}},
                "Contact": {"Description": "Contact measured (Monopolar), or first contact of the pair (Bipolar)"},
                "Contact2": {"Description": "Second contact of the pair - n/a for Monopolar rows"},
                "Impedance": {"Description": "Measured impedance", "Units": "Ohm"},
                "LeadModel": {"Description": "Implanted lead model this measurement was taken on, as reported by the device"},
            })

    if events:
        df = patient_events_dataframe(events, session_start, onset_bounds, device_id)
        write_beh_tsv(bids_root, subject, session, "PatientEvents", df, {
            "onset": {"Description": "Seconds relative to session start", "Units": "s"},
            "duration": {"Description": "Always 0 - patient/device events are instantaneous, not intervals", "Units": "s"},
            "DeviceId": {"Description": "De-identified id (hashed serial number) of the implant this row's event came from - see the corresponding ieeg.json's DeviceSerialNumber"},
            "SourceId": {"Description": "SourceFile.uid of the specific upload this row came from - a session can merge several uploads (see Gather.gather_day()), so this can differ row to row"},
            "trial_type": {"Description": "Event category"},
            "Previous": {"Description": "For a therapy modification, the state before the change (e.g. 'Off'); for a plain device/patient event, its single label"},
            "New": {"Description": "For a therapy modification, the state after the change (e.g. 'On'); n/a for a plain device/patient event with no before/after pair"},
        })

    if annotations:
        df = annotations_dataframe(annotations, session_start, onset_bounds, timezone)
        write_beh_tsv(bids_root, subject, session, "Annotations", df, {
            "onset": {"Description": "Seconds relative to session start", "Units": "s"},
            "duration": {"Description": "Annotation duration, 0 if instantaneous", "Units": "s"},
            "trial_type": {"Description": "Annotation type, as recorded by the annotating researcher/clinician"},
            "value": {"Description": "Annotation label/name"},
            "StartTimestamp": {"Description": "Absolute UTC start time (session start + onset, spelled out) - convenience column so the real date/time doesn't require doing that math by hand"},
            "EndTimestamp": {"Description": "Absolute UTC end time (StartTimestamp + duration) - equal to StartTimestamp for an instantaneous (duration=0) annotation"},
            "Timezone": {"Description": "BRAVO-stored UTC offset (e.g. 'UTC-04:00') for this session - StartTimestamp/EndTimestamp are UTC, this recovers local time. No per-annotation timezone is stored, so this is the session's timezone, not necessarily this exact annotation's"},
        })

    if scale_records:
        # One beh.tsv per distinct form NAME, not per exact ScaleForms row -
        # see Gather.export_participant()'s scale_records_by_day comment.
        # Two different form names could sanitize to the same BIDS label
        # (e.g. "MDS-UPDRS"/"MDS UPDRS" both -> "MDSUPDRS") - fall_back on a
        # numeric suffix rather than silently overwriting one form's file
        # with another's.
        by_name = {}
        for record in scale_records:
            by_name.setdefault(record["name"], []).append(record)
        used_labels = set()
        for name, records in by_name.items():
            # Every form shares one constant task-PatientSurvey - acq-<label>
            # (a real BIDS entity, same pattern as BrainSenseStream's
            # acq-Power/acq-TD) is what distinguishes forms, instead of
            # baking the form name into the task itself. BIDS task/acq
            # labels are alphanumeric only (verified against the real
            # validator - a literal "_"/"-" fails with
            # TASK_NAME_CONTAIN_ILLEGAL_CHARACTER; a made-up "form-<x>"
            # entity fails NOT_INCLUDED, "form" isn't a real BIDS entity).
            label = _bids_label(name, f"Form{len(used_labels)}")
            while label in used_labels:
                label = f"{label}{len(used_labels)}"
            used_labels.add(label)
            df = scale_form_dataframe(records, session_start, onset_bounds)
            write_beh_tsv(bids_root, subject, session, "PatientSurvey", df, {
                "onset": {"Description": "Seconds relative to session start", "Units": "s"},
                "duration": {"Description": "Always 0 - a form submission is a point-in-time readout, not an interval", "Units": "s"},
                "Date": {"Description": "Absolute UTC completion date/time - the form may be attributed to a session well before/after this (see docs/BIDS_MAPPING.md), so this is the only way to recover when it was actually completed"},
            }, acquisition=label)

    # Written last, deliberately - mne-bids's write_raw_bids() (called
    # above, inside write_ieeg_recording) unconditionally overwrites
    # dataset_description.json/participants.json with its own generic
    # template every time it runs (fake "[Unspecified1]"-style Authors,
    # irrelevant hand/weight/height columns neither BRAVO nor a DBS Percept
    # dataset has). Writing these first and letting the ieeg loop run
    # after them meant whichever session's export ran last silently left
    # mne-bids's placeholder junk as the final on-disk content instead of
    # ours. Doing it last here guarantees this call's (and therefore -
    # since every session ends the same way - the whole export's) content
    # wins.
    write_dataset_description(bids_root)
    write_readme(bids_root)
    upsert_participant(bids_root, subject, age, participant.get("sex"), participant.get("diagnosis"))

    return written_paths


def demo():
    """Self-check with synthetic data shaped exactly like
    Session.decodeMedtronicJSON()'s output - run directly:
        python -m modules.BIDSExport.Convert
    Does not require Django or a database."""
    import tempfile

    # _clamp_onset: unbounded when a side is None, clips to whichever side
    # is exceeded, leaves an in-range value alone.
    assert _clamp_onset(-500, (None, None)) == -500
    assert _clamp_onset(-500, (-100, 100)) == -100, "should clip to the lower bound"
    assert _clamp_onset(500, (-100, 100)) == 100, "should clip to the upper bound"
    assert _clamp_onset(50, (-100, 100)) == 50, "in-range value should pass through unchanged"
    assert _clamp_onset(-500, (None, 100)) == -500, "unbounded lower side should never clip"
    assert _clamp_onset(500, (-100, None)) == 500, "unbounded upper side should never clip"

    rng = np.random.default_rng(0)
    n_samples = 250 * 30  # 30s at 250Hz
    session_start = 1700000000.0

    participant = {
        "sex": "Male", "diagnosis": "Parkinson's Disease",
        "dob": session_start - 60 * 365.25 * 24 * 3600,
        "session_date": session_start,
    }
    impedance_measurements = [
        {"date": session_start, "hemisphere": "Right", "measurement_type": "Monopolar", "contact": "E00", "impedance_ohm": 1200, "lead_model": "LEAD_B33015"},
        {"date": session_start, "hemisphere": "Right", "measurement_type": "Monopolar", "contact": "E01", "impedance_ohm": 1150, "lead_model": "LEAD_B33015"},
        {"date": session_start, "hemisphere": "Right", "measurement_type": "Bipolar", "contact": "E00", "contact_2": "E01", "impedance_ohm": 2600, "lead_model": "LEAD_B33015"},
    ]
    electrodes = [{
        "target": "Right STN", "hemisphere": "Right",
        "channel_names": ["E00", "E01", "E02", "E03"],
        "channel_coordinates": [],
    }]
    # Electrode.get_info()-shaped (Target/CustomName, unmerged) - see
    # Gather.gather_session()'s electrode_info and DataAnalysis.queryAllRecordings().
    electrode_info = [{"Target": "Right STN", "CustomName": "Right STN LFP"}]
    streaming_recordings = [{
        "type": "MedtronicBrainSenseTimeDomain",
        "recording": {
            "SamplingRate": 250.0,
            "ChannelNames": ["ZERO_AND_THREE_RIGHT_RING"],
            "Data": rng.normal(0, 5, size=(n_samples, 1)),
            "Missing": np.zeros((n_samples, 1)),
            "StartTime": session_start, "Duration": n_samples / 250.0,
            "Type": "MedtronicBrainSenseTimeDomain", "Name": "n/a",
        },
        "metadata": {"ChannelNames": ["ZERO_AND_THREE_RIGHT_RING"], "Duration": n_samples / 250.0},
    }, {
        # Regression case: Power-domain values are arbitrary units in the
        # thousands (real device output goes well past 10000), not the
        # microvolt-scale TD signal above - see write_ieeg_recording's
        # docstring for why this class of value used to blow past EDF's
        # 8-char physical min/max header field and crash the export.
        "type": "MedtronicBrainSensePowerDomain",
        "recording": {
            "SamplingRate": 2.0,
            "ChannelNames": ["ZERO_TWO_RIGHT Power", "ZERO_TWO_RIGHT Stimulation"],
            "Data": np.column_stack([
                rng.uniform(200, 10831, size=60),
                rng.uniform(0, 2.0, size=60),
            ]),
            "StartTime": session_start,
        },
    }]
    device = {"model": "PerceptPC", "serial_hash": "deadbeef" * 8}
    chronic_time = (session_start + np.arange(0, 3600 * 24, 600.0)).tolist()
    chronic_activities = [{
        "TherapyStartTime": session_start,
        "Time": chronic_time,
        "Data": rng.normal(50, 10, size=(2, len(chronic_time))),  # channel-major, see _chronic_recording()
        "ChannelNames": ["RightHemisphere LFP", "RightHemisphere Amplitude"],
        "ChannelNamesFix": ["Right STN LFP", "Right STN Amplitude"],
        "device": device,
    }]
    therapies = [{
        "hemisphere": "Right", "type": "Post-visit Therapy", "date": session_start,
        "group_id": "GroupIdDef.GROUP_0", "group_name": "Group 1", "group_type": "Active", "stimulation_type": "Continuous",
        "stimulation_settings": [{
            "Contact": ["E01"], "ReturnContact": ["CAN"],
            "Amplitude": 2.5, "AmplitudeUnit": "mA", "FractionalAmplitudes": [2.5],
            "Pulsewidth": 60, "PulsewidthUnit": "uS",
            "Frequency": 130, "Cycling": 0, "CyclingPeriod": 0,
        }],
        "adaptive_settings": [None],
    }, {
        # Regression case: adaptive/sensing config is a nested Medtronic
        # dict (see Client TherapyHistory view) - therapy_adaptive_dataframe
        # must flatten the common fields without crashing on the ones it
        # doesn't recognize.
        "hemisphere": "Left", "type": "Post-visit Therapy", "date": session_start,
        "group_id": "GroupIdDef.GROUP_1", "group_name": "Adaptive", "stimulation_type": "BrainSense",
        "stimulation_settings": [{
            "Contact": ["E01", "E02"], "ReturnContact": ["CAN"],
            "Amplitude": 1.8, "AmplitudeUnit": "mA", "Pulsewidth": 60, "PulsewidthUnit": "uS",
            "Frequency": 125, "Cycling": 0, "CyclingPeriod": 0,
        }],
        "adaptive_settings": [{
            "RecordingConfiguration": {"Type": "LFP", "Config": {
                "SensingSetup": {"FrequencyInHertz": 22, "AveragingDurationInMilliSeconds": 450},
                "Thresholds": {"AmplitudeThreshold": [1.0, 2.5], "CaptureAmplitudes": [1.2, 2.3], "MeasuredLFP": [10, 40], "LFPThresholds": [15, 35]},
            }},
            "StimulationConfiguration": {"Type": "Medtronic Adaptive", "Config": {
                "Mode": "AdaptiveModeDef.DUAL_THRESHOLD_DIRECT", "DetectionBlankingDurationInMilliSeconds": 200,
                "LowerThresholdOnsetInMilliSeconds": 300, "UpperThresholdOnsetInMilliSeconds": 300,
                "RampUpTime": 1000, "RampDownTime": 1000,
            }},
        }],
    }]
    events = [
        {"previous": "PatientTriggeredEvent", "new": "n/a", "type": "PatientControllerEvent", "date": session_start + 120},
        {"previous": "Off", "new": "On", "type": "TherapyStatus", "date": session_start + 180},
    ]
    annotations = [{"name": "Beta burst review", "type": "ResearcherAnnotation", "date": session_start + 60, "duration": 5}]

    with tempfile.TemporaryDirectory() as bids_root:
        paths = convert_participant(
            bids_root, subject="TEST01", session="20231114", participant=participant,
            electrodes=electrodes, streaming_recordings=streaming_recordings,
            chronic_activities=chronic_activities, therapies=therapies, events=events,
            impedance_measurements=impedance_measurements, device=device, annotations=annotations,
            electrode_info=electrode_info,
        )
        written = sorted(os.listdir(bids_root))
        assert "dataset_description.json" in written, "dataset_description.json missing"
        assert "participants.tsv" in written, "participants.tsv missing"
        assert len(paths) == 3, f"expected 3 continuous recordings written (TD, Power, ChronicLFP), got {len(paths)}"
        for path in paths:
            assert os.path.exists(path.fpath), f"EDF file was not actually written to disk: {path.fpath}"

        power_path = next(p for p in paths if p.acquisition == "Power")
        raw = mne.io.read_raw_edf(power_path.fpath, preload=True, verbose=False)
        readback_max = raw.get_data()[0].max() * 1e6  # undo mne's internal Volts assumption
        assert 10000 < readback_max < 11000, (
            f"Power-domain value round-tripped wrong: expected ~10831, got {readback_max} "
            "- the EDF physical-range scale-cancellation bug is back"
        )

        power_channels_path = str(power_path.copy().update(suffix="channels", extension=".tsv").fpath)
        power_channels_df = pd.read_csv(power_channels_path, sep="\t")
        assert "ClinicalName" in power_channels_df.columns, "ClinicalName column missing from channels.tsv"
        assert set(power_channels_df["ClinicalName"]) == {"Right STN LFP E00-E02 Recording", "Right STN LFP E00-E02 Stimulation"}, (
            f"ClinicalName should mirror queryAllRecordings' hemisphere->CustomName substitution + Recording/Stimulation suffix, got {power_channels_df['ClinicalName'].tolist()!r}"
        )

        with open(os.path.join(bids_root, "sub-TEST01", "ses-20231114", "sub-TEST01_ses-20231114_scans.tsv")) as fid:
            scans_rows = fid.read().splitlines()[1:]
        assert scans_rows, "scans.tsv has no rows"
        assert all("n/a" not in row.split("\t")[1] for row in scans_rows), (
            f"scans.tsv acq_time is n/a - RawArray's meas_date was never set: {scans_rows}"
        )

        ieeg_dir = os.path.join(bids_root, "sub-TEST01", "ses-20231114", "ieeg")
        electrodes_files = [f for f in os.listdir(ieeg_dir) if f.endswith("_electrodes.tsv")]
        assert electrodes_files, "electrodes.tsv missing"
        with open(os.path.join(ieeg_dir, electrodes_files[0])) as fid:
            assert "impedance" not in fid.readline(), "electrodes.tsv should no longer carry an impedance column"

        chronic_path = next(p for p in paths if p.task == "ChronicLFP")
        assert os.path.exists(chronic_path.fpath), "ChronicLFP ieeg.edf missing"
        chronic_raw = mne.io.read_raw_edf(chronic_path.fpath, preload=False, verbose=False)
        assert chronic_raw.info["sfreq"] == 1.0, (
            f"ChronicLFP EDF should be declared at a nominal 1 Hz (real rate lives in ieeg.json's "
            f"SamplingFrequency/SamplingFrequencyMultiplier, not the EDF header), got {chronic_raw.info['sfreq']}"
        )
        with open(chronic_path.copy().update(suffix="ieeg", extension=".json").fpath) as fid:
            chronic_sidecar = json.load(fid)
        assert abs(chronic_sidecar["SamplingFrequency"] - 1 / 600) < 1e-9, (
            f"ieeg.json SamplingFrequency should report the true 1/600 Hz rate, got {chronic_sidecar['SamplingFrequency']}"
        )
        assert chronic_sidecar["SamplingFrequencyMultiplier"] == 600, (
            f"SamplingFrequencyMultiplier should be 600 (real seconds per EDF-declared 'second'), got {chronic_sidecar.get('SamplingFrequencyMultiplier')}"
        )
        chronic_channels_path = str(chronic_path.copy().update(suffix="channels", extension=".tsv").fpath)
        chronic_channels_df = pd.read_csv(chronic_channels_path, sep="\t")
        assert set(chronic_channels_df["name"]) == {"RH LFP", "RH Amp"}, (
            f"ChronicLFP channel names should be word-abbreviated (RightHemisphere->RH, Amplitude->Amp), not blindly truncated, got {chronic_channels_df['name'].tolist()!r}"
        )
        assert set(chronic_channels_df["OriginalName"]) == {"RightHemisphere LFP", "RightHemisphere Amplitude"}, (
            f"ChronicLFP channels.tsv OriginalName should hold the raw device spelling, got {chronic_channels_df['OriginalName'].tolist()!r}"
        )
        assert "ClinicalName" not in chronic_channels_df.columns, (
            "ChronicLFP channels.tsv should not have a ClinicalName column"
        )

        beh_dir = os.path.join(bids_root, "sub-TEST01", "ses-20231114", "beh")
        beh_files = os.listdir(beh_dir)
        assert not any("ChronicLFP" in f for f in beh_files), (
            "ChronicLFP should no longer be written to beh/ - it's a real ieeg/ recording now"
        )
        assert any("TherapyHistory" in f for f in beh_files), "therapy history beh.tsv missing"
        assert not any("TherapyStimulation" in f for f in beh_files), (
            "TherapyStimulation should no longer be written separately - merged into TherapyHistory"
        )
        history_path = next(os.path.join(beh_dir, f) for f in beh_files if "TherapyHistory" in f and f.endswith("_beh.tsv"))
        history_df = pd.read_csv(history_path, sep="\t", dtype=str, keep_default_na=False)
        active_group = history_df[history_df["GroupId"] == "GroupIdDef.GROUP_0"]
        assert (active_group["GroupType"] == "Active").all(), (
            f"GroupType should round-trip as 'Active' for every row of this group, got {active_group['GroupType'].tolist()!r}"
        )
        assert any("TherapyAdaptive" in f for f in beh_files), "therapy adaptive beh.tsv missing"
        assert any("Impedance" in f for f in beh_files), "impedance beh.tsv missing"
        assert any("PatientEvents" in f for f in beh_files), "patient events beh.tsv missing"

        impedance_path = next(os.path.join(beh_dir, f) for f in beh_files if "Impedance" in f and f.endswith("_beh.tsv"))
        impedance_df = pd.read_csv(impedance_path, sep="\t")
        assert set(impedance_df["MeasurementType"]) == {"Monopolar", "Bipolar"}, "expected both impedance measurement types"

        active_row = active_group[active_group["Role"] == "Active"].iloc[0]
        assert active_row["FractionalAmplitude"] == "2.5", (
            f"FractionalAmplitude should carry FractionalAmplitudes[0]=2.5, got {active_row['FractionalAmplitude']!r}"
        )
        return_row = active_group[active_group["Role"] == "Return"].iloc[0]
        assert return_row["FractionalAmplitude"] == "n/a", "Return contacts should never carry a fractional amplitude"

        assert any("Annotations" in f for f in beh_files), "annotations beh.tsv missing"
        annotations_path = next(os.path.join(beh_dir, f) for f in beh_files if "Annotations" in f and f.endswith("_beh.tsv"))
        annotations_df = pd.read_csv(annotations_path, sep="\t")
        assert annotations_df.iloc[0]["value"] == "Beta burst review", "annotation value round-tripped wrong"

        td_path = next(p for p in paths if p.acquisition == "TD")
        with open(td_path.copy().update(suffix="ieeg", extension=".json").fpath) as fid:
            ieeg_sidecar = json.load(fid)
        assert ieeg_sidecar.get("ManufacturersModelName") == "PerceptPC", "device model missing from ieeg.json sidecar"
        assert ieeg_sidecar.get("DeviceSerialNumber") == "deadbeef" * 8, "hashed device serial missing from ieeg.json sidecar"

        td_channels_df = pd.read_csv(td_path.copy().update(suffix="channels", extension=".tsv").fpath, sep="\t")
        assert ieeg_sidecar["metadata"]["ChannelNames"] == td_channels_df["name"].tolist(), (
            f"ieeg.json metadata.ChannelNames should be remapped to the shortened channels.tsv names, "
            f"got {ieeg_sidecar['metadata']['ChannelNames']!r} vs channels.tsv names {td_channels_df['name'].tolist()!r}"
        )
        assert ieeg_sidecar["metadata"]["ChannelNames"] != ["ZERO_AND_THREE_RIGHT_RING"], (
            "metadata.ChannelNames still holds the raw >16-char name - shortening wasn't applied"
        )

        # MedtronicChronicNeuralActivity derivative - synthetic single segment,
        # one LFP sample per hemisphere, shaped like ChronicBrainSense's
        # chronic-neural-activity computation (Data is (n_channels, n_samples)).
        chronic_activity = [{
            "Time": [session_start + 3600],
            "Data": np.array([[42.0], [1.9]]),
            "ChannelNamesFix": ["Right STN LFP", "Right STN Amplitude"],
            "TherapyString": ["Group 1, 130 Hz", "Group 1, 130 Hz"],
        }]
        write_chronic_neural_activity_derivative(bids_root, "TEST01", "20231114", chronic_activity, session_start)
        derivative_root = os.path.join(bids_root, "derivatives", "bravo-chronic-neural-activity")
        with open(os.path.join(derivative_root, "dataset_description.json")) as fid:
            derivative_description = json.load(fid)
        assert derivative_description["DatasetType"] == "derivative", "derivative dataset_description.json has wrong DatasetType"
        derivative_beh_dir = os.path.join(derivative_root, "sub-TEST01", "ses-20231114", "beh")
        derivative_files = os.listdir(derivative_beh_dir)
        assert any("ChronicNeuralActivity" in f for f in derivative_files), "chronic neural activity derivative beh.tsv missing"
        derivative_path = next(os.path.join(derivative_beh_dir, f) for f in derivative_files if "ChronicNeuralActivity" in f and f.endswith("_beh.tsv"))
        derivative_df = pd.read_csv(derivative_path, sep="\t")
        assert set(derivative_df["Value"]) == {42.0, 1.9}, "chronic neural activity derivative values round-tripped wrong"

        print(f"OK - demo dataset assembled at (now discarded) {bids_root}")
        print("Written files:")
        for root, _, files in os.walk(bids_root):
            for f in sorted(files):
                print(" ", os.path.relpath(os.path.join(root, f), bids_root))


if __name__ == "__main__":
    demo()
