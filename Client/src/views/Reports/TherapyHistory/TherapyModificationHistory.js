/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Card,
  Grid,
  Slider,
  Tooltip,
  Autocomplete,
  TextField,
} from "@mui/material"

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import MDBadge from "components/MDBadge";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapyModificationHistory({therapyHistoryRaw, device, viewConfigurationTable}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { language, report } = controller;

  const [therapyTable, setTherapyTable] = React.useState({});
  const [interleavingSwitch, setInterleavingSwitch] = React.useState({});
  const [therapyDateSlider, setTherapyDateSlider] = React.useState({active: 0, options: []});
  const [therapyHistory, setTherapyHistory] = React.useState(therapyHistoryRaw);
  const [mostUsedConfig, setMostUsedConfig] = React.useState([]);

  const [therapyOptions, setTherapyOptions] = React.useState({active: null, options: []});

  const sliderRef = React.useRef(null);

  const [alert, setAlert] = React.useState(null);
  const { participant_uid } = useParams();

  React.useEffect(() => {
    if (therapyHistoryRaw) setTherapyHistory(therapyHistoryRaw);
  }, [therapyHistoryRaw]);

  React.useEffect(() => {
    if (!therapyHistoryRaw) return;

    let therapyDates = {active: 0, options: []};
    for (let i in therapyHistoryRaw.TherapyTimeline) {
      if (therapyHistoryRaw.TherapyTimeline[i].DefinedTherapies.some((a) => a.Device.Name == device) == false) continue;
      therapyDates.options.push(therapyHistoryRaw.TherapyTimeline[i].Date);
    }

    if (therapyDates.options.length > 0) {
      if (therapyDates.options.length > 1) {
        if (therapyDates.options[therapyDates.options.length-1] - therapyDates.options[therapyDates.options.length-2] < 3600*12) {
          therapyDates.active = therapyDates.options[therapyDates.options.length-2];
        }
      } else {
        therapyDates.active = therapyDates.options[therapyDates.options.length-1];
      }
    } 
    setTherapyDateSlider(therapyDates);
  }, [therapyHistoryRaw, device]);

  React.useEffect(() => {
    for (let i in therapyHistory.TherapyTimeline) {
      if (therapyHistory.TherapyTimeline[i].Date == therapyDateSlider.active) {
        setTherapyOptions(() => {
          let options = {active: null, pre: [], post: [], options: []};
          for (let j in therapyHistory.TherapyTimeline[i].DefinedTherapies) {
            for (let l in therapyHistory.TherapyTimeline[i].Therapies) {
              for (let k in therapyHistory.TherapyTimeline[i].Therapies[l].Processed) {
                if (therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Device.Id == therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Device.Id) {
                  if (!options.options.map((a) => a.TherapyIds).includes(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].TherapyIds)) {
                    options.options.push(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k]);
                  }
                  if (listMatch(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].TherapyIds, therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Pre)) {
                    options.pre.push(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k]);
                  }
                  if (listMatch(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].TherapyIds, therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Post)) {
                    options.post.push(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k]);
                  }
                }
              }
            }
            if (options.pre.length < parseInt(j)+1) {
              options.pre.push(null);
            }
            if (options.post.length < parseInt(j)+1) {
              options.post.push(null);
            }
          }
          return options;
        });

        setTherapyTable(() => {
          const definedTherapies = therapyHistory.TherapyTimeline[i].DefinedTherapies.filter((a) => a.Device.GenericName == device);
          return { ...therapyHistory.TherapyTimeline[i], DefinedTherapies: definedTherapies, };
        });
        break;
      }
    }
  }, [therapyHistory, therapyDateSlider]);

  React.useEffect(() => {
    setMostUsedConfig(() => {
      let mostUsed = [];
      for (let i in therapyHistory.TherapyTimeline) {
        let activeConfigs = {
          LeftAmplitude: "", LeftContact: "", LeftFrequency: "", LeftPulsewidth: "", PercentUsage: 0,
          RightAmplitude: "", RightContact: "", RightFrequency: "", RightPulsewidth: "", Date: therapyHistory.TherapyTimeline[i].Date,
        };
        for (let j in therapyHistory.TherapyTimeline[i].DefinedTherapies) {
          if (therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Device.GenericName != device) continue;
          if (therapyHistory.TherapyTimeline[i].DefinedTherapies[j].PercentUsage > activeConfigs.PercentUsage) {
            activeConfigs = {
              LeftAmplitude: "", LeftContact: "", LeftFrequency: "", LeftPulsewidth: "", PercentUsage: 0,
              RightAmplitude: "", RightContact: "", RightFrequency: "", RightPulsewidth: "", Date: therapyHistory.TherapyTimeline[i].Date,
            };
            for (let l in therapyHistory.TherapyTimeline[i].Therapies) {
              for (let k in therapyHistory.TherapyTimeline[i].Therapies[l].Processed) {
                if (therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Device.Id == therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Device.Id) {
                  if (listMatch(therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].TherapyIds, therapyHistory.TherapyTimeline[i].DefinedTherapies[j].Pre)) {
                    for (let m in therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation) {
                      if (therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m].length == 0) continue;
                      for (let n in therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m]) {
                        if (therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Electrodes[m].Target.startsWith("Left") && therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Electrode.Target.startsWith("Left")) {
                          activeConfigs.LeftAmplitude += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Amplitude.toFixed(1) + " " + therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].AmplitudeUnit;
                          let contacts = [];
                          for (let c of therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Contact) {
                            if (!contacts.includes(c.split("-")[0])) {
                              contacts.push(c.split("-")[0]);
                            }
                          }
                          activeConfigs.LeftContact += contacts.join(", ");
                          activeConfigs.LeftFrequency += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Frequency.toFixed(0) + " Hz";
                          activeConfigs.LeftPulsewidth += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Pulsewidth.toFixed(0) + " " + therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].PulsewidthUnit;
                        } else if (therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Electrodes[m].Target.startsWith("Right") && therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Electrode.Target.startsWith("Right")) {
                          activeConfigs.RightAmplitude += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Amplitude.toFixed(1) + " " + therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].AmplitudeUnit;
                          let contacts = [];
                          for (let c of therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Contact) {
                            if (!contacts.includes(c.split("-")[0])) {
                              contacts.push(c.split("-")[0]);
                            }
                          }
                          activeConfigs.RightContact += contacts.join(", ");
                          activeConfigs.RightFrequency += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Frequency.toFixed(0) + " Hz";
                          activeConfigs.RightPulsewidth += therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].Pulsewidth.toFixed(0) + " " + therapyHistory.TherapyTimeline[i].Therapies[l].Processed[k].Stimulation[m][n].PulsewidthUnit;
                        }
                      }
                    }
                    activeConfigs.PercentUsage = therapyHistory.TherapyTimeline[i].DefinedTherapies[j].PercentUsage;
                  }
                }
              }
            }
          }
        }
        mostUsed.push(activeConfigs);
      }
      return mostUsed;
    });
  }, [therapyHistory]);

  const sliderMin = therapyDateSlider.options.length > 0 ? therapyDateSlider.options[0] : 0;
  const sliderMax = therapyDateSlider.options.length > 0 ? therapyDateSlider.options[therapyDateSlider.options.length-1] : sliderMin;
  const formatMarkTooltip = (ts) => {
    let tableRows = [];
    for (let i in mostUsedConfig) {
      if (mostUsedConfig[i].Date == ts) {
        const rowIndex = ["Current", "Last Visit", "2 Visits Ago"];
        tableRows.push(["", "Left Amplitude", "Left Contact", "Left Frequency", "Left Pulsewidth",
                      "Right Amplitude", "Right Contact", "Right Frequency", "Right Pulsewidth"]);
        for (let j = i; (j > 0 && j > i-3); j--) {
          tableRows.push([rowIndex[i-j], mostUsedConfig[j].LeftAmplitude, mostUsedConfig[j].LeftContact, mostUsedConfig[j].LeftFrequency, mostUsedConfig[j].LeftPulsewidth,
                        mostUsedConfig[j].RightAmplitude, mostUsedConfig[j].RightContact, mostUsedConfig[j].RightFrequency, mostUsedConfig[j].RightPulsewidth]);
        }
        break;
      }
    }

    return <MDBox p={1}>
      <MDTypography variant={"h6"} fontWeight={"bold"} color={"light"}> 
        {new Date(ts*1000).toLocaleDateString("en-US", {
          month: "2-digit",
          day: "2-digit",
          year: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </MDTypography>

      <div style={{ marginTop: 6 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 180 }}>
          <tbody>
            {tableRows.map((row, rIdx) => (
              <tr key={rIdx}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} style={{
                    border: "1px solid rgba(0,0,0,0.12)",
                    padding: "6px 8px",
                    textAlign: "center",
                    background: rIdx % 2 === 0 ? "rgba(0,0,0,0.02)" : "rgba(0,0,0,0)",
                    fontSize: 12,
                  }}>
                    <MDTypography variant={"p"} fontWeight={rIdx === 0 ? "bold" : "regular"} color={"light"}>
                      {cell}
                    </MDTypography>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </MDBox>
  };

  const getPreTherapySettingsBilateral = (config) => {
    if (!config) return;

    for (let i = 0; i < config.Electrodes.length; i++) {
      config.Adaptive[i] = config.Adaptive[i].filter((a,j) => config.Stimulation[i][j].Electrode.Target.split(" ")[0] == config.Electrodes[i].Target.split(" ")[0]);
      config.Stimulation[i] = config.Stimulation[i].filter((a) => a.Electrode.Target.split(" ")[0] == config.Electrodes[i].Target.split(" ")[0]);
    }
    
    return (
      <MDBox px={2} pt={1} pb={2}>
        <MDTypography variant={"h6"} fontWeight={"bold"}>
          {"Therapy Settings Before Visit:"}
        </MDTypography>
        {getTherapySettings(config, 0)}
        {getTherapySettings(config, 1)}
      </MDBox>
    )
  }

  const getPostTherapySettingsBilateral = (config) => {
    if (!config) return;

    for (let i = 0; i < config.Electrodes.length; i++) {
      config.Adaptive[i] = config.Adaptive[i].filter((a,j) => config.Stimulation[i][j].Electrode.Target == config.Electrodes[i].Target);
      config.Stimulation[i] = config.Stimulation[i].filter((a) => a.Electrode.Target == config.Electrodes[i].Target);
    }

    return (
      <MDBox px={2} pt={1} pb={2}>
        <MDTypography variant={"h6"} fontWeight={"bold"}>
          {"Therapy Settings After Visit:"}
        </MDTypography>
        {config.GroupType == "Active" ? (
        <MDTypography variant={"h5"} fontWeight={"bold"} color={"error"}>
          {"(Active)"}
        </MDTypography>
        ) : null}
        {getTherapySettings(config, 0)}
        {getTherapySettings(config, 1)}
      </MDBox>
    )
  }

  const getTherapySettings = (config, index) => {
    if (config.Stimulation.length < index+1) return;

    let interleaving = false;
    if (config.Stimulation[index].length > 1) {
      interleaving = true;
    }

    if (config.Stimulation[index].length == 0) return;

    let sensing = false;
    let adaptive = false;
    if (!interleaving && config.Adaptive[index][0]) {
      if (config.Adaptive[index][0].RecordingConfiguration) {
        if (!interleaving && config.Adaptive[index][0].RecordingConfiguration.Type !== "Unknown") {
          sensing = true;
        }
      }
      
      try {
        if (config.Adaptive[index][0].StimulationConfiguration) {
          if (config.Adaptive[index][0].StimulationConfiguration.Type === "Medtronic Adaptive") {
            if (config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.LFPThresholds[0] != 20 && config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.LFPThresholds[1] != 30) {
              adaptive = true;
            }
          }
        }
      } catch (e) {
        console.log(e)
      }
    }

    if (config.Type == "Past Therapy") {
      for (let i in config.Stimulation[index]) {
        for (let j in config.Stimulation[index][i].FractionalAmplitudes) {
          config.Stimulation[index][i].FractionalAmplitudes[j] = (config.Stimulation[index][0].FractionalAmplitudes[j] / config.Stimulation[index][i].Contact.length);
        }
      }
    }

    return (
      <MDBox pt={1} pb={2}>
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
          <MDTypography variant={"h6"} fontWeight={"bold"} color={"primary"}>
            {config.Stimulation[index][0].Electrode.CustomName}
          </MDTypography>
          <MDTypography variant={"subtitle1"} color={"secondary"} fontSize={15} fontWeight={"medium"} lineHeight={1} style={{cursor: "pointer"}}>
            {" ( " + new Date(interleaving ? (config.Stimulation[index][0].Date*1000) : (config.Stimulation[index][0].Date*1000)).toLocaleString("en-US", {...SessionController.getTimezoneName(config.Stimulation[index][0].Timezone),
              hour: "2-digit",
              minute: "2-digit",
            }) + " ) "}
          </MDTypography>
        </MDBox>
        <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
          {interleaving ? (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Frequency: "}<b>{config.Stimulation[index][0].Frequency}</b>{" Hz"}{" | "}<b>{config.Stimulation[index][1].Frequency}</b>{" Hz"}<br/>
          </MDTypography>
          ) : (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Frequency: "}<b>{config.Stimulation[index][0].Frequency}</b>{" Hz"}<br/>
          </MDTypography>
          )}
        </MDBox>
        <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
          {interleaving ? (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Pulsewidth: "}<b>{config.Stimulation[index][0].Pulsewidth}</b>{" "}{config.Stimulation[index][0].PulsewidthUnit}{" | "}<b>{config.Stimulation[index][1].Pulsewidth}</b>{" "}{config.Stimulation[index][1].PulsewidthUnit}<br/>
          </MDTypography>
          ) : (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Pulsewidth: "}<b>{config.Stimulation[index][0].Pulsewidth}</b>{" "}{config.Stimulation[index][0].PulsewidthUnit}<br/>
          </MDTypography>
          )}
        </MDBox>
        <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
          {interleaving ? (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Amplitude: "}<b>{config.Stimulation[index][0].Amplitude}</b>{" " + config.Stimulation[index][0].AmplitudeUnit}{" | "}<b>{config.Stimulation[index][1].Amplitude}</b>{" " + config.Stimulation[index][1].AmplitudeUnit}<br/>
          </MDTypography>
          ) : (
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Amplitude: "}<b>{config.Stimulation[index][0].Amplitude}</b>{" " + config.Stimulation[index][0].AmplitudeUnit}<br/>
          </MDTypography>
          )}
        </MDBox>
        
        {interleaving ? (
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} justifyContent={"start"} pt={1}>
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Active Contact: "}
          </MDTypography>
          {config.Stimulation[index][0].Contact.map((a, sindex) => {
            return <MDBox key={a}>
              <MDBadge badgeContent={a} color={"error"} size={"xs"} container sx={{marginLeft: 1, cursor: "pointer"}} />
              <MDTypography variant={"h6"} fontSize={12} fontWeight={"regular"} lineHeight={1} ml={1}>
                {(config.Stimulation[index][0].FractionalAmplitudes[sindex]).toFixed(1) + " " + config.Stimulation[index][0].AmplitudeUnit}
              </MDTypography>
            </MDBox>
          })}
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1} ml={1}>
            {" | "}
          </MDTypography>
          {config.Stimulation[index][1].Contact.map((a, sindex) => {
            return <MDBox key={a}>
              <MDBadge badgeContent={a} color={"error"} size={"xs"} container sx={{marginLeft: 1, cursor: "pointer"}} />
              <MDTypography variant={"h6"} fontSize={12} fontWeight={"regular"} lineHeight={1} ml={1}>
                {(config.Stimulation[index][1].FractionalAmplitudes[sindex]).toFixed(1) + " " + config.Stimulation[index][1].AmplitudeUnit}
              </MDTypography>
            </MDBox>
          })}
        </MDBox>
        ) : (
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} justifyContent={"start"} pt={1}>
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Active Contact: "}
          </MDTypography>
          {config.Stimulation[index][0].Contact.map((a, sindex) => {
            return <MDBox key={a}>
              <MDBadge badgeContent={a} color={"error"} size={"xs"} container sx={{marginLeft: 1, cursor: "pointer"}} />
              <MDTypography variant={"h6"} fontSize={12} fontWeight={"regular"} lineHeight={1} ml={1}>
                {(config.Stimulation[index][0].FractionalAmplitudes[sindex]).toFixed(1) + " " + config.Stimulation[index][0].AmplitudeUnit}
              </MDTypography>
            </MDBox>
          })}
        </MDBox>
        )}
        
        {interleaving ? (
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} justifyContent={"start"} pt={1}>
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Return Contact: "}
          </MDTypography>
          {config.Stimulation[index][0].ReturnContact.map((a) => {
            return <MDBadge key={a} badgeContent={a} color={"info"} size={"xs"} container sx={{marginLeft: 1}} />
          })}
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1} ml={1}>
            {" | "}
          </MDTypography>
          {config.Stimulation[index][1].ReturnContact.map((a) => {
            return <MDBadge key={a} badgeContent={a} color={"info"} size={"xs"} container sx={{marginLeft: 1}} />
          })}
        </MDBox>
        ) : (
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} pt={1}>
          <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
            {"Return Contact: "}
          </MDTypography>
          {config.Stimulation[index][0].ReturnContact.map((a) => {
            return <MDBadge key={a} badgeContent={a} color={"info"} size={"xs"} container sx={{marginLeft: 1}} />
          })}
        </MDBox>
        )}

        {config.Stimulation[index][0].CyclingPeriod > 0 ? <>
          {interleaving? ( 
          <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} pt={1}>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1} pr={1}>
              {"Cycling: "}{" "}
            </MDTypography>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
              {"Duty Cycle " + (config.Stimulation[index][0].Cycling*100).toFixed(1) + "%"}<br/>
              {"Duty Period " + (config.Stimulation[index][0].CyclingPeriod/60000).toFixed(1) + " minutes"}
            </MDTypography>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1} px={1}>
              {" | "}
            </MDTypography>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
              {"Duty Cycle " + (config.Stimulation[index][1].Cycling*100).toFixed(1) + "%"}<br/>
              {"Duty Period " + (config.Stimulation[index][1].CyclingPeriod/60000).toFixed(1) + " minutes"}
            </MDTypography>
          </MDBox>
          ) : (
          <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} pt={1}>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1} pr={1}>
              {"Cycling: "}{" "}
            </MDTypography>
            <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
              {"Duty Cycle " + (config.Stimulation[index][0].Cycling*100).toFixed(1) + "%"}<br/>
              {"Duty Period " + (config.Stimulation[index][0].CyclingPeriod/60000).toFixed(1) + " minutes"}
            </MDTypography>
          </MDBox>
          )}
        </> : null}
        
        {interleaving || !sensing ? null : (
          <MDBox pt={2}>
            <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
              <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                {"Sensing Frequency: "}<b>{config.Adaptive[index][0].RecordingConfiguration.Config.SensingSetup.FrequencyInHertz}</b>{" Hz"}<br/>
              </MDTypography>
            </MDBox>
            {adaptive ? (
              <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"Adaptive Mode: "}<b>{config.Adaptive[index][0].StimulationConfiguration.Config.Status}</b><br/>
                </MDTypography>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"Onset Durations (L|H): "}<b>{config.Adaptive[index][0].StimulationConfiguration.Config.LowerThresholdOnsetInMilliSeconds}</b>{" ms"} {" | "}
                  <b>{config.Adaptive[index][0].StimulationConfiguration.Config.UpperThresholdOnsetInMilliSeconds}</b>{" ms"}<br/>
                </MDTypography>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"Ramp Time (Up|Down): "}<b>{config.Adaptive[index][0].StimulationConfiguration.Config.RampUpTime}</b>{" ms"} {" | "}
                  <b>{config.Adaptive[index][0].StimulationConfiguration.Config.RampDownTime}</b>{" ms"}<br/>
                </MDTypography>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"Amplitude Limits (Up|Down): "}<b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[0]}</b>{" mA"} {" | "}
                  <b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[1]}</b>{" mA"}<br/>
                </MDTypography>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"LFP Thresholds (Up|Down): "}<b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.LFPThresholds[0]}</b>{" a.u."} {" | "}
                  <b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.LFPThresholds[1]}</b>{" a.u."}<br/>
                </MDTypography>
                <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                  {"Medtronic LFP Thresholds (Up|Down): "}<b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.MeasuredLFP[0]}</b>{" a.u."} {" | "}
                  <b>{config.Adaptive[index][0].RecordingConfiguration.Config.Thresholds.MeasuredLFP[1]}</b>{" a.u."}<br/>
                </MDTypography>
                {config.Adaptive[index][0].StimulationConfiguration.Config.Bypass ? (
                  <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                    {"Signal Bypass: "}<b>{config.Adaptive[index][0].StimulationConfiguration.Config.Bypass}</b><br/>
                  </MDTypography>
                ) : null}
              </MDBox>
            ) : null}
          </MDBox>
        )}
      </MDBox>
    )
  };

  const getTimeString = (timestamp) => {
    return new Date(timestamp*1000).toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  };
  
  const listMatch = (list1, list2) => {
    if (list1.length != list2.length) return false;
    for (let i in list1) {
      if (list1[i] != list2[i]) return false;
    }
    return true;
  }

  return useMemo(() => (
    <MDBox>
      {alert}
      {therapyDateSlider.options.length > 1 && (
        <MDBox p={2} mt={2} pb={0}>
          <div style={{ position: "relative" }}>
            <Slider
              ref={sliderRef}
              aria-label="TherapyDates"
              value={therapyDateSlider.active}
              getAriaValueText={(value) => {
                return new Date(value*1000).toLocaleDateString("en-US", {
                  month: "2-digit",
                  day: "2-digit",
                  year: "2-digit"
                });
              }}
              marks={therapyDateSlider.options.map((date,i) => {
                if (i > 0) {
                  const minScale = therapyDateSlider.options[therapyDateSlider.options.length-1] - therapyDateSlider.options[0];
                  if (date - therapyDateSlider.options[i-1] < minScale * 0.01) {
                    return { value: date, label: "" };
                  }
                }
                return { value: date, label: new Date(date*1000).toLocaleDateString("en-US", {
                  month: "2-digit", day: "2-digit", year: "2-digit"
                }) };
              })}
              valueLabelDisplay="on"
              valueLabelFormat={value =>
                new Date(value * 1000).toLocaleDateString("en-US", {
                  month: "2-digit",
                  day: "2-digit",
                  year: "2-digit"
                })
              }
              step={null}
              min={therapyDateSlider.options.length > 0 ? therapyDateSlider.options[0] : 0}
              max={therapyDateSlider.options.length > 0 ? therapyDateSlider.options[therapyDateSlider.options.length-1] : 0}
              onChange={(event, newValue) => {
                setTherapyDateSlider((state) => ({ ...state, active: newValue }));
              }}
              sx={{
                '& .MuiSlider-markLabel': {
                  transform: 'rotate(-45deg) translate(-50px, -40px)',
                  whiteSpace: 'nowrap',
                  fontSize: '0.85em',
                  minWidth: '40px',
                  textAlign: 'left',
                  display: "none"
                },
                '& .MuiSlider-mark': {
                  width: '4px',
                  height: '4px',
                  borderRadius: '50%',
                  backgroundColor: '#f53131ff',
                  marginLeft: '-6px',
                }
              }}
            />
            <div style={{
              position: "absolute",
              left: 0,
              top: 0,
              right: 0,
              bottom: 0,
              pointerEvents: "none",
            }}>
              {therapyDateSlider.options.map((date, i) => {
                const percent = sliderMax !== sliderMin ? ((date - sliderMin) / (sliderMax - sliderMin)) * 100 : 0;
                return (
                  <Tooltip
                    key={i}
                    title={formatMarkTooltip(date)}
                    placement="bottom"
                    interactive arrow
                    componentsProps={{
                      tooltip: {
                        sx: {
                          maxWidth: '700px',
                          whiteSpace: 'normal',
                        },
                      },
                    }}
                  >
                    <div
                      onClick={(e) => {
                        setTherapyDateSlider((state) => ({ ...state, active: date }));
                      }}
                      style={{
                        position: "absolute",
                        left: `${percent}%`,
                        top: "30px",
                        transform: "translateX(-50%)",
                        pointerEvents: "auto",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <div style={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        background: "#f53131",
                        boxShadow: "0 0 4px rgba(0,0,0,0.3)"
                      }} />
                    </div>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        </MDBox>
      )}

      {therapyTable.Date ? (
        <MDBox p={2} pt={0}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <MDBox p={2} pt={0}>
                <MDTypography variant={"h4"} fontWeight={"bold"}>
                  {"Therapy Configurations on " + new Date(therapyTable.Date*1000).toLocaleDateString("en-US", {
                    month: "2-digit",
                    day: "2-digit",
                    year: "2-digit"
                  })}
                </MDTypography>
              </MDBox>
            </Grid>
          
            {therapyTable.DefinedTherapies.map((config, g) => {
              let PreTherapy = [], PostTherapy = [];
              for (let h in therapyTable.Therapies) {
                for (let k in therapyTable.Therapies[h].Processed) {
                  if (therapyTable.Therapies[h].Processed[k].Device.Id != config.Device.Id) continue;
                  if (listMatch(therapyTable.Therapies[h].Processed[k].TherapyIds, config.Pre)) {
                    PreTherapy = [therapyTable.Therapies[h].Processed[k]];
                  }
                  if (listMatch(therapyTable.Therapies[h].Processed[k].TherapyIds, config.Post)) {
                    PostTherapy = [therapyTable.Therapies[h].Processed[k]];
                  }
                }
              }

              return <Grid item xs={12} key={config.Date+"_"+config.GroupId+"_"+config.Device.Id}>
                <Card p={2}>
                  <MDBox px={2} pt={1}>
                    <MDTypography variant={"h5"} >
                      {config.GroupName ? config.GroupName : config.GroupId.replace("GroupIdDef.", "").replace("_", " ")}{config.PercentUsage ? (" ("+(config.PercentUsage*100).toFixed(1)+"%)") : ""}
                    </MDTypography>
                  </MDBox>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <MDBox px={2}>
                        <Autocomplete selectOnFocus clearOnBlur disableClearable
                          renderInput={(params) => (
                            <TextField {...params} variant="standard" label={"Select Configuration as Active Pre-visit Group"}/>
                          )}
                          isOptionEqualToValue={(option, value) => {
                            return listMatch(option.TherapyIds, value.TherapyIds);
                          }}
                          renderOption={(props, option) => <li {...props}>{getTimeString(option.Date) + " " + option.Type + " [" + option.TherapyIds + "]"}</li>}
                          getOptionLabel={(option) => option ? getTimeString(option.Date) + " " + option.Type : ""}
                          value={therapyOptions.pre[g]}
                          options={therapyOptions.options.filter((a) => a.GroupId == config.GroupId && ["Pre-visit Therapy", "Past Therapy"].includes(a.Type))}
                          onChange={(event, newValue) => {
                            SessionController.query("/api/assignTherapyLabel", {
                              ParticipantId: participant_uid,
                              TimelineDate: therapyTable.Date,
                              GroupId: config.GroupId,
                              TherapyLabel: "Pre-visit Preferred",
                              TherapyIds: newValue ? newValue.TherapyIds : [],
                            }).then((response) => {
                              setTherapyTable((table) => {
                                table.DefinedTherapies[g] = {
                                  ...table.DefinedTherapies[g],
                                  Pre: newValue ? newValue.TherapyIds : [],
                                }
                                return {...table};
                              });
                              setTherapyOptions((state) => {
                                state.pre[g] = newValue;
                                return {...state};
                              });
                            }).catch((error) => {
                              SessionController.displayError(error, setAlert);
                            });
                          }}
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <MDBox px={2}>
                        <Autocomplete selectOnFocus clearOnBlur disableClearable
                          renderInput={(params) => (
                            <TextField {...params} variant="standard" label={"Select Configuration as Active Post-visit Group"}/>
                          )}
                          isOptionEqualToValue={(option, value) => {
                            return listMatch(option.TherapyIds, value.TherapyIds);
                          }}
                          renderOption={(props, option) => <li {...props}>{getTimeString(option.Date) + " " + option.Type + " [" + option.TherapyIds + "]"}</li>}
                          getOptionLabel={(option) => getTimeString(option.Date) + " " + option.Type}
                          value={therapyOptions.post[g]}
                          options={therapyOptions.options.filter((a) => a.GroupId == config.GroupId && ["Post-visit Therapy"].includes(a.Type))}
                          onChange={(event, newValue) => {
                            SessionController.query("/api/assignTherapyLabel", {
                              ParticipantId: participant_uid,
                              TimelineDate: therapyTable.Date,
                              GroupId: config.GroupId,
                              TherapyLabel: "Post-visit Preferred",
                              TherapyIds: newValue ? newValue.TherapyIds : [],
                            }).then((response) => {
                              setTherapyTable((table) => {
                                table.DefinedTherapies[g] = {
                                  ...table.DefinedTherapies[g],
                                  Post: newValue ? newValue.TherapyIds : [],
                                }
                                return {...table};
                              });
                              setTherapyOptions((state) => {
                                state.post[g] = newValue;
                                return {...state};
                              });
                            }).catch((error) => {
                              SessionController.displayError(error, setAlert);
                            });
                          }}
                        />
                      </MDBox>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      {getPreTherapySettingsBilateral(PreTherapy.length > 0 ? PreTherapy[0] : null)}
                    </Grid>
                    <Grid item xs={12} md={6}>
                      {getPostTherapySettingsBilateral(PostTherapy.length > 0 ? PostTherapy[0] : null)}
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
            })}
          </Grid>
        </MDBox>
      ) : null}
    </MDBox>
  ), [therapyTable, therapyOptions, device, therapyDateSlider, interleavingSwitch]);
}

export default TherapyModificationHistory;
