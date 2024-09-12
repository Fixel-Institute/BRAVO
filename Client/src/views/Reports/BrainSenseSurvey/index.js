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
  Autocomplete,
  Card,
  Grid,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Drawer,
  IconButton,
  Divider,
} from "@mui/material";

import { 
  Edit as EditIcon,
  KeyboardDoubleArrowUp as KeyboardDoubleArrowUpIcon,
  Settings as SettingsIcon,
  ChevronRight as ChevronRightIcon
} from "@mui/icons-material";

import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import SurveyFigure from "./SurveyFigure";
import ChannelCompare from "./ChannelCompare";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import { dictionaryLookup } from "assets/translation";

function BrainSenseSurvey() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language, user } = controller;

  const [data, setData] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState({open: false, config: {}});

  const [dateOfView, setDateOfView] = useState(null);
  const [viewSessions, setViewSessions] = useState([]);

  const [channelOfView, setChannelOfView] = useState(null);
  const [viewChannels, setViewChannels] = useState([]);

  const [leftDataToRender, setLeftDataToRender] = useState(null);
  const [rightDataToRender, setRightDataToRender] = useState(null);
  const [chronicDataToCompare, setChronicDataToCompare] = useState(null);

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryAverageNeuralActivity", {
        id: patientID
      }).then((response) => {
        setData(response.data.data)
        setDrawerOpen({...drawerOpen, config: response.data.config});
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const verifySessionInclusion = (data, criteria) => {
    if (criteria.timestamp - 120 < data.Timestamp && criteria.timestamp >= data.Timestamp && criteria.device >= data.DeviceName) {
      return (data.Channel[0] % 1 == 0 ? "Ring" : "Segmented") == criteria.segmented;
    }
    return false;
  }

  // Divide all PSDs by day or by channel
  useEffect(() => {
    var uniqueSurveySession = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);

      var found = false
      for (var session of uniqueSurveySession) {
        if (verifySessionInclusion(data[i], session)) {
          found = true;
          break;
        }
      }
      if (!found) {
        const segmented = data[i].Channel[0] % 1 == 0 ? "Ring" : "Segmented";
        uniqueSurveySession.push({
          segmented: segmented,
          timestamp: data[i]["Timestamp"],
          device: data[i]["DeviceName"],
          value: "[" + data[i]["DeviceName"] + "] " + timestruct.toLocaleString(language),
          label: "[" + data[i]["DeviceName"] + "] (" + timestruct.toLocaleString(language) + ") " + segmented + " Survey"
        });
      }
    }

    if (uniqueSurveySession.length > 0) {
      setViewSessions(uniqueSurveySession);
      setViewDate(uniqueSurveySession[0]);
    }

    uniqueSurveySession = [];
    for (var i = 0; i < data.length; i++) {
      var uniqueChannel = data[i]["CustomName"] + ` E${data[i]["Channel"][0]}`;
      if (data[i]["Channel"].length > 1) {
        uniqueChannel += `-E${data[i]["Channel"][1]}`;
      } else {
        uniqueChannel += ` Monopolar`;
      }

      var found = false;
      for (var session of uniqueSurveySession) {
        if (session.channel == uniqueChannel) {
          found = true;
        }
      }

      if (!found) {
        uniqueSurveySession.push({
          channel: uniqueChannel,
          device: data[i]["DeviceName"],
          value: "[" + data[i]["DeviceName"] + "] " + uniqueChannel,
          label: "[" + data[i]["DeviceName"] + "] " + uniqueChannel
        });
      }
    }

    if (uniqueSurveySession.length > 0) {
      setViewChannels(uniqueSurveySession);
      setViewChannel(uniqueSurveySession[0]);
    }

  }, [data]);

  const setViewDate = (value) => {
    setDateOfView(value);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      if (verifySessionInclusion(data[i], value) && data[i]["Hemisphere"].startsWith("Left")) {
        collectiveData.push(data[i]);
      }
    }
    setLeftDataToRender(collectiveData);

    collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      if (verifySessionInclusion(data[i], value) && data[i]["Hemisphere"].startsWith("Right")) {
        collectiveData.push(data[i]);
      }
    }
    setRightDataToRender(collectiveData);
  };

  const setViewChannel = (value) => {
    setChannelOfView(value);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      var uniqueChannel = data[i]["CustomName"] + ` E${data[i]["Channel"][0]}`;
      if (data[i]["Channel"].length > 1) {
        uniqueChannel += `-E${data[i]["Channel"][1]}`;
      } else {
        uniqueChannel += ` Monopolar`;
      }
      if (value.channel == uniqueChannel) {
        collectiveData.push(data[i]);
      }
    }
    setChronicDataToCompare(collectiveData);
  };

  return (
    <>
      {alert}
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    {viewSessions.length > 0 ? (<>
                      <Grid item xs={12}>
                        <MDBox p={2} lineHeight={1}>
                          <Autocomplete
                            options={viewSessions}
                            value={dateOfView}
                            onChange={(event, value) => setViewDate(value)}
                            getOptionLabel={(option) => {
                              return option.label || "";
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={dictionary.BrainSenseSurvey.Select.Session[language]}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                            disableClearable
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <SurveyFigure dataToRender={leftDataToRender} height={500} config={drawerOpen.config} figureTitle="LeftHemisphereSurvey"/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <SurveyFigure dataToRender={rightDataToRender} height={500}  config={drawerOpen.config}figureTitle="RightHemisphereSurvey"/>
                      </Grid>
                    </>) : (
                      <Grid item xs={12}>
                        <MDBox p={2}>
                          <MDTypography variant="h6" fontSize={24}>
                            {dictionary.WarningMessage.NoData[language]}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                    )}
                  </Grid>
                </Card>
              </Grid>
              {viewChannels.length > 0 ? (
              <Grid item xs={12} lg={8}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1}>
                        <Autocomplete
                          value={channelOfView}
                          options={viewChannels}
                          onChange={(event, value) => setViewChannel(value)}
                          getOptionLabel={(option) => {
                            return option.label || "";
                          }}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={dictionary.BrainSenseSurvey.Select.Channel[language]}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                          disableClearable
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <ChannelCompare dataToRender={chronicDataToCompare} height={700} config={drawerOpen.config} figureTitle="ChannelSurveyAcrossTime"/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              ) : null}
            </Grid>
            <Drawer
              sx={{
                width: 300,
                flexShrink: 0,
                '& .MuiDrawer-paper': {
                  width: 300,
                  boxSizing: 'border-box',
                },
              }}
              PaperProps={{
                sx: {
                  borderWidth: "2px",
                  borderColor: "black",
                  borderStyle: "none",
                  boxShadow: "-2px 0px 5px gray",
                }
              }}
              variant="persistent"
              anchor="right"
              open={drawerOpen.open}
            >
            <MDBox>
              <IconButton onClick={() => setDrawerOpen({...drawerOpen, open: false})}>
                <ChevronRightIcon />
                <MDTypography>
                  {"Close"}
                </MDTypography>
              </IconButton>
            </MDBox>
            <MDBox>
            <Grid container spacing={2} sx={{paddingLeft: 2, paddingRight: 2}}>
              {Object.keys(drawerOpen.config).map((key) => {
                return <Grid item xs={12} key={key} sx={{
                  wordWrap: "break-word",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word"
                }}>
                  <MDTypography fontSize={18} fontWeight={"bold"}>
                    {drawerOpen.config[key].name}
                  </MDTypography>
                  <MDTypography fontSize={15} fontWeight={"regular"}>
                    {drawerOpen.config[key].description}
                  </MDTypography>
                  <Autocomplete
                    options={drawerOpen.config[key].options}
                    value={drawerOpen.config[key].value}
                    onChange={(event, value) => setDrawerOpen((option) => {
                      option.config[key].value = value;
                      return {...option};
                    })}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                  <Divider variant="middle" />
                </Grid>
              })}
            </Grid>
            </MDBox>
            <MDBox p={3}>
              <MDButton variant={"gradient"} color={"success"} onClick={() => {
                setAlert(<LoadingProgress/>);
                SessionController.query("/api/updateSession", {
                  "BrainSenseSurvey": drawerOpen.config
                }).then(() => {
                  
                  SessionController.query("/api/queryAverageNeuralActivity", {
                    id: patientID
                  }).then((response) => {
                    setData(response.data.data)
                    setDrawerOpen({...drawerOpen, config: response.data.config});
                    setAlert(null);
                  }).catch((error) => {
                    SessionController.displayError(error, setAlert);
                  });

                }).catch((error) => {
                  SessionController.displayError(error, setAlert);
                });
                
              }} fullWidth>
                <MDTypography color={"light"}>
                  {"Update"}
                </MDTypography>
              </MDButton>
            </MDBox>
            </Drawer>
            <MDBox style={{
              position: 'sticky',
              bottom: 32,
              right: 32,
              pointerEvents: "none"
            }}>
              <SpeedDial
                ariaLabel={"SurveySpeedDial"}
                color={"info"}
                icon={<SpeedDialIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                FabProps={{
                  color: "info",
                  sx: {display: "flex", marginLeft: "auto"}
                }}
                sx={{alignItems: "end"}}
                hidden={viewSessions.length == 0}
              >
                <SpeedDialAction
                  key={"GoToTop"}
                  icon={<KeyboardDoubleArrowUpIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                  tooltipTitle={"Go to Top"}
                  onClick={() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                />
                <SpeedDialAction
                  key={"ChangeSettings"}
                  icon={<SettingsIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                  tooltipTitle={"Edit Processing Configurations"}
                  onClick={() => setDrawerOpen({...drawerOpen, open: true})}
                />
              </SpeedDial>
            </MDBox>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default BrainSenseSurvey;
