# Source Data Inventory — BRAVO / Medtronic Percept

This is a field-level catalog of every data type BRAVO extracts from a Medtronic
Percept PC/Tablet JSON export, plus the participant/device/electrode metadata
around it. It is the ground truth that `BIDS_MAPPING.md` maps onto BIDS. Everything
here was read directly out of the BRAVO source, not assumed — where a value (e.g.
an exact sampling rate or hardware filter) isn't present in code, it's marked
`CONFIRM` rather than guessed.

Source repo: `/home/chintan/Projects/BRAVO/BRAVO/` (Django app, nested one level
under the git root `/home/chintan/Projects/BRAVO/`).

- Parsers: `modules/MedtronicPercept/*.py` (`Session.py` is the entry point —
  `decodeMedtronicJSON()` fans out to the per-type extractors)
- DB models: `Server/models/*.py`

## Participant / Device / Electrode metadata

**`Participant`** (`Server/models/Participant.py`)
- `name`, `date_of_birth` (unix float), `sex` ("Male"/"Female"/"Unknown"),
  `mrn`, `diagnosis` (e.g. "Parkinson's Disease", "Essential Tremor"),
  `disease_start_time`, `institute`, `tags`

**`DBSDevice`** (`Server/models/Device.py`)
- `serial_number`, `type` (neurostimulator model), `implanted_location`
  ("Right IPG"/"Left IPG"), `implanted_date`, `estimated_eol`, `device_bloodline`
- `electrodes`: M2M to `Electrode`

**`Electrode`** (lead, one row per physical lead)
- `type` (e.g. "SenSight B33015", "Medtronic 3387/3389", "Other")
- `hemisphere`, `target` (e.g. "Left STN"), `custom_name`
- `channel_count` (4 or 8), `channel_names` (e.g.
  `["E00","E01-A","E01-B","E01-C","E02-A","E02-B","E02-C","E03"]` for SenSight
  8-contact directional leads, `["E00","E01","E02","E03"]` for 3387/3389)
- `channel_coordinates`: XYZ/trajectory, populated only if imaging registration
  (e.g. Lead-DBS) has run — **often empty**
- `implanted_date`

Session-level extraction (`Session.py::extractPatientInformation`) also pulls,
per programmer-session JSON: `SessionTimestamp`, `SessionEndTimestamp`,
`SessionTimezone` (UTC offset string), device `BatteryPercent`, `EOL` estimate.

## `Recording` model (generic container, `Server/models/Recording.py`)

Every neural/streaming data blob is a `Recording` row: `uid`, `name`, `type`
(the string tag below), `date`, `adjusted_alignment`, `pointer` (file path into
`DATASERVER_PATH`), `hashed` (HMAC), `metadata` (JSON), `source` (FK to the
originating `SourceFile`/JSON upload), `original` (FK for derived recordings).
The actual array data is NOT in SQL — it's blosc2-compressed, Fernet-encrypted
pickle on disk at `pointer`, loaded via `modules/Database.py::loadSourceFile`.

### `MedtronicBrainSenseTimeDomain` (raw continuous LFP)
Source: `StreamingTD` → `BrainSenseStream.saveBrainSenseStreams()`
- `SamplingRate` (Hz, per-recording, device-reported — CONFIRM typical value,
  commonly 250 Hz for Percept BrainSense TD but not hardcoded in BRAVO)
- `ChannelNames`: 1–2 entries, e.g. `"ZERO_TWO_LEFT"` style raw Medtronic
  channel codes (contact pair + hemisphere)
- `Data`: `(n_samples, n_channels)` float array, raw LFP in **not confirmed
  units** — Percept TD is documented by Medtronic as µV-scale; verify before
  publication
- `Missing`: same shape, 1 = missing/interpolated sample (device drops packets;
  this is what makes the stream "discontinuous" rather than gap-free)
- `StartTime` (unix), `Duration` (s)
- Adjacent streams may get merged across short (<30s) gaps by
  `FixBreaking` logic — merged data still carries the `Missing` mask for the
  filled gap

### `MedtronicBrainSensePowerDomain` (band power + stim amplitude, same session)
Source: `StreamingPower` → same function
- `ChannelNames`: 2 or 4 entries — `"<contact> Power"` and `"<contact>
  Stimulation"` pairs (mA), one pair per hemisphere in dual-channel sensing
- `Data`, `Missing`: same shape convention as TD
- `SamplingRate`: independent, lower than TD (device streams power bins at a
  slower cadence)
- `Descriptor.Therapy`: full `TherapySnapshot` dict active during the stream
  (group id, per-hemisphere stim/sensing config) — this is a rich nested
  object, see Therapy section below for shape

### `MedtronicChronicBrainSense` (chronic LFP trend, weeks of history)
Source: `LFPTrends` → `ChronicBrainSense.saveChronicBrainSense()`
- `SamplingRate = -1` — **explicitly variable/irregular**, one row per
  device-logged sample (roughly every several minutes while worn, with real
  gaps when off-body — not a fixed cadence)
- `Time`: array of unix timestamps (irregular spacing)
- `Data`: `(n_samples, 2)` = `[LFP, Amplitude]` per hemisphere
- `ChannelNames`: `["<Hemisphere> LFP", "<Hemisphere> Amplitude"]`
- This is the data type with no natural continuous-recording BIDS home — see
  mapping doc.

### `MedtronicIndefiniteStream` (long continuous raw stream, no power channel)
Source: `IndefiniteStream.saveIndefiniteStreams()` — same `SamplingRate` /
`ChannelNames` / `Data` / `Missing` / `StartTime` / `Duration` shape as TD,
grouped by `FirstPacketDateTime`.

### Survey / montage families (short screening recordings)
`BrainSenseSurvey.saveBrainSenseSurvey()`, used for four Recording `type`s:
`MedtronicElectrodeIdentifier`, `MedtronicBrainSenseSurvey`,
`MedtronicBaselineMontages`, `MedtronicStimulationMontages`
- `SamplingRate`, `ChannelNames` (one per contact pair surveyed),
  `Data`/`Missing` (short, seconds-to-minutes long per contact pair)
- `Descriptor.MedtronicPSD`: device-computed PSD per channel, when present —
  this is a **derived** quantity riding along with raw data

### `MedtronicDeviceImpedance`
- A `Recording` with no file on disk (`pointer=""`) - the impedance values
  live entirely in `.metadata`, per hemisphere: `{"Left": {...}, "Right":
  {...}}`.
- Each hemisphere dict has **two** measurement types, both positional
  (index 0 = first contact in that electrode's `channel_names`), not keyed
  by channel name:
  - `Monopolar`: flat list, one value (Ohm) per contact vs. the device case.
  - `Bipolar`: an `n_contacts × n_contacts` matrix, upper-triangular only
    (row `i`, col `j` for `j > i` = the reading between contact `i` and
    contact `j`; diagonal and lower triangle are structural zeros, not real
    0-Ohm readings).
  - `LeadModel`: string, e.g. `"LEAD_B33015"`.
- **Was silently dropping the entire Bipolar matrix** until this was caught
  mid-export-redesign - only Monopolar was ever read. Both are gathered now
  (`Gather._impedance_records()`).

### Patient-triggered events + LFP snapshots
`BrainSenseEvent.saveBrainSenseEvents()` (from `PatientEventLogs`)
- `name` (event label, patient-pressed), `date` (unix)
- Optional attached `data`: `LfpFrequencySnapshotEvents` — per-hemisphere
  `Frequency` (bin centers) + `FFTBinData` (power) captured at the moment of
  the event, plus `SenseID` (sensing config in effect)

### Therapy settings (`modules/MedtronicPercept/Therapy.py` →
`Server/models/Therapy.py`)
Three sources merged in `Session.py`: `StimulationGroups` ("Post-visit"),
`PreviousGroups` ("Pre-visit"), `TherapyHistory` ("Past Therapy", one entry
per historical device readout). Each yields one `ElectricalTherapy` per
hemisphere per group:
- `hemisphere`, `group_type` (Active/""), `group_name`, `group_id`
- `stimulation_type`: e.g. "Interleaving" (two independent programs) vs.
  standard single-program
- `stimulation_settings` (list, len 1 or 2 for interleaving) — each is an
  `ElectricalStimulation.get_info()`: `StimulationType`, `Electrode`,
  `Contact`/`ReturnContact` (resolved to channel names, e.g. `["E01-A",
  "E01-B"]`), `Amplitude` (mA), `AmplitudeUnit`, `FractionalAmplitudes`
  (per-contact current steering, not currently exported to BIDS - see
  "Known gaps" in BIDS_MAPPING.md), `Pulsewidth` (µs), `PulsewidthUnit`,
  `Frequency` (Hz), `Cycling`/`CyclingPeriod` (duty cycling, if enabled)
- `adaptive_settings` (list, usually `[None]` for non-adaptive groups) —
  each non-None entry is `AdaptiveTherapy.get_info()`, the **combined**
  `{"RecordingConfiguration": {"Type", "Config": {...}}, "StimulationConfiguration":
  {"Type", "Config": {...}}}` shape (kept together on purpose - they're one
  adaptive program, not two independent lists; `Gather._therapy_dicts()`
  used to split them, which was wrong). `Config` nests
  `SensingSetup.FrequencyInHertz`/`AveragingDurationInMilliSeconds` and
  `Thresholds.{AmplitudeThreshold,CaptureAmplitudes,MeasuredLFP,LFPThresholds}`
  under Recording, and `Mode`/`DetectionBlankingDurationInMilliSeconds`/
  `{Lower,Upper}ThresholdOnsetInMilliSeconds`/`Ramp{Up,Down}Time` under
  Stimulation - only present for Percept RC / adaptive-capable devices.

### Therapy change history (event log, not settings)
`Therapy.saveTherapyEvents()` → `TherapyModification` rows: `type` one of
`TherapyStatus`, `AdaptiveTherapyStatus`, `RechargeStatus`,
`TherapyChangeGroup`; each has `date`, `previous_state`, `new_state`.

## Recording types that exist in the DB but are NOT exported (verified against real data)

Queried every distinct `Recording.type` actually present across the 6
participants in `BRAVOStorage`. Three exist that `Gather.py` doesn't
recognize at all (silently skipped - not in `STREAMING_TYPES`/
`SURVEY_TYPES`/`CHRONIC_TYPES`, so they fall through the type-dispatch
if/elif with no else branch):

- **`MedtronicChronicNeuralActivity`** - inspected one directly: it's a
  list of per-therapy-period entries, each carrying the *full* nested
  therapy config (`TherapyNote`: complete `Electrode`/`Stimulation`/
  `Adaptive` objects, duplicating what `ElectricalTherapy` already has)
  plus exactly one `[LFP, Amplitude]` sample per hemisphere at that
  period's start. This is a BRAVO-computed join of data already exported
  separately and correctly (`ChronicLFP` + `TherapyHistory`/
  `TherapyStimulation`/`TherapyAdaptive`) - `DataCurator.py` even
  find-and-deletes/rebuilds it on every new upload, confirming it's a
  derived cache, not raw device output. **Correctly out of scope for a
  `raw`-type BIDS dataset**, not a gap - would belong in `derivatives/` if
  ever needed, and isn't, since the raw ingredients are already there.
- **`TimeFrequencyAnalysis`**, **`NeuralActivitySnapshot`** - not
  inspected in as much depth, but named and positioned (feeding
  `Client/src/views/Reports/NeuralActivitySnapshot`) the same way as the
  above: BRAVO-computed spectral/analysis results, not raw samples. Same
  reasoning applies - flag if that assumption turns out wrong for either.

`SourceFile.type` also has values beyond `"MedtronicJSON"`:
`"CachedResult"` and `"ChronicNeuralActivitySource"` - both have empty or
non-JSON `pointer` values, so both are already correctly excluded by
`export_participant()`'s `pointer.endswith(".json")` filter without any
special-casing needed. `ChronicNeuralActivitySource` is the synthetic
`SourceFile` the `MedtronicChronicNeuralActivity` derived Recording above
is attached to.

## Unexported feature: `Annotation` model

`Server/models/Event.py::Annotation` (`name`, `type`, `date`, `duration`,
`owner`, nullable `source`) - a manual/researcher annotation feature.
Exists in the schema, has an API, but only 2 rows exist across the entire
current DB and both are named "Test"/"Test2" with `source=None` - looks
like dev scratch data, not a real clinical annotation workflow in active
use. Not wired into the BIDS export. Worth revisiting if this feature
starts seeing real use - `source=None` would need a fallback rule for
which session/day it belongs to, since it isn't always tied to a specific
upload.

## Not neural / out of scope for v1
`ScaleForms`/`ScaleRecord` (REDCap-linked clinical scales), `GoogleHealth`/
`FitbitDevice`/`OuraRingDevice` (wearables, separate `modules/` per-vendor
parsers) exist in BRAVO but are not part of the Percept BIDS conversion —
flag if they need to come in later as a `beh`/physio extension.
