# BRAVO/Percept → BIDS Mapping Specification

Phase 1 of `cloud-first-bids`: convert BRAVO's Medtronic Percept data
(cataloged in `DATA_INVENTORY.md`) into a **validator-passing** BIDS dataset.
This is the ground layer everything else (Zarr/icechunk store, dask-backed
lazy loading, MNE adapters) gets built from later — get this wrong and
everything downstream inherits the mistake.

Target validator: [`bids-validator`](https://github.com/bids-standard/bids-validator)
(schema-based, current `deno`-based validator). Spec version target: BIDS
1.10+ (has the `DBS` iEEG channel type and `sampling_frequency` per-channel
column we rely on below — confirm against whatever validator version is
pinned in CI).

## Hard constraint that shapes everything else

**BIDS raw data types only accept `.edf`, `.vhdr`/`.eeg`/`.vmrk`
(BrainVision), or `.set`/`.fdt` (EEGLAB) for `ieeg`/`eeg` recordings.**
Zarr is not a recognized raw format. Consequence:

- `rawdata/` (the actual BIDS tree) holds continuous recordings as **EDF**
  (simplest, MNE can write it via `mne.export.export_raw`, universally
  supported by every downstream tool including the eventual MNE adapter).
- The Zarr/icechunk store is a **derivative**, built by re-reading the
  validated BIDS EDF files — `derivatives/zarr-store/`. This also means the
  BIDS conversion is useful completely independent of the Zarr work, which
  is good: it's a shippable, citable artifact on its own.
- `bids-validator` does not deep-validate `derivatives/` content against the
  raw-data schema — it mainly checks `dataset_description.json` has
  `"DatasetType": "derivative"` + `GeneratedBy`, and that filenames follow
  entity-suffix conventions. Zarr directories under `derivatives/` are safe.

## Dataset skeleton (as actually implemented - not the standalone-package
draft this section used to describe)

BIDS export lives inside BRAVO itself (`modules/BIDSExport/`), writing into
one shared dataset at `DATASERVER_PATH/BIDS`, accumulating every
participant. Verified against the real, current output:

```
BRAVOStorage/BIDS/
  dataset_description.json          # Convert.write_dataset_description() - unconditional overwrite
  README                             # Convert.write_readme() - unconditional overwrite
  participants.tsv / .json           # Convert.upsert_participant() - unconditional overwrite
  .bravo_subject_ids.json            # NOT a BIDS file (dotfile) - Gather._subject_label()'s UID->sub-NNN map
  sub-<NNN>/
    sub-<NNN>_sessions.tsv / .json   # Convert.write_sessions_tsv() - one row per ses-<YYYYMMDD>, written once at
                                      #   the end of Gather.export_participant()
    ses-<YYYYMMDD>/                  # one calendar day of clinic-visit uploads, merged - see Gather.gather_day()
      sub-<NNN>_ses-<YYYYMMDD>_scans.tsv   # mne-bids auto-generated, not written by our code
      ieeg/
        sub-<NNN>_ses-<YYYYMMDD>_space-Other_electrodes.tsv   # Convert.write_electrodes() - once per session
        ..._coordsystem.json
        ..._task-<T>[_acq-<A>]_run-<i>_ieeg.edf                # Convert.write_ieeg_recording(), one per continuous recording
        ..._ieeg.json
        ..._channels.tsv / .json
        ..._events.tsv / .json       # mne-bids auto, only on runs where a sample got masked (see gotchas below)
      beh/
        ..._task-TherapyHistory_beh.tsv / .json      # Convert.therapy_history_dataframe() - one row per (group, program, contact)
        ..._task-TherapyAdaptive_beh.tsv / .json     # Convert.therapy_adaptive_dataframe() - only if any group is adaptive
        ..._task-Impedance_beh.tsv / .json           # Convert.impedance_dataframe()
        ..._task-ChronicLFP_beh.tsv / .json          # Convert.chronic_lfp_dataframe()
        ..._task-PatientEvents_beh.tsv / .json       # Convert.patient_events_dataframe()
```

No `sourcedata/`/`code/` - those were part of the abandoned standalone-package
plan. The original Percept JSON stays exactly where BRAVO already keeps it
(`BRAVOStorage/raws/`), encrypted; this export never touches or copies it.

One `derivatives/` dataset exists - `bravo-chronic-neural-activity/`, a
convenience pre-joined export of the `MedtronicChronicNeuralActivity`
BRAVO-computed cache (see "Known gaps" below and `write_chronic_neural_activity_derivative()`
in `Convert.py`). It mirrors the same `sub-<NNN>/ses-<YYYYMMDD>/beh/` layout
as `rawdata/`, with its own `dataset_description.json`
(`"DatasetType": "derivative"`).

## Per-type mapping table (column-level, matches current `Convert.py`/`Gather.py`)

| BRAVO source | BIDS destination | Columns / fields | Notes |
|---|---|---|---|
| `MedtronicBrainSenseTimeDomain`, `MedtronicIndefiniteStream`, `MedtronicElectrodeIdentifier`, `MedtronicBrainSenseSurvey`, `MedtronicBaselineMontages`, `MedtronicStimulationMontages` | `ieeg/..._ieeg.edf`, channel type `dbs` | n/a (signal) | `RecordingType` in `_ieeg.json` is `"discontinuous"` whenever any sample was masked (device `Missing` OR the corrupted-value mask - see gotchas), else `"continuous"`. `StartTime` (-> `scans.tsv` `acq_time`) includes `Recording.adjusted_alignment`, the manual clock-drift correction set via the UI's Time Shift tool (`/api/setRecordingTimeShift`) - see `Gather.gather_session()`. The raw correction value is also written per-run into `scans.tsv`'s custom `AdjustedAlignment` column (see gotchas) so it stays traceable, not just its already-applied effect on `acq_time`. |
| `MedtronicBrainSensePowerDomain` | `ieeg/..._acq-Power_..._ieeg.edf`, channel type `dbs` (uniform, see gotchas) | n/a | Power channels get `units="n/a"` in `_channels.tsv` (arbitrary device units), Stimulation channels get `units="mA"` - set via `_channel_units_for()`, not the mne channel type. |
| Every continuous recording's `ChannelNames` | `_channels.tsv`: `name, type, units, low_cutoff, high_cutoff, OriginalName, ClinicalName` | `OriginalName` is BRAVO-specific (not spec) - the full Medtronic channel code before shortening to fit EDF's 16-char limit. `ClinicalName` (also not spec) is the clinician-facing name - `Electrode.custom_name` substituted for the hemisphere prefix, same reformatting `DataAnalysis.queryAllRecordings()` uses platform-wide (see gotchas), falls back to `OriginalName` if no electrode matched. |
| `Electrode` (per participant, per session) | `ieeg/..._space-Other_electrodes.tsv`: `name, x, y, z, size, manufacturer, group, hemisphere, type` | No `impedance` column (moved out, see below) - written once per session, not deduplicated across sessions even when geometry is identical, because BRAVO's own `target`/`group` label for the same physical lead has been observed to drift across a participant's own visits (e.g. "Right Other" -> "Right GPi" once a clinician refines it) - per-session preserves that history rather than picking one. |
| `MedtronicDeviceImpedance` (Monopolar + Bipolar) | `beh/..._task-Impedance_beh.tsv`: `onset, Hemisphere, MeasurementType, Contact, Contact__2, Impedance, LeadModel` | Both measurement types share one table, `MeasurementType` distinguishes them (`Contact__2` is `n/a` for Monopolar). Neither lives in `_electrodes.tsv` - BIDS's `impedance` column there is scalar-per-contact only (fits Monopolar) and electrodes.tsv is meant to stay static across sessions, not carry a value that changes every visit; Bipolar (a full contact-pair matrix) has no BIDS-native home at all either way. |
| `MedtronicChronicBrainSense` | `beh/..._task-ChronicLFP_beh.tsv`: `onset, <CustomName>_LFP, <CustomName>_Amplitude` | Irregular spacing, weeks of history - see "why beh" reasoning above. Per-hemisphere column names use the same hemisphere-prefix -> `Electrode.custom_name` substitution `DataAnalysis.queryAllRecordings()` already applies to this exact recording type (see gotchas) - falls back to the raw device spelling (`LeftHemisphere`/`RightHemisphere`) if no electrode's `Target` matches. |
| `ElectricalTherapy` + `ElectricalStimulation` (group + its stimulation programs, merged) | `beh/..._task-TherapyHistory_beh.tsv`: `onset, duration, Hemisphere, RecordType, GroupId, GroupName, GroupType, Label, StimulationType, ProgramIndex, Contact, Role, Amplitude, AmplitudeUnit, FractionalAmplitude, Pulsewidth, PulsewidthUnit, Frequency, Cycling, CyclingPeriod` | One row per (group, stimulation program, contact) - fully normalized, no packed/JSON cells (see gotchas). Group-level fields (`RecordType`/`GroupName`/`GroupType`/`Label`/`StimulationType`) repeat across every row for that group, same denormalization as a `channels.tsv` repeating acquisition params per channel. `RecordType` is `Past Therapy` / `Pre-visit Therapy` / `Post-visit Therapy`. `GroupType` is `Active` if this group was actually running on the device at the visit (vs. a stored alternate program), `n/a` otherwise. `Label` is the clinician-assigned preference tag from the UI's therapy timeline (`/api/assignTherapyLabel`), `n/a` if never set. `Role` is `Active`/`Return`; a group with no stimulation programs at all (shouldn't happen for real Percept data, but not model-guaranteed) still gets one row with `ProgramIndex`/`Contact`/`Role`/program fields `n/a`, so a group is never silently dropped. `FractionalAmplitude` (`ElectricalStimulation.amplitude_fraction`) is positionally parallel to `Contact` (cathodes) only - `n/a` for Return contacts and for programs with no current-steering configured. Unit-suffixed names (`frequency_hz`, `cycling_period_s`, ...) were dropped in favor of the plain field name - the unit already lives in the column's `Units` entry in the matching `.json` sidecar. This used to be two separate tables (TherapyHistory: one summary row per group; TherapyStimulation: one row per program/contact, joined by `(onset, hemisphere, group_id)`) - merged because `ElectricalStimulation.get_info()`'s `StimulationType` is literally `self.group.stimulation_type` (see `Server/models/Therapy.py`), the exact same group-level value TherapyHistory already carried, not a distinct per-program concept - splitting them bought nothing but an extra join. |
| `AdaptiveTherapy` (only groups with real adaptive config) | `beh/..._task-TherapyAdaptive_beh.tsv`: `onset, Hemisphere, GroupId, ProgramIndex, SensingType, AdaptiveType, SensingFrequency, AveragingDuration, AmplitudeThreshold__{Low,High}, CaptureThreshold__{Low,High}, LFPAtCaptureThreshold__{Low,High}, LFPThreshold__{Low,High}, ThresholdMode, DetectionBlanking, ThresholdOnset__{Lower,Upper}, Ramp__{Up,Down}` | File only written when at least one group in the session has real (non-None) adaptive settings. No raw-JSON residual column - if a real device ever surfaces a field outside this set, add it as a named column, don't fall back to a blob (see gotchas). Paired low/high (or lower/upper, up/down) columns use `__` to mark the base field's nested variant (e.g. `AmplitudeThreshold__Low`) instead of folding it into one run-on name. |
| Patient-triggered events + `TherapyModification` | `beh/..._task-PatientEvents_beh.tsv`: `onset, duration, trial_type, value` | Merged into one timeline - `trial_type` carries the BRAVO event/modification `type` (`PatientControllerEvent`, `TherapyStatus`, `AdaptiveTherapyStatus`, `RechargeStatus`, `TherapyChangeGroup`), so they're still distinguishable despite sharing a table. `onset`/`duration`/`trial_type`/`value` stay lowercase (unlike every other custom column in this export) because they're the literal BIDS `events.tsv`-family column names other BIDS tooling keys off - see "Column naming convention" below. |
| `Annotation` (manual/researcher annotations, incl. the UI's "add event" timeframe editor and chronic-event logging - Reports/ChronicTimeline, Reports/ChronicNeuralActivity, the Chronic Events CSV importer) | `beh/..._task-Annotations_beh.tsv`: `onset, duration, trial_type, value, StartTimestamp, EndTimestamp` | Bucketed by calendar day using each annotation's own `.date`, not `source` (which the UI flow never sets) - see `Gather.export_participant()` and "Known gaps". `StartTimestamp`/`EndTimestamp` spell `onset`/`onset+duration` out as absolute UTC date/times, so reading the real start/end doesn't need `sessions.tsv`'s `acq_time` added by hand. A day with `ChronicCustomEvent`-typed annotations but **no** device upload still gets a real BIDS session - just `beh/Annotations_beh.tsv`, no `ieeg/` - since that type is only ever logged from views not anchored to one recording (chronic/seizure logging routinely happens on non-visit days). `RecordingCustomEvent`-typed annotations never trigger this - that type is only ever added while viewing one specific existing recording, so one with no matching upload day is orphaned/stale data, not real chronic logging, and is skipped rather than manufacturing a session for it. |
| `ScaleRecord` (clinical rating-scale/questionnaire submissions) | One `beh/..._task-<FormName>_beh.tsv` per distinct `ScaleForms.name`: `onset, duration, <question text columns...>` | Grouped by form NAME, not by the exact `ScaleForms` row - `ScaleForms.update_version()` creates a new row (new uid) per edit, so the same form name can span several schema versions over a participant's history; each `ScaleRecord` still carries its own `source` (the exact version it was submitted against), so each row's answers are labeled using that record's own schema, not "the form" generically. Column labels are each question's own `text` (its real prompt, e.g. "Do you have difficulty walking?") - deliberately left as free text, not forced through PascalCase like BRAVO-invented columns (see naming convention below) - this is human-authored clinical content. Different rows can legitimately have different columns if the form was edited between submissions - `pd.DataFrame` unions them, gaps become `n/a`. Bucketed by `.date` like `Annotation` (no `SourceFile` link - `ScaleRecord.participant` is a direct FK) - a day with a scale submission but no device upload/annotation still gets a real BIDS session, same reasoning as `Annotation`'s `ChronicCustomEvent` case. `onset` clamped exactly like `TherapyHistory` (see `_clamp_onset`/`onset_bounds`). Form name sanitized to a BIDS-legal alphanumeric-only task label (`_bids_label()`) - a collision after sanitizing gets a numeric suffix rather than overwriting. |
| `Participant` | `participants.tsv`/`.json`: `participant_id, age, sex, diagnosis` | `age` computed from DOB at each session's date, DOB itself never written. MRN/name never included. Canonical column set enforced on every write (see gotchas - `mne-bids` otherwise pollutes this with irrelevant columns). |
| Session grouping (calendar day) | `sub-<NNN>_sessions.tsv`: `session_id, acq_time` | `session_id` is `ses-YYYYMMDD` (BIDS labels can't contain `-`/`:`, so the date can't be the literal ISO string); `acq_time` carries the real ISO8601 timestamp of the day's earliest upload. |
| `DBSDevice` | `_ieeg.json` sidecar: `Manufacturer="Medtronic"`, `ManufacturersModelName` (`DBSDevice.type`), `DeviceSerialNumber` (HMAC-SHA256 of `serial_number`, unconditionally re-hashed at export time with `DATASERVER_HASHKEY` regardless of whether ingestion already hashed it - see `Gather._device_dict()`) | Battery %/estimated EOL/implant date have no BIDS-recognized `_ieeg.json` field, so they're deliberately not written anywhere - see "Known gaps". Battery % additionally isn't persisted on `DBSDevice` at all (see gotchas). |

## Column naming convention

BIDS spec-defined names are never touched - `_channels.tsv`/`_electrodes.tsv`
column names (`name`, `type`, `units`, `low_cutoff`, `x`, `y`, `z`,
`hemisphere`, `impedance`, ...), `_ieeg.json`/`dataset_description.json`
sidecar keys (`SamplingFrequency`, `Manufacturer`, `BIDSVersion`, ...),
`participants.tsv` (`participant_id`, `age`, `sex`, `diagnosis`) and
`sessions.tsv`/`scans.tsv` (`session_id`, `acq_time`, `filename`) columns all
keep their exact spec spelling - the wider BIDS tooling ecosystem (pybids,
MNE-BIDS, fMRIPrep, ...) keys off these literally, and `_ieeg.json`'s schema
rejects unrecognized keys outright regardless of casing (see the reverted
channels.json→ieeg.json merge attempt).

Every column/key BRAVO itself invents (the `beh/` task tables, `OriginalName`
in `channels.tsv`) uses **PascalCase**, reusing the exact spelling already in
the source `get_info()` where one exists (`ElectricalTherapy.get_info()`'s
`GroupId`/`GroupType`/`Label`/`StimulationType`/`Pulsewidth`/`CyclingPeriod`,
...) rather than reinventing a name. Unit suffixes (`_ma`, `_hz`, `_ms`,
`_au`, `_s`) are dropped from the column name itself when the same unit is
already recorded in that column's `Units` entry in the matching
`beh.json`/`channels.json` sidecar - carrying it in both places was
redundant.

`__` is reserved for exactly one thing: flattening a model's JSON field into
one column per key, `name_of_json_field__key` - it does NOT mean "these two
columns are related." A pair of independently-fetched values that BRAVO
groups under one invented umbrella name (e.g. `TherapyAdaptive`'s
`LowerThresholdOnsetInMilliSeconds`/`UpperThresholdOnsetInMilliSeconds`,
`RampUpTime`/`RampDownTime` - two separate source keys, not one JSON field
being split) is a plain run-on PascalCase name instead:
`ThresholdOnsetLower`/`ThresholdOnsetUpper`, `RampUp`/`RampDown`,
`Contact2`. This used to also cover `AmplitudeThreshold`/`CaptureThreshold`/
`LFPAtCaptureThreshold`/`LFPThreshold` (`__Low`/`__High`) - those are a
different case again (a real 2-element array in the source,
`thresholds["AmplitudeThreshold"] == [Lower, Upper]`, not two independently-
named keys) and are still being decided (see gotchas -
`therapy_adaptive_dataframe()`'s open question on whether they should
instead be single array-valued columns).

The one deliberate exception: `onset`, `duration`, `trial_type`, `value` stay
lowercase in every `beh/` table that uses them, matching BIDS `events.tsv`'s
own column names exactly - these are the columns other BIDS-aware tooling
actually looks for by name, so keeping the spec casing here (unlike every
other custom column) is what preserves interoperability rather than breaking
it. Per-channel dynamic columns (`ChronicLFP`'s `<Hemisphere>_LFP`/
`<Hemisphere>_Amplitude`) also keep the device's own channel-name spelling
verbatim - those are data labels pulled from the recording, not a header
BRAVO is naming.

Verified against `bids-validator@1.15.0` with zero errors after converting
every custom column (see "Verification status" below) - casing of a
non-spec-recognized column/key is not itself validated, only its presence in
that file's `.json` description sidecar.

## Known gaps

- **`FractionalAmplitudes`** - resolved. `FractionalAmplitude` column
  in `TherapyHistory_beh.tsv`, positionally parallel to `Contact`
  (cathodes) only - `n/a` for Return contacts.
- **Device hardware facts** - partially resolved. `ManufacturersModelName`
  and a hashed `DeviceSerialNumber` are now written to every `_ieeg.json`
  sidecar (see `Gather._device_dict()`). Battery %/estimated EOL/implant
  date remain unwritten - deliberately, they have no BIDS-recognized
  `_ieeg.json` field to live in. Battery % additionally isn't persisted on
  `DBSDevice` at all (see `DATA_INVENTORY.md` and the `Gather.py` gotchas
  below) - would need a new model field + ingestion change, not just an
  export change.
- **`Annotation` model** - resolved. Exported to
  `beh/..._task-Annotations_beh.tsv`, bucketed by calendar day using each
  annotation's own `.date` (same single-fixed-timezone approximation as
  `MedtronicChronicNeuralActivity` below) rather than by `source` -
  `Annotation.source` is nullable and the live UI "add event" flow
  (`modules/Event.py::addAnnotation`, used by the timeframe-select event
  editors in `Reports/*` and the Chronic Events CSV importer) never sets
  it, so a `source`-based match would have silently dropped every
  annotation added through that UI. See `Gather.export_participant()`.
  Days with annotations but no device upload at all (routine for chronic
  seizure-event logging, which happens on non-visit days) also get a real
  session now - `beh/Annotations_beh.tsv` only, no `ieeg/` - instead of
  being dropped for having no matching upload day.
- **`dataset_description.json`'s `Authors` field is empty** (`NO_AUTHORS`
  validator warning) - deliberately left as-is for now, not a blocker.
  Needs a real name/institution before this dataset is
  finalized/published/DOI-registered.
- **`MedtronicChronicNeuralActivity`** - exported to
  `derivatives/bravo-chronic-neural-activity/` (see
  `write_chronic_neural_activity_derivative()`), one calendar day per
  session bucketed by each segment's `TherapyStartTime` using a single
  fixed timezone offset for the whole participant (no per-segment timezone
  exists to read - see the docstring on `Gather.export_participant()`).
  Still a redundant join of data already exported raw (ChronicLFP +
  TherapyHistory/TherapyAdaptive) - written anyway as a convenience
  pre-joined table, not because the raw ingredients are missing.
- **`TimeFrequencyAnalysis`/`NeuralActivitySnapshot` Recording types remain
  excluded on purpose** - unlike `MedtronicChronicNeuralActivity`, these
  are on-demand analysis caches keyed by an arbitrary user-chosen config
  (`Recording.find(original=recording, type=..., metadata=config)`), not a
  fixed per-session data type - there's no single stable "the" derivative
  per session to export, only whatever configs happen to be cached when
  export runs. Revisit if a specific analysis config becomes a first-class,
  reproducibly-generated artifact rather than an ad hoc UI cache.

## TD/Power merge decision (needs a call before writing the converter)

Two channels of BrainSense data share a clock but different sampling rates:
TD (raw LFP) and Power (band power + stim amplitude, slower cadence). Two
validator-legal options:

1. **Separate runs**, linked by identical `task`/`acq` base + a `recording-`
   entity distinguishing `recording-TD` vs `recording-Power`. Simpler to
   implement, simpler for MNE (`mne.io.read_raw_edf` per file, no mixed
   rates). Recommended default.
2. **Single EDF, mixed per-channel sample rates** using `_channels.tsv`'s
   optional `sampling_frequency` column (EDF's format natively supports
   different samples-per-record per signal). More "correct" alignment
   story, but `mne.export.export_raw` may not write mixed-rate EDF cleanly —
   would need direct `pyedflib` calls. Higher effort, marginal benefit for
   v1.

**Recommendation: option 1 for the first working converter.** Revisit if a
downstream analysis genuinely needs single-file TD+Power alignment.

**Implemented as: option 1**, using an `acq-TD`/`acq-Power` split (not a
`recording-` entity — `acquisition` was simpler to thread through mne-bids's
`BIDSPath` and validates the same way). See `modules/BIDSExport/Convert.py`.

## Implementation gotchas found while building this (read before touching `Convert.py`)

These aren't in the original design above because they only surfaced once
real Percept sample data was pushed through `mne`/`mne-bids`/`edfio` and
checked against the actual `bids-validator`. Keep them - reintroducing any
of these breaks something that isn't obvious from a code read alone.

- **Per-visit `beh.tsv` onsets are clamped to `[end of previous session, end
  of this session]`, not left unbounded.** A Percept upload's `Therapies`
  list includes device-reported historical readouts ("Past Therapy") going
  back over the device's rolling log - the same historical entry gets
  re-included in every subsequent visit's upload. Without a bound, a stale
  duplicate landing in visit N's session can carry a date from weeks before
  visit N-1, producing a wildly-negative `onset` that reaches back past the
  actual previous visit and makes consecutive sessions' date coverage look
  like it overlaps/skips around instead of advancing cleanly.
  `Gather.export_participant()` tracks each session's `session_end` (latest
  upload of that calendar day) and the previous session's `session_end`,
  passes both into `participant["session_end"]`/`participant["prev_session_end"]`,
  and `Convert.convert_participant()` turns them into `onset_bounds` -
  applied via `_clamp_onset()` in `therapy_history_dataframe`,
  `therapy_adaptive_dataframe`, `impedance_dataframe`,
  `patient_events_dataframe`, and `annotations_dataframe`. `onset=0` is
  still session start either way; only how far a row's `onset` can drift
  from it changes. A participant's very first session has no previous
  session to bound against, so its rows are left unclamped on the low end
  (`prev_session_end=None` -> unbounded). `ChronicLFP`/
  `ChronicNeuralActivity` are NOT clamped - those are continuous,
  real-timestamped device trends, not point-in-time snapshots duplicated
  per visit, so the same reasoning doesn't apply. `gather_session()`/
  `gather_and_convert()` (single-visit, no day-merging) don't have a
  day-level start/end to give, so they leave both bounds unset -
  unaffected, same as before this was added.

- **`Recording.adjusted_alignment` is recorded in `scans.tsv`, not
  `ieeg.json`.** It's a manual clock-drift correction set via the UI's "Time
  Shift" tool (`/api/setRecordingTimeShift`); `Gather.gather_session()` folds
  it into `StartTime` (so `acq_time` reflects the corrected clock, matching
  what `DataAnalysis.py` does everywhere else it reads a recording's start
  time) and also stashes the raw value in `recording["AdjustedAlignment"]`.
  Writing that value into the `ieeg.json` sidecar fails `bids-validator`
  (`JSON_SCHEMA_VALIDATION_ERROR` - the ieeg sidecar schema rejects
  unrecognized top-level keys), so `write_ieeg_recording()` instead patches
  it into `scans.tsv` as a custom `AdjustedAlignment` column (one row per
  run, same post-hoc-patch pattern as `channels.tsv`'s `OriginalName`), with
  a matching `scans.json` description. This keeps the correction itself
  traceable in the export, not just its already-applied effect on
  `acq_time`.

- **`ieeg.json` also carries a non-spec `"metadata"` key** - the source
  `Recording`'s DB-row-level `metadata` JSONField (e.g.
  `{"ChannelNames": [...], "Duration": ...}` - set at ingestion, see
  `DataCurator.py`), passed through by `Gather.gather_session()` and written
  verbatim by `write_ieeg_recording()` when present. **This fails strict
  `bids-validator` schema validation** the same way `AdjustedAlignment`
  originally did (`JSON_SCHEMA_VALIDATION_ERROR` - unrecognized top-level
  key) - kept anyway per explicit instruction, unlike `AdjustedAlignment`
  which got moved to `scans.tsv` instead. A dataset produced by this export
  will not pass `npx bids-validator` clean as long as this is in place.

- **`SEEGChannelCount`/`MiscChannelCount` are corrected for BrainSense
  Power-domain runs.** Power-domain channels are forced to mne's `"dbs"`
  channel type purely for the Volts pre-scale workaround (see
  `write_ieeg_recording()`'s docstring) - they aren't real SEEG contacts, so
  mne-bids's auto-computed `SEEGChannelCount` is wrong for that run.
  `write_ieeg_recording()` moves the count into `MiscChannelCount` after the
  fact for `ch_type == "power_stim"` runs only (TD/other `"dbs"`-typed runs
  are untouched) - the mne channel type itself is deliberately left as
  `"dbs"` so the Volts-scaling fix (and the physical min/max overflow crash
  it prevents) stays in effect.

- **`electrodes.tsv` carries `Electrode.custom_name` as its own `CustomName`
  column**, not just folded into the spec `group` column (`group` already
  prefers `custom_name` over the anatomical `target` when set - see
  `Gather._electrode_dicts()`). Same "raw value must stay traceable, not
  just its already-applied effect" reasoning as `AdjustedAlignment` above.
  A matching `electrodes.json` describes the custom column.

- **Channel/label naming reuses `DataAnalysis.queryAllRecordings()` as the
  platform-canonical reference, instead of reinventing it.** That function
  (used by the UI's data browser) calls
  `modules.MedtronicPercept.BrainSenseStream.reformatChannelName()` /
  the `MedtronicChronicBrainSense` branch's own hemisphere-prefix match to
  turn raw Medtronic channel codes into clinician-facing names (electrode
  `Target`'s hemisphere word swapped for `CustomName`, e.g.
  `"ZERO_AND_THREE_RIGHT_RING"` -> `"Right STN LFP E00-E03"`). `Convert.py`
  now calls the same functions rather than duplicating this logic:
  `write_ieeg_recording()`'s `ClinicalName` column (`channels.tsv`, guarded
  per-channel with a `try`/`except` falling back to the raw name -
  `Percept.reformatChannelName()` can raise on a shape it doesn't
  recognize, and `MedtronicElectrodeIdentifier`/`MedtronicStimulationMontages`
  aren't in `queryAllRecordings()`'s own `type__in` filter, so they're not
  vetted against real platform behavior the way the other types are) and
  `chronic_lfp_dataframe()`'s renamed columns (see above). Needs
  `Electrode.get_info()`-shaped electrode data (`Target`/`CustomName`, real
  unmerged values) - NOT the same shape as `Gather._electrode_dicts()`'s
  BIDS-specific `electrodes` list (whose `target` is already
  `custom_name`-or-`target` merged for `electrodes.tsv`) - so
  `Gather.gather_session()` builds a separate `electrode_info` list
  (`device.get_info()["Electrodes"]`) and threads it through
  `convert_participant()` alongside `electrodes`. Power-domain channels get
  an unconditional `" Stimulation"`/`" Recording"` suffix appended after
  reformatting, mirroring `queryAllRecordings()`'s
  `MedtronicBrainSensePowerDomain` branch exactly (note:
  `reformatStimulationChannel()` exists in `BrainSenseStream.py` but is
  never actually called anywhere in the codebase, including by
  `queryAllRecordings()` itself - `reformatChannelName()` is used for
  every branch, Power-domain included).

- **`DeviceId` column on `TherapyHistory`/`Impedance`/`PatientEvents`.**
  `convert_participant()` computes it once (`device["serial_hash"]`, or
  `"n/a"` if no device - the same de-identified value written into every
  session's `ieeg.json` `DeviceSerialNumber`) and passes it into
  `therapy_history_dataframe`/`impedance_dataframe`/`patient_events_dataframe`
  as a `device_id` kwarg, so a row can be tied back to the physical implant
  it came from (e.g. across a device replacement between visits) without
  cross-referencing the session's `ieeg.json` by hand. Deliberately NOT
  added to `TherapyAdaptive`/`Annotations`/`ChronicLFP` - not requested,
  and `TherapyAdaptive` already joins back to `TherapyHistory` via `onset`.

- **`sub-<NNN>_devices.json`** (subject root, optional - only written when
  at least one session has device info) - `Gather.export_participant()`
  collects `{session_id: {Model, DeviceSerialNumber}}` across every session
  for the participant and `Convert.write_subject_devices()` writes it, so
  which physical device recorded which session is visible in one place
  instead of opening every session's `ieeg.json`. Not a BIDS-recognized
  filename - would otherwise fail `bids-validator` with `NOT_INCLUDED`
  (unlike the `ieeg.json` `metadata`/`AdjustedAlignment` cases above, this
  one has a clean fix: `write_subject_devices()` self-registers
  `sub-*/sub-*_devices.json` in `.bidsignore`, idempotently, so it doesn't
  add a validator error). Only wired into `export_participant()`'s
  multi-session flow, same as `write_sessions_tsv()` - the single-visit
  `gather_and_convert()` path doesn't maintain subject-level aggregate
  files at all, so this doesn't either.

- **`channels.tsv`'s `name` column is the EDF-safe shortened label, not the
  original Medtronic channel code, and stays that way.** Verified against a
  real `>16`-char mismatch: `bids-validator@1.15.0` does NOT cross-check
  `channels.tsv`'s `name` against the actual `.edf` file's channel labels,
  but real BIDS tooling (`mne_bids.read_raw_bids()`, pybids, ...) does -
  they match metadata rows to the recording file's real channels by `name`.
  Writing the full original name there would silently desync the dataset
  from itself for any real downstream tool, even though the validator
  happens not to catch it. `OriginalName` already exists to carry the full
  name without breaking that link - use it, don't touch `name`.

- **`Timezone` columns wherever an absolute timestamp is written** -
  `sessions.tsv` (`acq_time`), `scans.tsv` (`acq_time`, alongside
  `AdjustedAlignment`/`SourceId`), and `Annotations` `beh.tsv`
  (`StartTimestamp`/`EndTimestamp`) - carry BRAVO's stored UTC-offset
  string (e.g. `"UTC-04:00"`, `SourceFile.metadata["Timezone"]`) so the
  participant's real local time is recoverable; `scans.tsv`/`sessions.tsv`
  `acq_time` and the `Annotations` timestamps are otherwise UTC-anchored
  (`set_meas_date`/`_iso()`) with no way to know which timezone that
  corresponds to. Per-recording for `scans.tsv` (`Gather.gather_session()`
  sets `data["Timezone"]` per upload, same as `SourceId` - a day-merged
  session could in principle span uploads with different stored
  timezones), per-session for `sessions.tsv`/`Annotations` (threaded
  through `participant["timezone"]`, since neither has a finer-grained
  per-row source). `Annotations`' `Timezone` is explicitly documented as an
  approximation - no per-annotation timezone is stored, so it's the
  session's timezone, not necessarily that exact annotation's.

- **EDF signal labels are hard-capped at 16 characters.** BRAVO's raw
  Medtronic channel codes (e.g. `ZERO_AND_THREE_LEFT_RING`) routinely
  exceed that. `Convert.py` abbreviates deterministically
  (`_shorten_channel_names`) and keeps the full name recoverable via an
  `OriginalName` column added to `channels.tsv` (with its own
  `channels.json` sidecar next to each run - a bare dataset-root
  `channels.json` is NOT recognized by `bids-validator@1.15.0` for
  inheritance, despite that being nominally BIDS-inheritance-legal).
- **`mne-bids` always writes a placeholder `electrodes.tsv`/`coordsystem.json`
  per acquisition** (all-`n/a` coordinates, no hemisphere/impedance) even
  with no montage set, whenever `datatype="ieeg"`. It's deleted immediately
  after each `write_raw_bids()` call so it doesn't coexist with our own
  authoritative `space-Other` one, which is written once at the end.
- **Mixing mne channel types (`dbs` + `misc`) within one multi-channel EDF
  export silently corrupts the scaling of some channels** - verified
  empirically, not a BIDS or mne-bids requirement. The BrainSense
  Power-domain recording (Power + Stimulation channels together) types
  every channel `dbs` uniformly for this reason; the real distinction
  (Power = arbitrary units, Stimulation = mA) is recorded honestly via a
  post-hoc `units` column patch in `channels.tsv`, not via the mne channel
  type. Do not "fix" this back to a semantically-nicer `dbs`/`misc` split
  without re-verifying round-trip values first.
- **`mne`/`edfio` always treat a `dbs`-typed channel's `RawArray` values as
  Volts and multiply by 1e6 when computing the EDF physical min/max -
  unconditionally, regardless of whether the data is actually voltage.**
  Found via a real production export (participant sub-001/ses-18): a
  Power-domain channel (arbitrary units, max ~10831) hit
  `write_raw_bids()` -> `edfio` with `ValueError: '10831000000' exceeds
  maximum field length: 11 > 8` - EDF's physical min/max header field is a
  fixed 8 ASCII characters, and 10831 x 1e6 doesn't fit. The earlier
  version of `write_ieeg_recording` only pre-divided data by 1e6 when a
  `voltage` flag was true, on the theory that "not really voltage" data
  (like Power) shouldn't get the uV->V scale. That reasoning was wrong:
  skipping the pre-divide doesn't avoid a scale factor, mne/edfio apply
  the x1e6 on export regardless of channel semantics, so skipping it just
  leaves that conversion uncancelled. The fix (and the only correct
  behavior for any `dbs`-typed channel written to EDF) is to
  unconditionally pre-divide by 1e6 before building the `RawArray`,
  purely to cancel mne/edfio's internal assumption back out - `voltage`
  was removed as a parameter to `write_ieeg_recording` and to
  `CONTINUOUS_TYPES` entirely, since it no longer controls anything.
  Regression-covered by `Convert.py`'s `demo()` (a Power-domain channel
  with a >10000 value) and would also be caught by
  `tests.py::test_bids_validator_accepts_real_export` /
  `test_round_trip_data_integrity` if a sample file with Power-domain data
  is used - the original sample file behind those two tests happens not to
  include a `MedtronicBrainSensePowerDomain` recording, which is why this
  shipped once already without either test catching it.
- `mne-bids` also requires **at least one `ieeg`-family channel type**
  (`dbs`/`seeg`/`ecog`/`eeg`) to accept `datatype="ieeg"` at all - an
  all-`misc` recording is rejected outright. This is the other reason the
  Power-domain recording can't just be `misc` throughout.
- Empty-string values (e.g. an unnamed therapy group) must be converted to
  literal `n/a` before `to_csv` - pandas's `na_rep` only catches real
  `NaN`/`None`, not empty strings, and the validator flags a blank TSV cell
  as an error (`TSV_EMPTY_CELL`), not just a warning.
- `coordsystem.json` with `iEEGCoordinateSystem: "Other"` requires an
  `iEEGCoordinateSystemDescription` field - the validator hard-errors
  without it.
- **EDF pads the tail of any recording whose duration isn't a whole number
  of seconds up to the next full second**, by holding the last real sample
  constant (not zero-filling). BRAVO recording durations are essentially
  never whole seconds, so this fires on almost every `ieeg` file - e.g. a
  153188-sample/250Hz recording (612.752s) reads back as 153250 samples
  (613.000s), with the trailing 62 samples all equal to sample 153187's
  value. Confirmed via `modules/BIDSExport/tests.py::test_round_trip_data_integrity`,
  which reads every written EDF back with `mne.io.read_raw_edf` and checks
  it against the exact source array head-to-head. This is standard EDF
  record-duration quantization, not data loss or corruption - every real
  acquired sample is preserved exactly (within EDF's 16-bit-per-record
  quantization step) - but a consumer of the exported EDF who isn't aware
  of it could mistake the padded tail for real recording. Not fixed because
  there's no way to avoid it while staying in EDF (the format requires
  whole data records); documenting it here is the fix.

**Verification status:** `Convert.py`'s `demo()` self-check (synthetic data,
covers the TD/Power split) and `modules/BIDSExport/tests.py` (real
Adaptive-cohort sample file: 17 continuous recordings - 12 BrainSenseSurvey
+ 5 IndefiniteStream runs, plus ChronicLFP/TherapyHistory/PatientEvents
`beh` files) both pass `npx bids-validator@1.15.0` with zero errors, and are
now checked automatically:
- `test_bids_validator_accepts_real_export` runs the real CLI validator
  against a real export and fails the test on any validator error.
- `test_round_trip_data_integrity` reads every written EDF/TSV back and
  compares it against the exact in-memory values `Gather` pulled from the
  DB - continuous data within one EDF quantization step (see the padding
  gotcha above), electrodes.tsv/TherapyHistory.tsv exactly.

Run both with `python manage.py test modules.BIDSExport.tests -v 2` before
trusting any further change to this file or to `Convert.py`/`Gather.py`.

`demo()` additionally covers, as of the FractionalAmplitudes/device-sidecar/
Annotations/chronic-neural-activity-derivative work: the `fractional_amplitude_ma`
column (both an Active row with a real value and a Return row asserting
`n/a`), `ManufacturersModelName`/`DeviceSerialNumber` in a real written
`_ieeg.json`, an `Annotations_beh.tsv` round-trip, and a
`write_chronic_neural_activity_derivative()` call asserting the derivative
`dataset_description.json` has `"DatasetType": "derivative"` and the
`ChronicNeuralActivity_beh.tsv` values round-trip. Also re-run
`npx bids-validator@1.15.0` against a real `demo()`-produced dataset after
touching any of this - confirmed zero errors (only the expected
`NO_AUTHORS` warning) at the time this was written. **Not re-verified**:
`Gather.py`'s DB-side additions (`_device_dict`, `_annotation_dicts`, the
`MedtronicChronicNeuralActivity` day-bucketing in `export_participant()`)
against a real database - `modules.BIDSExport.tests` needs a MySQL test
database this environment doesn't have (`python manage.py test` fails at
`CREATE DATABASE test_BRAVOServer` here); only `python manage.py check`
(import/config check, no DB) and `Convert.py`'s DB-independent `demo()`
were run. Run the real test suite in an environment with MySQL before
trusting the `Gather.py` changes in production.

## DB adapter (`Gather.py`) gotchas found while building it

`Gather.py` bridges Django ORM rows to the plain dicts `Convert.py` expects.
A BIDS session is one **calendar day** (participant-local timezone) of
clinic-visit uploads, not one `SourceFile` - a single visit routinely
produces several separate JSON uploads minutes apart (programming check,
survey, streaming recording, ...), and `Gather.gather_day()` merges all of
a day's `gather_session()` results into one session before `Convert.py`
ever sees it (`export_participant()` groups by local date first). This cut
one participant's session count from 105 (one per upload) to 21 (one per
real clinic day) in the first real multi-upload dataset tested against.
`gather_session()`/`gather_and_convert()` still operate on exactly one
`SourceFile` at a time and are kept for direct/test use. Verified end-to-end against a real
sample file run through the actual production ingestion path
(`DataCurator.MedtronicPerceptJSONDecoder`, the same code the upload API
calls) inside a Django `TestCase` (`modules/BIDSExport/tests.py`, isolated
test DB, never touches the real dev/production database) - re-run that test
plus a `bids-validator` pass before trusting further changes here too.

- **`Server.models.Therapy.get_info()` silently returns `None` for
  `type == "Past Therapy"`** (it only handles `"Pre-visit Therapy"`/
  `"Post-visit Therapy"`), even though `Past Therapy` rows have real,
  populated `ElectricalTherapy` data - using it directly would silently
  drop most of a participant's actual therapy history (every historical
  device readout). `_therapy_dicts()` queries `ElectricalTherapy` directly
  instead, bypassing that gate. This is a pre-existing bug in BRAVO's own
  model code, not something introduced here - worth fixing upstream at
  some point, but out of scope for this module.
- **`Electrode.hemisphere` is never actually populated** by Percept
  ingestion - `DataCurator.MedtronicPerceptJSONDecoder` only sets
  `type`/`custom_name`/`channel_count`/`channel_names` on electrode
  creation. It's blank for every real electrode this was tested against.
  `Electrode.target` always starts with `"Left"`/`"Right"` (e.g.
  `"Right STN"`, `"Right Other"` when the lead location is unrecognized -
  see `Session.py::extractPatientInformation`'s `TargetLocation`), so both
  `_electrode_dicts()` and `_therapy_dicts()` derive hemisphere from
  `target` when `.hemisphere` is empty, rather than emitting a blank BIDS
  cell. Same pre-existing-bug caveat as above.
- **Percept impedance data (`MedtronicDeviceImpedance` events) is
  positional, not name-keyed** - `{"Left": {"Monopolar": [8 floats]}, ...}`,
  index 0 = first contact. `_impedances()` zips it against each electrode's
  `channel_names` in order; if BRAVO ever reorders `channel_names` without
  also reordering the source `Monopolar` list this would silently
  mismatch - low risk since both derive from the same Medtronic contact
  ordering, but worth knowing if impedance values ever look shifted.
- **`SourceFile.type` is NOT a reliable marker for "this is a decoded
  Percept session"** - it's just whatever `DataType` the original upload
  request specified. The generic auto-detect-by-extension upload path sets
  it to `"DefaultType"` and leaves it there forever, even though the file
  gets decoded by the exact same `MedtronicPerceptJSONDecoder` as an
  explicit `"MedtronicJSON"`-typed upload. Caught by a real test asserting
  `export_participant()`'s return value, not by reading the code - it
  silently returned zero exported sessions for a normally-uploaded
  participant before the fix. `export_participant()` now filters by
  `pointer__endswith(".json")` instead, which is reliable post-ingestion
  (`DataCurator.py` always moves the file under `raws/<participant>/*.json`
  regardless of upload path). Note `modules/Database.py::listSourceFiles()`
  has this exact same `type == "MedtronicJSON"` assumption baked in - if
  that function's Source Files list ever looks incomplete, this is why;
  out of scope to fix here.
- **No JSON-encoded strings as TSV cell values, anywhere, no exceptions.**
  The first design semicolon-joined list-valued fields (`contact`/
  `return_contact`) into single cells and kept a `json.dumps(...)` "raw
  config" column as a catch-all for anything not flattened into a named
  column. Both were the same mistake in different disguises - a TSV cell
  should always be a plain scalar. Fixed: `TherapyHistory` is one row per
  (group, program, contact) with a `Role` (Active/Return) column instead of
  a joined list; the raw-JSON residual columns were deleted outright - if a
  real device ever surfaces an adaptive-config field worth keeping that
  isn't already a named column, add the column, don't reach for a blob.
- **`TherapyHistory`/`TherapyStimulation` used to be two separate `beh`
  tables** (one summary row per group; one row per program/contact, joined
  by `(onset, hemisphere, group_id)`) - merged into one `TherapyHistory`
  table because `ElectricalStimulation.get_info()`'s `StimulationType` key
  turned out to literally be `self.group.stimulation_type` (see
  `Server/models/Therapy.py`) - the same group-level value the old
  TherapyHistory table already carried under the same column name, not a
  distinct per-program concept. The two tables' only real relationship was
  that join key; keeping them apart cost a join for zero information gain.
- **`upsert_participant()` corrupted `participants.tsv` under concurrent
  exports - found via a real production dataset, not a test.** It's a
  read-modify-write (`pd.read_csv` the existing file, drop-and-reappend this
  subject's row, write it back) on the **one file shared by every
  participant in the dataset**, called once per session with no locking.
  Two exports racing on it (two different participants' `export_participant()`
  calls, or two runs for the same one) interleave their read/write cycles
  and tear the file - observed directly as a truncated row and a doubled-up
  row after a real multi-participant export. Once torn, every later
  `convert_participant()` call in *any* in-flight export's loop then throws
  `pandas.errors.ParserError` trying to re-read it, and since nothing
  catches that inside `export_participant()`, the whole export dies right
  there - silently truncating that participant's session count (one real
  case: 21 expected sessions, only 4 written before the corruption killed
  the loop). Fixed with the same `FileLock` pattern `Gather._subject_label()`
  already used for its own shared dotfile. `write_sessions_tsv()` doesn't
  have this problem - it's a full overwrite of a per-subject file from an
  already-complete in-memory list, not a shared cross-subject read-modify-write.
- **`write_dataset_description()`/`upsert_participant()` used to run
  *before* the per-run `write_raw_bids()` loop in `convert_participant()`,
  and both were "write once" (skip if the file already exists).**
  `mne-bids`'s own `write_raw_bids()` unconditionally overwrites
  `dataset_description.json`/`participants.json`/`README` with its own
  generic template every time it's called - fake `"[Unspecified1]"`-style
  `Authors`, irrelevant `hand`/`weight`/`height` participant columns. Since
  every session's `write_raw_bids()` calls ran *after* our clean write,
  whichever session's export ran last silently left `mne-bids`'s
  placeholder junk as the final on-disk content. Fixed two ways together
  (both needed - either alone still loses eventually): moved our writes to
  run *last* inside `convert_participant()`, and made them unconditional
  overwrites instead of write-once. `upsert_participant()` additionally
  reindexes to a fixed canonical column set on every call, so a junk
  column introduced by a past `mne-bids` clobber doesn't just keep getting
  carried forward once it's in the file.

## AsyncJob / API layer

Implemented, not just designed - see `modules/BIDSExport/Gather.py::export_participant()`,
the `AsyncJobScripts["BIDSExport"]` entry in `modules/AsyncJobScheduler/ProcessingScheduler.py`,
the `BIDSExport` branch in `modules/AnalysisPipelineScripts/AnalysisPipeline.py`,
and the `ExportBIDS` `RequestType` added to `Server/APIs/DataFilter.py`'s
existing `QueryFilterData` view (POST `/api/queryFilterData`,
`{"RequestType": "ExportBIDS", "ParticipantId": "..."}`) - added there
rather than a new URL/view file to match the codebase's existing
`RequestType`-dispatched-single-view convention (see `GetFilterOptions`/
`ApplyFilters`/`DownloadAllData` in the same file).

- Dispatch is async via the existing `ProcessingScheduler.ScheduleSlurmJob` /
  `AsyncJob` machinery (same pattern `BurstAnalysis` uses) - no new
  job-status endpoint needed, the existing generic `queryAsyncJobQueue`
  (`Server/APIs/AsyncJobScheduling.py`) already polls any `AsyncJob` by type.
- Output lands at `DATASERVER_PATH/BIDS/` as **one shared BIDS dataset**
  covering every exported participant (`sub-<participant_uid>/...`), not
  one dataset per participant - `dataset_description.json`/`participants.tsv`
  are written once and accumulate rows across exports (`Convert.py`'s
  `write_dataset_description`/`upsert_participant` are both idempotent for
  this reason).
- `export_participant(participant_uid)` exports **every** session
  (`SourceFile`) for that participant in one call, `ses-01` = earliest
  upload chronologically. There is no partial/single-session API surface
  yet - add one if a use case needs it.
- The frontend "Export as BIDS" button lives in
  `Client/src/views/Dashboard/FilterData/index.js`'s `ExpandableRow`, next
  to the existing "Open participant" action - a per-row `DatasetIcon`
  button that POSTs `ExportBIDS`, then polls `queryAsyncJobQueue`
  (`GetJobStatus`) every 3s until the job leaves `Pending`/`Running`,
  swapping the icon to a spinner → check/error. No new frontend dependency;
  reused the same `SessionController.query` + `setAlert` error-display
  pattern the rest of the file already uses.
- **Not tested**: the actual `ScheduleSlurmJob`/subprocess dispatch path
  end-to-end, or the frontend button in a real browser - a dispatched
  subprocess can't see the Django test runner's in-memory SQLite DB, no
  MySQL server exists in this environment to test the real dispatch path
  against, and there's no way to click through a browser here either. The
  direct function calls (`export_participant()`, `gather_and_convert()`)
  are covered by real tests and the frontend file passes the project's own
  ESLint config with zero new errors/warnings, but neither the job
  subprocess nor the button has been run for real. Verify both before
  relying on this in production.

## De-identification (required before any dataset described here leaves
this machine)

Raw Percept JSON contains `PatientFirstName`, `PatientLastName`, `PatientId`
(MRN), full `PatientDateOfBirth`, and device serial numbers — direct
identifiers. Before any `rawdata/`/`sourcedata/` is shared or published:

- `sub-<label>` assignment via a pseudonym lookup table kept **outside**
  version control (`code/` scripts reference it by path, the table itself
  is `.gitignore`d and never committed)
- Name / MRN / DOB — **confirmed already fake in the current fixture data**
  (upstream substitution, not something this converter needs to do). Still
  implement the DOB→age-at-session conversion in the sidecar/participants
  writer so the converter is correct for any future dataset where DOB is
  real, but this is not a blocker against the current fixtures.
- Device serial numbers → **real in current fixtures, not yet hashed.**
  Active blocker: hash before any output leaves this machine (not omit —
  hashing preserves the "same device across sessions" signal without the
  identifier).
- Session/event timestamps → **real in current fixtures, not date-shifted.**
  Active blocker: date-shifting policy (common practice for longitudinal
  PHI-bearing datasets) is **not yet designed**, required before any real
  participant data is converted, not merely a nice-to-have.

## Open items to resolve before writing `code/percept_to_bids.py`

1. Confirm Percept TD/Power/Chronic units against Medtronic's technical
   manual — do not silently assume µV.
2. Confirm `HardwareFilters`/`SoftwareFilters` values for the `_ieeg.json`
   sidecar from Medtronic documentation, not memory.
3. Decide the TD/Power merge strategy (recommendation above).
4. Decide date-shifting policy for de-identification.
5. Pin the exact `bids-validator` version this repo targets, and get one
   real converted dataset through it in CI before calling this "done."
