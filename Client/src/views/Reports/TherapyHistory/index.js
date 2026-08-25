/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Autocomplete,
  Box,
  Backdrop,
  IconButton,
  Dialog,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  Grid,
  Tabs,
  Tab,
  Table,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
} from "@mui/material"

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import LoadingProgress from "components/LoadingProgress";
import FormField from "components/MDInput/FormField.js";
import MDButton from "components/MDButton";
import MDBadge from "components/MDBadge";

import TherapyHistoryTable from "./TherapyHistoryTable";
import TherapyModificationHistory from "./TherapyModificationHistory";

import DatabaseLayout from "layouts/DatabaseLayout";
import TherapyHistoryFigure from "./TherapyHistoryFigure";
import ImpedanceHeatmap from "./ImpedanceHeatmap";
import ImpedanceHistory from "./ImpedanceHistory";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapyHistory() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { language, report } = controller;

  const [data, setData] = React.useState({});
  const [therapyHistory, setTherapyHistory] = React.useState({TherapyModification: [], TherapyDevices: []});
  const [therapyHistoryOld, setTherapyHistoryOld] = React.useState({});
  const [therapyDate, setTherapyDate] = React.useState({active: false, options: []});
  const [therapyConfigurations, setTherapyConfigurations] = React.useState([]);

  const [therapyMetadata, setTherapyMetadata] = React.useState({DBSDevices: [], TherapyVisitDates: []});
  const [therapyGroups, setTherapyGroups] = React.useState([]);

  const [impedanceLogs, setImpedanceLogs] = React.useState([]);
  const [impedanceMode, setImpedanceMode] = React.useState({show: false, history: [], config: null});
  const [availableDevices, setAvailableDevices] = React.useState({active: "", options: []});
  const [therapyConfig, setTherapyConfig] = React.useState({show: false, config: null});
  const [currentTherapy, setCurrentTherapy] = React.useState({show: false, configs: []});

  const [alert, setAlert] = React.useState(null);
  const [therapyTypes, setTherapyTypes] = React.useState([]);
  const [activeTab, setActiveTab] = React.useState(null);
  const [activeDevice, setActiveDevice] = React.useState(null);

  const { participant_uid } = useParams();

  React.useEffect(() => {
    if (!participant_uid) {
      navigate("/database", {replace: false});
      return
    }
    setContextState(dispatch, "report", "GeneralReports");

    const queryTherapyHistory = async () => {
      setAlert(<LoadingProgress/>);
      try {
        const response = await SessionController.query("/api/queryTherapyHistory", {
          ParticipantId: participant_uid
        });
        let availableDevices = [];
        for (let i in response.data.TherapyDevices) {
          if (!availableDevices.includes(response.data.TherapyDevices[i].Heritage)) {
            availableDevices.push(response.data.TherapyDevices[i].Heritage);
          }
        }
        setAvailableDevices({active: availableDevices[0], options: availableDevices});
        setImpedanceLogs(response.data.DeviceImpedance);
        setTherapyHistory(response.data);

        const metadataResponse = await SessionController.query("/api/v2/queryTherapyHistory", {
          ParticipantId: participant_uid,
          RequestType: "Metadata"
        });
        setTherapyMetadata(metadataResponse.data);
        const groupResponse = await SessionController.query("/api/v2/queryTherapyHistory", {
          ParticipantId: participant_uid,
          RequestType: "TherapyGroup"
        });
        setTherapyGroups(groupResponse.data);
        
      } catch (error) {
        SessionController.displayError(error, setAlert);
      } finally {
        setAlert(null);
      }
    }

    queryTherapyHistory();

  }, [participant_uid]);

  React.useEffect(() => {
    let UniqueDateStrings = [];
    let TherapyConfigurations = {};
    let DuplicateCheck = {};
    for (let i in therapyHistory.TherapyConfiguration) {
      for (let j in therapyHistory.TherapyConfiguration[i].History) {
        const dateString = new Date(therapyHistory.TherapyConfiguration[i].History[j].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(therapyHistory.TherapyConfiguration[i].History[j].Timezone),
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          timeZoneName: "longGeneric"
        })
        if (!UniqueDateStrings.map((a)=>a.label).includes(dateString)) {
          UniqueDateStrings.push({
            label: dateString,
            value: therapyHistory.TherapyConfiguration[i].History[j].Date
          });
          TherapyConfigurations[dateString] = [];
          DuplicateCheck[dateString] = [];
        }

        const fullDescriptor = JSON.stringify({
          ...therapyHistory.TherapyConfiguration[i].History[j],
          Id: "", Date: "", Percent: ""
        });

        if (!DuplicateCheck[dateString].includes(fullDescriptor)) {
          DuplicateCheck[dateString].push(fullDescriptor);
          TherapyConfigurations[dateString].push({
            ...therapyHistory.TherapyConfiguration[i].History[j],
            Device: therapyHistory.TherapyConfiguration[i].Device,
          })
        }
        
      }
    }
    UniqueDateStrings = UniqueDateStrings.sort((a,b) => b.value - a.value).map((a) => a.label)
    
    if (UniqueDateStrings.length > 0) {
      setTherapyConfigurations(TherapyConfigurations)
      setTherapyDate({
        active: UniqueDateStrings[0],
        options: UniqueDateStrings
      })
    } else {
      setTherapyConfigurations({})
      setTherapyDate({
        active: null,
        options: []
      })
    }

  }, [therapyHistory, language]);

  const translateMedtronicAdaptiveString = (string) => {
    if (string === "AdaptiveModeDef.SINGLE_THRESHOLD_DIRECT") {
      return "Single Threshold"
    } else if (string === "AdaptiveModeDef.DUAL_THRESHOLD_DIRECT" ) {
      return "Dual Threshold"
    } else {
      return string
    }
  }

  const formatConfigurationTable = (config) => {
    if (config.StimulationType === "BrainSense") {
      return (
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Grid container spacing={0}>
              <Grid item xs={12}>
                <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                  {"Sensing Frequency: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.SensingSetup.FrequencyInHertz} {" Hz"}</b>
                </MDTypography>
              </Grid>
              <Grid item xs={12}>
                <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                  {"Averaging Duration: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.SensingSetup.AveragingDurationInMilliSeconds} {" milliseconds"}</b>
                </MDTypography>
              </Grid>
              {therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[0] != therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[1] ? (
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Amplitude Threshold: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[0]}
                    {" - "}{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.AmplitudeThreshold[1]}
                    {" mA"}</b>
                  </MDTypography>
                </Grid>
              ) : null}
            </Grid>
          </Grid>
          {therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Type === "Medtronic Adaptive" ? (
            <Grid item xs={12} pt={5}>
              <Grid container spacing={0}>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Threshold Mode: "}<b>{translateMedtronicAdaptiveString(therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.Mode)}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Capture Threshold: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.CaptureAmplitudes[0]}
                    {" - "}{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.CaptureAmplitudes[1]}
                    {" mA"}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"LFP at Capture Threshold: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.MeasuredLFP[0]}
                    {" - "}{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.MeasuredLFP[1]}
                    {" A.U."}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Final Threshold: "}<b>{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.LFPThresholds[0]}
                    {" - "}{therapyConfig.config.AdaptiveSettings[0].RecordingConfiguration.Config.Thresholds.LFPThresholds[1]}
                    {" A.U."}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Detection Blanking: "}<b>{therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.DetectionBlankingDurationInMilliSeconds} {" milliseconds"}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Lower Onset Duration: "}<b>{therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.LowerThresholdOnsetInMilliSeconds} {" milliseconds"}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Upper Onset Duration: "}<b>{therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.UpperThresholdOnsetInMilliSeconds} {" milliseconds"}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Ramp-up Time: "}<b>{therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.RampUpTime} {" milliseconds"}</b>
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant={"p"} fontSize={18} fontFamily={"lato"}>
                    {"Ramp-down Time: "}<b>{therapyConfig.config.AdaptiveSettings[0].StimulationConfiguration.Config.RampDownTime} {" milliseconds"}</b>
                  </MDTypography>
                </Grid>
              </Grid>
            </Grid>
          ) : null}
        </Grid>
      )
    }

    return <></>
  }

  const exportTherapyHistory = (raw) => {
    if (raw) {
      let downloader = document.createElement('a');
      downloader.href = SessionController.getDownloadLink("/api/downloadData", {
        ParticipantId: participant_uid,
        CacheType: "queryTherapyHistory",
        RequestType: "Raw"
      });
      downloader.target = '_blank';
      downloader.click();
    } else {
      for (let type of ["TherapyHistory", "TherapyModification"]) {
        let downloader = document.createElement('a');
        downloader.href = SessionController.getDownloadLink("/api/downloadData", {
          ParticipantId: participant_uid,
          CacheType: "queryTherapyHistory",
          RequestType: type
        });
        downloader.target = '_blank';
        downloader.click();
      }
    }
  }

  return (
    <DatabaseLayout>
      {alert}
      <MDBox py={2}>
        <Grid container spacing={2}>
          {therapyHistory.TherapyModification.length > 0 ? (
          <Grid item xs={12}>
            <Card>
              <MDBox p={2}>
                <TherapyHistoryFigure dataToRender={therapyHistory} 
                  onTimeClick={(time, group) => {
                    let configs = {
                      Pre: {},
                      Post: {}
                    };
                    for (let i in therapyHistory.TherapyTimeline) {
                      if (therapyHistory.TherapyTimeline[i].Date < time) {
                        for (let j in therapyHistory.TherapyTimeline[i].DefinedTherapies) {
                          if (therapyHistory.TherapyTimeline[i].DefinedTherapies[j].GroupId == group) {
                            configs.Post = therapyHistory.TherapyTimeline[i].DefinedTherapies[j];
                          }
                        }
                      } else if (!configs.Pre.Date) {
                        for (let j in therapyHistory.TherapyTimeline[i].DefinedTherapies) {
                          if (therapyHistory.TherapyTimeline[i].DefinedTherapies[j].GroupId == group) {
                            configs.Pre = therapyHistory.TherapyTimeline[i].DefinedTherapies[j];
                          }
                        }
                      }
                    }
                    
                    setCurrentTherapy({configs: configs, show: true});
                  }}
                  height={400} figureTitle={"TherapyHistoryLog"}/>
              </MDBox>
            </Card>
          </Grid>
          ) : null}

          <Grid item xs={12}>
            <Card>
              <MDBox p={2} fullWidth >
                <Autocomplete
                  value={availableDevices.active}
                  options={availableDevices.options}   
                  onChange={(event, value) => setAvailableDevices({...availableDevices, active: value})}
                  renderOption={(props, option) => <li {...props}>{option}</li>}
                  renderInput={(params) => (
                    <FormField
                      {...params}
                      label={"Select Percept Device"}
                      InputLabelProps={{ shrink: true }}
                    />
                  )}
                />
              </MDBox>
              <MDBox p={2}>
                <ImpedanceHeatmap 
                  onContactSelect={(index) => {
                    setImpedanceMode({
                      show: true,
                      history: impedanceLogs.filter((a) => a.DeviceHeritage == availableDevices.active && a.Recording.length > 0 && a.Recording[0].Metadata[index.curveNumber == 0 ? "Left" : "Right"]).map((a) => {
                        if (a.Recording[0].Metadata[index.curveNumber == 0 ? "Left" : "Right"]["Bipolar"].length < index.data.x.length) {
                          return {
                            date: a.Date,
                            data: null
                          }
                        }

                        return {
                          date: a.Date,
                          data: a.Recording[0].Metadata[index.curveNumber == 0 ? "Left" : "Right"]["Bipolar"][index.y][index.x]
                        }
                      }),
                      config: (index.curveNumber == 0 ? "Left" : "Right") + " Hemisphere Contact "
                    });
                  }}
                  dataToRender={impedanceLogs.filter((a) => a.DeviceHeritage == availableDevices.active && a.Recording.length > 0)} 
                  height={600} logType={"Bipolar"} figureTitle={"Impedance Heatmap - "+availableDevices.active}/>
              </MDBox>
            </Card>
          </Grid>
          
          <Grid item xs={12}>
            <MDBox display={"flex"} justifyContent={"space-between"}>
              <MDButton size="large" variant="contained" color="info" style={{marginBottom: 3}} onClick={() => exportTherapyHistory(false)}>
                {"Export CSV"}
              </MDButton>
              <MDButton size="large" variant="contained" color="info" style={{marginBottom: 3}} onClick={() => exportTherapyHistory(true)}>
                {"Export Raw"}
              </MDButton>
            </MDBox>
          </Grid>
          
          <Grid item xs={12}>
            <MDBox>
              <TherapyModificationHistory therapyHistoryRaw={therapyGroups} availableDevices={therapyMetadata.DBSDevices} device={availableDevices.active} visitDates={therapyMetadata.TherapyVisitDates} viewConfigurationTable={() => {}} />
            </MDBox>
          </Grid>
        </Grid>
      </MDBox>

      <Dialog open={impedanceMode.show} onClose={() => setImpedanceMode({show: false, config: null})} maxWidth={"md"} fullWidth={true}>
        <DialogContent>
          <MDBox p={2}>
            <ImpedanceHistory dataToRender={impedanceMode.history} height={500} figureTitle={"Impedance History - " + impedanceMode.config}/>
          </MDBox>
        </DialogContent>
        <DialogActions>
          <MDButton variant="text" color="info" onClick={() => setImpedanceMode({show: false, config: null})}>
            {"Close"}
          </MDButton>
        </DialogActions>
      </Dialog>
    </DatabaseLayout>
  );
}

export default TherapyHistory;
