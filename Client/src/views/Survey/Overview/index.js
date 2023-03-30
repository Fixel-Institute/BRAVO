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
  Grid,
  Dialog,
  DialogContent,
  DialogActions,
  TextField,
  Step,
  StepLabel,
  Stepper,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from "@mui/material";

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import MuiAlertDialog from "components/MuiAlertDialog";
import SurveyTable from "components/Tables/SurveyTable";
import RedcapLinkTable from "components/Tables/RedcapLinkTable";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SurveyList() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [surveys, setSurveys] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [newSurveyDialog, setNewSurveyDialog] = useState({surveyName: "", state: false});
  const [scheduleSurveyLinkDialog, setScheduleSurveyLinkDialog] = useState({activeStep: 0, verified: false, surveyId: "", redcapServer: "", redcapToken: "", redcapSurveyName: "", patientId: "", accountId: "", authToken: "", serviceId: "", frequency: {repeat: "daily", timestamps: []}, receiver: {type: "mobile", value: ""}, messageFormat: "", state: false});
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    SessionController.query("/api/queryAvailableSurveys").then((response) => {
      if (response.status == 200) {
        setSurveys(response.data);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });

    SessionController.query("/api/queryAvailableRedcapSchedule").then((response) => {
      if (response.status == 200) {
        setSchedules(response.data);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const handlePatientFilter = (event) => {
    setFilterOptions({value: event.currentTarget.value});
  };

  const addNewSurvey = () => {
    SessionController.query("/api/addNewSurvey", {
      name: newSurveyDialog.surveyName
    }).then((response) => {
      if (response.status == 200) {
        setSurveys([...surveys, response.data]);
      }
      setNewSurveyDialog({surveyName: "", state: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const deleteSurvey = (id) => {
    SessionController.query("/api/deleteSurvey", {
      id: id
    }).then((response) => {
      if (response.status == 200) {
        setSurveys([...surveys.filter((value) => value.url != id)]);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const verifyRedcapConnectivity = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/verifyRedcapLink", {
      redcapServer: scheduleSurveyLinkDialog.redcapServer,
      redcapSurveyName: scheduleSurveyLinkDialog.redcapSurveyName,
      redcapToken: scheduleSurveyLinkDialog.redcapToken,
      surveyId: scheduleSurveyLinkDialog.surveyId,
    }).then((response) => {
      setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, linkageId: response.data.linkageId, verified: true});
      setAlert(
        <MuiAlertDialog title={"Success"} message={"Verification Success"}
          handleClose={() => setAlert()} 
          handleConfirm={() => setAlert()}/>)
    }).catch((error) => {
      setAlert(
        <MuiAlertDialog title={"Cannot Verify"} message={"Please make sure information is correct"}
          handleClose={() => setAlert()} 
          handleConfirm={() => setAlert()}/>)
    });
  };

  const skipRedcapConnectivity = () => {
    setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, linkageId: "skip",  activeStep: scheduleSurveyLinkDialog.activeStep + 1});
  };

  const handleLastPage = () => {
    setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, activeStep: scheduleSurveyLinkDialog.activeStep - 1});
  };

  const handleNextPage = () => {
    if (scheduleSurveyLinkDialog.activeStep == 2) {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/surveySchedulerSetup", {
        linkageId: scheduleSurveyLinkDialog.linkageId,
        receiver: {
          ...scheduleSurveyLinkDialog.receiver,
          patientId: scheduleSurveyLinkDialog.patientId,
          messageFormat: scheduleSurveyLinkDialog.messageFormat
        },
        twilio: {
          authToken: scheduleSurveyLinkDialog.authToken,
          accountId: scheduleSurveyLinkDialog.accountId,
          serviceId: scheduleSurveyLinkDialog.serviceId
        },
        frequency: scheduleSurveyLinkDialog.frequency
      }).then((response) => {
        setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, show: false});
        setAlert(null);
      }).catch((error) => {
        setAlert(
          <MuiAlertDialog title={"Cannot Verify"} message={"Please make sure information is correct"}
            handleClose={() => setAlert()} 
            handleConfirm={() => setAlert()}/>)
      });
    } else {
      setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, activeStep: scheduleSurveyLinkDialog.activeStep + 1});
    }
  };

  useEffect(() => {
    const filterTimer = setTimeout(() => {
      
    }, 200);
    return () => clearTimeout(filterTimer);
  }, [filterOptions, surveys]);

  return (
    <DatabaseLayout>
      <MDBox>
        <Card sx={{marginTop: 5}}>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {dictionary.Surveys.SurveyList[language]}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6} display="flex" sx={{
                justifyContent: {
                  sm: "space-between",
                  md: "end"
                }
              }}>
                <MDInput label={dictionary.Surveys.SearchSurvey[language]} value={filterOptions.text} onChange={(value) => handlePatientFilter(value)} sx={{paddingRight: 2}}/>
                <MDButton variant="contained" color="info" onClick={() => setNewSurveyDialog({surveyName: "", state: true})}>
                  {dictionary.Surveys.AddNewSurvey[language]} 
                </MDButton>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <SurveyTable data={surveys} onDelete={deleteSurvey} />
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
      <MDBox>
        <Card sx={{marginTop: 5}}>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {"Redcap Survey Scheduler"}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6} display="flex" sx={{
                justifyContent: {
                  sm: "space-between",
                  md: "end"
                }
              }}>
                <MDButton variant="contained" color="info" onClick={() => setScheduleSurveyLinkDialog({activeStep: 0, verified: false, surveyId: "", redcapServer: "", redcapToken: "", redcapSurveyName: "", patientId: "", accountId: "", authToken: "", serviceId: "", frequency: {repeat: "daily", timestamps: []}, receiver: {type: "mobile", value: ""}, messageFormat: "", state: true})}>
                  {"Add New Schedule/Linkage"} 
                </MDButton>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <RedcapLinkTable data={schedules} onDelete={deleteSurvey} />
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>

      <Dialog open={newSurveyDialog.state} onClose={() => setNewSurveyDialog({surveyName: "", state: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {dictionary.Surveys.AddNewSurvey[language]} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <TextField
            variant="standard"
            margin="dense" id="name"
            value={newSurveyDialog.surveyName}
            onChange={(event) => setNewSurveyDialog({...newSurveyDialog, surveyName: event.target.value})}
            label={dictionary.Surveys.EnterSurveyName[language]} type="text"
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setNewSurveyDialog({surveyName: "", state: false})}>Cancel</MDButton>
          <MDButton color="info" onClick={() => addNewSurvey()}>Create</MDButton>
        </DialogActions>
      </Dialog>

      <Dialog open={scheduleSurveyLinkDialog.state} onClose={() => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, state: false})}>
        <MDBox px={2} pt={2} style={{width: "575px"}}>
          <MDTypography variant="h5">
            {"Scheduled Survey with Redcap Link"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <Stepper activeStep={scheduleSurveyLinkDialog.activeStep}>
            {["Linking Redcap Survey", "Twilio Setup", "Notification Setup"].map((label, index) => {
              const stepProps = {};
              const labelProps = {};
              return (
                <Step key={label} {...stepProps}>
                  <StepLabel {...labelProps}>{label}</StepLabel>
                </Step>
              );
            })}
          </Stepper>
          {scheduleSurveyLinkDialog.activeStep == 0 ? (
            <Grid container spacing={1} sx={{padding: 2}}>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.redcapServer}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, redcapServer: event.target.value})}
                  label={"Redcap Server Address"} type="text"
                  disabled={scheduleSurveyLinkDialog.verified} 
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.redcapToken}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, redcapToken: event.target.value})}
                  label={"Redcap Access Token (Secure)"} type="text"
                  disabled={scheduleSurveyLinkDialog.verified} 
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.surveyId}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, surveyId: event.target.value})}
                  label={"Web Survey ID"} type="text"
                  disabled={scheduleSurveyLinkDialog.verified} 
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.redcapSurveyName}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, redcapSurveyName: event.target.value})}
                  label={"Redcap Survey Identifier"} type="text"
                  disabled={scheduleSurveyLinkDialog.verified} 
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <MDButton color="info" onClick={verifyRedcapConnectivity} disabled={scheduleSurveyLinkDialog.verified} fullWidth>{"Verify Connectivity"}</MDButton>
              </Grid>
              <Grid item xs={12}>
                <MDButton color="secondary" onClick={skipRedcapConnectivity} disabled={scheduleSurveyLinkDialog.verified} fullWidth>{"Skip REDCap Link"}</MDButton>
              </Grid>
            </Grid>
          ) : null}
          {scheduleSurveyLinkDialog.activeStep == 1 ? (
            <Grid container spacing={1} sx={{padding: 2}}>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.patientId}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, patientId: event.target.value})}
                  label={"Patient Record ID"} type="text"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.receiver.value}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, receiver: {...scheduleSurveyLinkDialog.receiver, value: event.target.value}})}
                  label={"Contact Phone (+12345678910)"} type="text"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.accountId}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, accountId: event.target.value})}
                  label={"Twilio Account ID"} type="text"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.serviceId}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, serviceId: event.target.value})}
                  label={"Twilio SMS Service ID"} type="text"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="outlined"
                  margin="dense" id="name"
                  value={scheduleSurveyLinkDialog.authToken}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, authToken: event.target.value})}
                  label={"Twilio AuthToken"} type="text"
                  fullWidth
                />
              </Grid>
            </Grid>
          ) : null}
          {scheduleSurveyLinkDialog.activeStep == 2 ? (
            <Grid container spacing={1} sx={{padding: 2}}>
              <Grid item xs={12} sx={{display: "flex", flexDirection: "column"}}>
                <TextField
                  variant="outlined"
                  multiline
                  rows={4}
                  value={scheduleSurveyLinkDialog.messageFormat}
                  placeholder={"Example: Hello , please remember to fill out your survey at {%SURVEY_LINK%}."}
                  onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, messageFormat: event.target.value})}
                  label={"Automatic Message Content"} type="text"
                  fullWidth
                />
                <MDBox py={2} style={{display: "flex", flexDirection: "row"}}>

                  <MDTypography variant={"h6"} size={15}>
                    {"Repeat Mode"}
                  </MDTypography>
                  <FormControl variant="standard" sx={{ marginX: 1, minWidth: 120 }}>
                    <Select
                      value={scheduleSurveyLinkDialog.frequency.repeat}
                      onChange={(event) => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, frequency: {repeat: event.target.value, timestamps: []}})}
                    >
                      <MenuItem value={"daily"}>{"Daily"}</MenuItem>
                      <MenuItem value={"weekly"}>{"Weekly"}</MenuItem>
                    </Select>
                  </FormControl>
                </MDBox>
                {scheduleSurveyLinkDialog.frequency.timestamps.map((timestamp, index) => {
                  return <MDBox key={index} pb={2} style={{display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "space-between"}}>
                    {scheduleSurveyLinkDialog.frequency.repeat === "daily" ? (
                      <LocalizationProvider dateAdapter={AdapterMoment}>
                        <TimePicker
                          label="Local Time"
                          value={timestamp}
                          onChange={(newDate) => {
                            scheduleSurveyLinkDialog.frequency.timestamps[index] = newDate.toDate();
                            setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog})
                          }}
                          renderInput={(params) => <TextField {...params} />}
                        />
                      </LocalizationProvider>
                    ) : (<>
                      <FormControl variant="outlined" sx={{minWidth: 120 }}>
                        <Select
                          value={timestamp.getDay()}
                          sx={{ paddingTop: 1, paddingBottom: 1, width: 250 }}
                          onChange={(event) => {
                            const currentDay = timestamp.getDay();
                            scheduleSurveyLinkDialog.frequency.timestamps[index] = new Date(scheduleSurveyLinkDialog.frequency.timestamps[index].getTime() - (currentDay - event.target.value) * 24*3600000);
                            setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog});
                          }}
                        >
                          <MenuItem value={0}>{"Sunday"}</MenuItem>
                          <MenuItem value={1}>{"Monday"}</MenuItem>
                          <MenuItem value={2}>{"Tuesday"}</MenuItem>
                          <MenuItem value={3}>{"Wednesday"}</MenuItem>
                          <MenuItem value={4}>{"Thursday"}</MenuItem>
                          <MenuItem value={5}>{"Friday"}</MenuItem>
                          <MenuItem value={6}>{"Saturday"}</MenuItem>
                        </Select>
                      </FormControl>
                      <LocalizationProvider dateAdapter={AdapterMoment}>
                        <TimePicker
                          label="Local Time"
                          value={timestamp}
                          onChange={(newDate) => {
                            scheduleSurveyLinkDialog.frequency.timestamps[index] = newDate.toDate();
                            setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog})
                          }}
                          renderInput={(params) => <TextField {...params} />}
                        />
                      </LocalizationProvider>
                    </>)}
                  </MDBox>
                })}
                <MDButton color="info" onClick={() => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, frequency: {...scheduleSurveyLinkDialog.frequency, timestamps: [...scheduleSurveyLinkDialog.frequency.timestamps, new Date()]}})} fullWidth >New Timestamp</MDButton>
              </Grid>
            </Grid>
          ) : null}
        </DialogContent>
        <DialogActions style={{display: "flex"}}>
          <MDButton color="secondary" onClick={() => setScheduleSurveyLinkDialog({...scheduleSurveyLinkDialog, state: false})}>Cancel</MDButton>
          <MDButton color="error" onClick={handleLastPage} disabled={scheduleSurveyLinkDialog.activeStep == 0} style={{marginLeft: "auto"}} >Previous</MDButton>
          <MDButton color="info" onClick={handleNextPage} disabled={scheduleSurveyLinkDialog.activeStep == 0 ? !scheduleSurveyLinkDialog.verified : false}>{scheduleSurveyLinkDialog.activeStep == 2 ? "Submit" : "Next"}</MDButton>
        </DialogActions>
      </Dialog>
      {alert}
      
    </DatabaseLayout>
  );
};

