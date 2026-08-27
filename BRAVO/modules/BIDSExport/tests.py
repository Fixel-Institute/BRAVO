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
BIDS Export - DB Adapter Integration Test
===================================================
Runs the real ingestion path (DataCurator.MedtronicPerceptJSONDecoder, same
code the upload API calls) against a real sample Percept export, then runs
modules.BIDSExport.Gather against the resulting DB rows. Uses Django's
isolated test database - never touches the real dev/production DB.

Run with:
    python manage.py test modules.BIDSExport.tests -v 2
"""

import json
import os
import shutil
import subprocess
import tempfile

import numpy as np
from django.test import TestCase

from Server import models
from modules import DataCurator
from modules.BIDSExport import Gather

SAMPLE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "sample_data", "Adaptive", "705508f1-26c4-4679-92a1-62afe65f1c47_dbe72748-52ab-4293-8453-33e5cb1d7bf5.json",
)


class GatherAndConvertTest(TestCase):
    def setUp(self):
        self.institute = models.Institute.create("BIDSExportTestInstitute")

    def _ingest_sample(self):
        with open(SAMPLE_FILE, "rb") as fid:
            raw_bytes = fid.read()

        metadata = {"UploadType": "DefaultType", "Institute": self.institute.pk, "Uploader": None}
        source_file = DataCurator.saveCacheFile(os.path.basename(SAMPLE_FILE), metadata, raw_bytes)
        source_file.metadata = {**source_file.metadata, **{
            "device_location": "", "automatic_deidentification": False,
            "infer_from_device": True, "automatic_concatenation": False,
        }}
        DataCurator.MedtronicPerceptJSONDecoder(source_file, person=None)

        person = source_file.owner
        self.assertIsNotNone(person, "ingestion did not attach a Participant to the SourceFile")
        self.assertTrue(models.Recording.find_all(source=source_file).exists(), "no Recording rows were created")
        return source_file

    def test_real_sample_end_to_end(self):
        source_file = self._ingest_sample()
        kwargs = Gather.gather_session(source_file)
        self.assertGreater(
            len(kwargs["streaming_recordings"]) + len(kwargs["survey_recordings"]),
            0, "expected at least one continuous recording gathered from the DB",
        )
        self.assertGreater(len(kwargs["therapies"]), 0, "expected at least one therapy group gathered from the DB")

        bids_root = tempfile.mkdtemp(prefix="bids_export_test_")
        try:
            written_paths = Gather.gather_and_convert(bids_root, source_file, subject="TESTSUBJ", session="01")
            self.assertGreater(len(written_paths), 0)
            for path in written_paths:
                self.assertTrue(os.path.exists(path.fpath), f"EDF not written: {path.fpath}")

            self.assertTrue(os.path.exists(os.path.join(bids_root, "dataset_description.json")))
            self.assertTrue(os.path.exists(os.path.join(bids_root, "participants.tsv")))

            ieeg_dir = os.path.join(bids_root, "sub-TESTSUBJ", "ses-01", "ieeg")
            self.assertTrue(any(f.endswith("_electrodes.tsv") for f in os.listdir(ieeg_dir)))

            beh_dir = os.path.join(bids_root, "sub-TESTSUBJ", "ses-01", "beh")
            self.assertTrue(os.path.isdir(beh_dir) and any("TherapyHistory" in f for f in os.listdir(beh_dir)))
        finally:
            shutil.rmtree(bids_root, ignore_errors=True)

    def test_export_participant_writes_to_dataserver_path(self):
        """Exercises Gather.export_participant() itself - the function the
        BIDSExport AsyncJob actually calls (see AnalysisPipeline.py) - not
        just gather_and_convert(). Points DATASERVER_PATH at a scratch temp
        dir for the duration of the test so it never touches the real
        BRAVOStorage/BIDS on disk."""
        source_file = self._ingest_sample()
        person = source_file.owner

        scratch_dataserver_path = tempfile.mkdtemp(prefix="bids_export_dataserver_")
        original = os.environ.get("DATASERVER_PATH")
        os.environ["DATASERVER_PATH"] = scratch_dataserver_path
        try:
            exported = Gather.export_participant(person.uid)
            self.assertEqual(exported, [source_file.uid])

            date_label, acq_time = Gather._local_date_and_time(source_file.date, source_file.metadata.get("Timezone"))
            bids_root = os.path.join(scratch_dataserver_path, "BIDS")
            ieeg_dir = os.path.join(bids_root, "sub-001", f"ses-{date_label}", "ieeg")
            self.assertTrue(os.path.isdir(ieeg_dir), f"expected session output at {ieeg_dir}")
            from modules.BIDSExport.Convert import IEEG_FORMAT
            data_ext = "_ieeg.edf" if IEEG_FORMAT == "EDF" else "_ieeg.eeg"
            self.assertTrue(any(f.endswith(data_ext) for f in os.listdir(ieeg_dir)))

            sessions_tsv = os.path.join(bids_root, "sub-001", "sub-001_sessions.tsv")
            with open(sessions_tsv) as fid:
                contents = fid.read()
            self.assertIn(f"ses-{date_label}", contents)
            self.assertIn(acq_time, contents)

            # re-exporting the same participant must land back on sub-001, not sub-002
            exported_again = Gather.export_participant(person.uid)
            self.assertEqual(exported_again, [source_file.uid])
            self.assertTrue(os.path.isdir(ieeg_dir), "re-export did not reuse the same subject label")
        finally:
            if original is not None:
                os.environ["DATASERVER_PATH"] = original
            else:
                del os.environ["DATASERVER_PATH"]
            shutil.rmtree(scratch_dataserver_path, ignore_errors=True)

    def test_bids_validator_accepts_real_export(self):
        """Ground-truth structural check: runs the actual `bids-validator`
        CLI (same tool BIDS-compliance is judged by) against a real export.
        Skips rather than fails if npx/bids-validator isn't installed - this
        is an environment check, not a code bug."""
        if shutil.which("npx") is None:
            self.skipTest("npx not available in this environment")

        source_file = self._ingest_sample()
        bids_root = tempfile.mkdtemp(prefix="bids_export_validator_")
        try:
            written_paths = Gather.gather_and_convert(bids_root, source_file, subject="VALIDATE01", session="01")
            self.assertGreater(len(written_paths), 0)

            result = subprocess.run(
                ["npx", "--yes", "bids-validator@1.15.0", bids_root, "--json"],
                capture_output=True, text=True, timeout=120,
            )
            try:
                report = json.loads(result.stdout)
            except json.JSONDecodeError:
                self.fail(f"bids-validator did not return JSON.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")

            errors = report.get("issues", {}).get("errors", [])
            if errors:
                summary = "\n".join(f"- {e.get('key')}: {e.get('reason')}" for e in errors)
                self.fail(f"bids-validator reported {len(errors)} error(s):\n{summary}")
        finally:
            shutil.rmtree(bids_root, ignore_errors=True)

    def test_round_trip_data_integrity(self):
        """Answers "was the mapping executed correctly?" directly, by
        reading the written BIDS files back and comparing them against the
        same in-memory values Gather pulled from the DB - not just checking
        that files exist.

        Compared against the tolerance appropriate for whichever format
        IEEG_FORMAT selects: BrainVision (32-bit float, no fixed digital
        range - the default) is effectively lossless for real-world
        magnitudes, checked with a tight relative tolerance for float32
        rounding; EDF (16-bit integer, fixed per-channel physical range)
        needs a wider tolerance sized to that channel's own quantization
        step. Everything else (electrodes.tsv, TherapyHistory beh.tsv) is
        plain TSV/JSON with no lossy encoding, so those are checked for
        exact equality regardless of IEEG_FORMAT."""
        import mne

        from modules.BIDSExport.Convert import CONTINUOUS_TYPES, IEEG_FORMAT, convert_participant

        source_file = self._ingest_sample()
        # Gather.gather_session() re-queries Recording rows with no explicit
        # ordering (no Meta.ordering on the model) - calling it twice (once
        # here, once inside gather_and_convert) is not guaranteed to return
        # the same order both times, which would misalign this zip. Gather
        # once and convert directly from that one snapshot instead.
        kwargs = Gather.gather_session(source_file)
        bids_root = tempfile.mkdtemp(prefix="bids_export_roundtrip_")
        try:
            written_paths = convert_participant(bids_root, subject="ROUNDTRIP01", session="01", **kwargs)

            mapped_entries = [
                entry for entry in (kwargs["streaming_recordings"] + kwargs["survey_recordings"])
                if entry["type"] in CONTINUOUS_TYPES
            ]
            self.assertEqual(len(mapped_entries), len(written_paths))

            for entry, path in zip(mapped_entries, written_paths):
                original = np.asarray(entry["recording"]["Data"], dtype=float)

                if IEEG_FORMAT == "EDF":
                    # EDF mode pre-scales by 1e-6 before writing (cancels
                    # mne/edfio's internal x1e6) - see write_ieeg_recording's
                    # docstring.
                    original = original * 1e-6
                    raw = mne.io.read_raw_edf(
                        path.copy().update(suffix="ieeg", extension=".edf").fpath, preload=True, verbose=False
                    )
                else:
                    raw = mne.io.read_raw_brainvision(
                        path.copy().update(suffix="ieeg", extension=".vhdr").fpath, preload=True, verbose=False
                    )
                readback = raw.get_data().T
                n_original = original.shape[0]

                if IEEG_FORMAT == "EDF":
                    # EDF pads the final data record up to a whole second by
                    # holding the last real sample constant - see the
                    # "EDF pads the tail" gotcha in docs/BIDS_MAPPING.md.
                    self.assertGreaterEqual(readback.shape[0], n_original, f"real samples missing in {path.fpath}")
                    self.assertLess(readback.shape[0] - n_original, entry["recording"]["SamplingRate"],
                                     f"more than one second of unexplained padding in {path.fpath}")
                    # EDF digitizes each channel to 16 bits over its own min/max range.
                    per_channel_step = (np.nanmax(original, axis=0) - np.nanmin(original, axis=0)) / 65535
                    atol = np.maximum(per_channel_step, 1e-12) * 2  # x2 safety margin for rounding
                    np.testing.assert_allclose(
                        readback[:n_original], original, atol=atol.max(), rtol=0,
                        err_msg=f"{entry['type']} values drifted past EDF quantization tolerance in {path.fpath}",
                    )
                    if readback.shape[0] > n_original:
                        padding = readback[n_original:]
                        np.testing.assert_allclose(
                            padding, np.broadcast_to(original[-1], padding.shape), atol=atol.max(), rtol=0,
                            err_msg=f"EDF tail padding in {path.fpath} isn't a constant hold of the last real sample",
                        )
                else:
                    # BrainVision has no EDF-style "data record" duration to
                    # pad to - verified directly (777-sample write
                    # round-trips to exactly 777) - so sample counts should
                    # match exactly. float32 storage, no fixed digital
                    # range - a tight relative tolerance is the right check,
                    # not a per-channel quantization-step allowance.
                    self.assertEqual(readback.shape[0], n_original, f"sample count mismatch in {path.fpath}")
                    np.testing.assert_allclose(
                        readback, original, rtol=1e-4, atol=1e-8,
                        err_msg=f"{entry['type']} values drifted past float32 rounding tolerance in {path.fpath}",
                    )

            electrodes_path = next(
                os.path.join(bids_root, "sub-ROUNDTRIP01", "ses-01", "ieeg", f)
                for f in os.listdir(os.path.join(bids_root, "sub-ROUNDTRIP01", "ses-01", "ieeg"))
                if f.endswith("_electrodes.tsv")
            )
            with open(electrodes_path) as fid:
                rows = [line.split("\t") for line in fid.read().splitlines()]
            header, rows = rows[0], rows[1:]
            self.assertNotIn("impedance", header, "electrodes.tsv should no longer carry an impedance column")
            written_names = [row[header.index("name")] for row in rows]
            expected_names = [name for lead in kwargs["electrodes"] for name in lead["channel_names"]]
            self.assertEqual(written_names, expected_names, "electrodes.tsv channel order/identity does not match source")

            if kwargs["impedance_measurements"]:
                beh_dir = os.path.join(bids_root, "sub-ROUNDTRIP01", "ses-01", "beh")
                impedance_path = next(
                    os.path.join(beh_dir, f) for f in os.listdir(beh_dir)
                    if "Impedance" in f and f.endswith("_beh.tsv")
                )
                with open(impedance_path) as fid:
                    written_rows = [line.split("\t") for line in fid.read().splitlines()]
                self.assertEqual(len(written_rows) - 1, len(kwargs["impedance_measurements"]),
                                  "Impedance beh.tsv row count does not match source impedance measurements")
                impedance_header = written_rows[0]
                written_types = {row[impedance_header.index("MeasurementType")] for row in written_rows[1:]}
                expected_types = {m["measurement_type"] for m in kwargs["impedance_measurements"]}
                self.assertEqual(written_types, expected_types,
                                  "Impedance beh.tsv measurement_type values do not match source")

            if kwargs["therapies"]:
                # TherapyHistory is now one row per (stimulation program,
                # contact) within each group - not one row per group - so
                # row count isn't checked against len(therapies) directly;
                # the set of GroupId values covered is what must match.
                beh_dir = os.path.join(bids_root, "sub-ROUNDTRIP01", "ses-01", "beh")
                self.assertFalse(
                    any("TherapyStimulation" in f for f in os.listdir(beh_dir)),
                    "TherapyStimulation should no longer be written separately - merged into TherapyHistory",
                )
                therapy_path = next(
                    os.path.join(beh_dir, f) for f in os.listdir(beh_dir)
                    if "TherapyHistory" in f and f.endswith("_beh.tsv")
                )
                with open(therapy_path) as fid:
                    written_rows = [line.split("\t") for line in fid.read().splitlines()]
                written_group_ids = {row[written_rows[0].index("GroupId")] for row in written_rows[1:]}
                expected_group_ids = {str(t["group_id"]) for t in kwargs["therapies"]}
                self.assertEqual(written_group_ids, expected_group_ids,
                                  "TherapyHistory GroupId values do not match source therapies")
        finally:
            shutil.rmtree(bids_root, ignore_errors=True)
