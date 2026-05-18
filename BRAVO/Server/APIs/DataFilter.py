import numpy as np
import pandas as pd
from io import BytesIO

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings
from django.db.models import Count

from Server import models
from .Participants import queryParticipantFunc
from modules.HelperFunctions import sanitize_input, get_or_none, json_compliant_handler
from modules import Database
from modules.MedtronicPercept import BrainSenseStream

# These types store raw Medtronic internal channel-definition strings (e.g.
# "RIGHT_RING_OR_SEGMENT_ELECTRODE_E00_PLUS_E01_PLUS") that need reformatting.
MEDTRONIC_RAW_CHANNEL_TYPES = {
    "MedtronicBrainSenseTimeDomain",
    "MedtronicBrainSenseSurvey",
    "MedtronicIndefiniteStream",
    "MedtronicBaselineMontages",
    "MedtronicStimulationMontages",
    "MedtronicElectrodeIdentifier",
}

ALLOWED_RECORDING_TYPES = {
    "MedtronicBrainSenseTimeDomain",
    "MedtronicBrainSensePowerDomain",
    "MedtronicChronicBrainSense",
    "MedtronicBrainSenseSurvey",
    "MedtronicIndefiniteStream",
    "MedtronicBaselineMontages",
    "MedtronicElectrodeIdentifier",
    "MedtronicDeviceImpedance",
    "MedtronicStimulationMontages",
    "PatientControllerEvent",
    "DelsysMDAT",
    "AOMPX",
    "MATFile",
}

# These are always paired with other recordings and add no value as filter options.
HIDDEN_FILTER_TYPES = {"MedtronicBrainSensePowerDomain", "PatientControllerEvent"}
FILTERABLE_RECORDING_TYPES = ALLOWED_RECORDING_TYPES - HIDDEN_FILTER_TYPES

TIME_DOMAIN_TYPES = {
    "MedtronicBrainSenseTimeDomain",
    "MedtronicBrainSensePowerDomain",
    "MedtronicIndefiniteStream",
    "MedtronicBrainSenseSurvey",
    "MedtronicBaselineMontages",
    "MedtronicStimulationMontages",
    "MedtronicElectrodeIdentifier",
    "DelsysMDAT",
    "AOMPX",
    "MATFile",
}


def _get_device_electrodes(source):
    device_uid = source.metadata.get("Device")
    if not device_uid:
        return []
    device = models.DBSDevice.find(uid=device_uid)
    if not device:
        return []
    return [e.get_info() for e in device.electrodes.all()]


def _reformat_channel_names(raw_names, source):
    electrodes = _get_device_electrodes(source)
    if not electrodes:
        return raw_names
    return [BrainSenseStream.reformatChannelName(n, electrodes) for n in raw_names]


def _attach_power_domain(df, td_recording, time_col):
    """Interpolate the paired PowerDomain (amplitude) columns into a TimeDomain DataFrame."""
    for pd_rec in models.Recording.objects.filter(
        source=td_recording.source, type="MedtronicBrainSensePowerDomain"
    ):
        if BrainSenseStream.calculateOverlap(td_recording, pd_rec) > 0.7:
            try:
                pd_data = Database.loadSourceFile(pd_rec.pointer, pd_rec.hashed)
                n_pd = len(pd_data["Data"])
                pd_times = pd_data.get("StartTime", 0) + np.arange(n_pd) / pd_data["SamplingRate"]
                for i, col in enumerate(pd_data["ChannelNames"]):
                    vals = np.interp(time_col, pd_times, pd_data["Data"][:, i])
                    vals[time_col < pd_times[0]] = np.nan
                    vals[time_col > pd_times[-1]] = np.nan
                    df[col] = vals
            except Exception:
                pass
            break
    return df


def _attach_chronic_events(df, recording):
    """Add an Event column to a ChronicLFP DataFrame from PatientControllerEvent recordings."""
    participant = recording.source.owner
    times_arr = df["Time"].values
    if len(times_arr) == 0:
        return df

    chronic_start, chronic_end = times_arr[0], times_arr[-1]
    events = []
    for ev_rec in models.Recording.objects.filter(
        source__owner=participant, type="PatientControllerEvent"
    ):
        try:
            ev_data = Database.loadSourceFile(ev_rec.pointer, ev_rec.hashed)
            for ev in ev_data.get("Events", []):
                t = ev.get("Time", 0)
                if chronic_start <= t <= chronic_end:
                    events.append((t, ev.get("Name", "")))
        except Exception:
            continue

    if not events:
        return df

    events_col = np.full(len(times_arr), "", dtype=object)
    for ev_time, ev_name in events:
        idx = np.searchsorted(times_arr, ev_time)
        idx = min(idx, len(times_arr) - 1)
        if abs(times_arr[idx] - ev_time) <= 30:
            events_col[idx] = ev_name
    df["Event"] = events_col
    return df


def _recording_to_dataframe(recording, use_raw_names=False):
    Data = Database.loadSourceFile(recording.pointer, recording.hashed)

    if recording.type in TIME_DOMAIN_TYPES:
        n = len(Data["Data"])
        sr = Data["SamplingRate"]
        t0 = Data.get("StartTime", 0)
        time_col = t0 + np.arange(n) / sr
        if not use_raw_names and recording.type in MEDTRONIC_RAW_CHANNEL_TYPES:
            channel_names = _reformat_channel_names(Data["ChannelNames"], recording.source)
        else:
            channel_names = Data["ChannelNames"]
        df = pd.DataFrame(Data["Data"], columns=channel_names)
        df.insert(0, "Time", time_col)
        if recording.type == "MedtronicBrainSenseTimeDomain":
            df = _attach_power_domain(df, recording, time_col)

    elif recording.type == "MedtronicChronicBrainSense":
        time_col = np.array(Data["Time"])
        channel_names = (
            Data["ChannelNames"] if use_raw_names
            else _reformat_channel_names(Data["ChannelNames"], recording.source)
        )
        df = pd.DataFrame(Data["Data"], columns=channel_names)
        df.insert(0, "Time", time_col)
        df = _attach_chronic_events(df, recording)

    elif recording.type == "PatientControllerEvent":
        rows = [{"Timestamp": ev.get("Time", 0), "EventName": ev.get("Name", "")}
                for ev in Data.get("Events", [])]
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Timestamp", "EventName"])
        if Data.get("PSD"):
            freq_step = 250 / 256
            psd_data = np.array(Data["PSD"])
            if psd_data.ndim == 2:
                for i in range(psd_data.shape[1]):
                    df[f"PSD_{i * freq_step:.2f}Hz"] = psd_data[:, i]

    elif recording.type == "MedtronicDeviceImpedance":
        df = pd.DataFrame(Data.get("Impedance", []))

    else:
        df = pd.DataFrame()

    return df


def _recording_to_csv_response(recording, participant_uid, use_raw_names=False):
    df = _recording_to_dataframe(recording, use_raw_names=use_raw_names)
    suffix = "_raw" if use_raw_names else ""
    filename = f"{participant_uid}_{recording.uid}{suffix}.csv"
    buf = BytesIO()
    df.to_csv(buf, index=False)
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


class QueryFilterData(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ParticipantId = request.query_params.get("ParticipantId")
        RecordingId = request.query_params.get("RecordingId")
        if not ParticipantId or not RecordingId:
            return Response(status=400, data={"message": "Malformed Input"})

        study_uid = request.user.configuration.get("ActiveStudy")
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, study_uid=study_uid)
        if not Permissions:
            return Response(status=403)

        recording = models.Recording.find(uid=RecordingId)
        if not recording:
            return Response(status=404, data={"message": "Recording not found"})

        use_raw = request.query_params.get("ChannelFormat", "clean") == "raw"
        return _recording_to_csv_response(recording, ParticipantId, use_raw_names=use_raw)

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})

        # ── GetFilterOptions ──────────────────────────────────────────────────
        if request.data["RequestType"] == "GetFilterOptions":
            ParticipantInfos = queryParticipantFunc(request.user)
            participant_uids = [p["Id"] for p in ParticipantInfos]
            qs = models.Participant.objects.filter(uid__in=participant_uids)
            source_files = models.SourceFile.objects.filter(owner__in=qs)

            diagnoses = list(
                qs.exclude(diagnosis="")
                  .exclude(diagnosis="Unknown")
                  .values_list("diagnosis", flat=True)
                  .distinct()
            )
            tags = list(
                models.Tag.objects.filter(has_tag__in=qs)
                         .values_list("name", flat=True)
                         .distinct()
            )
            tag_counts = dict(
                qs.filter(tags__isnull=False)
                  .values("tags__name")
                  .annotate(n=Count("uid", distinct=True))
                  .values_list("tags__name", "n")
            )
            recording_types = list(
                models.Recording.objects.filter(source__in=source_files)
                                .filter(type__in=FILTERABLE_RECORDING_TYPES)
                                .values_list("type", flat=True)
                                .distinct()
            )
            device_types = list(
                models.DBSDevice.objects.filter(owner__in=qs)
                                .exclude(type="")
                                .values_list("type", flat=True)
                                .distinct()
            )
            targets = list(
                models.Electrode.objects.filter(owner__in=qs)
                                .exclude(target="")
                                .values_list("target", flat=True)
                                .distinct()
            )

            return Response(status=200, data={
                "Diagnoses": diagnoses,
                "Tags": tags,
                "TagCounts": tag_counts,
                "RecordingTypes": recording_types,
                "Devices": device_types,
                "Targets": targets,
            })

        # ── ApplyFilters ──────────────────────────────────────────────────────
        if request.data["RequestType"] == "ApplyFilters":
            if not get_or_none(sanitize_input)(request.data, required_keys=["Filters"]):
                return Response(status=400, data={"message": "Malformed Input"})

            filters = request.data["Filters"]
            ParticipantInfos = queryParticipantFunc(request.user)
            participant_uids = [p["Id"] for p in ParticipantInfos]
            participant_info_map = {p["Id"]: p for p in ParticipantInfos}

            qs = models.Participant.objects.filter(uid__in=participant_uids)

            if filters.get("Diagnosis"):
                qs = qs.filter(diagnosis__in=filters["Diagnosis"])

            if filters.get("Tags"):
                qs = qs.filter(tags__name__in=filters["Tags"]).distinct()

            if filters.get("Targets"):
                qs = qs.filter(dbsdevice__electrodes__target__in=filters["Targets"]).distinct()

            if filters.get("RecordingTypes"):
                source_files = models.SourceFile.objects.filter(owner__in=qs)
                matched_uids = (
                    models.Recording.objects
                          .filter(source__in=source_files, type__in=filters["RecordingTypes"])
                          .values_list("source__owner__uid", flat=True)
                          .distinct()
                )
                qs = qs.filter(uid__in=matched_uids)

            if filters.get("Devices"):
                device_uids = list(
                    models.DBSDevice.objects.filter(owner__in=qs, type__in=filters["Devices"])
                                    .values_list("uid", flat=True)
                )
                matched_uids = (
                    models.SourceFile.objects
                          .filter(owner__in=qs, metadata__Device__in=device_uids)
                          .values_list("owner__uid", flat=True)
                          .distinct()
                )
                qs = qs.filter(uid__in=matched_uids)

            date_range = filters.get("DateRange", {})
            if date_range.get("Start") and date_range.get("End"):
                source_files = models.SourceFile.objects.filter(owner__in=qs)
                matched_uids = (
                    models.Recording.objects
                          .filter(source__in=source_files,
                                  date__gte=date_range["Start"],
                                  date__lte=date_range["End"])
                          .values_list("source__owner__uid", flat=True)
                          .distinct()
                )
                qs = qs.filter(uid__in=matched_uids)

            result = []
            for participant in qs:
                info = participant_info_map.get(participant.uid, participant.get_info())
                info["DBSDevices"] = Database.extractParticipantDevices(participant)
                p_source_files = models.SourceFile.objects.filter(owner=participant)
                rec_qs = (
                    models.Recording.objects
                          .filter(source__in=p_source_files, type__in=ALLOWED_RECORDING_TYPES)
                )
                if filters.get("RecordingTypes"):
                    rec_qs = rec_qs.filter(type__in=filters["RecordingTypes"])
                info["Recordings"] = list(rec_qs.order_by("type").values("uid", "type", "date", "name"))
                result.append(info)

            return Response(status=200, data=json_compliant_handler(result))

        # ── DownloadAllData ───────────────────────────────────────────────────
        if request.data["RequestType"] == "DownloadAllData":
            participant_ids = request.data.get("ParticipantIds", [])
            type_filter = request.data.get("RecordingTypes") or None
            use_raw = request.data.get("ChannelFormat", "clean") == "raw"
            study_uid = request.user.configuration.get("ActiveStudy")
            all_dfs = []

            for participant in models.Participant.objects.filter(uid__in=participant_ids):
                if not Database.checkAccessPermission(request.user, participant.uid, study_uid=study_uid):
                    continue
                rec_qs = models.Recording.objects.filter(
                    source__owner=participant, type__in=ALLOWED_RECORDING_TYPES
                )
                if type_filter:
                    rec_qs = rec_qs.filter(type__in=type_filter)
                for recording in rec_qs:
                    try:
                        df = _recording_to_dataframe(recording, use_raw_names=use_raw)
                        if df.empty:
                            continue
                        df.insert(0, "RecordingName", recording.name or "")
                        df.insert(0, "RecordingDate", recording.date or "")
                        df.insert(0, "RecordingType", recording.type)
                        df.insert(0, "RecordingId", recording.uid)
                        df.insert(0, "ParticipantId", participant.uid)
                        df.insert(0, "Participant", getattr(participant, "name", "") or participant.uid)
                        all_dfs.append(df)
                    except Exception:
                        continue

            combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
            buf = BytesIO()
            combined.to_csv(buf, index=False)
            fname = "bravo_all_recordings_raw.csv" if use_raw else "bravo_all_recordings.csv"
            response = HttpResponse(buf.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{fname}"'
            return response

        return Response(status=400, data={"message": "Unknown RequestType"})
