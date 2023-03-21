import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Backdrop,
  LinearProgress,
  Card,
  Grid,
  Slider
} from "@mui/material"

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import MDProgress from "components/MDProgress";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import TimeFrequencyAnalysis from "../../Reports/BrainSenseStreaming/TimeFrequencyAnalysis";
import StimulationPSD from "../../Reports/BrainSenseStreaming/StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";

import TherapeuticPredictionTable from "./TherapeuticPredictionTable";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapeuticPrediction() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [data, setData] = React.useState([]);
  const [configuration, setConfiguration] = React.useState({});
  const [predictionModel, setPredictionModel] = React.useState([]);
  const [predictionToRender, setPredictionToRender] = React.useState([]);
  const [dataToRender, setDataToRender] = React.useState(false);
  const [channelInfos, setChannelInfos] = React.useState([]);
  const [leftHemispherePSD, setLeftHemispherePSD] = React.useState(false);
  const [rightHemispherePSD, setRightHemispherePSD] = React.useState(false);
  const [leftHemisphereBox, setLeftHemisphereBox] = React.useState(false);
  const [rightHemisphereBox, setRightHemisphereBox] = React.useState(false);

  const [centerFrequencyLeft, setCenterFrequencyLeft] = React.useState(0);
  const [centerFrequencyRight, setCenterFrequencyRight] = React.useState(0);
  
  const [timeFrequencyPlotHeight, setTimeFrequencyPlotHeight] = React.useState(600)
  const [alert, setAlert] = React.useState(null);

  const [processingProgress, setProcessingProgress] = React.useState({show: false, currentRecording: "", progress: 0});

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryPredictionModel", {
        id: patientID,
        requestOverview: true
      }).then((response) => {
        setContextState(dispatch, "therapeuticPredictionTableDate", null);
        setData(response.data);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const retrievePredictionModels = async () => {
    setProcessingProgress({progress: 0, currentRecording: "", show: true});
    var predictedModels = [];
    try {
      for (var i in data) {
        setProcessingProgress({progress: i / data.length * 100, currentRecording: new Date(data[i].Timestamp * 1000).toLocaleString(language, SessionController.getDateTimeOptions("DateFull")),  show: true});
        const response = await SessionController.query("/api/queryPredictionModel", {
          updatePredictionModels: true,
          id: patientID,
          recordingId: data[i].RecordingID,
        });
        predictedModels.push({...data[i], Prediction: response.data});
        setProcessingProgress({...processingProgress, progress: (i+1) / data.length * 100});
      }
      setPredictionModel([...predictedModels]);
    } catch (error) {
      console.log(error);
    }
    setProcessingProgress({progress: 0, currentRecording: "", show: false});
  };

  React.useEffect(() => {
    retrievePredictionModels();
  }, [data])

  const getRecordingData = (timestamp) => {
    var ChannelInfos = [];
    for (var i in data) {
      if (data[i].RecordingID == timestamp) {
        ChannelInfos = data[i].Channels;
      }
    }

    var centerFrequencies = [];
    for (var i in predictionModel) {
      if (predictionModel[i].RecordingID == timestamp) {
        setPredictionToRender(predictionModel[i].Prediction);
        for (var j in predictionModel[i].Prediction) {
          centerFrequencies.push(predictionModel[i].Prediction[j].CenterFrequency ? predictionModel[i].Prediction[j].CenterFrequency : 0);
        }
      }
    }
    setRecordingId(timestamp);

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryBrainSenseStreaming", {
      id: patientID, 
      recordingId: timestamp, 
      requestFrequency: centerFrequencies,
      requestData: true
    }).then((response) => {
      if (response.data.Channels.length == 2) setTimeFrequencyPlotHeight(7*200);
      else setTimeFrequencyPlotHeight(4*200);
      setChannelInfos(ChannelInfos);
      setDataToRender(response.data);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const onCenterFrequencyChange = (side, freq) => {
    var channelName = "";
    if (side === "Left") {
      for (var i in dataToRender.Channels) {
        if (dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
      SessionController.query("/api/queryPredictionModel", {
        updateStimulationPSD: true,
        id: patientID,
        recordingId: recordingId,
        channel: channelName,
        centerFrequency: freq
      }).then((response) => {
        setLeftHemisphereBox(response.data.StimPSD);
        setPredictionModel((models) => {
          for (var j in models) {
            if (models[j].RecordingID == recordingId) {
              for (var k in models[j]["Channels"]) {
                if (models[j]["Channels"][k]["Hemisphere"].startsWith("Left")) {
                  models[j].Prediction[k] = response.data.PredictionModel;
                }
              }
            }
          }
          return [...models]
        });
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    } else {
      for (var i in dataToRender.Channels) {
        if (!dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
      SessionController.query("/api/queryPredictionModel", {
        updateStimulationPSD: true,
        id: patientID,
        recordingId: recordingId,
        channel: channelName,
        centerFrequency: freq
      }).then((response) => {
        setRightHemisphereBox(response.data.StimPSD);
        for (var j in predictionModel) {
          if (predictionModel[j].RecordingID == recordingId) {
            for (var k in predictionModel[j]["Channels"]) {
              if (predictionModel[j]["Channels"][k]["Hemisphere"].startsWith("Right")) {
                predictionModel[j].Prediction[k] = response.data.PredictionModel;
              }
            }
          }
        }
        setPredictionModel([...predictionModel]);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  };

  const toggleCardiacFilter = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryBrainSenseStreaming", {
      updateCardiacFilter: !dataToRender.Info.CardiacFilter,
      id: patientID,
      recordingId: recordingId,
    }).then((response) => {
      setDataToRender(response.data);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  // Divide all PSDs by day or by channel
  React.useEffect(() => {
    for (var i in dataToRender.Channels) {
      if (dataToRender.Channels[i].endsWith("LEFT")) {
        setLeftHemispherePSD(dataToRender[dataToRender.Channels[i]].StimPSD);
        setLeftHemisphereBox(dataToRender[dataToRender.Channels[i]].StimPSD);
      } else {
        setRightHemispherePSD(dataToRender[dataToRender.Channels[i]].StimPSD);
        setRightHemisphereBox(dataToRender[dataToRender.Channels[i]].StimPSD);
      }
    }
  }, [dataToRender]);

  return (
    <>
      {alert}

      <Backdrop
        sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
        open={processingProgress.show}
        onClick={() => {}}
      >
        <MDBox display={"flex"} alignItems={"center"} flexDirection={"column"}>
          <MDTypography color={"white"} fontWeight={"bold"} fontSize={30}>
            Currently Processing Data
          </MDTypography>
          <MDTypography color={"white"} fontWeight={"bold"} fontSize={30}>
            {processingProgress.currentRecording}
          </MDTypography>
          <MDBox sx={{width: "100%"}}>
            <MDProgress color={"info"} value={processingProgress.progress} />
          </MDBox>
        </MDBox>
      </Backdrop>

      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1}>
                        {predictionModel.length > 0 ? (
                          <TherapeuticPredictionTable data={predictionModel} getRecordingData={getRecordingData}/>
                        ) : (
                          <MDTypography variant="h6" fontSize={24}>
                            {dictionary.WarningMessage.NoData[language]}
                          </MDTypography>
                        )}
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              {dataToRender && channelInfos.length > 0 ? (
                <Grid item xs={12}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} justifyContent={"space-between"} p={3}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "RawData", language)}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <TimeFrequencyAnalysis dataToRender={dataToRender} channelInfos={channelInfos} figureTitle={"TimeFrequencyAnalysis"} height={timeFrequencyPlotHeight}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {dataToRender && channelInfos.length > 0 ? (
                <Grid item xs={12}>
                  <Card>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={3}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "EffectOfStim", language)}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationPSD dataToRender={leftHemispherePSD} channelInfos={channelInfos} type={"Left"} figureTitle={"LeftStimulationPSD"} onCenterFrequencyChange={onCenterFrequencyChange} height={600}/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationBoxPlot dataToRender={leftHemisphereBox} predictionTrend={predictionToRender} channelInfos={channelInfos} type={"Left"} figureTitle={"LeftStimulationBar"} height={600}/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationPSD dataToRender={rightHemispherePSD} channelInfos={channelInfos} type={"Right"} figureTitle={"RightStimulationPSD"} onCenterFrequencyChange={onCenterFrequencyChange} height={600}/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationBoxPlot dataToRender={rightHemisphereBox} predictionTrend={predictionToRender} channelInfos={channelInfos} type={"Right"} figureTitle={"RightStimulationBar"} height={600}/>
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

export default TherapeuticPrediction;
