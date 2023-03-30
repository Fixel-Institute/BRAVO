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
} from "@mui/material"

import MDBox from "components/MDBox";
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
  const { patientID, language } = controller;

  const [data, setData] = useState(false);

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
      SessionController.query("/api/queryBrainSenseSurveys", {
        id: patientID
      }).then((response) => {
        setData(response.data)
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  // Divide all PSDs by day or by channel
  useEffect(() => {
    var uniqueSurveySession = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);

      var found = false
      for (var session of uniqueSurveySession) {
        if (session.timestamp-60 < data[i]["Timestamp"] && session.timestamp >= data[i]["Timestamp"] && session.device == data[i]["DeviceName"]) {
          found = true;
          break;
        }
      }
      if (!found) {
        uniqueSurveySession.push({
          timestamp: data[i]["Timestamp"],
          device: data[i]["DeviceName"],
          value: "[" + data[i]["DeviceName"] + "] " + timestruct.toLocaleString(language),
          label: "[" + data[i]["DeviceName"] + "] " + timestruct.toLocaleString(language)
        });
      }
    }

    if (uniqueSurveySession.length > 0) {
      setViewSessions(uniqueSurveySession);
      setViewDate(uniqueSurveySession[0]);
    }

    uniqueSurveySession = [];
    for (var i = 0; i < data.length; i++) {
      const uniqueChannel = data[i]["Hemisphere"] + ` E${data[i]["Channel"][0]}-E${data[i]["Channel"][1]}`;

      var found = false;
      for (var session of uniqueSurveySession) {
        if (session.channel == uniqueChannel && session.device == data[i]["DeviceName"]) {
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
      if (data[i]["Timestamp"] > value.timestamp - 60 && data[i]["Timestamp"] <= value.timestamp && data[i]["Hemisphere"].startsWith("Left") && data[i]["DeviceName"] == value.device) {
        collectiveData.push(data[i]);
      }
    }
    setLeftDataToRender(collectiveData);

    collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      if (data[i]["Timestamp"] > value.timestamp - 60 && data[i]["Timestamp"] <= value.timestamp && data[i]["Hemisphere"].startsWith("Right") && data[i]["DeviceName"] == value.device) {
        collectiveData.push(data[i]);
      }
    }
    setRightDataToRender(collectiveData);
  };

  const setViewChannel = (value) => {
    setChannelOfView(value);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      const uniqueChannel = data[i]["Hemisphere"] + ` E${data[i]["Channel"][0]}-E${data[i]["Channel"][1]}`;
      if (value.channel == uniqueChannel && value.device == data[i]["DeviceName"]) {
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
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <SurveyFigure dataToRender={leftDataToRender} height={500} figureTitle="LeftHemisphereSurvey"/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <SurveyFigure dataToRender={rightDataToRender} height={500} figureTitle="RightHemisphereSurvey"/>
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
              <Grid item xs={12} lg={6}>
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
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <ChannelCompare dataToRender={chronicDataToCompare} height={500} figureTitle="ChannelSurveyAcrossTime"/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              ) : null}
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default BrainSenseSurvey;
