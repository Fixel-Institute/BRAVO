import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Box,
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

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import MDButton from "components/MDButton";
import MDBadge from "components/MDBadge";

function TherapyHistory() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [changeLogs, setChangeLogs] = React.useState({});
  const [data, setData] = React.useState({});
  const [therapyHistory, setTherapyHistory] = React.useState({});

  const [alert, setAlert] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState(null);
  const [activeDevice, setActiveDevice] = React.useState(null);

  React.useEffect(async () => {
    if (!patientID) {
      navigate("/dashboard", {replace: true});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.getTherapyHistory().then((response) => {
        setChangeLogs(response.data.TherapyChangeLogs);
        setData(response.data.TherapyConfigurations);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  React.useEffect(async () => {
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
          <MDTypography fontSize={12} color={color} style={{flexDirection: "row", paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
            {therapy.Channel.map((contact) => {
              if (!contact.Electrode.startsWith("ElectrodeDef")) {
                return contact.Electrode + " ";
              }
            })}
          </MDTypography>
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
    }
  };

  const formatCyclingStim = (cycling) => {
    const percent = cycling.OnDurationInMilliSeconds / (cycling.OnDurationInMilliSeconds + cycling.OffDurationInMilliSeconds);
    return `${percent.toFixed(1)}% (${(cycling.OnDurationInMilliSeconds/1000).toFixed(0) + " " + dictionary.Time.Seconds[language]} : ${(cycling.OffDurationInMilliSeconds/1000).toFixed(0) + " " + dictionary.Time.Seconds[language]})`;
  };

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
        </Grid>
      </MDBox>
    </DatabaseLayout>
  );
}

export default TherapyHistory;
