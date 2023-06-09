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
import PollIcon from '@mui/icons-material/Poll';
import SensorsIcon from '@mui/icons-material/Sensors';
import TimelineIcon from '@mui/icons-material/Timeline';
import BatchPredictionIcon from '@mui/icons-material/BatchPrediction';
import FlashAutoIcon from "@mui/icons-material/FlashAuto";
import PhotoIcon from "@mui/icons-material/Photo";
import WatchIcon from "@mui/icons-material/Watch";
import ArticleIcon from '@mui/icons-material/Article';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";
import UploadDialog from "./UploadDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";

import {
  experimentalRoutes
} from "views/Experimental/plugins";
import MuiAlertDialog from "components/MuiAlertDialog";

const filter = createFilterOptions();

export default function PatientOverview() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { user, language, patientID } = controller;

  const [patientInfo, setPatientInfo] = useState(false);
  const [editPatientInfo, setEditPatientInfo] = useState({show: false});
  const [editDeviceInfo, setEditDeviceInfo] = useState({LeadInfo: [], show: false});
  const [uploadNewJson, setUploadNewJson] = useState({show: false});
  const [addNewDevice, setAddNewDevice] = useState({show: false});
  const [availableTags, setAvailableTags] = useState([]);

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.getPatientInfo(patientID).then((response) => {
        response.data.Tags = response.data.Tags.map((tag) => ({
          title: tag,
          value: tag
        }));
        setEditPatientInfo({...editPatientInfo, ...response.data});
        setPatientInfo(response.data);
        setAvailableTags(response.data.AvailableTags.map((tag) => ({
          title: tag,
          value: tag
        })));
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const removeDevice = (deviceId) => {
    setAlert(<MuiAlertDialog 
      title={"Remove Device"}
      message={"Are you sure you want to delete the device entry and all associated data?"}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        SessionController.query("/api/deleteSessionFiles", {
          deleteDevice: true,
          patientId: patientID,
          deviceId: deviceId
        }).then(() => {
          setPatientInfo({...patientInfo, Devices: patientInfo.Devices.filter((device) => device.ID != deviceId)});
          setAlert(null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />)
  };

  const removePatient = () => {
    SessionController.query("/api/deleteSessionFiles", {
      deletePatient: true,
      patientId: patientID,
    }).then(() => {
      setPatientInfo(false);
      setContextState(dispatch, "patientID", null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const updatePatientInformation = () => {
    SessionController.query("/api/updatePatientInformation", {
      updatePatientInfo: patientID,
      FirstName: editPatientInfo.FirstName,
      LastName: editPatientInfo.LastName,
      Diagnosis: editPatientInfo.Diagnosis,
      MRN: editPatientInfo.MRN,
      Tags: editPatientInfo.Tags ? editPatientInfo.Tags.map((tag) => tag.value ? tag.value : tag.inputValue ) : []
    }).then(() => {
      setPatientInfo({...patientInfo, 
        FirstName: editPatientInfo.FirstName,
        LastName: editPatientInfo.LastName,
        Diagnosis: editPatientInfo.Diagnosis,
        MRN: editPatientInfo.MRN,
        Tags: editPatientInfo.Tags ? editPatientInfo.Tags : []
      });
      setEditPatientInfo({...editPatientInfo, show: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const updateDeviceInformation = () => {
    SessionController.query("/api/updatePatientInformation", {
      updatePatientInfo: patientID,
      updateDeviceID: editDeviceInfo.DeviceID,
      newDeviceName: editDeviceInfo.DeviceName == editDeviceInfo.DeviceID ? "" : editDeviceInfo.DeviceName,
      leadAnnotations: editDeviceInfo.LeadInfo.map((lead) => lead.CustomName),
    }).then(() => {
      setPatientInfo({...patientInfo, Devices: patientInfo.Devices.map((device) => {
        if (device.ID != editDeviceInfo.DeviceID) return device
        return {
          ...device,
          DeviceName: editDeviceInfo.DeviceName,
          Leads: device.Leads.map((lead, index) => {
            return {
              ...lead,
              CustomName: editDeviceInfo.LeadInfo[index].CustomName
            }
          })
        };
      })});
      setEditDeviceInfo({...editDeviceInfo, show: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  const routes = [
    {title: "TherapyHistory", icon: <BoltIcon/>, route: "/reports/therapy-history"},
    {title: "BrainSenseSurvey", icon: <PollIcon/>, route: "/reports/survey"},
    {title: "BrainSenseStreaming", icon: <SensorsIcon/>, route: "/reports/stream"},
    {title: "IndefiniteStreaming", icon: <SensorsIcon/>, route: "/reports/multistream"},
    {title: "ChronicRecordings", icon: <TimelineIcon/>, route: "/reports/chronic-recordings"},
    {title: "SessionOverview", icon: <ArticleIcon/>, route: "/reports/session-overview"}
  ];

  const experimentals = experimentalRoutes.map((route) => {
    return {
      title: route.name, 
      icon: route.icon,
      route: route.route,
    };
  });

  return (
    <DatabaseLayout>
      {alert}
      <MDBox py={3}>
        {patientInfo ? (
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
                          {patientInfo.FirstName + " " + patientInfo.LastName}
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
                          {dictionary.PatientOverview.PatientInformation[patientInfo.Diagnosis] ? dictionary.PatientOverview.PatientInformation[patientInfo.Diagnosis][language] : patientInfo.Diagnosis}
                        </MDTypography>
                      </MDBox>
                      <MDBox mb={0.5} lineHeight={1}>
                        <MDTypography
                          variant="p"
                          fontWeight="medium"
                          fontSize={13}
                          textTransform="capitalize"
                        >
                          {dictionary.PatientOverview.PatientInformation.DOB[language]}: {new Date(patientInfo.DOB).toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"))}
                        </MDTypography>
                      </MDBox>
                      <MDBox lineHeight={1}>
                        <MDTypography
                          variant="p"
                          fontWeight="medium"
                          fontSize={13}
                          textTransform="capitalize"
                        >
                          {dictionary.PatientOverview.PatientInformation.MRN[language]}: {patientInfo.MRN}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} xl={user.Clinician ? 12 : 6}>
                      <Divider variant="middle" />
                      <MDButton variant="outlined" color="warning" fullWidth 
                        onClick={() => setEditPatientInfo({...patientInfo, show: true})}
                      >
                        {dictionary.PatientOverview.EditPatientInfo[language]}
                      </MDButton>
                    </Grid>
                    {!user.Clinician ? (
                      <Grid item xs={12} xl={6}>
                        <Divider variant="middle" />
                        <MDButton variant="outlined" color="info" fullWidth
                          onClick={() => setUploadNewJson({show: true})}
                        >
                          {dictionary.PatientOverview.UploadNewSession[language]}
                        </MDButton>
                      </Grid>
                    ) : null}
                  </Grid>
                </MDBox>
              </Card>

              <Dialog open={editPatientInfo.show} onClose={() => setEditPatientInfo({...editPatientInfo, show: false})}>
                <MDBox px={2} pt={2}>
                  <MDTypography variant="h5">
                    Edit Patient Information
                  </MDTypography>
                  <MDTypography variant="h5">
                    {patientID}
                  </MDTypography>
                </MDBox>
                <DialogContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        variant="standard"
                        margin="dense" id="name"
                        value={editPatientInfo.FirstName}
                        onChange={(event) => setEditPatientInfo({...editPatientInfo, FirstName: event.target.value})}
                        label={user.Clinician ? dictionary.SessionUpload.PatientFirstName[language] : dictionary.SessionUpload.PatientIdentifier[language]} type="text"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        variant="standard"
                        margin="dense" id="name"
                        value={editPatientInfo.LastName}
                        onChange={(event) => setEditPatientInfo({...editPatientInfo, LastName: event.target.value})}
                        label={user.Clinician ? dictionary.SessionUpload.PatientLastName[language] : dictionary.SessionUpload.StudyIdentifier[language]} type="text"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        variant="standard"
                        margin="dense" id="name"
                        value={editPatientInfo.Diagnosis}
                        onChange={(event) => setEditPatientInfo({...editPatientInfo, Diagnosis: event.target.value})}
                        label={dictionary.SessionUpload.Diagnosis[language]} type="text"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        variant="standard"
                        margin="dense" id="name"
                        value={editPatientInfo.MRN}
                        onChange={(event) => setEditPatientInfo({...editPatientInfo, MRN: event.target.value})}
                        label={dictionary.SessionUpload.MRN[language]} type="text"
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <Autocomplete 
                        selectOnFocus 
                        clearOnBlur 
                        multiple
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            variant="standard"
                            placeholder={dictionary.PatientOverview.TagNames[language]}
                          />
                        )}
                        filterOptions={(options, params) => {
                          const filtered = filter(options, params);
                          const { inputValue } = params;

                          // Suggest the creation of a new value
                          const isExisting = options.some((option) => inputValue === option.title);
                          if (inputValue !== '' && !isExisting) {
                            filtered.push({
                              inputValue,
                              title: `Add "${inputValue}"`,
                            });
                          }
                          return filtered;
                        }}
                        getOptionLabel={(option) => {
                          if (typeof option === 'string') {
                            return option;
                          }
                          if (option.inputValue) {
                            return option.inputValue;
                          }
                          return option.title;
                        }}
                        isOptionEqualToValue={(option, value) => {
                          return option.value === value.value;
                        }}
                        renderOption={(props, option) => <li {...props}>{option.title}</li>}

                        value={editPatientInfo.Tags}
                        options={availableTags}
                        onChange={(event, newValue) => setEditPatientInfo({...editPatientInfo, Tags: newValue})}
                      />
                    </Grid>
                    <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
                      <MDBox style={{paddingLeft: 5}}>
                        <MDButton color={"error"} 
                          onClick={() => removePatient()}
                        >
                          Delete
                        </MDButton>
                      </MDBox>
                      <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
                        <MDButton color={"secondary"} 
                          onClick={() => setEditPatientInfo({...editPatientInfo, show: false})}
                        >
                          Cancel
                        </MDButton>
                        <MDButton color={"info"} 
                          onClick={() => updatePatientInformation()} style={{marginLeft: 10}}
                        >
                          Update
                        </MDButton>
                      </MDBox>
                    </Grid>
                  </Grid>
                </DialogContent>
              </Dialog>
            </Grid>
            <Grid item xs={12} lg={8} display={"flex"} alignItems={"stretch"}>
              <Card sx={{width: "100%", overflowX: "auto"}}>
                <Table size="small">
                  <TableHead sx={{display: "table-header-group"}}>
                    <TableRow key={"header"}>
                      {["DeviceType", "DeviceName", "Electrodes", "ImplantDate","LastAccessDate","BatteryEOL"].map((col) => {
                        return (
                          <TableCell key={col} variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 5, paddingTop: 5, textAlign: "center", lineHeight: 1}}>
                            <MDTypography variant="p" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                              {dictionary.PatientOverview.DeviceTable[col][language]}
                            </MDTypography>
                          </TableCell>
                      )})}
                      <TableCell key={"viewdelete"} variant="head" style={{width: "15%", verticalAlign: "bottom", paddingBottom: 5, paddingTop: 5, textAlign: "center", lineHeight: 1}}>
                        <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}> {" "} </MDTypography>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {patientInfo.Devices.map((device) => {
                      return <TableRow key={device.ID}>
                        <TableCell key={"devicetype"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {device.DeviceType}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"devicename"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {device.DeviceName}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"leadname"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          {device.Leads.map((lead) => {
                            return <MDBox key={lead.ElectrodeType + lead.TargetLocation} style={{marginBottom: 5}}>
                            <MDTypography style={{marginBottom: 0, marginTop: 0}} align="center" fontSize={8}>
                              {lead.ElectrodeType}
                            </MDTypography>
                            <MDTypography style={{marginBottom: 0, marginTop: 0}} align="center" fontSize={11}>
                              {lead.CustomName}
                            </MDTypography>
                          </MDBox>
                          })}
                        </TableCell>
                        <TableCell key={"implantdate"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {new Date(device.ImplantDate*1000).toLocaleString(language, SessionController.getDateTimeOptions("DateNumeric"))}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"lastseendate"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {new Date(device.LastSeenDate*1000).toLocaleDateString(language, SessionController.getDateTimeOptions("DateNumeric"))}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"eoldate"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDTypography align="center" style={{marginBottom: 0}} fontSize={12}>
                            {new Date(device.EOLDate*1000).toLocaleDateString(language, SessionController.getDateTimeOptions("DateNumeric"))}
                          </MDTypography>
                        </TableCell>
                        <TableCell key={"viewedit"} style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                          <MDBox style={{display: "flex", flexDirection: "row"}}>
                            <Tooltip title="Delete Device" placement="top">
                              <IconButton variant="contained" color="error" onClick={() => removeDevice(device.ID)}>
                                <i className="fa-solid fa-xmark" style={{fontSize: 10}}></i>
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Edit Device" placement="top">
                              <IconButton variant="contained" color="info" onClick={() => setEditDeviceInfo({...editDeviceInfo, LeadInfo: device.Leads, DeviceName: device.DeviceName, DeviceID: device.ID, show: true})}>
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

              <Dialog open={editDeviceInfo.show} onClose={() => setEditDeviceInfo({...editDeviceInfo, show: false})}>
                <MDBox px={2} pt={2}>
                  <MDTypography variant="h5">
                    Edit Device Information
                  </MDTypography>
                  <MDTypography variant="h5">
                    {`(${editDeviceInfo.DeviceID})`}
                  </MDTypography>
                </MDBox>
                <DialogContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        variant="standard"
                        margin="dense"
                        label="Device Name"
                        placeholder="Device Name"
                        value={editDeviceInfo.DeviceName}
                        onChange={(event) => setEditDeviceInfo({...editDeviceInfo, DeviceName: event.target.value})}
                        fullWidth
                      />
                    </Grid>
                    {editDeviceInfo.LeadInfo.map((lead, index) => (
                      <Grid key={lead.TargetLocation} item xs={6}>
                        <TextField
                          variant="standard"
                          margin="dense"
                          label={`Lead #${index+1}`}
                          placeholder="editDeviceInfo"
                          value={lead.CustomName}
                          onChange={(event) => setEditDeviceInfo({...editDeviceInfo, LeadInfo: editDeviceInfo.LeadInfo.map((oldLead, oldIndex) => {
                            if (index == oldIndex) return {...oldLead, CustomName: event.target.value};
                            return oldLead;
                          })})}
                          fullWidth
                        />
                      </Grid>
                    ))}
                  </Grid>
                </DialogContent>
                <DialogActions>
                  <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
                    <MDButton color={"secondary"} 
                      onClick={() => setEditDeviceInfo({...editDeviceInfo, show: false})}
                    >
                      Cancel
                    </MDButton>
                    <MDButton color={"info"} 
                      onClick={() => updateDeviceInformation()} style={{marginLeft: 10}}
                    >
                      Update
                    </MDButton>
                  </MDBox>
                </DialogActions>
              </Dialog>
            </Grid>
          </Grid>
        </MDBox>
        ) : null}
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} display={"flex"} alignItems={"stretch"}>
              <MDTypography variant={"span"} fontSize={15} fontWeight={"bold"}>
                {dictionary.Routes.Reports[language]}
              </MDTypography>
            </Grid>
            {routes.map((item) => (
              <Grid item xs={6} md={4} lg={3} xl={2} key={item.title} display={"flex"} alignItems={"stretch"}>
                <Card sx={{width: "100%"}}>
                  <MDBox p={2} mx={3} display="flex" justifyContent="center">
                    <MDBox
                      display="grid"
                      justifyContent="center"
                      alignItems="center"
                      width="4rem"
                      height="4rem"
                      shadow="md"
                      borderRadius="lg"
                      variant="gradient"
                    >
                      <Icon fontSize="large">
                        {item.icon}
                      </Icon>
                    </MDBox>
                  </MDBox>
                  <MDBox pb={6} px={2} textAlign="center" lineHeight={1.25}>
                    <MDTypography variant="h6" fontWeight="medium" textTransform="capitalize" pb={2}>
                      {dictionary.Routes[item.title][language]}
                    </MDTypography>
                  </MDBox>
                  <MDBox pb={2} px={2} lineHeight={1.25} sx={{position: "absolute", bottom: 0, width: "100%"}}>
                    <MDButton variant={"contained"} color={"info"} fullWidth onClick={() => navigate(item.route, {replace: false})}>
                      {dictionary.PatientOverview.PatientInformation.View[language]}
                    </MDButton>
                  </MDBox>
                </Card>
              </Grid>
            ))}
          </Grid>
        </MDBox>
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} display={"flex"} alignItems={"stretch"}>
              <MDTypography variant={"span"} fontSize={15} fontWeight={"bold"}>
                {dictionary.Routes.Experimental[language]}
              </MDTypography>
            </Grid>
            {experimentals.map((item) => (
              <Grid item xs={6} md={4} lg={3} xl={2} key={item.title} display={"flex"} alignItems={"stretch"}>
                <Card sx={{width: "100%"}}>
                  <MDBox p={2} mx={3} display="flex" justifyContent="center">
                    <MDBox
                      display="grid"
                      justifyContent="center"
                      alignItems="center"
                      width="4rem"
                      height="4rem"
                      shadow="md"
                      borderRadius="lg"
                      variant="gradient"
                      style={{
                        background: "#544f4f"
                      }}
                    >
                      <Icon fontSize="large">
                        {item.icon}
                      </Icon>
                    </MDBox>
                  </MDBox>
                  <MDBox pb={6} px={2} textAlign="center" lineHeight={1.25}>
                    <MDTypography variant="h6" fontWeight="medium" textTransform="capitalize" pb={2}>
                      {dictionary.Routes[item.title][language]}
                    </MDTypography>
                  </MDBox>
                  <MDBox pb={2} px={2} lineHeight={1.25} sx={{position: "absolute", bottom: 0, width: "100%"}}>
                    <MDButton variant={"contained"} color={"info"} fullWidth onClick={() => navigate(item.route, {replace: false})}>
                      {dictionary.PatientOverview.PatientInformation.View[language]}
                    </MDButton>
                  </MDBox>
                </Card>
              </Grid>
            ))}
          </Grid>
        </MDBox>
      </MDBox>

      <UploadDialog show={uploadNewJson.show} availableDevices={patientInfo.Devices ? patientInfo.Devices.map((device) => ({label: device.DeviceName, value: device.ID})) : []} onCancel={() => setUploadNewJson({show: false})} />

    </DatabaseLayout>
  );
};
