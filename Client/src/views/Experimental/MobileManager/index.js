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
import { useNavigate } from "react-router-dom";

import {
  TextField,
  Autocomplete,
  Card,
  Grid,
  Dialog,
  Input,
  InputAdornment,
  DialogTitle,
  DialogActions,
  DialogContent,
  IconButton,
  Tooltip,
  Modal,
  ListItemButton,
  ListItemText,
  ListItemIcon
} from "@mui/material";

import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from "@fullcalendar/interaction"

import React from "react";
import * as THREE from "three";
import { Canvas, useThree } from '@react-three/fiber';

import colormap from "colormap";

import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import RadioButtonGroup from "components/RadioButtonGroup";
import MDBadge from "components/MDBadge";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

import DatabaseLayout from "layouts/DatabaseLayout";
import InertiaSensorSpectrum from "./InertiaSensorSpectrum";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function MobileManager() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ChartTooltip, Legend);
  const chartCanvas = React.createRef();

  const [alert, setAlert] = useState(null);

  const [mobileAccount, setMobileAccount] = useState({
    Username: "",
    Token: "",
    New: true
  });

  const [editMobileAccount, setEditMobileAccount] = useState({
    Username: "",
    Password: "",
    showPassword: false,
    show: false
  });

  const [availableRecordings, setAvailableRecordings] = useState({
    list: [],
    current: "",
  });

  const [dataToRender, setDataToRender] = useState(false);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/mobile/wearable/queryMobileAccount", {
        queryMobileAccount: true,
        patientId: patientID,
      }).then((response) => {
        if (response.data.length > 0) {
          setMobileAccount(response.data[0]);
        }
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });

      SessionController.query("/api/queryMobileRecordings", {
        patientId: patientID, 
        requestOverview: true
      }).then((response) => {
        setAvailableRecordings({list: response.data.filter((a) => a.Time > 0), current: ""});
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const handleMobileAccountUpdate = () => {
    if (mobileAccount.Username === "") {
      SessionController.query("/mobile/wearable/queryMobileAccount", {
        createMobileAccount: true,
        patientId: patientID,
        username: editMobileAccount.Username,
        password: editMobileAccount.Password,
      }).then((response) => {
        if (response.data.length > 0) {
          setMobileAccount(response.data[0]);
          setEditMobileAccount({...editMobileAccount, show: false, showPassword: false});
        }
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    } else {

      setAlert(<MuiAlertDialog 
        title={"Delete Account"}
        message={"Are you sure you want to delete the account? Existing App Session will not function after next network update."}
        confirmText={"YES"}
        denyText={"NO"}
        denyButton
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => {
          SessionController.query("/mobile/wearable/queryMobileAccount", {
            deleteMobileAccount: true,
            patientId: patientID,
          }).then((response) => {
            if (response.data.length > 0) {
              setMobileAccount(response.data[0]);
              setEditMobileAccount({...editMobileAccount, show: false, showPassword: false});
              setAlert(null);
            }
          }).catch((error) => {
            SessionController.displayError(error, setAlert);
          });
        }}
      />)
    }
  };

  const handleLogout = () => {
    setAlert(<MuiAlertDialog 
      title={"Logout Existing Device"}
      message={"Are you sure you want to log out? This action reset access token and existing App Session will not function after next network update."}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        SessionController.query("/mobile/auth/logout", {
          Username: mobileAccount.Username,
          currentToken: mobileAccount.Token
        }).then((response) => {
          setMobileAccount({...mobileAccount,
            Token: "",
          });
          setAlert(null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />)
  };

  const handleDownloadRecording = () => {
    for (let key of Object.keys(dataToRender)) {
      if (key == "DeviceID") continue;

      let totalSize = 0;
      let csvContent = "";
      let savedField = [];
      
      for (let field of Object.keys(dataToRender[key])) {
        totalSize = dataToRender[key][field].length > totalSize ? dataToRender[key][field].length : totalSize;
        if (dataToRender[key][field].length > 0) {
          csvContent += field + ","
          savedField.push(field);
        }
      }

      if (totalSize == 0) continue;
    
      csvContent = csvContent.slice(0,-1) + "\n";
      for (let i = 0; i < totalSize; i++) {
        for (let j = 0; j < savedField.length; j++) {
          csvContent += dataToRender[key][savedField[j]][i].toString() + (j == savedField.length-1 ? "\n" : ",");
        }
      }
  
      var downloader = document.createElement('a');
      downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvContent);
      downloader.target = '_blank';
      downloader.download = dataToRender.DeviceID.replace("DATA:","") + "_" + key + ".csv";
      downloader.click();
    }
  };

  const handleDeleteRecording = () => {
    SessionController.query("/api/queryMobileRecordings", {
      patientId: patientID, 
      recordingId: availableRecordings.current,
      deleteData: true
    }).then((response) => {
      setDataToRender(null);
      setAvailableRecordings({list: availableRecordings.list.filter((a) => a.RecordingId != availableRecordings.current), current: ""});
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  return (
    <>
      {alert}
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Dialog open={editMobileAccount.show} onClose={() => setEditMobileAccount({...editMobileAccount, show: false})}>
              <MDBox px={2} pt={2}>
                <MDTypography variant="h5">
                  {mobileAccount.New ? "New Mobile Account" : "Edit Account Password"}
                </MDTypography>
              </MDBox>
              <DialogContent>
                <Grid container spacing={2}>
                  {mobileAccount.New ? (
                    <Grid item xs={12} md={6}>
                      <Input
                        variant="standard"
                        margin="dense"
                        value={editMobileAccount.Username}
                        placeholder={"Username"}
                        onChange={(event) => setEditMobileAccount({...editMobileAccount, Username: event.target.value})}
                        label={"Username"} type="text"
                        autoComplete={""}
                        fullWidth
                      />
                    </Grid>
                  ) : null}
                  <Grid item xs={12} md={6}>
                    <Input
                      variant="standard"
                      margin="dense"
                      value={editMobileAccount.Password}
                      placeholder={"Password"}
                      onChange={(event) => setEditMobileAccount({...editMobileAccount, Password: event.target.value})}
                      label={"Password"} type={editMobileAccount.showPassword ? "text" : "password"}
                      autoComplete={"new-password"}
                      endAdornment={
                        <IconButton color="secondary" size="small" onClick={() => setEditMobileAccount({...editMobileAccount, showPassword: !editMobileAccount.showPassword})} sx={{paddingX: 1}}>
                          <i className="fa-solid fa-eye"></i>
                        </IconButton>
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
                    <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
                      <MDButton color={"secondary"} 
                        onClick={() => setEditMobileAccount({...editMobileAccount, show: false})}
                      >
                        Cancel
                      </MDButton>
                      <MDButton color={"info"} 
                        onClick={handleMobileAccountUpdate} style={{marginLeft: 10}}
                      >
                        {mobileAccount.New ? "Create" : "Update"}
                      </MDButton>
                    </MDBox>
                  </Grid>
                </Grid>
              </DialogContent>
            </Dialog>
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Card sx={{width: "100%"}}>
                  {mobileAccount.Username === "" ? (
                    <MDBox display={"flex"} justifyContent={"space-between"} alignItems={"center"} px={5} py={2}>
                      <MDTypography fontWeight={"bold"} fontSize={24}>
                        {"Mobile Account Not Available"}
                      </MDTypography>
                      <MDButton variant="gradient" color="info" onClick={() => {
                        setEditMobileAccount({...editMobileAccount, show: true});
                      }}>
                        <MDTypography fontWeight={"bold"} fontSize={18} py={0} color={"white"}>
                          {"Create"}
                        </MDTypography>
                      </MDButton>
                    </MDBox>
                  ) : (
                    <MDBox display={"flex"} justifyContent={"space-between"} alignItems={"center"} px={5} py={2}>
                      <MDTypography fontWeight={"bold"} fontSize={24}>
                        {mobileAccount.Username}
                      </MDTypography> 
                      <MDBox style={{marginLeft: "auto"}}>
                        {mobileAccount.Token !== "" ? (
                          <MDButton variant="gradient" color="warning" style={{marginRight: 10, marginTop: 5, marginBottom: 5}} onClick={handleLogout}>
                            <MDTypography fontWeight={"bold"} fontSize={18} py={0} color={"white"}>
                              {"Log Out"}
                            </MDTypography>
                          </MDButton>
                        ) : null}
                        <MDButton variant="gradient" color="error" style={{marginRight: 0, marginTop: 5, marginBottom: 5}} onClick={handleMobileAccountUpdate}>
                          <MDTypography fontWeight={"bold"} fontSize={18} py={0} color={"white"}>
                            {"Delete"}
                          </MDTypography>
                        </MDButton>
                      </MDBox>
                    </MDBox>
                  )}
                </Card>
              </Grid>
            </Grid>
          </MDBox>
        </MDBox>

        <Dialog 
          sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          PaperProps={{
            sx: { minWidth: 1000 }
          }}
          open={Boolean(dataToRender)}
          onClose={() => setDataToRender(null)}
        >
          <MDBox px={5} pt={5}>
            <MDTypography fontWeight={"bold"} fontSize={24}>
              {"Wearable Recording Viewer"}
            </MDTypography> 
            <MDBox flexDirection={"row"}>
              <MDButton variant="gradient" color="success" style={{marginRight: 5, marginTop: 5, marginBottom: 5}} onClick={handleDownloadRecording}>
                <MDTypography fontWeight={"bold"} fontSize={18} py={0} color={"white"}>
                  {"Download Recording"}
                </MDTypography>
              </MDButton>
              <MDButton variant="gradient" color="error" style={{marginRight: 0, marginTop: 5, marginBottom: 5}} onClick={handleDeleteRecording}>
                <MDTypography fontWeight={"bold"} fontSize={18} py={0} color={"white"}>
                  {"Delete Recording"}
                </MDTypography>
              </MDButton>
            </MDBox>
          </MDBox>
          <MDBox p={5} display={"flex"} alignItems={"center"} flexDirection={"column"} >
            {dataToRender ? (
              <InertiaSensorSpectrum dataToRender={dataToRender} height={1500} figureTitle={"BRAVO Wearable Data Viewer"}/>
            ) : null}
          </MDBox>
        </Dialog>

        {availableRecordings.list.length > 0 ? (
          <MDBox pt={3}>
            <MDBox>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={2}>
                          <MDTypography variant={"h6"} fontSize={24}>
                            {"Wearable Recording Viewer"}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <MDBox p={4}>
                          <FullCalendar
                            plugins={[ dayGridPlugin, interactionPlugin ]}
                            initialView={"dayGridMonth"}
                            initialDate={availableRecordings.list.length > 0 ? new Date(availableRecordings.list[availableRecordings.list.length-1].Time*1000) : null}
                            eventContent={(event) => {
                              return <>
                                <MDBox px={1} flexDirection={"column"} style={{cursor: "pointer", overflow: "hidden"}} onClick={() => {
                                  setAlert(<LoadingProgress />);
                                  SessionController.query("/api/queryMobileRecordings", {
                                    patientId: patientID, 
                                    recordingId: event.event._def.publicId,
                                    requestData: true
                                  }).then((response) => {
                                    setAvailableRecordings({...availableRecordings, current: event.event._def.publicId});
                                    setDataToRender(response.data);
                                    setAlert(null);
                                  }).catch((error) => {
                                    SessionController.displayError(error, setAlert);
                                  });
                                }}>
                                  <MDBox display={"flex"} flexDirection={"row"}>
                                    <FiberManualRecordIcon color={"info"} fontSize={"sm"} />
                                    <MDTypography display={"flex"} fontSize={9} alignItems={"center"} justifyContent={"center"}>
                                      {event.event.start.toLocaleTimeString("en-US", {hour: "2-digit", minute: "2-digit"})} {"-"} {event.event.end.toLocaleTimeString("en-US", {hour: "2-digit", minute: "2-digit"})}
                                    </MDTypography>
                                  </MDBox>
                                  <MDTypography fontSize={9}>
                                    {event.event.title}
                                  </MDTypography>
                                </MDBox>
                              </>;
                            }}
                            events={availableRecordings.list.map((recording) => {
                              return {
                                id: recording.RecordingId,
                                title: recording.RecordingLabel,
                                date: new Date(recording.Time*1000),
                                end: new Date((recording.Time + recording.Duration)*1000),
                                display: "list-item"
                              };
                            })}
                          />
                        </MDBox>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              </Grid>
            </MDBox>
          </MDBox>
        ) : null}
      </DatabaseLayout>
    </>
  );
}

export default MobileManager;
