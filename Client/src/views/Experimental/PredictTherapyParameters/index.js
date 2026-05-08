/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Autocomplete,
  Drawer,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Grid,
  IconButton,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Slider
} from "@mui/material"

import { 
  ChevronRight as ChevronRightIcon,
  Settings as SettingsIcon,
  KeyboardDoubleArrowUp as KeyboardDoubleArrowUpIcon, 
  Dashboard as DashboardIcon
} from "@mui/icons-material";

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import LoadingProgress from "components/LoadingProgress";
import MuiAlertDialog from "components/MuiAlertDialog";
import FormField from "components/MDInput/FormField";

import DatabaseLayout from "layouts/DatabaseLayout";
import ConfigurationDialog from "components/ConfigurationDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function PredictTherapyParameters() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;
  const { participant_uid } = useParams();

  const [surveyList, setSurveyList] = useState({active: null, options: [], list: []});
  const [thresholdList, setThresholdList] = useState({active: null, options: [], sessions: []});
  const [recordingList, setRecordingList] = useState({active: null, options: []});

  const [surveyResults, setSurveyResults] = useState([]);
  const [surveyAIResults, setSurveyAIResults] = useState([]);
  const [surveyAIResults2026, setSurveyAIResults2026] = useState([]);
  const [betaResults, setBetaResults] = useState([]);

  const [drawerOpen, setDrawerOpen] = useState({open: false, config: {}});
  const [alert, setAlert] = useState(null);

  const queryAvailableSessions = async () => {
    setAlert(<LoadingProgress/>);
    try {
      const surveyResponse = await SessionController.query("/api/queryAIModels", {
        RequestType: "RequestQualifyRecordings",
        ModelType: "Survey-based Contact Selection (Lavu et. al., 2025)",
        ParticipantId: participant_uid,
      });
      surveyResponse.data.sort((a, b) => b.Date - a.Date);
      let recordingDates = [];
      for (let i = 0; i < surveyResponse.data.length; i++) {
        if (!recordingDates.includes(new Date(surveyResponse.data[i].Date*1000).toLocaleDateString("en-US", {month: '2-digit', day: '2-digit', year: 'numeric'}))) {
          recordingDates.push(new Date(surveyResponse.data[i].Date*1000).toLocaleDateString("en-US", {month: '2-digit', day: '2-digit', year: 'numeric'}));
        }
        surveyResponse.data[i].Label = `${new Date(surveyResponse.data[i].Date*1000).toLocaleDateString("en-US", {month: '2-digit', day: '2-digit', year: 'numeric'})}`;
      }
      setSurveyList({active: recordingDates.length > 0 ? recordingDates[0] : null, options: recordingDates, list: surveyResponse.data});

      const betaResponse = await SessionController.query("/api/queryAIModels", {
        RequestType: "RequestQualifyRecordings",
        ModelType: "Automated Beta Detection (BRAVO)",
        ParticipantId: participant_uid,
      });
      let betaRecordingDates = [];
      for (let i = 0; i < betaResponse.data.length; i++) {
        let uniqueLabel = betaResponse.data[i].Date + " | " + betaResponse.data[i].TherapyParameters;
        if (!betaRecordingDates.includes(uniqueLabel)) {
          betaRecordingDates.push(uniqueLabel);
        }
      }

      let availableSessions = [];
      for (let i = 0; i < betaRecordingDates.length; i++) {
        let sensingTargets = {};
        for (let j = 0; j < betaResponse.data.length; j++) {
          if (betaResponse.data[j].Date + " | " + betaResponse.data[j].TherapyParameters === betaRecordingDates[i]) {
            const target = betaResponse.data[j].Contact.replace(" E01-E02", "").replace(" E01", "").replace(" E02", "");
            if (!sensingTargets[target]) {
              sensingTargets[target] = [];
            }
            if (betaResponse.data[j].Contact.endsWith(" E01")) {
              sensingTargets[target].push("E01");
            } else if (betaResponse.data[j].Contact.endsWith(" E02")) {
              sensingTargets[target].push("E02");
            }
          }
        }

        for (let target in sensingTargets) {
          if (sensingTargets[target].length > 1) {
            availableSessions.push({
              Date: betaRecordingDates[i].split(" | ")[0],
              TherapyParameters: betaRecordingDates[i].split(" | ")[1],
              Target: target,
            });
          }
        }
      }

      let uniqueAvailableSessions = [];
      for (let i = 0; i < availableSessions.length; i++) {
        if (!uniqueAvailableSessions.includes(availableSessions[i].Date)) {
          uniqueAvailableSessions.push(availableSessions[i].Date);
        }
      }
      setThresholdList({active: uniqueAvailableSessions.length > 0 ? uniqueAvailableSessions[0] : null, options: uniqueAvailableSessions, sessions: availableSessions});
      

      setAlert(null);
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  }

  const aggregatedSurveyPredictions = async () => {
    setAlert(<LoadingProgress/>);
    let results = {};
    for (let i = 0; i < surveyList.list.length; i++) {
      if (surveyList.list[i].Label === surveyList.active) {
        const response = await SessionController.query("/api/queryAIModels", {
          RequestType: "RequestAIResult",
          ModelType: "Survey-based Contact Selection (Lavu et. al., 2025)",
          ParticipantId: participant_uid,
          RecordingId: surveyList.list[i].Id,
        });
        for (let target in response.data) {
          if (!results[target]) {
            results[target] = {E01: 0, E02: 0, Total: 0}
          }
          if (response.data[target][0] == 0) {
            results[target].E01 += 1;
          } else if (response.data[target][0] == 1) {
            results[target].E02 += 1;
          }
          results[target].Total += 1;
        }
      }
    }

    setSurveyAIResults(() => {
      let options = [];
      for (let target in results) {
        options.push({
          target: target,
          E01: results[target].E01,
          E02: results[target].E02,
          E01_Percent: (results[target].E01 / results[target].Total * 100).toFixed(1),
          E02_Percent: (results[target].E02 / results[target].Total * 100).toFixed(1),
        });
      }
      return options; 
    });

    let results2026 = {};
    for (let i = 0; i < surveyList.list.length; i++) {
      if (surveyList.list[i].Label === surveyList.active) {
        const response = await SessionController.query("/api/queryAIModels", {
          RequestType: "RequestAIResult",
          ModelType: "Survey-based Contact Selection (Wong et. al., 2026)",
          ParticipantId: participant_uid,
          RecordingId: surveyList.list[i].Id,
        });
        for (let target in response.data) {
          if (!results2026[target]) {
            results2026[target] = {E01: 0, E02: 0, Total: 0}
          }
          if (response.data[target][0] == 0) {
            results2026[target].E01 += 1;
          } else if (response.data[target][0] == 1) {
            results2026[target].E02 += 1;
          }
          results2026[target].Total += 1;
        }
      }
    }

    setSurveyAIResults2026(() => {
      let options = [];
      for (let target in results2026) {
        options.push({
          target: target,
          E01: results2026[target].E01,
          E02: results2026[target].E02,
          E01_Percent: (results2026[target].E01 / results2026[target].Total * 100).toFixed(1),
          E02_Percent: (results2026[target].E02 / results2026[target].Total * 100).toFixed(1),
        });
      }
      return options; 
    });

    let betaPeakResults = {}
    for (let i = 0; i < surveyList.list.length; i++) {
      if (surveyList.list[i].Label === surveyList.active) {
        const response = await SessionController.query("/api/queryAIModels", {
          RequestType: "RequestAIResult",
          ModelType: "Peak Beta Power in Survey",
          ParticipantId: participant_uid,
          RecordingId: surveyList.list[i].Id,
        });
        
        let resultComparison = {};
        for (let j = 0; j < response.data.Channels.length; j++) {
          const channelSplit = response.data.Channels[j].split(" ");
          const channel = channelSplit[channelSplit.length - 1];
          if (channel == "E00-E02" || channel == "E01-E03") {
            const target = response.data.Channels[j].replace(" "+channel, "");
            if (!resultComparison[target]) {
              resultComparison[target] = {E01: 0, E02: 0, Total: 0}
            }
            if (response.data.Channels[j].endsWith(" E00-E02")) {
              resultComparison[target].E01 = response.data.BandPowers[j].Beta.Power;
            } else if (response.data.Channels[j].endsWith(" E01-E03")) {
              resultComparison[target].E02 += response.data.BandPowers[j].Beta.Power;
            }
          }
        }
        
        for (let target in resultComparison) {
          if (!betaPeakResults[target]) {
            betaPeakResults[target] = {E01: 0, E02: 0, Total: 0}
          }
          if (resultComparison[target].E01 > resultComparison[target].E02) {
            betaPeakResults[target].E01 += 1;
          } else if (resultComparison[target].E01 < resultComparison[target].E02) {
            betaPeakResults[target].E02 += 1;
          }
          betaPeakResults[target].Total += 1;
        }
      }
    }
    setSurveyResults(() => {
      let options = [];
      for (let target in betaPeakResults) {
        options.push({
          target: target,
          E01: betaPeakResults[target].E01,
          E02: betaPeakResults[target].E02,
          E01_Percent: (betaPeakResults[target].E01 / betaPeakResults[target].Total * 100).toFixed(1),
          E02_Percent: (betaPeakResults[target].E02 / betaPeakResults[target].Total * 100).toFixed(1),
        });
      }
      return options; 
    });

    setAlert(null);
  };

  const matchedRequests = (request, listOfRequests) => {
    for (let i = 0; i < listOfRequests.length; i++) {
      if (request.Date === listOfRequests[i].Date && request.TherapyParameters === listOfRequests[i].TherapyParameters && request.Target === listOfRequests[i].Target) {
        return true;
      }
    }
    return false;
  }

  const aggregatedBetaThresholdPredictions = async () => {
    setAlert(<LoadingProgress/>);

    let uniqueRequests = [];
    for (let i = 0; i < thresholdList.sessions.length; i++) {
      if (thresholdList.sessions[i].Date === thresholdList.active) {
        if (!matchedRequests(thresholdList.sessions[i], uniqueRequests)) {
          uniqueRequests.push(thresholdList.sessions[i]);
        }
      }
    }

    let results = [];
    for (let i = 0; i < uniqueRequests.length; i++) {
      const response = await SessionController.query("/api/queryAIModels", {
        RequestType: "RequestAIResult",
        ModelType: "Automated Beta Detection (BRAVO)",
        ParticipantId: participant_uid,
        RecordingType: uniqueRequests[i].Date,
        TherapyParameters: uniqueRequests[i].TherapyParameters,
        Contact: uniqueRequests[i].Target,
      });
      
      let result = [];
      for (let j = 0; j < response.data.length; j++) {
        const contact = response.data[j].Contact.replace(uniqueRequests[i].Target + " ", "");
        if (contact == "E01" || contact == "E02") {
          result.push({
            Contact: contact,
            BetaFrequency: response.data[j].BetaStats.BetaFrequency,
            Threshold: -response.data[j].BetaStats.BetaThreshold.Threshold,
            BaselinePower: response.data[j].BetaStats.BaselineBetaPower,
            AmplitudeOnChange: response.data[j].BetaStats.BetaThreshold.Amplitude,
            MinimumBetaAmplitude: response.data[j].BetaStats.MinBeta.Amplitude,
          });
        }
      }

      if (result.length > 1) {
        result.sort((a, b) => a.Contact.localeCompare(b.Contact));
        results.push({target: uniqueRequests[i].Target, results: result});
      }
    }
    setBetaResults(results);

    setAlert(null);
  };

  useEffect(() => {
    if (!participant_uid) {
      navigate("/database", {replace: false});
      return;
    }
    setContextState(dispatch, "report", "CustomizedAnalysis");

    queryAvailableSessions();
  }, [participant_uid]);

  useEffect(() => {
    if (!surveyList.active) return;

    aggregatedSurveyPredictions();
  }, [participant_uid, surveyList.active]);

  useEffect(( ) => {
    if (!thresholdList.active) return;

    aggregatedBetaThresholdPredictions();
  }, [participant_uid, thresholdList.active])

  return (
    <DatabaseLayout>
      {alert}
      <MDBox pt={3}>
        <MDBox mb={3}>
          <Card sx={{width: "100%"}}>
            <MDBox p={2}>
              <MDTypography variant="h4" fontWeight="bold">
                {"Prediction Results (Latest)"}
              </MDTypography>
            </MDBox>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <MDBox px={2} pt={2} lineHeight={1}>
                  <MDTypography variant="h6" fontSize={20}>
                    {"Survey-based AI Contact Selection (Wong 2026)"}
                  </MDTypography>
                </MDBox>
                <MDBox px={2} pb={2} lineHeight={1}>
                  <Autocomplete
                    value={surveyList.active}
                    options={surveyList.options}
                    onChange={(event, value) => {
                      setSurveyList({...surveyList, active: value})
                    }}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        label={"Select Session Date"}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                    disableClearable
                  />
                </MDBox>
                <MDBox px={2} pb={2} lineHeight={1}>
                  {surveyAIResults2026.map((result, index) => (
                    <MDBox key={index} mb={2}>
                      <MDTypography variant="h6" fontSize={18}>
                        {`Target: ${result.target}`}
                      </MDTypography>
                      <MDTypography variant="body2" color={"error"} fontSize={20}>
                        <b>{`Suggested Contact: ` + (result.E01 > result.E02 ? "E01" : result.E02 > result.E01 ? "E02" : "Tie")}</b>
                      </MDTypography>
                    </MDBox>
                  ))}
                </MDBox>
              </Grid>
              <Grid item xs={6}>
                <MDBox px={2} pt={2} lineHeight={1}>
                  <MDTypography variant="h6" fontSize={20}>
                    {"Survey-based Contact Selection (Peak Beta Method)"}
                  </MDTypography>
                </MDBox>
                <MDBox px={2} pb={2} lineHeight={1}>
                  <Autocomplete
                    value={surveyList.active}
                    options={surveyList.options}
                    onChange={(event, value) => {
                      setSurveyList({...surveyList, active: value})
                    }}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        label={"Select Session Date"}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                    disableClearable
                  />
                </MDBox>
                <MDBox px={2} pb={2} lineHeight={1}>
                  {surveyResults.map((result, index) => (
                    <MDBox key={index} mb={2}>
                      <MDTypography variant="h6" fontSize={18}>
                        {`Target: ${result.target}`}
                      </MDTypography>
                      <MDTypography variant="body2" color={"error"} fontSize={20}>
                        <b>{`Suggested Contact: ` + (result.E01 > result.E02 ? "E01" : result.E02 > result.E01 ? "E02" : "Tie")}</b>
                      </MDTypography>
                    </MDBox>
                  ))}
                </MDBox>
              </Grid>
            </Grid>
          </Card> 
        </MDBox>
        <MDBox>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                      <MDTypography variant="h6" fontSize={24}>
                        {"Survey-based Contact Selection (Lavu et. al., 2025)"}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      {surveyAIResults.length === 0 ? (
                        <MDTypography variant="body2" color="text">
                          {"No survey results found for the selected date."}
                        </MDTypography>
                      ) : (
                        surveyAIResults.map((result, index) => (
                          <MDBox key={index} mb={2}>
                            <MDTypography variant="h6" fontSize={18}>
                              {`Target: ${result.target}`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E01 > result.E02 ? "error" : "text"}>
                              {`Contact E01: ${result.E01} selections (${result.E01_Percent}%)`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E02 > result.E01 ? "error" : "text"}>
                              {`Contact E02: ${result.E02} selections (${result.E02_Percent}%)`}
                            </MDTypography>
                          </MDBox>
                        ))
                      )}
                    </MDBox>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                      <MDTypography variant="h6" fontSize={24}>
                        {"Survey-based Contact Selection (Wong et. al., 2026)"}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      {surveyAIResults2026.length === 0 ? (
                        <MDTypography variant="body2" color="text">
                          {"No survey results found for the selected date."}
                        </MDTypography>
                      ) : (
                        surveyAIResults2026.map((result, index) => (
                          <MDBox key={index} mb={2}>
                            <MDTypography variant="h6" fontSize={18}>
                              {`Target: ${result.target}`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E01 > result.E02 ? "error" : "text"}>
                              {`Contact E01: ${result.E01} selections (${result.E01_Percent}%)`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E02 > result.E01 ? "error" : "text"}>
                              {`Contact E02: ${result.E02} selections (${result.E02_Percent}%)`}
                            </MDTypography>
                          </MDBox>
                        ))
                      )}
                    </MDBox>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                      <MDTypography variant="h6" fontSize={24}>
                        {"Survey-based Contact Selection (Survey Peak Beta Detection)"}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      {surveyResults.length === 0 ? (
                        <MDTypography variant="body2" color="text">
                          {"No survey results found for the selected date."}
                        </MDTypography>
                      ) : (
                        surveyResults.map((result, index) => (
                          <MDBox key={index} mb={2}>
                            <MDTypography variant="h6" fontSize={18}>
                              {`Target: ${result.target}`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E01 > result.E02 ? "error" : "text"}>
                              {`Contact E01: ${result.E01} selections (${result.E01_Percent}%)`}
                            </MDTypography>
                            <MDTypography variant="body2" color={result.E02 > result.E01 ? "error" : "text"}>
                              {`Contact E02: ${result.E02} selections (${result.E02_Percent}%)`}
                            </MDTypography>
                          </MDBox>
                        ))
                      )}
                    </MDBox>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                      <MDTypography variant="h6" fontSize={24}>
                        {"Beta Desynchronization Detection (BRAVO Method)"}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox p={2}>
                      {betaResults.length === 0 ? (
                        <MDTypography variant="body2" color="text">
                          {"No beta detection results found for the selected recording."}
                        </MDTypography>
                      ) : (
                        betaResults.map((result, index) => (
                          <MDBox key={index} mb={2}>
                            <MDTypography variant="h6" fontSize={18}>
                              {`Target: ${result.target}`}
                            </MDTypography>
                            <Grid container spacing={2}>
                              {result.results.map((contactResult, cIndex) => {
                                const otherIndex = cIndex === 0 ? 1 : 0;

                                return <Grid item xs={12} md={6} key={cIndex}>
                                  <MDBox border={1} borderRadius={2} borderColor="grey.300" p={2}>
                                    <MDTypography variant="subtitle1" fontSize={16} mb={1}>
                                      {`Contact: ${contactResult.Contact}`}
                                    </MDTypography>
                                    <MDTypography variant="body2" color="text">
                                      {`Beta Frequency: ${contactResult.BetaFrequency.toFixed(2)} Hz`}
                                    </MDTypography>
                                    <MDTypography variant="body2" color="text">
                                      {`Threshold: ${contactResult.Threshold.toFixed(2)} µV²/Hz`}
                                    </MDTypography>
                                    <MDTypography variant="body2" color="text">
                                      {`Baseline Beta Power: ${contactResult.BaselinePower.toFixed(2)} µV²/Hz`}
                                    </MDTypography>
                                    <MDTypography variant="body2" color="text">
                                      {`Amplitude on First Reduction: ${contactResult.AmplitudeOnChange.toFixed(2)} mA`}
                                    </MDTypography>
                                    <MDTypography variant="body2" color="text">
                                      {`Amplitude on Minimum Beta: ${contactResult.MinimumBetaAmplitude.toFixed(2)} mA`}
                                    </MDTypography>
                                  </MDBox>
                                </Grid>
                              })} 
                            </Grid>
                          </MDBox>
                        ))
                      )}
                    </MDBox>
                  </Grid>
                </Grid>
              </Card>
            </Grid>
          </Grid>
        </MDBox>
      </MDBox>
    </DatabaseLayout>
  );
}

export default PredictTherapyParameters;
