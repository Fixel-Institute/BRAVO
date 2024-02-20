/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

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

import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";

import TherapeuticPredictionTable from "./TherapeuticPredictionTable";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapeuticPrediction() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [data, setData] = React.useState([]);
  const [predictionModel, setPredictionModel] = React.useState([]);
  const [predictionToRender, setPredictionToRender] = React.useState([]);
  const [annotations, setAnnotations] = React.useState([]);
  const [dataToRender, setDataToRender] = React.useState(false);
  const [channelInfos, setChannelInfos] = React.useState([]);
  const [channelPSDs, setChannelPSDs] = React.useState([]);

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
          recordingId: data[i].AnalysisID,
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
      if (data[i].AnalysisID == timestamp) {
        ChannelInfos = data[i].Channels;
      }
    }
    var centerFrequencies = [];
    for (var i in predictionModel) {
      if (predictionModel[i].AnalysisID == timestamp) {
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
      setChannelInfos(ChannelInfos);
      setDataToRender(response.data);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };
  
  React.useEffect(() => {
    if (dataToRender.Stream) {
      setChannelPSDs(dataToRender.Stream.map((data) => data.StimPSD));
    } else {
      setChannelPSDs([]);
    }
  }, [dataToRender]);

  const onCenterFrequencyChange = (side, freq) => {
    var reference = "Ipsilateral";
    
    SessionController.query("/api/queryBrainSenseStreaming", {
      updateStimulationPSD: true,
      id: patientID,
      recordingId: recordingId,
      channel: side,
      centerFrequency: freq,
      stimulationReference: reference
    }).then((response) => {
      setChannelPSDs((channelPSDs) => {
        for (let i in channelInfos) {
          if (channelInfos[i] == side) {
            channelPSDs[i] = response.data;
          }
        }
        return [...channelPSDs];
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleAddEvent = async (eventInfo) => {
    try {
      const response = await SessionController.query("/api/queryCustomAnnotations", {
        id: patientID,
        addEvent: true,
        name: eventInfo.name,
        time: eventInfo.time / 1000,
        type: "Streaming",
        duration: parseFloat(eventInfo.duration)
      });

      if (response.status == 200) {
        setDataToRender((dataToRender) => {
          dataToRender.Annotations = [...dataToRender.Annotations, {
            Time: eventInfo.time / 1000,
            Name: eventInfo.name,
            Duration: parseFloat(eventInfo.duration)
          }];
          return {...dataToRender};
        });

        setAnnotations((annotations) => {
          if (!annotations.includes(eventInfo.name)) {
            annotations.push(eventInfo.name);
          }
          return [...annotations];
        });
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const handleDeleteEvent = async (eventInfo) => {
    if (dataToRender.Annotations.length > 0) {
      eventInfo.targetInfo = eventInfo;
      eventInfo.targetInfo.timeDiff = 10;
    }

    for (let i = 0; i < dataToRender.Annotations.length; i++) {
      let absoluteDiffTime = Math.abs(dataToRender.Annotations[i].Time - eventInfo.time/1000);
      if (absoluteDiffTime < eventInfo.targetInfo.timeDiff) {
        eventInfo.targetInfo = dataToRender.Annotations[i];
        eventInfo.targetInfo.timeDiff = absoluteDiffTime;
      }
    }
    
    if (eventInfo.targetInfo.timeDiff < 10) {
      setAlert(<MuiAlertDialog 
        title={`Remove ${eventInfo.targetInfo.Name} Event`}
        message={`Are you sure you want to delete the entry [${eventInfo.targetInfo.Name}] @ ${new Date(eventInfo.targetInfo.Time*1000)} ?`}
        confirmText={"YES"}
        denyText={"NO"}
        denyButton
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => {
          SessionController.query("/api/queryCustomAnnotations", {
            id: patientID,
            deleteEvent: true,
            name: eventInfo.targetInfo.Name,
            time: eventInfo.targetInfo.Time
          }).then(() => {
            setDataToRender((dataToRender) => {
              dataToRender.Annotations = dataToRender.Annotations.filter((a) => {
                if (a.Name == eventInfo.targetInfo.Name && a.Time == eventInfo.targetInfo.Time && a.Duration == eventInfo.targetInfo.Duration) {
                  return false;
                }
                return true;
              })
              return {...dataToRender};
            });
            setAlert(null);
          }).catch((error) => {
            SessionController.displayError(error, setAlert);
          });
        }}
      />)
    }
  }

  const handleAdjustAlignment = async (alignment) => {
    try {
      const response = await SessionController.query("/api/updateBrainSenseStream", {
        id: patientID,
        recordingId: recordingId,
        adjustAlignment: true,
        alignment: alignment
      });

      if (response.status == 200) {
        return true;
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  }

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
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                              {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "RawData", language)}
                            </MDTypography>
                          </MDBox>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <TimeFrequencyAnalysis dataToRender={dataToRender} channelInfos={channelInfos} 
                          handleAddEvent={handleAddEvent} handleDeleteEvent={handleDeleteEvent} handleAdjustAlignment={handleAdjustAlignment} annotations={annotations}
                          figureTitle={"TimeFrequencyAnalysis"} height={700}/>
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
                      {channelPSDs.map((channelData, index) => {
                        if (!channelInfos[index]) return;
                        return <React.Fragment key={index}>
                          <Grid item xs={12} lg={6}>
                            <MDBox display={"flex"} flexDirection={"column"}>
                              <StimulationPSD dataToRender={channelData} channelInfos={channelInfos[index]} type={"Left"} figureTitle={channelInfos[index].Hemisphere + index.toFixed(0) + " PSD"} onCenterFrequencyChange={onCenterFrequencyChange} height={600}/>
                            </MDBox>
                          </Grid>
                          <Grid item xs={12} lg={6}>
                            <StimulationBoxPlot dataToRender={channelData} channelInfos={channelInfos[index]} type={"Left"} figureTitle={channelInfos[index].Hemisphere + index.toFixed(0) + " Box"} height={600}/>
                          </Grid>
                        </React.Fragment>
                      })}
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
