/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";

import {
  Card,
  Collapse,
  Grid,
  Dialog,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";

import { formatStimulationChannel } from "database/helper-function";
import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SessionOverview() {
  const [controller, dispatch] = usePlatformContext();
  const { user, patientID, language } = controller;

  const [alert, setAlert] = useState(null);
  const [availableSessions, setAvailableSessions] = useState([]);

  const [sessionOverview, setSessionOverview] = useState(null);
  const [showSessionLists, setShowSessionLists] = useState(true);

  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [patients, setPatients] = useState([]);
  const [uploadInterface, setUploadInterface] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    SessionController.query("/api/querySessionOverview", {
      id: patientID
    }).then((response) => {
      setAvailableSessions(response.data.AvailableSessions.sort((a,b) => b.SessionTimestamp - a.SessionTimestamp))
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const deleteSession = (id) => {
    SessionController.query("/api/deleteSessionFiles", {
      patientId: patientID,
      deleteSession: id,
    }).then((response) => {
      setAvailableSessions(availableSessions.filter((session) => session.SessionID != id))
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };
  
  const formatForEMR = (id) => {
    SessionController.query("/api/extractSessionEMR", {
      id: patientID,
      sessionId: id,
    }).then((response) => {
      setSessionOverview(response.data);
      setShowSessionLists(false);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const formatTherapyGroup = (group) => {
    return <MDBox key={group.GroupId} mb={1} mt={2} lineHeight={1}>
      <MDBox mb={0} lineHeight={1}>
        <MDTypography variant="p" fontSize={15} fontWeight={"medium"} style={{marginBottom: 0}}>
          {group.GroupName === "" ? group.GroupId.replace("GroupIdDef.GROUP_","Group ") : group.GroupName}{" "}
        </MDTypography>
        <MDTypography variant="p" fontSize={15} fontWeight={"medium"} style={{marginBottom: 0}}>
          {group.DutyPercent ? group.DutyPercent : group.ActiveGroup ? "(Active)" : ""}{": "}
        </MDTypography>
      </MDBox>
      <MDBox mb={0} lineHeight={1}>
        {group.LeftHemisphere ? <>
          {group.LeftHemisphere.Mode === "Interleaving" ? <>
            {[0,1].map((index) => {
              return <MDBox key={index} mb={0} lineHeight={1}>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {"["}{dictionary.SessionOverview.LeftHemisphere[language]}{"] "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {formatStimulationChannel(group.LeftHemisphere.Channel[index]).map((channel) => {
                    return channel + " ";
                  })}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.LeftHemisphere.Frequency[index]}{" "}{dictionary.FigureStandardUnit.Hertz[language]}{" "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.LeftHemisphere.PulseWidth[index]}{" "}{dictionary.FigureStandardUnit.uS[language]}{" "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.LeftHemisphere.Amplitude[index]}{" "}{dictionary.FigureStandardUnit.mA[language]}{" "}
                </MDTypography>
              </MDBox>
            })}
          </> : <>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {"["}{dictionary.SessionOverview.LeftHemisphere[language]}{"] "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {formatStimulationChannel(group.LeftHemisphere.Channel).map((channel) => {
                return channel + " ";
              })}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.LeftHemisphere.Frequency}{" "}{dictionary.FigureStandardUnit.Hertz[language]}{" "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.LeftHemisphere.PulseWidth}{" "}{dictionary.FigureStandardUnit.uS[language]}{" "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.LeftHemisphere.Amplitude}{" "}{dictionary.FigureStandardUnit.mA[language]}{" "}
            </MDTypography>
            {group.LeftHemisphere.AmplitudeThreshold ? (
              <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                {"["}{group.LeftHemisphere.AmplitudeThreshold[0]}{"-"}{group.LeftHemisphere.AmplitudeThreshold[1]}{dictionary.FigureStandardUnit.mA[language]}{" ]"}
              </MDTypography>
            ) : null}
          </>}
        </> : null}
      </MDBox>
      <MDBox mb={0} lineHeight={1}>
        {group.RightHemisphere ? <>
          {group.RightHemisphere.Mode === "Interleaving" ? <>
            {[0,1].map((index) => {
              return <MDBox key={index} mb={0} lineHeight={1}>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {"["}{dictionary.SessionOverview.RightHemisphere[language]}{"] "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {formatStimulationChannel(group.RightHemisphere.Channel[index]).map((channel) => {
                    return channel + " ";
                  })}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.RightHemisphere.Frequency[index]}{" "}{dictionary.FigureStandardUnit.Hertz[language]}{" "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.RightHemisphere.PulseWidth[index]}{" "}{dictionary.FigureStandardUnit.uS[language]}{" "}
                </MDTypography>
                <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                  {group.RightHemisphere.Amplitude[index]}{" "}{dictionary.FigureStandardUnit.mA[language]}{" "}
                </MDTypography>
              </MDBox>
            })}
          </> : <>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {"["}{dictionary.SessionOverview.RightHemisphere[language]}{"] "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {formatStimulationChannel(group.RightHemisphere.Channel).map((channel) => {
                return channel + " ";
              })}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.RightHemisphere.Frequency}{" "}{dictionary.FigureStandardUnit.Hertz[language]}{" "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.RightHemisphere.PulseWidth}{" "}{dictionary.FigureStandardUnit.uS[language]}{" "}
            </MDTypography>
            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
              {group.RightHemisphere.Amplitude}{" "}{dictionary.FigureStandardUnit.mA[language]}{" "}
            </MDTypography>
            {group.RightHemisphere.AmplitudeThreshold ? (
              <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                {"["}{group.RightHemisphere.AmplitudeThreshold[0]}{"-"}{group.RightHemisphere.AmplitudeThreshold[1]}{dictionary.FigureStandardUnit.mA[language]}{" ]"}
              </MDTypography>
            ) : null}
          </>}
        </> : null}
      </MDBox>
    </MDBox>;
  };

  return (
    <DatabaseLayout>
      {alert}
      <MDBox mt={2}>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={0}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3" style={{cursor: "pointer", marginBottom: 0}} onClick={() => {
                  setShowSessionLists(!showSessionLists);
                }}>
                  {showSessionLists ? null : "Show "} {dictionary.SessionOverview.SessionList[language]}
                </MDTypography>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <Collapse in={showSessionLists}>
                  <MDBox style={{overflowX: "auto"}}>
                    <Table size="small">
                      <TableHead sx={{display: "table-header-group"}}>
                        <TableRow>
                          {["SessionDate", "SessionName", "SessionData"].map((col) => {
                            return (
                              <TableCell key={col} variant="head" style={{width: "30%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                                  {dictionaryLookup(dictionary.SessionOverview, col, language)}
                                </MDTypography>
                              </TableCell>
                          )})}
                          <TableCell key={"viewedit"} variant="head" style={{width: "100px", verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                            <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>
                              {" "}
                            </MDTypography>
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {availableSessions.map((session) => {
                          return (
                            <TableRow key={session.SessionID}>
                              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                                  {session.DeviceName}
                                </MDTypography>
                                <MDTypography variant="span" fontSize={12} style={{marginBottom: 0}}>
                                  {new Date(session.SessionTimestamp*1000).toLocaleString(language)}
                                </MDTypography>
                              </TableCell>
                              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                                <MDTypography variant="p" fontSize={10} style={{marginBottom: 0}}>
                                  {session.SessionFilename}
                                </MDTypography>
                              </TableCell>
                              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                                {Object.keys(session.AvailableRecording).map((key) => {
                                  if (session.AvailableRecording[key] == 0) return;
                                  
                                  return (
                                    <MDTypography key={key} variant="p" fontSize={12} style={{marginBottom: 0}}>
                                      {dictionary.Routes[key][language]}{":"} {session.AvailableRecording[key]}<br />
                                    </MDTypography>
                                  )
                                })}
                              </TableCell>
                              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                                <MDBox style={{display: "flex", flexDirection: "row"}}>
                                  <MDButton variant={"outlined"} color={"info"} size={"small"} style={{marginRight: 15}} onClick={() => {
                                    formatForEMR(session.SessionID)
                                  }}>
                                    <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                                      {dictionary.SessionOverview.SessionEMR[language]}
                                    </MDTypography>
                                  </MDButton>
                                  <MDButton variant={"outlined"} color={"error"} size={"small"} onClick={() => {
                                    deleteSession(session.SessionID)
                                  }}>
                                    <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                                      {"DELETE"}
                                    </MDTypography>
                                  </MDButton>
                                </MDBox>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </MDBox>
                </Collapse>
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
      {sessionOverview ? (
        <MDBox mt={2}>
          <Card>
            <MDBox p={2}>
              <Grid container spacing={2}>
                <Grid item sm={12} md={6}>
                  <MDTypography variant="h3">
                    {dictionary.SessionOverview.SessionDate[language]}{": "}

                    {new Date(sessionOverview.Overall.SessionDate*1000).toLocaleString(language, {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </MDTypography>
                </Grid>
                <Grid item xs={12} sx={{marginTop: 0}}>
                  <MDBox style={{overflowX: "auto"}}>
                    <Grid container spacing={2}>
                      <Grid item sm={12} md={6}>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="h6" fontSize={18} style={{marginBottom: 0}}>
                            {sessionOverview.Overall.PatientInformation.PatientFirstName} {sessionOverview.Overall.PatientInformation.PatientLastName}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.PatientInformation.Diagnosis[language]}: {dictionaryLookup(dictionary.PatientOverview.PatientInformation, sessionOverview.Overall.PatientInformation.Diagnosis, language)}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.PatientInformation.MRN[language]}: {sessionOverview.Overall.PatientInformation.PatientId}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                          {dictionary.PatientOverview.PatientInformation.ClinicianNotes[language]}: {sessionOverview.Overall.PatientInformation.ClinicianNotes} <br/>
                          </MDTypography>
                        </MDBox>
                      </Grid>
                      <Grid item sm={12} md={6}>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="h6" fontSize={18} style={{marginBottom: 0}}>
                            {sessionOverview.Overall.DeviceInformation.Neurostimulator} {" "}
                            {sessionOverview.Overall.DeviceInformation.NeurostimulatorModel} {" "}
                            {"("} 
                            {sessionOverview.Overall.DeviceInformation.NeurostimulatorSerialNumber}
                            {")"} 
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.DeviceTable.ImplantDate[language]} {": "}
                            {new Date(sessionOverview.Overall.DeviceInformation.ImplantDate).toLocaleString(language, {
                              year: "numeric",
                              month: "long",
                              day: "numeric",
                            })}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.DeviceTable.DeviceLocation[language]} {": "}
                            {sessionOverview.Overall.DeviceInformation.NeurostimulatorLocation}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.DeviceTable.BatteryPercent[language]} {": "}
                            {sessionOverview.Overall.BatteryInformation.BatteryPercentage} {" %"}
                          </MDTypography>
                        </MDBox>
                        <MDBox mb={0} lineHeight={1}>
                          <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                            {dictionary.PatientOverview.DeviceTable.BatteryEOL[language]} {": "}
                            {sessionOverview.Overall.BatteryInformation.EstimatedBatteryLifeMonths} {" months"}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                    </Grid>
                  </MDBox>
                </Grid>

                <Grid item xs={12} sx={{marginTop: 0}}>
                  <Grid container spacing={2}>
                    <Grid item sm={12}>
                      <MDTypography variant="h3">
                        {dictionary.PatientOverview.DeviceTable.Electrodes[language]}: 
                      </MDTypography>
                    </Grid>
                    {sessionOverview.Overall.LeadConfiguration.map((config, index) => {
                      return <Grid key={index} item sm={12} md={6}>
                        <MDBox mb={0} lineHeight={1}>
                          <MDBox mb={0} lineHeight={1}>
                            <MDTypography variant="h6" fontSize={18} style={{marginBottom: 0}}>
                              {dictionaryLookup(dictionary.FigureStandardText, config.TargetLocation.split(" ")[0], language)} {" "}
                              {dictionaryLookup(dictionary.BrainRegions, config.TargetLocation.split(" ")[1], language)}
                            </MDTypography>
                          </MDBox>
                          <MDBox mb={0} lineHeight={1}>
                            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                              {dictionary.PatientOverview.DeviceTable.ElectrodeType[language]} {": "}
                              {config.ElectrodeType}
                            </MDTypography>
                          </MDBox>
                          <MDBox mb={0} lineHeight={1}>
                            <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                              {dictionary.PatientOverview.DeviceTable.ElectrodeChannel[language]} {": "}
                              {config.ElectrodeNumber}
                            </MDTypography>
                          </MDBox>
                        </MDBox>
                      </Grid>
                    })}
                  </Grid>
                </Grid>

                <Grid item xs={12} sx={{marginTop: 0}}>
                  <Grid container spacing={2}>
                    <Grid item sm={12}>
                      <MDTypography variant="h3">
                        {dictionary.SessionOverview.TherapyConfiguration[language]}: 
                      </MDTypography>
                    </Grid>
                    <Grid item sm={12} md={6}>
                      <MDTypography variant="h3" fontSize={18}>
                        {dictionary.SessionOverview.PreviousTherapy[language]}: 
                      </MDTypography>
                      {sessionOverview.Therapy.PreviousGroups.map(formatTherapyGroup)}
                    </Grid>
                    <Grid item sm={12} md={6}>
                      <MDTypography variant="h3" fontSize={18}>
                        {dictionary.SessionOverview.NewTherapy[language]}: 
                      </MDTypography>
                      {sessionOverview.Therapy.StimulationGroups.map(formatTherapyGroup)}
                    </Grid>

                  </Grid>
                </Grid>
              </Grid>
            </MDBox>
          </Card>
        </MDBox>
      ) : null}
    </DatabaseLayout>
  );
};

