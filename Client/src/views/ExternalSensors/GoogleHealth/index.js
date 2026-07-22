/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  Card,
  Grid,
  Link,
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

import moment from "moment";
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";
import FitbitScoreTimeline from "./FitbitScoreTimeline";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function GoogleHealthDashboard() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;
  const { participant_uid } = useParams();

  const [alert, setAlert] = useState(null);
  const [data, setData] = useState(null);

  const [authenticated, setAuthenticated] = useState(0);
  const [OAuthURL, setOAuthURL] = useState(null);
  const [googleHealthTokenURL, setGoogleHealthTokenURL] = useState("");
  const [authPeriod, setAuthPeriod] = useState([]);

  useEffect(() => {
    SessionController.query("/api/requestGoogleHealthAuth", {
      RequestType: "RequestURL",
      ParticipantId: participant_uid
    }).then((response) => {
      if (!response.data.OAuthURL) {
        setAuthenticated((a) => a+1);
        setAuthPeriod(response.data.map((a) => a.map((b) => moment(new Date(b*1000+new Date().getTimezoneOffset()*60000)))))
      } else {
        setOAuthURL(response.data.OAuthURL);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  useEffect(() => {
    if (authenticated < 1) return;
    
    setAlert(<LoadingProgress />)
    SessionController.query("/api/queryGoogleHealthData", {
      RequestType: "RequestOverview",
      ParticipantId: participant_uid
    }).then((response) => {
      setData(response.data)
      setAlert(null)
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, [authenticated])

  useEffect(() => {
    if (!authenticated || !authPeriod) return;
    SessionController.query("/api/requestGoogleHealthAuth", {
      RequestType: "SetAuthPeriod",
      ParticipantId: participant_uid,
      DatePeriods: authPeriod.map((a) => a.map((b) => {
        const timestamp = new Date(b.format("YYYY-MM-DD")+"T00:00:00Z").getTime()/1000 - b.utcOffset()*60;
        return timestamp
      })),
    }).then((response) => {
      
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, [authPeriod])

  return (
    <DatabaseLayout>
      {alert}
      
      {authenticated ? (
        <MDBox>
          <Card sx={{marginTop: 5}}>
            <MDBox p={2}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <MDTypography variant="h3">
                    {"Define Data Collection Period"}
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant="h5" fontWeight="regular" color={"black"} fontSize={15}>
                    {"If multiple participants are sharing the same device, please use this section to define time period of data collection. All dates are inclusive. If empty, server will send error. "}
                  </MDTypography>

                  <MDButton variant="contained" color="info" style={{marginTop: 5}} onClick={() => {
                    setAuthPeriod((authPeriod) => {
                      return [...authPeriod, [moment(new Date()), moment(new Date())]]
                    });
                  }}>
                    {"Add Date Periods"} 
                  </MDButton>
                  
                  <MDButton variant="contained" color="error" style={{marginTop: 5, marginLeft: 5}} onClick={() => {
                    SessionController.query("/api/requestGoogleHealthAuth", {
                      RequestType: "DeleteAuthentication",
                      ParticipantId: participant_uid
                    }).then((response) => {
                      setAuthenticated(0);
                      setAuthPeriod([])
                    }).catch((error) => {
                      SessionController.displayError(error, setAlert);
                    });
                  }}>
                    {"Delete Authentication"} 
                  </MDButton>
                </Grid>
                {authPeriod.map((section, sectionIndex) => {
                return <Grid key={sectionIndex} item xs={12}>
                  <MDBox p={2} display={"flex"} flexDirection={"row"} alignItems={"center"}>
                    <MDTypography variant={"h6"} fontSize={24} pr={2}>
                      {"Date " + (sectionIndex+1).toFixed(0) + ": From"}
                    </MDTypography>
                    <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
                      <DatePicker
                        label="Start Date"
                        value={section[0]}
                        onChange={(newDate) => {
                          setAuthPeriod((authPeriod) => {
                            authPeriod[sectionIndex][0] = newDate;
                            return [...authPeriod];
                          });
                        }}
                        renderInput={(params) => <TextField {...params} />}
                      />
                    </LocalizationProvider>
                    <MDTypography variant={"h6"} fontSize={24} px={2}>
                      {"To"}
                    </MDTypography>
                    <LocalizationProvider dateAdapter={AdapterMoment}>
                      <DatePicker
                        label="End Date"
                        value={section[1]}
                        onChange={(newDate) => {
                          setAuthPeriod((authPeriod) => {
                            authPeriod[sectionIndex][1] = newDate;
                            return [...authPeriod];
                          });
                        }}
                        renderInput={(params) => <TextField {...params} />}
                      />
                    </LocalizationProvider>
                    <MDButton variant="contained" color="error" style={{marginLeft: 15}} onClick={() => {
                      setAuthPeriod((authPeriod) => {
                        authPeriod.splice(sectionIndex, 1);
                        return [...authPeriod]
                      });
                    }}>
                      {"Remove"} 
                    </MDButton>
                  </MDBox>
                </Grid>
                })}
              </Grid>
            </MDBox>
          </Card>
          <Card sx={{marginTop: 5}}>
            <MDBox p={2}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <MDTypography variant="h3">
                    {"Request Fitbit Data Update"}
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant="h5" fontWeight="regular" color={"black"} fontSize={15}>
                    {"Fitbit Data API has a request data limit of 150 Request Per Hour (Reset at xx:00), therefore, the data will be be automatically requested unless user interaction. "}
                    {"Please use the button below to request data update. Each refresh (depending on the duration of data acquisition) takes about 20 Requests to complete. "}
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDButton variant="contained" color="info" style={{marginTop: 5}} onClick={() => {
                    setAlert(<LoadingProgress />)
                    SessionController.query("/api/queryGoogleHealthData", {
                      RequestType: "RefreshGoogleHealthData",
                      ParticipantId: participant_uid
                    }).then((response) => {
                      setAuthenticated((a) => a+1);
                      setAlert(null);
                    }).catch((error) => {
                      SessionController.displayError(error, setAlert);
                    });
                  }}>
                    {"Refresh Fitbit Data"} 
                  </MDButton>
                  <MDButton variant="contained" color="primary" style={{marginTop: 5, marginLeft: 15}} onClick={() => {
                    let downloader = document.createElement('a');
                    downloader.href = SessionController.getDownloadLink("/api/queryGoogleHealthData", {
                      ParticipantId: participant_uid
                    });
                    downloader.download = 'GoogleHealthData.pkl';
                    downloader.target = '_blank';
                    downloader.click();
                  }}>
                    {"Download Google Health Data"} 
                  </MDButton>
                </Grid>
              </Grid>
            </MDBox>
            <MDBox p={2}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FitbitScoreTimeline dataToRender={data} figureTitle={"FitbitScoreTimeline"}/>
                </Grid>
              </Grid>
            </MDBox>
          </Card>
        </MDBox>
      ) : (
        <MDBox>
          <Card sx={{marginTop: 5}}>
            <MDBox p={2}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <MDTypography variant="h3">
                    {"Request Fitbit Web API Access"}
                  </MDTypography>
                </Grid>
                <Grid item xs={12}>
                  <MDTypography variant="h5" fontWeight="regular" color={"black"} fontSize={15}>
                    {"The Fitbit Dashboard Web API require OAuth 2.0 authentication for your account. Please use the Authentication Link provided below to request Authentication token. "}
                    {"Once authentication is successful, please copy the redirect URL into the textbox below to extract authentication token. "}
                  </MDTypography>
                </Grid>
                {OAuthURL ? (
                <Grid item xs={12} sx={{lineHeight: 1}}>
                  <Link href={OAuthURL} target="_blank">
                    <MDTypography variant="p" fontWeight="regular" color={"info"} fontSize={12}>
                      {OAuthURL}
                    </MDTypography>
                  </Link>
                </Grid>
                ) : null}

                {OAuthURL ? (
                <Grid item xs={12} sx={{lineHeight: 1}}>
                  <MDBox display={"flex"} flexDirection={"row"}>
                    <TextField
                      variant="standard"
                      margin="dense" id="google_health_oauth_redirect"
                      value={googleHealthTokenURL}
                      onChange={(event) => setGoogleHealthTokenURL(event.target.value)}
                      fullWidth
                    />
                    <MDButton variant="contained" color="info" style={{minWidth: 200, marginLeft: 15}} onClick={() => {
                      setAlert(<LoadingProgress />)
                      SessionController.query("/api/requestGoogleHealthAuth", {
                        RequestType: "VerifyToken",
                        ParticipantId: participant_uid,
                        TokenURL: googleHealthTokenURL
                      }).then((response) => {
                        setAlert(null);
                        setAuthenticated(true);
                      }).catch((error) => {
                        SessionController.displayError(error, setAlert);
                      });
                    }}>
                      {"Verify Token"} 
                    </MDButton>
                  </MDBox>
                </Grid>
                ) : null}
              </Grid>
            </MDBox>
          </Card>
        </MDBox>
      )}

    </DatabaseLayout>
  );
};

