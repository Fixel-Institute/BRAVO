import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Box,
  Backdrop,
  IconButton,
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
        console.log(response.data.Impedance)
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
          therapyHistory[data[therapyTimestamp[i]][j].DeviceID] = {Device: data[therapyTimestamp[i]][j].Device, Therapy: {"Past Therapy": {}, "Pre-visit Therapy": {}, "Post-visit Therapy": {}}};
        }
        const dateString = new Date(data[therapyTimestamp[i]][j].TherapyDate*1000).toLocaleDateString(language, {dateStyle: "full"});
        if (!Object.keys(therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType]).includes(dateString)) {
          therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString] = [];
        }
        therapyHistory[data[therapyTimestamp[i]][j].DeviceID].Therapy[data[therapyTimestamp[i]][j].TherapyType][dateString].push(data[therapyTimestamp[i]][j]);
      }
    }
    setActiveDevice(Object.keys(therapyHistory)[0]);
    setActiveTab("Past Therapy");
    setTherapyHistory(therapyHistory);
  }, [data, language]);

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
        if (therapy.LFPThresholds[0] == 20 && therapy.LFPThresholds[1] == 30 && therapy.CaptureAmplitudes[0] == 0 && therapy.CaptureAmplitudes[1] == 0) {
          return (
          <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
            <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
              {therapy.SensingSetup.FrequencyInHertz} {" Hz"} 
            </MDTypography>
            <MDBox display={"flex"} flexDirection={"column"} ml={2}>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {"Adaptive DBS Disabled"}
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
            <MDBox display={"flex"} flexDirection={"column"} ml={2}>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {"Threshold at: "} {`[${therapy.LFPThresholds[0]} , ${therapy.LFPThresholds[1]}]`}
              </MDTypography>
              <MDTypography color={color} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {"Stimulation Range at: "} {`[${therapy.CaptureAmplitudes[0]} , ${therapy.CaptureAmplitudes[1]}]`}
              </MDTypography>
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

    } else {
      // This is Right Side
      dataToRender.data = impedanceLogs.map((data) => {
        try {
          if (therapyHistory[activeDevice].Device != data.device) return null;
          return {timestamps: data.session_date, value: impedanceMode === "Monopolar" ? data.log.Left[impedanceMode][point.y] : data.log.Left[impedanceMode][point.y][point.x]};
        } catch (error) {
          return null;
        }
      }).filter((value) => value);
    }

    dataToRender.point = point;

    setAlert(<>
      <Backdrop
        sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
        open={true}
        onClick={() => setAlert(null)}
      >
        <Card>
          <MDBox p={5} display={"flex"} alignItems={"center"} flexDirection={"column"} style={{minWidth: 800}}>
            <ImpedanceHistory dataToRender={dataToRender} height={300} figureTitle={"Impedance History"} />
          </MDBox>
        </Card>
      </Backdrop>
    </>);
  }

  return (
    <DatabaseLayout>
      {alert}
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
                      const therapyList = therapyHistory[activeDevice].Therapy[activeTab][key];
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
                        onChange={(event, value) => setImpedanceMode(value)}
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
