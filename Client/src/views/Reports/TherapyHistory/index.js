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
import { dictionary } from "assets/translation.js";
import MDButton from "components/MDButton";
import MDBadge from "components/MDBadge";

function TherapyHistory() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = React.useState({});
  const [changeLogs, setChangeLogs] = React.useState({});
  const [therapyHistory, setTherapyHistory] = React.useState({});
  const [impedanceLogs, setImpedanceLogs] = React.useState({});
  const [impedanceMode, setImpedanceMode] = React.useState("Bipolar");
  const [dataToRender, setDataToRender] = React.useState(null);

  const [alert, setAlert] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState(null);
  const [activeDevice, setActiveDevice] = React.useState(null);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryTherapyHistory", {id: patientID}).then((response) => {
        setChangeLogs(response.data.TherapyChangeLogs);
        setData(response.data.TherapyConfigurations);
        setImpedanceLogs(response.data.Impedance);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  React.useEffect(() => {
    var therapyHistory = {};
    var therapyTimestamp = Object.keys(data);
    therapyTimestamp = therapyTimestamp.map((value, index) => therapyTimestamp[therapyTimestamp.length - 1 - index]);
    for (var i in therapyTimestamp) {
      for (var j in data[therapyTimestamp[i]]) {
        if (!Object.keys(therapyHistory).includes(data[therapyTimestamp[i]][j].DeviceID)) {
          therapyHistory[data[therapyTimestamp[i]][j].DeviceID] = {Device: data[therapyTimestamp[i]][j].Device, Lead: null, Therapy: {"Past Therapy": {}, "Pre-visit Therapy": {}, "Post-visit Therapy": {}}};
        }
        const dateString = new Date(data[therapyTimestamp[i]][j].TherapyDate*1000).toLocaleDateString(language, {dateStyle: "full"});
        if (!Object.keys(therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType]).includes(dateString)) {
          therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString] = [];
        }
        therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString].push(data[therapyTimestamp[i]][j]);
        therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Lead = data[therapyTimestamp[i]][j].LeadInfo;
      }
    }
    setActiveDevice(Object.keys(therapyHistory)[0]);
    setActiveTab("Past Therapy");
    setTherapyHistory(therapyHistory);
  }, [data, language]);

  const showAdaptiveSettings = (therapy) => {
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
            <MDBox display={"flex"} flexDirection={"column"} ml={2} style={{cursor: "pointer"}} onClick={() => {
              showAdaptiveSettings(therapy.AdaptiveSetup);
            }}>
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
              showAdaptiveSettings(therapy.AdaptiveSetup);
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
          if (therapyHistory[activeDevice].Device != data.device) return null;
          return {timestamps: data.session_date, value: impedanceMode === "Monopolar" ? data.log.Left[impedanceMode][point.y] : data.log.Left[impedanceMode][point.y][point.x]};
        } catch (error) {
          return null;
        }
      }).filter((value) => value);
      for (let i in therapyHistory[activeDevice].Lead) {
        if (therapyHistory[activeDevice].Lead[i].TargetLocation.startsWith("Left")) {
          dataToRender.title = `${therapyHistory[activeDevice].Device} ${therapyHistory[activeDevice].Lead[i].CustomName} `;
        }
      }
    } else {
      // This is Right Side
      dataToRender.data = impedanceLogs.map((data) => {
        try {
          if (therapyHistory[activeDevice].Device != data.device) return null;
          return {timestamps: data.session_date, value: impedanceMode === "Monopolar" ? data.log.Right[impedanceMode][point.y] : data.log.Right[impedanceMode][point.y][point.x]};
        } catch (error) {
          return null;
        }
      }).filter((value) => value);
      for (let i in therapyHistory[activeDevice].Lead) {
        if (therapyHistory[activeDevice].Lead[i].TargetLocation.startsWith("Right")) {
          dataToRender.title = `${therapyHistory[activeDevice].Device} ${therapyHistory[activeDevice].Lead[i].CustomName} `;
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
      <Dialog 
        sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
        PaperProps={{
          sx: { minWidth: 800 }
        }}
        open={Boolean(dataToRender)}
        onClose={() => setDataToRender(null)}
      >
        <MDBox p={5} display={"flex"} alignItems={"center"} flexDirection={"column"} >
          <ImpedanceHistory dataToRender={dataToRender} height={400} figureTitle={"Impedance History"} />
        </MDBox>
      </Dialog>
      <MDBox py={2}>
        <Grid container spacing={2}>
          {changeLogs.length > 0 ? (
          <Grid item xs={12}>
            <Card>
              <MDBox p={2}>
                  <TherapyHistoryFigure dataToRender={changeLogs} height={400} figureTitle={"TherapyHistoryLog"}/>
              </MDBox>
            </Card>
          </Grid>
          ) : null} 
          <Grid item xs={12}>
            {Object.keys(therapyHistory).length > 0 ? (
              <Card>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      <MDTypography variant="h5" fontWeight="bold" fontSize={24}>
                        {dictionary.TherapyHistory.Table.TableTitle[language]}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12} md={3} display={"flex"} flexDirection={{
                    xs: "row",
                    md: "column"
                  }}>
                    {Object.keys(therapyHistory).map((key) => (
                      <MDBox key={key} p={2}>
                        <MDButton variant={activeDevice == key ? "contained" : "outlined"} color="info" fullWidth onClick={() => setActiveDevice(key)}>
                          <TabletAndroidIcon sx={{marginRight: 1}} />
                          <MDTypography variant="h5" fontWeight="bold" fontSize={15} color={activeDevice == key ? "white" : "black"}>
                            {therapyHistory[key].Device}
                          </MDTypography>
                        </MDButton>
                      </MDBox>
                    ))}
                  </Grid>
                  <Grid item xs={12} md={9}>
                    <MDBox display={"flex"} flexDirection={"row"}>
                      {["Past Therapy", "Pre-visit Therapy", "Post-visit Therapy"].map((type) => (
                      <MDBox key={type} p={2}>
                        <MDButton variant={activeTab == type ? "contained" : "outlined"} color="warning" onClick={() => setActiveTab(type)} sx={{borderRadius: 30}}>
                          <TabletAndroidIcon sx={{marginRight: 1}} />
                          <MDTypography variant="h5" fontWeight="bold" fontSize={15} color={activeDevice == type ? "white" : "black"}>
                            {dictionary.TherapyHistory.Table[type][language]}
                          </MDTypography>
                        </MDButton>
                      </MDBox>
                      ))}
                    </MDBox>
                    {Object.keys(therapyHistory[activeDevice].Therapy[activeTab]).map((key) => {
                      let therapyList = [];
                      if (activeTab === "Pre-visit Therapy") {
                        let availableTimestamp = therapyHistory[activeDevice].Therapy[activeTab][key].map((group) => group.TherapyDate);
                        let firstSession = Math.min(...availableTimestamp);
                        therapyList = therapyHistory[activeDevice].Therapy[activeTab][key].filter((group) => group.TherapyDate == firstSession)
                      } else if (activeTab === "Post-visit Therapy") {
                        let availableTimestamp = therapyHistory[activeDevice].Therapy[activeTab][key].map((group) => group.TherapyDate);
                        let lastSession = Math.max(...availableTimestamp);
                        therapyList = therapyHistory[activeDevice].Therapy[activeTab][key].filter((group) => group.TherapyDate == lastSession)
                      } else {
                        therapyList = therapyHistory[activeDevice].Therapy[activeTab][key];
                      }
                      let leadInfo = therapyList[0].LeadInfo;

                      return (
                      <MDBox key={key} pr={2} pb={2}>
                        <Accordion>
                          <AccordionSummary
                            expandIcon={<ExpandMoreIcon />}
                          >
                            <MDTypography>
                              {key}
                            </MDTypography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} px={2}>
                              {leadInfo.map((lead) => {
                                if (lead.TargetLocation.startsWith("Left")) {
                                  return <MDBox key={lead.TargetLocation} display={"flex"} flexDirection={"row"} alignItems={"center"} px={2}>
                                    <MDBadge badgeContent="L" color={"info"} size={"xs"} container sx={{marginRight: 1}} />
                                    <MDBox>
                                      <MDTypography fontWeight={"medium"} fontSize={15} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                        {lead.CustomName}
                                      </MDTypography>
                                    </MDBox>
                                  </MDBox>
                                } else {
                                  return <MDBox key={lead.TargetLocation} display={"flex"} flexDirection={"row"} alignItems={"center"} px={2}>
                                    <MDBadge badgeContent="R" color={"error"} size={"xs"} container sx={{marginRight: 1}} />
                                    <MDBox>
                                      <MDTypography fontWeight={"medium"} fontSize={15} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                        {lead.CustomName}
                                      </MDTypography>
                                    </MDBox>
                                  </MDBox>
                                }
                              })}
                            </MDBox>
                            <Table>
                              <TableBody>
                                {therapyList.map((therapy) => {
                                  return <TableRow key={therapy.LogID}>
                                    <TableCell>
                                      <MDTypography fontWeight={"bold"} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                        {therapy.Overview.GroupName} {" "} {therapy.Overview.DutyPercent}
                                      </MDTypography>
                                      <MDTypography fontWeight={"medium"} fontSize={10} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                        {new Date(therapy.TherapyDate*1000).toLocaleString(language)}
                                      </MDTypography>
                                    </TableCell>
                                    <TableCell>
                                      {therapy.Therapy.LeftHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="L" color={"info"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.LeftHemisphere, "Contacts", "info")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                      {therapy.Therapy.RightHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="R" color={"error"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.RightHemisphere, "Contacts", "error")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                    </TableCell>
                                    <TableCell>
                                      {therapy.Therapy.LeftHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="L" color={"info"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.LeftHemisphere, "Settings", "info")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                      {therapy.Therapy.RightHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="R" color={"error"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.RightHemisphere, "Settings", "error")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                    </TableCell>
                                    <TableCell>
                                      {therapy.Therapy.LeftHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="L" color={"info"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.LeftHemisphere, "BrainSense", "info")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                      {therapy.Therapy.RightHemisphere ? (
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <MDBadge badgeContent="R" color={"error"} size={"xs"} container sx={{marginRight: 1}} />
                                          <MDBox>
                                            {formatTherapySettings(therapy.Therapy.RightHemisphere, "BrainSense", "error")}
                                          </MDBox>
                                        </MDBox>
                                      ) : null}
                                    </TableCell>
                                    <TableCell>
                                      <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          {therapy.Therapy.GroupSettings ? (
                                          <MDBox>
                                            {therapy.Therapy.GroupSettings.Cycling ? therapy.Therapy.GroupSettings.Cycling.Enabled ? (
                                              <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                                {dictionary.TherapyHistory.Table.CyclingOn[language]}
                                              </MDTypography>
                                            ) : null : null}
                                            {therapy.Therapy.GroupSettings.Cycling ? therapy.Therapy.GroupSettings.Cycling.Enabled ? (
                                              <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                                {formatCyclingStim(therapy.Therapy.GroupSettings.Cycling)}
                                              </MDTypography>
                                            ) : (
                                              <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                                {dictionary.TherapyHistory.Table.CyclingOff[language]}
                                              </MDTypography>
                                            ) : null}
                                          </MDBox>
                                          ) : (
                                            <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                                              {dictionary.WarningMessage.NoData[language]}
                                            </MDTypography>
                                          )}
                                      </MDBox>
                                    </TableCell>
                                  </TableRow>
                                })}
                              </TableBody>
                            </Table>
                          </AccordionDetails>
                        </Accordion>
                      </MDBox>
                      )
                    })}
                  </Grid>
                </Grid>
              </Card>
            ) : null}
          </Grid>
          {impedanceLogs.length > 0 ? (
            <Grid item xs={12}>
              <Card>
                <Grid container spacing={1}>
                  <Grid item xs={12}>
                    <MDBox p={2} style={{display: "flex", justifyContent: "space-between"}}>
                      <MDTypography variant="h5" fontWeight="bold" fontSize={24}>
                        {dictionary.TherapyHistory.Table.ImpedanceTable[language]}
                      </MDTypography>
                      <ToggleButtonGroup
                        color="info"
                        value={impedanceMode}
                        exclusive
                        onChange={(event, value) => {
                          if (value) setImpedanceMode(value);
                        }}
                      >
                        <ToggleButton value="Bipolar">
                          <MDTypography variant="p" fontWeight="bold" fontSize={15}>
                            {"Bipolar"}
                          </MDTypography>
                        </ToggleButton>
                        <ToggleButton value="Monopolar">
                          <MDTypography variant="p" fontWeight="bold" fontSize={15}>
                            {"Monopolar"}
                          </MDTypography>
                        </ToggleButton>
                      </ToggleButtonGroup>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      <ImpedanceHeatmap dataToRender={impedanceLogs.filter((log) => {
                        if (Object.keys(therapyHistory).includes(activeDevice)) {
                          return therapyHistory[activeDevice].Device == log.device;
                        } 
                        return false;
                      })} logType={impedanceMode} onContactSelect={onContactSelect} height={600} figureTitle={dictionary.TherapyHistory.Table.ImpedanceTable[language]} />
                    </MDBox>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
          ) : null}
        </Grid>
      </MDBox>
    </DatabaseLayout>
  );
}

export default TherapyHistory;
