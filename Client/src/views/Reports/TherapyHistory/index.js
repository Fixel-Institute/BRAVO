/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { useNavigate } from "react-router-dom";

import {
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

import TabletAndroidIcon from '@mui/icons-material/TabletAndroid';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";
import TherapyHistoryFigure from "./TherapyHistoryFigure";
import ImpedanceHeatmap from "./ImpedanceHeatmap";
import ImpedanceHistory from "./ImpedanceHistory";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";
import MDButton from "components/MDButton";
import MDBadge from "components/MDBadge";
import TherapyHistoryTable from "./TherapyHistoryTable";

function TherapyHistory() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, language, report } = controller;

  const [data, setData] = React.useState({});
  const [therapyHistory, setTherapyHistory] = React.useState({TherapyModification: [], TherapyDevices: {}});
  const [therapyHistoryOld, setTherapyHistoryOld] = React.useState({});
  const [therapyDate, setTherapyDate] = React.useState({active: false, options: []});
  const [therapyConfigurations, setTherapyConfigurations] = React.useState([]);

  const [impedanceLogs, setImpedanceLogs] = React.useState({});
  const [impedanceMode, setImpedanceMode] = React.useState("Bipolar");
  const [dataToRender, setDataToRender] = React.useState(null);

  const [alert, setAlert] = React.useState(null);
  const [therapyTypes, setTherapyTypes] = React.useState([]);
  const [activeTab, setActiveTab] = React.useState(null);
  const [activeDevice, setActiveDevice] = React.useState(null);

  React.useEffect(() => {
    if (!participant_uid) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryTherapyHistory", {
        participant_uid: participant_uid
      }).then((response) => {
        setTherapyHistory(response.data);
        const TherapyDates = Object.keys(response.data.TherapyConfigurations);
        if (TherapyDates.length > 0) {
          setTherapyDate({active: TherapyDates[0], options: TherapyDates});
        }
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [participant_uid]);

  React.useEffect(() => {
    var therapyHistoryOld = {};
    var therapyTimestamp = Object.keys(data);
    therapyTimestamp = therapyTimestamp.map((value, index) => therapyTimestamp[therapyTimestamp.length - 1 - index]);

    var therapyTypes = [];

    for (var i in therapyTimestamp) {
      for (var j in data[therapyTimestamp[i]]) {
        if (!Object.keys(therapyHistoryOld).includes(data[therapyTimestamp[i]][j].DeviceID)) {
          therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID] = {Device: data[therapyTimestamp[i]][j].Device, Lead: null, Therapy: {}};
        }
        if (!Object.keys(therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Therapy).includes(data[therapyTimestamp[i]][j].TherapyType)) {
          therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType] = {};
          if (!therapyTypes.includes(data[therapyTimestamp[i]][j].TherapyType)) therapyTypes.push(data[therapyTimestamp[i]][j].TherapyType);
        }
        const dateString = new Date(data[therapyTimestamp[i]][j].TherapyDate*1000).toLocaleString(language, {dateStyle: "full"});
        if (!Object.keys(therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType]).includes(dateString)) {
          therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString] = [];
        }
        therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString].push(data[therapyTimestamp[i]][j]);
        therapyHistoryOld[data[therapyTimestamp[i]][j].DeviceID].Lead = data[therapyTimestamp[i]][j].LeadInfo;
      }
    }
    setActiveDevice(Object.keys(therapyHistoryOld)[0]);
    setTherapyTypes(therapyTypes);
    setActiveTab(therapyTypes[0]);
    setTherapyHistoryOld(therapyHistoryOld);
  }, [data, language]);

  const showPerceptAdaptiveSettings = (therapy, captureAmplitude, amplitudeThreshold) => {
    setAlert(
      <Dialog open={true} onClose={() => setAlert(null)}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Adaptive Configurations"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <MDBox px={2} pt={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"Adaptive Mode Configuration:"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("SINGLE_THRESHOLD_DIRECT") ? "Single Threshold" : ""} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("DUAL_THRESHOLD_DIRECT") ? "Dual Threshold" : ""} 
            </MDTypography>
          </MDBox>
          <MDBox px={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"Capture Amplitude:"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("SINGLE_THRESHOLD_DIRECT") ? captureAmplitude[1] : captureAmplitude[0]}
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("DUAL_THRESHOLD_DIRECT") ? captureAmplitude[1] : ""} 
            </MDTypography>
          </MDBox>
          <MDBox px={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"LFP Threshold:"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("SINGLE_THRESHOLD_DIRECT") ? amplitudeThreshold[1] : amplitudeThreshold[0]}
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("DUAL_THRESHOLD_DIRECT") ? amplitudeThreshold[1] : ""} 
            </MDTypography>
          </MDBox>
          <MDBox px={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"Detection Blanking:"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.DetectionBlankingDurationInMilliSeconds} {"ms"}
            </MDTypography>
          </MDBox>
          <MDBox px={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"Ramping Time (Up/Down):"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.RampUpTime} {"ms"} {"/"} {therapy.RampDownTime} {"ms"} 
            </MDTypography>
          </MDBox>
          <MDBox px={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"Threshold Onset Duration (Up/Down):"} 
            </MDTypography>
            <MDTypography variant="p" fontSize={12}>
              {therapy.Mode.endsWith("SINGLE_THRESHOLD_DIRECT") ? `${therapy.LowerThresholdOnsetInMilliSeconds} ms` : `${therapy.LowerThresholdOnsetInMilliSeconds} ms / ${therapy.UpperThresholdOnsetInMilliSeconds} ms`}
            </MDTypography>
          </MDBox>
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setAlert(null)}>{"Close"}</MDButton>
        </DialogActions>
      </Dialog>
    )
  }

  const showSummitAdaptiveSettings = (therapy) => {
    let powerChannel = {Ld0: [], Ld1: []};
    if (therapy.Adaptive.Detector.Ld0.detectionEnable > 0) {
      for (let i = 0; i < 8; i++) {
        if (therapy.Adaptive.Detector.Ld0.detectionInputs & (Math.pow(2, i))) {
          const LfpChan = parseInt(therapy.Adaptive.Power.Enabled[i][2]);
          const FreqResolution = therapy.Adaptive.Power.LfpConfig[LfpChan].SamplingRate / therapy.Adaptive.Power.NFFT;
          powerChannel.Ld0.push(therapy.Adaptive.Power.Enabled[i] + ` ${(therapy.Adaptive.Power.PowerBands[i][0]*FreqResolution).toFixed(2)}-${(therapy.Adaptive.Power.PowerBands[i][1]*FreqResolution).toFixed(2)}Hz`)
        }
      }
    }
    if (therapy.Adaptive.Detector.Ld1.detectionEnable > 0) {
      for (let i = 0; i < 8; i++) {
        if (therapy.Adaptive.Detector.Ld1.detectionInputs & (Math.pow(2, i))) {
          const LfpChan = parseInt(therapy.Adaptive.Power.Enabled[i][2]);
          const FreqResolution = therapy.Adaptive.Power.LfpConfig[LfpChan].SamplingRate / therapy.Adaptive.Power.NFFT;
          powerChannel.Ld1.push(therapy.Adaptive.Power.Enabled[i] + ` ${(therapy.Adaptive.Power.PowerBands[i][0]*FreqResolution).toFixed(2)}-${(therapy.Adaptive.Power.PowerBands[i][1]*FreqResolution).toFixed(2)}Hz`)
        }
      }
    }

    setAlert(
      <Dialog open={true} onClose={() => setAlert(null)}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Summit Adaptive Configurations"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <MDBox px={2} pt={2}>
            <MDTypography variant="h6" fontSize={15}>
              {"State Configurations:"} 
            </MDTypography>
            <Grid container>
              {therapy.Adaptive.Adaptive.State.map((state, index) => {
                return <Grid item xs={4} key={index}>
                  {state.prog0Amp < 255 ? state.prog0Amp/10 + " mA" : "Disabled"}
                </Grid>
              })}
            </Grid>
          </MDBox>
          {powerChannel.Ld0.length > 0 ? (
            <MDBox px={2} pt={1} display={"flex"} flexDirection={"column"}>
              <MDTypography variant="h6" fontSize={15}>
                {"Ld0 Channel Input:"} 
              </MDTypography>
              {powerChannel.Ld0.map((channel) => (
                <MDTypography key={channel} variant="p" fontSize={14}>
                  {channel} 
                </MDTypography>
              ))}
              <MDTypography variant="p" fontSize={14}>
                {"Thresholds: "} 
                {therapy.Adaptive.Detector.Ld0.biasTerm[0]} 
                {therapy.Adaptive.Detector.Ld0.biasTerm[0] == therapy.Adaptive.Detector.Ld0.biasTerm[1] ? "" : " / " + therapy.Adaptive.Detector.Ld0.biasTerm[1]} 
              </MDTypography>
              <MDTypography variant="p" fontSize={14}>
                {"Onset Duration: "} 
                {therapy.Adaptive.Detector.Ld0.onsetDuration * therapy.Adaptive.Detector.Ld0.updateRate * therapy.Adaptive.Power.Interval / 1000} {" sec"}
              </MDTypography>
              <MDTypography variant="p" fontSize={14}>
                {"Termination Duration: "} 
                {therapy.Adaptive.Detector.Ld0.terminationDuration * therapy.Adaptive.Detector.Ld0.updateRate * therapy.Adaptive.Power.Interval / 1000} {" sec"}
              </MDTypography>
            </MDBox>
          ) : null}
          {powerChannel.Ld1.length > 0 ? (
            <MDBox px={2} pt={1} display={"flex"} flexDirection={"column"}>
              <MDTypography variant="h6" fontSize={15}>
                {"Ld1 Channel Input:"} 
              </MDTypography>
              {powerChannel.Ld1.map((channel) => (
                <MDTypography key={channel} variant="p" fontSize={14}>
                  {channel} 
                </MDTypography>
              ))}
              <MDTypography variant="p" fontSize={14}>
                {"Thresholds:"} 
                {therapy.Adaptive.Detector.Ld1.biasTerm[0]} 
                {therapy.Adaptive.Detector.Ld1.biasTerm[0] == therapy.Adaptive.Detector.Ld1.biasTerm[1] ? "" : " / " + therapy.Adaptive.Detector.Ld1.biasTerm[1]} 
              </MDTypography>
              <MDTypography variant="p" fontSize={14}>
                {"Onset Duration: "} 
                {therapy.Adaptive.Detector.Ld1.onsetDuration * therapy.Adaptive.Detector.Ld1.updateRate * therapy.Adaptive.Power.Interval / 1000} {" sec"}
              </MDTypography>
              <MDTypography variant="p" fontSize={14}>
                {"Termination Duration: "} 
                {therapy.Adaptive.Detector.Ld1.terminationDuration * therapy.Adaptive.Detector.Ld1.updateRate * therapy.Adaptive.Power.Interval / 1000} {" sec"}
              </MDTypography>
            </MDBox>
          ) : null}
          <MDBox px={2}>
            
          </MDBox>
          <MDBox px={2}>
            
          </MDBox>
          <MDBox px={2}>
            
          </MDBox>
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setAlert(null)}>{"Close"}</MDButton>
        </DialogActions>
      </Dialog>
    )
  }

  const formatTherapySettings = (therapy, type, color) => {
    if (type == "Contacts") {
      if (therapy.Mode == "Interleaving") {
        return (
          therapy.Channel.map((program, index) => {
            return <MDTypography key={"program" + index.toString()} color={color} fontSize={12} style={{flexDirection: "row", paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
              {program.map((contact) => {
                if (!contact.Electrode.startsWith("ElectrodeDef")) {
                  return contact.Electrode + " ";
                }
              })}
            </MDTypography>
          })
        );
      } else {
        return (
          <MDBox style={{display: "flex", flexDirection: "row"}}>
            {therapy.Channel.map((contact) => {
              if (!contact.Electrode.startsWith("ElectrodeDef")) {
                if (contact.ElectrodeAmplitudeInMilliAmps) {
                  return <Tooltip key={contact.Electrode} title={contact.ElectrodeAmplitudeInMilliAmps + " mA"} placement="top">
                    <MDTypography fontSize={12} color={color} style={{paddingBottom: 0, paddingRight: 5, paddingTop: 0, marginBottom: 0}}>
                      {contact.Electrode + " "}
                    </MDTypography>
                  </Tooltip>
                } else {
                  return <MDTypography key={contact.Electrode} fontSize={12} color={color} style={{paddingBottom: 0, paddingRight: 5, paddingTop: 0, marginBottom: 0}}>
                    {contact.Electrode + " "}
                  </MDTypography>
                }
              }
            })}
          </MDBox>
        );
      }
    } else if (type == "Settings") {
      if (therapy.Mode == "Interleaving") {
        return (
          therapy.Channel.map((program, index) => {
            return (<MDTypography key={"program" + index.toString()} color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {therapy.Frequency[index]} {" Hz"} {therapy.PulseWidth[index]} {" μSec"} {therapy.Amplitude[index].toFixed(1)} {" "} {therapy.Unit[index]}
              </MDTypography>
            );
          })
        );
      } else {
        return (<MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
            {therapy.Frequency} {" Hz"} {therapy.PulseWidth} {" μSec"} {therapy.Amplitude.toFixed(1)} {" "} {therapy.Unit}
          </MDTypography>
        );
      }
    } else if (type == "BrainSense") {
      if (therapy.Mode == "BrainSense") {
        if ((therapy.LFPThresholds[0] == 20 && therapy.LFPThresholds[1] == 30 && therapy.CaptureAmplitudes[0] == 0 && therapy.CaptureAmplitudes[1] == 0) || !therapy.AdaptiveSetup) {
          return (
          <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
            <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
              {therapy.SensingSetup.FrequencyInHertz} {" Hz"} 
            </MDTypography>
            <MDBox display={"flex"} flexDirection={"column"} ml={2}>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {"Sense Only"}
              </MDTypography>
            </MDBox>
          </MDBox>
          );
        } else {
          return (
          <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
            <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
              {therapy.SensingSetup.FrequencyInHertz} {" Hz"} 
            </MDTypography>
            <MDBox display={"flex"} flexDirection={"column"} ml={2} style={{cursor: "pointer"}} onClick={() => {
              showPerceptAdaptiveSettings(therapy.AdaptiveSetup, therapy.CaptureAmplitudes, therapy.LFPThresholds);
            }}>
              {therapy.AdaptiveSetup.Bypass ? (
                <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                  {"Adaptive Sense Only"}
                </MDTypography>
              ) : (
                <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                  {therapy.AdaptiveSetup.Status === "ADBSStatusDef.RUNNING" ? "Adaptive Enabled" : ""}
                  {therapy.AdaptiveSetup.Status === "ADBSStatusDef.SUSPENDED" ? "Adaptive Suspended" : ""}
                  {therapy.AdaptiveSetup.Status === "ADBSStatusDef.DISABLED" ? "Adaptive Stim Only" : ""}
                </MDTypography>
              )}
            </MDBox>
          </MDBox>
          );
        }
      } else if (therapy.Mode == "SummitAdaptive") {
        if (therapy.Adaptive.Adaptive.Status != "EmbeddedActive") {
          return (<MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
              {"Adaptive Disabled"}
            </MDTypography>
          );
        } else {
          return (
            <MDBox display={"flex"} flexDirection={"column"} alignItems={"start"} style={{cursor: "pointer"}} onClick={() => {
              showSummitAdaptiveSettings(therapy);
            }}>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {therapy.Adaptive.Detector.Ld0.detectionEnable == 2 ? "LD0 Enabled" : ""}
              </MDTypography>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {therapy.Adaptive.Detector.Ld1.detectionEnable == 2 ? "LD1 Enabled" : ""}
              </MDTypography>
            </MDBox>
            );
        }
      } else {
        return (<MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
            {"BrainSense Disabled"}
          </MDTypography>
        );
      }
    }
  };

  const formatCyclingStim = (cycling) => {
    const percent = cycling.OnDurationInMilliSeconds / (cycling.OnDurationInMilliSeconds + cycling.OffDurationInMilliSeconds) * 100;
    return `${percent.toFixed(1)}% (${(cycling.OnDurationInMilliSeconds/1000).toFixed(1) + " " + dictionary.Time.Seconds[language]} : ${(cycling.OffDurationInMilliSeconds/1000).toFixed(1) + " " + dictionary.Time.Seconds[language]})`;
  };

  const onContactSelect = (point) => {
    let dataToRender = {};
    if (point.data.xaxis === "x") {
      // This is Left Side
      dataToRender.data = impedanceLogs.map((data) => {
        try {
          if (therapyHistoryOld[activeDevice].Device != data.device) return null;
          return {timestamps: data.session_date, value: impedanceMode === "Monopolar" ? data.log.Left[impedanceMode][point.y] : data.log.Left[impedanceMode][point.y][point.x]};
        } catch (error) {
          return null;
        }
      }).filter((value) => value);
      for (let i in therapyHistoryOld[activeDevice].Lead) {
        if (therapyHistoryOld[activeDevice].Lead[i].TargetLocation.startsWith("Left")) {
          dataToRender.title = `${therapyHistoryOld[activeDevice].Device} ${therapyHistoryOld[activeDevice].Lead[i].CustomName} `;
        }
      }
    } else {
      // This is Right Side
      dataToRender.data = impedanceLogs.map((data) => {
        try {
          if (therapyHistoryOld[activeDevice].Device != data.device) return null;
          return {timestamps: data.session_date, value: impedanceMode === "Monopolar" ? data.log.Right[impedanceMode][point.y] : data.log.Right[impedanceMode][point.y][point.x]};
        } catch (error) {
          return null;
        }
      }).filter((value) => value);
      for (let i in therapyHistoryOld[activeDevice].Lead) {
        if (therapyHistoryOld[activeDevice].Lead[i].TargetLocation.startsWith("Right")) {
          dataToRender.title = `${therapyHistoryOld[activeDevice].Device} ${therapyHistoryOld[activeDevice].Lead[i].CustomName} `;
        }
      }
    }

    if (impedanceMode === "Monopolar") {
      dataToRender.title += `Contact ${point.yaxis.ticktext.filter((value, index) => point.yaxis.tickvals[index] == point.y)[0]} `
    } else {
      dataToRender.title += `Contact ${point.yaxis.ticktext.filter((value, index) => point.yaxis.tickvals[index] == point.y)[0]}-${point.xaxis.ticktext.filter((value, index) => point.xaxis.tickvals[index] == point.x)[0]} `
    }

    dataToRender.point = point;
    setDataToRender(dataToRender);
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
                <TherapyHistoryFigure dataToRender={{TherapyModification: therapyHistory.TherapyModification, 
                                                    TherapyDevices: therapyHistory.TherapyDevices}} 
                  height={400} figureTitle={"TherapyHistoryLog"}/>
              </MDBox>
            </Card>
          </Grid>
          ) : null}

          <Grid item xs={6} sm={4}>
            <Tabs
              orientation="vertical"
              variant="scrollable"
              value={therapyDate.active}
              onChange={(event, newValue) => setTherapyDate({...therapyDate, active: newValue})}
              sx={{ borderRight: 1, borderColor: 'divider', maxHeight: "80vh" }}
            >
              {therapyDate.options.map((date) => {
                let dateString = new Date(parseFloat(date)*1000)
                return <Tab value={date} label={dateString.toDateString()}/>
              })}
            </Tabs>
          </Grid>
          
          {therapyDate.active ? (
            <Grid item xs={6} sm={8}>
              <TherapyHistoryTable therapyHistory={therapyHistory.TherapyConfigurations[therapyDate.active]} />
            </Grid>
          ) : null}

        </Grid>
      </MDBox>
    </DatabaseLayout>
  );
}

export default TherapyHistory;
