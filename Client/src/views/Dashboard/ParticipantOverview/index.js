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
import { Link, useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Divider,
  Dialog,
  DialogContent,
  DialogActions,
  Grid,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Tooltip,
  TextField,
  Icon,
  IconButton,
} from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";

import BoltIcon from '@mui/icons-material/Bolt';
import AssessmentIcon from '@mui/icons-material/Assessment';
import PollIcon from '@mui/icons-material/Poll';
import SensorsIcon from '@mui/icons-material/Sensors';
import TimelineIcon from '@mui/icons-material/Timeline';
import BatchPredictionIcon from '@mui/icons-material/BatchPrediction';
import FlashAutoIcon from "@mui/icons-material/FlashAuto";
import PhotoIcon from "@mui/icons-material/Photo";
import WatchIcon from "@mui/icons-material/Watch";
import ArticleIcon from '@mui/icons-material/Article';

import { FaBrain } from "react-icons/fa6";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";
import EditParticipantInfoView from "./EditParticipantInfoView";
import EditDeviceInfoView from "./EditDeviceInfoView";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";

import {
  experimentalRoutes
} from "views/Experimental/plugins";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

import routes from "routes.js";
import SetExperimentView from "./SetExperimentView";

const filter = createFilterOptions();

export default function ParticipantOverview() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { user, language, participant_uid, experiment, report } = controller;

  const [participantInfo, setParticipantInfo] = useState(false);
  const [editParticipantInfo, setEditParticipantInfo] = useState(false);
  const [editDeviceInfo, setEditDeviceInfo] = useState({show: false});
  const [activeExperiment, setActiveExperiment] = useState({show: false, options: [], active: experiment});
  const [uploadNewJson, setUploadNewJson] = useState({show: false});
  const [mergeRecords, setMergeRecords] = useState({show: false});
  const [addNewDevice, setAddNewDevice] = useState({show: false});
  const [availableTags, setAvailableTags] = useState([]);

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!participant_uid) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryParticipantInformation", {
        participant_uid: participant_uid
      }).then((response) => {
        response.data.tags = response.data.tags.map((tag) => ({
          title: tag,
          value: tag
        }));
        setEditParticipantInfo(false);
        setParticipantInfo(response.data);
        setAvailableTags([]);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });

      SessionController.query("/api/queryParticipantExperiments", {
        request_type: "Query",
        participant_uid: participant_uid
      }).then((response) => {
        setActiveExperiment({show: true, options: response.data, active: experiment});
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [participant_uid]);

  const removeDevice = (device_uid) => {
    setAlert(<MuiAlertDialog 
      title={"Remove Device"}
      message={"Are you sure you want to delete the device entry and all associated data?"}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        setAlert(<LoadingProgress />);
        SessionController.query("/api/deleteData", {
          participant_uid: participant_uid,
          device: device_uid
        }).then(() => {
          setParticipantInfo({...participantInfo, dbsDevices: participantInfo.dbsDevices.filter((device) => device.uid != device_uid)});
          setAlert(null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />)
  };

  const removeParticipant = () => {
    setAlert(<MuiAlertDialog 
      title={"Remove Participant"}
      message={"Are you sure you want to delete the participant entry and all associated data?"}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        setEditParticipantInfo(false);
        setAlert(<LoadingProgress />);
        SessionController.query("/api/deleteStudyParticipant", {
          participant_uid: participant_uid
        }).then(() => {
          setParticipantInfo(false);
          setContextState(dispatch, "participant_uid", null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />)
  };

  const updateParticipantInformation = (editParticipantInfo) => {
    SessionController.query("/api/updateStudyParticipant", {
      participant_uid: participant_uid,
      name: editParticipantInfo.name,
      diagnosis: editParticipantInfo.diagnosis,
      sex: editParticipantInfo.sex,
      tags: editParticipantInfo.tags ? editParticipantInfo.tags.map((tag) => tag.value ? tag.value : tag.inputValue ) : []
    }).then(() => {
      setParticipantInfo({...participantInfo, 
        name: editParticipantInfo.name,
        diagnosis: editParticipantInfo.diagnosis,
        sex: editParticipantInfo.sex,
        tags: editParticipantInfo.tags ? editParticipantInfo.tags : []
      });
      setEditParticipantInfo(false);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const updateDeviceInformation = (deviceInfo) => {
    SessionController.query("/api/updateDeviceInformation", {
      participant_uid: participant_uid,
      device: deviceInfo.uid,
      name: deviceInfo.name,
      leads: deviceInfo.leads,
    }).then(() => {
      setParticipantInfo({...participantInfo, dbsDevices: participantInfo.dbsDevices.map((device) => {
        if (device.uid != deviceInfo.uid) return device;
        return {
          ...device,
          name: deviceInfo.name,
          leads: deviceInfo.leads
        };
      })});
      setEditDeviceInfo({...editDeviceInfo, show: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  return (
    <DatabaseLayout>
      {alert}
      <MDBox py={3}>
        {participantInfo ? (
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} lg={4} display={"flex"} alignItems={"stretch"}>
              <Card sx={{width: "100%"}}>
                <MDBox p={2}>
                  <Grid container spacing={1}>
                    <Grid item xs={12}>
                      <MDBox mb={0.5} lineHeight={1}>
                        <MDTypography
                          variant="h5"
                          fontWeight="bold"
                          textTransform="capitalize"
                        >
                          {SessionController.decodeMessage(participantInfo.name)}
                        </MDTypography>
                      </MDBox>
                      <MDBox mb={2} lineHeight={1}>
                        <MDTypography
                          variant="p"
                          fontWeight="medium"
                          fontSize={15}
                          color="text"
                          textTransform="capitalize"
                        >
                          {participantInfo.diagnosis ? (
                            dictionary.ParticipantOverview.ParticipantInformation[participantInfo.diagnosis] ? dictionary.ParticipantOverview.ParticipantInformation[participantInfo.diagnosis][language] : participantInfo.diagnosis
                          ) : "Diagnosis: N/A"}
                        </MDTypography>
                      </MDBox>
                      <MDBox mb={0.5} lineHeight={1}>
                        <MDTypography
                          variant="p"
                          fontWeight="medium"
                          fontSize={13}
                          textTransform="capitalize"
                        >
                          {dictionary.ParticipantOverview.ParticipantInformation.DOB[language]}: {new Date(SessionController.decodeTimestamp(participantInfo.dob*1000)).toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"))}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <Divider variant="middle" />
                      <MDButton variant="outlined" color="warning" fullWidth 
                        onClick={() => setEditParticipantInfo(true)}
                      >
                        {dictionary.ParticipantOverview.EditParticipantInfo[language]}
                      </MDButton>
                    </Grid>
                  </Grid>
                </MDBox>
              </Card>
              <EditParticipantInfoView 
                show={editParticipantInfo} 
                participantInfo={participantInfo} 
                removeParticipant={removeParticipant}
                onCancel={() => setEditParticipantInfo(false)} 
                onUpdate={updateParticipantInformation} 
              />
            </Grid>
            <Grid item xs={12} lg={8} display={"flex"} alignItems={"stretch"}>
              <Card sx={{width: "100%", overflowX: "auto"}}>
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                          
                  </Grid>
                </Grid>
                <Table size="small">
                  <TableHead sx={{display: "table-header-group"}}>
                    <TableRow key={"header"}>
                      {["DeviceType", "DeviceName", "Electrodes", "ImplantDate"].map((col) => {
                        return (
                          <TableCell key={col} variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 5, paddingTop: 5, textAlign: "center", lineHeight: 1}}>
                            <MDTypography variant="p" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                              {dictionary.ParticipantOverview.DeviceTable[col][language]}
                            </MDTypography>
                          </TableCell>
                      )})}
                      <TableCell key={"viewdelete"} variant="head" style={{width: "15%", verticalAlign: "bottom", paddingBottom: 5, paddingTop: 5, textAlign: "center", lineHeight: 1}}>
                        <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}> {" "} </MDTypography>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {participantInfo.dbsDevices.map((device) => {
                      const deviceName = SessionController.decodeMessage(device.name);
                      return <TableRow key={device.uid}>
                        <TableCell key={"devicetype"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {device.type}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"devicename"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {deviceName.length > 32 ? deviceName.slice(0,32) : deviceName}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"leadname"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          {device.leads.map((lead) => {
                            return <MDBox key={lead.type + lead.name} style={{marginBottom: 5}}>
                            <MDTypography style={{marginBottom: 0, marginTop: 0}} align="center" fontSize={8}>
                              {lead.type}
                            </MDTypography>
                            <MDTypography style={{marginBottom: 0, marginTop: 0}} align="center" fontSize={11}>
                              {lead.custom_name ? lead.custom_name : lead.name}
                            </MDTypography>
                          </MDBox>
                          })}
                        </TableCell>
                        <TableCell key={"implantdate"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {new Date(SessionController.decodeTimestamp(device.implant_date*1000)).toLocaleString(language, SessionController.getDateTimeOptions("DateNumeric"))}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"viewedit"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDBox style={{display: "flex", flexDirection: "row"}}>
                            <Tooltip title="Delete Device" placement="top">
                              <IconButton variant="contained" color="error" onClick={() => removeDevice(device.uid)}>
                                <i className="fa-solid fa-xmark" style={{fontSize: 10}}></i>
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Edit Device" placement="top">
                              <IconButton variant="contained" color="info" onClick={() => setEditDeviceInfo({deviceInfo: device, show: true})}>
                                <i className="fa-solid fa-pen" style={{fontSize: 10}}></i>
                              </IconButton>
                            </Tooltip>
                          </MDBox>
                        </TableCell>
                      </TableRow>
                    })}
                  </TableBody>
                </Table>
              </Card>

              <EditDeviceInfoView 
                show={editDeviceInfo.show} 
                deviceInfo={editDeviceInfo.deviceInfo} 
                onCancel={() => setEditDeviceInfo({show: false})} 
                onUpdate={updateDeviceInformation} 
              />
            </Grid>
          </Grid>
        </MDBox>
        ) : null}
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} display={"flex"} alignItems={"stretch"}>
              <MDTypography variant={"span"} fontSize={15} fontWeight={"bold"}>
                {dictionary.Routes.Experiments[language]}
              </MDTypography>
            </Grid>
            {activeExperiment.options.map((experiment) => {
              return <Grid key={experiment.uid} item xs={12} display={"flex"} alignItems={"stretch"}>
              <Card sx={{width: "100%", background: activeExperiment.active == experiment.uid ? "light" : "transparent", 
                        border: activeExperiment.active == experiment.uid ? "solid" : "dashed", 
                        borderWidth: activeExperiment.active == experiment.uid ? 2 : 1, cursor: "pointer"}}
                onClick={() => {
                  setActiveExperiment((activeExperiment) => {
                    activeExperiment.active = experiment.uid;
                    activeExperiment.show = false;
                    setContextState(dispatch, "experiment", experiment.uid, false);
                    return {...activeExperiment};
                  })
                }}
              >
                <MDBox p={2} mx={3} display="flex" justifyContent="space-between">
                  <MDBox display="flex" justifyContent="start">
                    <MDTypography variant={"span"} fontSize={20} fontWeight={"bold"}>
                      {experiment.name}
                    </MDTypography>
                  </MDBox>
                  <MDBox display="flex" flexDirection={"column"} justifyContent="end">
                    <MDTypography variant={"span"} color={"secondary"} fontSize={12} fontWeight={"bold"}>
                      {"# of Recordings: " + experiment.recordings}
                    </MDTypography>
                    <MDTypography variant={"span"} color={"secondary"} fontSize={12} fontWeight={"bold"}>
                      {"# of Events: " + experiment.events}
                    </MDTypography>
                  </MDBox>
                </MDBox>
              </Card>
            </Grid>
            })}
          </Grid>
        </MDBox>
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} display={"flex"} alignItems={"stretch"}>
              <MDTypography variant={"span"} fontSize={15} fontWeight={"bold"}>
                {dictionary.Routes.Reports[language]}
              </MDTypography>
            </Grid>
            {Object.keys(routes).map((key) => {
              if (key === "Main") return;
              return <Grid key={key} item xs={6} md={4} lg={3} xl={2} display={"flex"} alignItems={"stretch"}>
                <Card sx={{width: "100%"}}>
                  <MDBox p={2} mx={3} display="flex" justifyContent="center">
                    <MDBox
                      display="grid" justifyContent="center" alignItems="center"
                      width="4rem" height="4rem" shadow="md"
                      borderRadius="lg" variant="gradient"
                    >
                      <Icon fontSize="large">
                        {routes[key].icon}
                      </Icon>
                    </MDBox>
                  </MDBox>
                  <MDBox pb={6} px={2} textAlign="center" lineHeight={1.25}>
                    <MDTypography variant="h6" fontWeight="medium" textTransform="capitalize" pb={2}>
                      {routes[key].name}
                    </MDTypography>
                  </MDBox>
                  <MDBox pb={2} px={2} lineHeight={1.25} sx={{position: "absolute", bottom: 0, width: "100%"}}>
                    <MDButton variant={"contained"} color={"info"} fullWidth onClick={() => {
                      setContextState(dispatch, "report", key);
                    }}>
                      {dictionary.ParticipantOverview.ParticipantInformation.View[language]}
                    </MDButton>
                  </MDBox>
                </Card>
              </Grid>
            })}
          </Grid>
        </MDBox>
        {routes[report] ? (
          <MDBox mb={3}>
            <Grid container spacing={2}>
              <Grid item xs={12} display={"flex"} alignItems={"stretch"}>
                <MDTypography variant={"span"} fontSize={15} fontWeight={"bold"}>
                  {dictionary.Routes[report] ? dictionary.Routes[report][language] : report}
                </MDTypography>
              </Grid>
              {routes[report].children.map((subreport) => {
                return <Grid item xs={6} md={4} lg={3} xl={2} display={"flex"} alignItems={"stretch"}>
                  <Card sx={{width: "100%"}}>
                    <MDBox p={2} mx={3} display="flex" justifyContent="center">
                      <MDBox
                        display="grid" justifyContent="center" alignItems="center"
                        width="4rem" height="4rem"
                        shadow="md" borderRadius="lg" variant="gradient"
                      >
                        <Icon fontSize="large">
                          {subreport.icon}
                        </Icon>
                      </MDBox>
                    </MDBox>
                    <MDBox pb={6} px={2} textAlign="center" lineHeight={1.25}>
                      <MDTypography variant="h6" fontWeight="medium" textTransform="capitalize" pb={2}>
                        {subreport.name}
                      </MDTypography>
                    </MDBox>
                    <MDBox pb={2} px={2} lineHeight={1.25} sx={{position: "absolute", bottom: 0, width: "100%"}}>
                      <MDButton variant={"contained"} color={"info"} fullWidth onClick={() => {
                        navigate(subreport.route, {replace: false})
                      }}>
                        {dictionary.ParticipantOverview.ParticipantInformation.View[language]}
                      </MDButton>
                    </MDBox>
                  </Card>
                </Grid>
              })}
            </Grid>
          </MDBox>
        ) : null}
      </MDBox>
    </DatabaseLayout>
  );
};
