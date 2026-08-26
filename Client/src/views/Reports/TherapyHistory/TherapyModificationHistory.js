/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Card,
  Grid,
  Slider,
  Tooltip,
  Autocomplete,
  TextField,
  Menu,
  MenuItem,
  Link
} from "@mui/material"

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import MDBadge from "components/MDBadge";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";
import MDButton from "components/MDButton";

const monthLabels = ['Past', 'Current', 'Next'];
const groupLegend = [
  { label: 'Group A', color: '#7c65ff' },
  { label: 'Group B', color: '#21f3b4' },
  { label: 'Group C', color: '#ffae00' },
  { label: 'Group D', color: '#f43636' },
];

function toMonthStart(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function toMonthIndex(date) {
  return date.getFullYear() * 12 + date.getMonth();
}

function fromMonthIndex(monthIndex) {
  const year = Math.floor(monthIndex / 12);
  const month = monthIndex % 12;
  return new Date(year, month, 1);
}

function addMonths(baseDate, monthOffset) {
  return new Date(baseDate.getFullYear(), baseDate.getMonth() + monthOffset, 1);
}

function clampMonthIndex(value, min, max) {
  return Math.max(min, Math.min(value, max));
}

function toDayStart(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function addDays(date, dayOffset) {
  const next = new Date(date);
  next.setDate(next.getDate() + dayOffset);
  return toDayStart(next);
}

function isSameDay(left, right) {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate();
}

function toDayKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function toVisibilityKey(eventId, day) {
  return `${eventId}|${toDayKey(day)}`;
}

function isWithinEventDay(date, event) {
  return date >= event.startDate && date <= event.endDate;
}

function getGroupColor(groupId) {
  if (groupId) {
    if (groupId === 'A') return '#7c65ff';
    if (groupId === 'B') return '#21f3b4';
    if (groupId === 'C') return '#ffae00';
    if (groupId === 'D') return '#f43636';
    return '#6a6b6b';
  }
}

const getDateString = (timestamp, timezone) => {
  return new Date(timestamp * 1000).toLocaleDateString("en-CA", {
    month: 'long',
    day: '2-digit',
    year: 'numeric',
  })
}

const getTimeString = (timestamp, timezone) => {
  return new Date(timestamp * 1000).toLocaleTimeString("en-US", {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function LeadComponentSvg({ components }) {
  const maxAmplitude = Math.max(...components);
  const componentColor = components.map((value) => {
    if (value < 0) {
      const contactColor = `color-mix(in srgb, ${"#AAAAAA"}, ${"#00c3ff"} 100%)`;
      return contactColor;
    }
    
    const intensity = Math.max(0, Math.min(1, value / maxAmplitude));
    const contactColor = `color-mix(in srgb, ${"#AAAAAA"}, ${"#FF0000"} ${(intensity)*100}%)`;
    return contactColor;
  });

  return (
    <svg
      className="group-history-lead-svg"
      viewBox="0 0 86 212"
      role="img"
      aria-label="Electrode component intensities"
    >
      <rect x="31" y="0" width="24" height="182" rx="12" fill="#000000" stroke="var(--dashboard-border)" />
      <path 
        d="M 31 176 
          H 55 
          V 200 
          A 12 12 0 0 1 31 200 
          Z" 
        fill="color-mix(in srgb, var(--dashboard-surface-raised), transparent 12%)" 
        stroke="var(--dashboard-border)" 
      />
      
      <rect x="31" y="162" width="24" height="25" fill={componentColor[0]} stroke="var(--dashboard-border)">
        <title>{components[0]}</title>
      </rect>
      {components.length === 8 && <rect x="62" y="112" width="24" height="25" fill={componentColor[1]} stroke="var(--dashboard-border)">
        <title>{components[1]}</title>
      </rect>}
      <rect x="31" y="112" width="24" height="25" fill={componentColor.length === 8 ? componentColor[2] : componentColor[1]} stroke="var(--dashboard-border)">
        <title>{componentColor.length === 8 ? components[2] : components[1]}</title>
      </rect>
      {components.length === 8 && <rect x="0" y="112" width="24" height="25" fill={componentColor[3]} stroke="var(--dashboard-border)" >
        <title>{components[3]}</title>
      </rect>}
      {components.length === 8 && <rect x="62" y="62" width="24" height="25" fill={componentColor[4]} stroke="var(--dashboard-border)" >
        <title>{components[4]}</title>
      </rect>}
      <rect x="31" y="62" width="24" height="25" fill={componentColor.length === 8 ? componentColor[5] : componentColor[2]} stroke="var(--dashboard-border)">
        <title>{componentColor.length === 8 ? components[5] : components[2]}</title>
      </rect>
      {components.length === 8 && <rect x="0" y="62" width="24" height="25" fill={componentColor[6]} stroke="var(--dashboard-border)" >
        <title>{components[6]}</title>
      </rect>}
      <rect x="31" y="12" width="24" height="25" fill={componentColor.length === 8 ? componentColor[7] : componentColor[3]} stroke="var(--dashboard-border)">
        <title>{componentColor.length === 8 ? components[7] : components[3]}</title>
      </rect>
    </svg>
  );
};

function TherapyModificationHistory({therapyHistoryRaw, availableDevices, device, visitDates}) {
  const { participant_uid } = useParams();
  const [therapyGroups, setTherapyGroups] = useState([]);

  const [timelineMenu, setTimelineMenu] = useState({open: false, anchorEl: null, eventId: "Pre", options: [], groupId: "A"});
  const [timelineData, setTimelineData] = useState([]);
  const [timelineStart, setTimelineStart] = useState(new Date().getTime() / 1000);
  const [timelineEnd, setTimelineEnd] = useState(new Date().getTime() / 1000 );

  const [sliderValue, setSliderValue] = useState(0);
  const sliderMin = 0;
  const sliderMax = Math.max(0, visitDates.length - 1);
  const selectedVisitDate = visitDates[sliderValue] ?? 0;

  useEffect(() => {
    setTherapyGroups(therapyHistoryRaw.sort((a, b) => a.Date - b.Date).map((a) => {
      a.Settings = a.StimulationSettings.map((s, i) => ({ ...s, ...a.AdaptiveSettings[i] }));
      return a;
    }));
  }, [therapyHistoryRaw]);

  useEffect(() => {
    if (therapyGroups.length == 0) return;
    setTimelineStart(therapyGroups.length > 0 ? therapyGroups[0].Date : new Date().getTime() / 1000);
    setTimelineEnd(therapyGroups.length > 0 ? therapyGroups[therapyGroups.length - 1].Date : new Date().getTime() / 1000);
    setSliderValue(sliderMax);
  }, [therapyGroups]);

  useEffect(() => {
    const visitDate = getDateString(selectedVisitDate.Date);
    const groups = therapyGroups.filter((group) =>  getDateString(group.Date) === visitDate && availableDevices.filter((device) => device.Id === group.Device)[0].Heritage === device);

    let groupOptions = groups.map((group) => {
      return { ...group, Time: getTimeString(group.Date), Active: false }
    });

    for (const groupId of ["A", "B", "C", "D"]) {
      const previsit = groupOptions.filter((group) => group.GroupId.endsWith(groupId) && ["Pre-visit Therapy", "Past Therapy"].includes(group.Type) && group.Label == "Preferenced");
      if (previsit.length > 0) {
        groupOptions = groupOptions.map((group) => {
          if (group.Id === previsit[0].Id) {
            return {...group, Active: true, Label: "Preferenced"};
          } else {
            return group;
          }
        });
      } else {
        const firstPrevisit = groupOptions.filter((group) => group.GroupId.endsWith(groupId) && group.Type == "Pre-visit Therapy");
        if (firstPrevisit.length > 0) {
          const visit = firstPrevisit.reduce((prev, curr) => (prev.Time < curr.Time ? prev : curr));
          groupOptions = groupOptions.map((group) => {
            if (group.Id === visit.Id) {
              return {...group, Active: true, Label: "Preferenced"};
            } else {
              return group;
            }
          });
        } else {
          const firstVisitHistory = groupOptions.filter((group) => group.GroupId.endsWith(groupId) && group.Type == "Past Therapy");
          if (firstVisitHistory.length > 0) {
            const visit = firstVisitHistory.reduce((prev, curr) => (prev.Time < curr.Time ? prev : curr));
            groupOptions = groupOptions.map((group) => {
              if (group.Id === visit.Id) {
                return {...group, Active: true, Label: "Preferenced"};
              } else {
                return group;
              }
            });
          }
        }
      }
      
      const postvisit = groupOptions.filter((group) => group.GroupId.endsWith(groupId) && group.Type == "Post-visit Therapy" && group.Label == "Preferenced");
      if (postvisit.length > 0) {
        groupOptions = groupOptions.map((group) => {
          if (group.Id === postvisit[0].Id) {
            return {...group, Active: true, Label: "Preferenced"};
          } else {
            return group;
          }
        });
      } else {
        const lastPostvisit = groupOptions.filter((group) => group.GroupId.endsWith(groupId) && group.Type == "Post-visit Therapy");
        if (lastPostvisit.length > 0) {
          const visit = lastPostvisit.reduce((prev, curr) => (prev.Time > curr.Time ? prev : curr));
          groupOptions = groupOptions.map((group) => {
            if (group.Id === visit.Id) {
              return {...group, Active: true, Label: "Preferenced"};
            } else {
              return group;
            }
          });
        }
      }
    }

    setTimelineData(groupOptions);
  }, [device, availableDevices, therapyGroups, selectedVisitDate]);

  const getLFPThresholds = (thresholdList) => {
    if (thresholdList[0] == 20 && thresholdList[1] == 30) {
      return null;
    }
    if (thresholdList[0] == thresholdList[1]) {
      return thresholdList[0].toFixed(0);
    }
    return thresholdList[0].toFixed(0) + " - " + thresholdList[1].toFixed(0);
  }

  const getRecordingConfigurationCard = (recordingConfiguration) => {
    if (recordingConfiguration.Type == "Unknown") return null;

    if (recordingConfiguration.Type == "Medtronic BrainSense") {
      return (
        <MDBox sx={{ display: "flex", flexDirection: "column", width: "100%", mt: 2 }}>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="error" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Recording Configuration:"}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"LFP Sense:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {recordingConfiguration.Config.SensingSetup.FrequencyInHertz}{" Hz"} ({(recordingConfiguration.Config.SensingSetup.AveragingDurationInMilliSeconds / 1000).toFixed(1)}{" sec"})
            </MDTypography>
          </MDBox>
          {getLFPThresholds(recordingConfiguration.Config.Thresholds.LFPThresholds) && (
            <MDBox sx={{ display: "flex", flexDirection: "row"}}>
              <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                {"LFP Threshold:"}
              </MDTypography>
              <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {getLFPThresholds(recordingConfiguration.Config.Thresholds.LFPThresholds)}
            </MDTypography>
          </MDBox>)}
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Amplitude Range:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {recordingConfiguration.Config.Thresholds.AmplitudeThreshold[0]} - {recordingConfiguration.Config.Thresholds.AmplitudeThreshold[1]}{" mA"}
            </MDTypography>
          </MDBox>
        </MDBox>
      );
    }
  }
  
  const getAdaptiveConfigurationCard = (adaptiveConfiguration) => {
    if (adaptiveConfiguration.Type == "Unknown") return null;

    if (adaptiveConfiguration.Type == "Medtronic Adaptive") {
      if (adaptiveConfiguration.Config.Status == "ADBSStatusDef.NOT_CONFIGURED") return null;
      
      return (
        <MDBox sx={{ display: "flex", flexDirection: "column", width: "100%", mt: 2 }}>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="error" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Adaptive Configuration:"}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Mode:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {adaptiveConfiguration.Config.Mode.split(".")[1].split("_").map((a) => a.charAt(0).toUpperCase() + a.slice(1).toLowerCase()).join(" ")}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Ramp Up Onset Duration:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {(adaptiveConfiguration.Config.UpperThresholdOnsetInMilliSeconds / 1000).toFixed(1)}{" sec"}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Ramp Up Time:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {(adaptiveConfiguration.Config.RampUpTime / 1000).toFixed(1)}{" sec"}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Ramp Down Onset Duration:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {(adaptiveConfiguration.Config.LowerThresholdOnsetInMilliSeconds / 1000).toFixed(1)}{" sec"}
            </MDTypography>
          </MDBox>
          <MDBox sx={{ display: "flex", flexDirection: "row"}}>
            <MDTypography variant="caption" color="black" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
              {"Ramp Down Time:"}
            </MDTypography>
            <MDTypography variant="caption" color="text" sx={{ fontSize: "12px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
              {(adaptiveConfiguration.Config.RampDownTime / 1000).toFixed(1)}{" sec"}
            </MDTypography>
          </MDBox>
        </MDBox>
      );
    }
  }
  
  const displayGroupParameters = (group) => {
    return group.Settings.sort((a, b) => a.Electrode.CustomName.localeCompare(b.Electrode.CustomName)).map((setting, index) => {
      const fractionalAmplitudes = setting.Electrode.ChannelNames.map((contact) => {
        if (setting.Contact.includes(contact)) return setting.FractionalAmplitudes[setting.Contact.indexOf(contact)] ?? 1;
        if (setting.ReturnContact.includes(contact)) return -1;
        return 0;
      });

      return (
        <Grid item xs={12} sm={12} lg={6} key={setting.Electrode.CustomName + group.Id + " " + index}>
          <MDBox sx={{ display: "flex", flexDirection: "row", alignItems: "start", justifyContent: "start", mt: 1, width: "100%" }}>
            <MDBox sx={{ width: "75%", display: "flex", flexDirection: "column", alignItems: "start", justifyContent: "start", mr: 2 }}>
              <MDBox sx={{ display: "flex", flexDirection: "row"}}>
                <MDTypography variant="caption" color="black" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                  {"Target: "}
                </MDTypography>
                <MDTypography variant="caption" color="info" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
                  {setting.Electrode.CustomName}
                </MDTypography>
              </MDBox>
              <MDBox sx={{ display: "flex", flexDirection: "row"}}>
                <MDTypography variant="caption" color="black" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                  {"Therapy Type:"}
                </MDTypography>
                <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap" }}>
                  {setting.StimulationType}
                </MDTypography>
              </MDBox>
              <MDBox sx={{ display: "flex", flexDirection: "row"}}>
                <MDTypography variant="caption" color="black" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                  {"Frequency:"}
                </MDTypography>
                <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                  {setting.Frequency}{" Hz"}
                </MDTypography>
              </MDBox>
              <MDBox sx={{ display: "flex", flexDirection: "row"}}>
                <MDTypography variant="caption" color="black" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                  {"Pulsewidth:"}
                </MDTypography>
                <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                  {setting.Pulsewidth} {setting.PulsewidthUnit}
                </MDTypography>
              </MDBox>
              <MDBox sx={{ display: "flex", flexDirection: "row"}}>
                <MDTypography variant="caption" color="black" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "auto", whiteSpace: "nowrap", mr: 1 }}>
                  {"Amplitude:"}
                </MDTypography>
                <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                  {setting.Amplitude} {setting.AmplitudeUnit}
                </MDTypography>
              </MDBox>
              
              {getRecordingConfigurationCard(setting.RecordingConfiguration)}
              {getAdaptiveConfigurationCard(setting.StimulationConfiguration)}

            </MDBox>
            <MDBox id={"electrode_contact"} sx={{ height: "100%", width: "15%" }}>
              <LeadComponentSvg components={fractionalAmplitudes} />
            </MDBox>
          </MDBox>
        </Grid>
      )
    });
  }

  return useMemo(() => (
    <MDBox>
      <MDBox sx={{ paddingBottom: 2, width: "100%" }}>
        <Card sx={{ px: 3, py: 1, display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <MDBox sx={{ width: "100%" }}>
            <MDBox color={"black"} sx={{
              fontFamily: 'Roboto',
              fontSize: '13px',
              fontWeight: 700,
              textAlign: 'center',
            }}>
              {selectedVisitDate ? getDateString(selectedVisitDate.Date) : 'No date selected'}
            </MDBox>
            <MDBox sx={{ width: "100%", px: 2 }}>
              <Slider
                type="range"
                min={0}
                max={1}
                step={0.0001}
                value={(() => {
                  // normalize sliderValue to 0..1 based on visit date timestamp
                  if (!visitDates || visitDates.length === 0) return 0;
                  const first = visitDates[0].Date || visitDates[0];
                  const last = visitDates[visitDates.length - 1].Date || visitDates[visitDates.length - 1];
                  const cur = selectedVisitDate ? (selectedVisitDate.Date || selectedVisitDate) : first;
                  if (last === first) return 0;
                  return Math.max(0, Math.min(1, (cur - first) / (last - first)));
                })()}
                onChange={(e) => {
                  const t = Number(e.target.value);
                  if (!visitDates || visitDates.length === 0) return;
                  const first = visitDates[0].Date || visitDates[0];
                  const last = visitDates[visitDates.length - 1].Date || visitDates[visitDates.length - 1];
                  const targetTs = first + t * (last - first);
                  let nearest = 0;
                  let mindiff = Infinity;
                  visitDates.forEach((d, idx) => {
                    const ts = d.Date || d;
                    const diff = Math.abs(ts - targetTs);
                    if (diff < mindiff) { mindiff = diff; nearest = idx; }
                  });
                  if (nearest !== sliderValue) {
                    setSliderValue(nearest);
                  }
                }}
                aria-label="Therapy history date slider (time-scaled)"
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </MDBox>
            <MDBox sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: 'Roboto',
              fontSize: '11px',
            }}>
              <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 500, textAlign: "start", width: "100%", display: "block" }}>
                {getDateString(timelineStart)}
              </MDTypography>
              <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 500, textAlign: "end", width: "100%", display: "block" }}>
                {getDateString(timelineEnd)}
              </MDTypography>
            </MDBox>
          </MDBox>
        </Card>
      </MDBox>
      <MDBox py={2} pt={0}>
        <Grid container spacing={2} sx={{ mb: 1 }}>
          <Grid item xs={12} sm={6}>
            <MDBox sx={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "start", width: "100%" }}>
              <MDTypography variant="caption" color="black" sx={{ fontSize: "18px", fontWeight: 800, textAlign: "start", width: "auto", display: "block" }}>
                {"Therapy Configurations Before Visit"}
              </MDTypography>
            </MDBox>
          </Grid>
          <Grid item xs={12} sm={6}>
            <MDBox sx={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "start", width: "100%" }}>
              <MDTypography variant="caption" color="black" sx={{ fontSize: "18px", fontWeight: 800, textAlign: "start", width: "auto", display: "block" }}>
                {"Therapy Configurations After Visit"}
              </MDTypography>
            </MDBox>
          </Grid>
          {["A", "B", "C", "D"].map((groupId) => {
            const pre_visit = timelineData.filter((event) => event.GroupId.endsWith(groupId) && event.Active && ["Pre-visit Therapy", "Past Therapy"].includes(event.Type));
            const post_visit = timelineData.filter((event) => event.GroupId.endsWith(groupId) && event.Active && ["Post-visit Therapy"].includes(event.Type));
            const therapy_cards = [];

            if (pre_visit.length === 0) {
              therapy_cards.push(
                <Grid item xs={12} sm={6} key={`group-${groupId}-pre`} />
              );
            } else {
              therapy_cards.push(
                <Grid item xs={12} sm={6} key={`group-${groupId}-pre`}>
                  <Card sx={{ px: 2, py: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <MDBox sx={{ display: "flex", flexDirection: "column", alignItems: "start", justifyContent: "center", width: "100%" }}>
                      <MDTypography variant="caption" color="black" sx={{ fontSize: "18px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                        {`Group ${groupId}`} {pre_visit[0].GroupName ? `(${pre_visit[0].GroupName})` : ''}
                      </MDTypography>
                      <MDBox sx={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "start" }}>
                        <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                          {pre_visit[0].Date !== Infinity ? `Visit Time: ${getTimeString(pre_visit[0].Date)}` : 'No Pre-Visit Therapy'}
                        </MDTypography>
                        <MDTypography variant="caption" color="text" onClick={(event) => {
                          setTimelineMenu({...timelineMenu, open: true, anchorEl: event.currentTarget, eventId: "Pre", groupId: groupId});
                        }} sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", ml: 2, p: 0, minWidth: "200px", height: "auto", width: "auto", cursor: "pointer", textDecoration: "underline" }} >
                          {"View Another Record"}
                        </MDTypography>
                      </MDBox>
                      <Grid container spacing={2} sx={{ display: "flex", flexDirection: "row", alignItems: "start", justifyContent: "start", mt: 1, width: "100%" }}>
                        {displayGroupParameters(pre_visit[0])}
                      </Grid>
                    </MDBox>
                  </Card>
                </Grid>
              );
            }
            
            if (post_visit.length === 0) {
              therapy_cards.push(
                <Grid item xs={12} sm={6} key={`group-${groupId}-post`} />
              );
            } else {
              therapy_cards.push(
                <Grid item xs={12} sm={6} key={`group-${groupId}-post`}>
                  <Card sx={{ px: 3, py: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <MDBox sx={{ display: "flex", flexDirection: "column", alignItems: "start", justifyContent: "center", width: "100%" }}>
                      <MDTypography variant="caption" color="black" sx={{ fontSize: "18px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                        {`Group ${groupId}`} {post_visit[0].GroupName ? `(${post_visit[0].GroupName})` : ''}
                      </MDTypography>
                      <MDBox sx={{ display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "start" }}>
                        <MDTypography variant="caption" color="text" sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", width: "100%", display: "block" }}>
                          {post_visit[0].Date !== Infinity ? `Visit Time: ${getTimeString(post_visit[0].Date)}` : 'No Post-Visit Therapy'}
                        </MDTypography>
                        <MDTypography variant="caption" color="text" onClick={(event) => {
                          setTimelineMenu({...timelineMenu, open: true, anchorEl: event.currentTarget, eventId: "Post", groupId: groupId});
                        }} sx={{ fontSize: "15px", fontWeight: 800, textAlign: "start", ml: 2, p: 0, minWidth: "200px", height: "auto", width: "auto", cursor: "pointer", textDecoration: "underline" }} >
                          {"View Another Record"}
                        </MDTypography>
                      </MDBox>
                      <Grid container spacing={2} sx={{ display: "flex", flexDirection: "row", alignItems: "start", justifyContent: "start", mt: 1, width: "100%" }}>
                        {displayGroupParameters(post_visit[0])}
                      </Grid>
                    </MDBox>
                  </Card>
                </Grid>
              );
            }
            return therapy_cards;
          })}
        </Grid>
      </MDBox>
      <Menu
        anchorEl={timelineMenu.anchorEl}
        anchorReference={null}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        keepMounted={false}
        disableRestoreFocus={false}
        autoFocus={false}
        open={timelineMenu.open}
        onClose={() => {
          setTimelineMenu({...timelineMenu, open: false, anchorEl: null, eventId: ""})
        }}
        slotProps={{
          paper: {
            sx: {
              py: 0.5,
              px: 0.3
            }
          }
        }}
        sx={{ mt: 2, p: 0 }}
      >
        {timelineData.filter((option) => option.GroupId.endsWith(timelineMenu.groupId) 
          && ((timelineMenu.eventId === "Pre" && ["Pre-visit Therapy", "Past Therapy"].includes(option.Type)) 
          || (timelineMenu.eventId === "Post" && ["Post-visit Therapy"].includes(option.Type)))
        ).map((option, index) => (
          <MenuItem key={option.Id} onClick={() => {
            setTherapyGroups((prev) => {
              return prev.map((group) => {
                if (getDateString(group.Date) === getDateString(option.Date) && group.GroupId === option.GroupId) {
                  if (timelineMenu.eventId === "Pre" && ["Pre-visit Therapy", "Past Therapy"].includes(group.Type)) {
                    return { ...group, Label: group.Id === option.Id ? "Preferenced" : "" };
                  } else if (timelineMenu.eventId === "Post" && ["Post-visit Therapy"].includes(group.Type)) {
                    return { ...group, Label: group.Id === option.Id ? "Preferenced" : "" };
                  }
                }
                return group;
              });
            });

            const allIds = []
            if (timelineMenu.eventId === "Pre") {
              allIds.push(...timelineData.filter((option) => option.GroupId.endsWith(timelineMenu.groupId) && ["Pre-visit Therapy", "Past Therapy"].includes(option.Type)).map((option) => option.Id));
            } else if (timelineMenu.eventId === "Post") {
              allIds.push(...timelineData.filter((option) => option.GroupId.endsWith(timelineMenu.groupId) && ["Post-visit Therapy"].includes(option.Type)).map((option) => option.Id));
            }

            SessionController.query("/api/assignTherapyLabel", {
              ParticipantId: participant_uid,
              TimelineDate: option.Date,
              SelectiveIds: allIds,
              GroupId: option.GroupId,
              TherapyLabel: "Preferenced",
              TherapyIds: [option.Id],
            }).then((response) => {
            }).catch((error) => {
              console.log("Error assigning therapy label:", error);
            });
            setTimelineMenu({...timelineMenu, open: false, anchorEl: null, eventId: ""});
          }}>
            <MDBox component={Link} sx={{ fontSize: "15px", p: 0, m: 0 }}>
              {option.Time} - ({option.Type})
            </MDBox>
          </MenuItem>
        ))}
      </Menu>
    </MDBox>
  ), [selectedVisitDate, sliderValue, timelineStart, timelineData, timelineMenu, alert]);
}

export default TherapyModificationHistory;
