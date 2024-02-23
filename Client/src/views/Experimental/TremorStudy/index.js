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
import MDButton from "components/MDButton";

import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import SurveyFigure from "./SurveyFigure";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import CorrelationMatrix from "./CorrelationMatrix";
import CorrelationScatterPlot from "./CorrelationScatterPlot";

function TremorStudy() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [overview, setOverview] = useState({Annotations: []});
  const [eventPeriod, setEventPeriod] = useState("");
  const [availableDevice, setAvailableDevices] = useState({currentSensor: "", sensors: [], currentData: "", dataChannels: [] });
  
  const [spectrumResult, setSpectrumResult] = useState({});
  const [correlationIndex, setCorrelationIndex] = useState({set: false, x: 0, y: 0});
  
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/experiment/queryTremorStudyResults", {
        id: patientID, 
        requestOverview: true
      }).then((response) => {
        setOverview(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  useEffect(() => {
    if (eventPeriod) {
      setAlert(<LoadingProgress/>);
      SessionController.query("/experiment/queryTremorStudyResults", {
        id: patientID, 
        requestAccelerometerData: true,
        analysisId: overview.AnalysisID,
        resultId: overview.ResultID,
        eventPeriod: eventPeriod
      }).then((response) => {
        setData(response.data);
        setAvailableDevices({currentSensor: response.data.SensorChannels[0], sensors: response.data.SensorChannels, 
          currentData: response.data.DataChannels[0], dataChannels: response.data.DataChannels });
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [eventPeriod]);

  const queryCorrelationMatrix = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/experiment/queryTremorStudyResults", {
      id: patientID, 
      analysisId: overview.AnalysisID,
      resultId: overview.ResultID,
      requestCorrelation: true,
      sensor: availableDevice.currentSensor,
      dataChannel: availableDevice.currentData,
      eventPeriod: eventPeriod
    }).then((response) => {
      setSpectrumResult(response.data)
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleCorrelationMatrixDisplay = (point) => {
    setCorrelationIndex({set: true, x: point.x, y: point.y});
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
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {"Wearable Data Analysis (UF Tremor/Dyskinesia Study)"}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} lg={12}>
                      <MDBox p={2}>
                        <Autocomplete
                          value={eventPeriod}
                          options={overview.Annotations}
                          onChange={(event, value) => setEventPeriod(value)}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Choose Event Periods for Analysis"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                          style={{marginBottom: 25}}
                        />
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              {data ? (
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {"Accelerometer Power Spectrum"}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} lg={12}>
                      <SurveyFigure dataToRender={data.AccelerometerSpectrogram} height={500} figureTitle="AccelerometerSurveys"/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              ) : null}
              {data ? (
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {"Brain-Muscle Coherence"}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <Autocomplete
                          value={availableDevice.currentSensor}
                          options={availableDevice.sensors}
                          onChange={(event, value) => setAvailableDevices({...availableDevice, currentSensor: value})}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Select Accelerometer Sensor of Interest"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                          style={{marginBottom: 25}}
                        />
                        <Autocomplete
                          value={availableDevice.currentData}
                          options={availableDevice.dataChannels}
                          onChange={(event, value) => setAvailableDevices({...availableDevice, currentData: value})}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Select Signal Channel of Interest"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                          style={{marginBottom: 25}}
                        />
                        <MDButton size="large" variant="contained" color="info" style={{marginBottom: 3}} onClick={queryCorrelationMatrix}>
                          {"Request Data"}
                        </MDButton>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} lg={12}>
                      <CorrelationMatrix dataToRender={spectrumResult} onIndexSelect={handleCorrelationMatrixDisplay} height={600} figureTitle={"CorrelationMatrix"} />
                    </Grid>
                    {correlationIndex.set ? (
                    <Grid item xs={12} lg={12}>
                      <CorrelationScatterPlot dataToRender={spectrumResult} correlationIndex={correlationIndex} height={600} figureTitle={"CorrelationScatterPlot"} />
                    </Grid>
                    ) : null}
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

export default TremorStudy;
