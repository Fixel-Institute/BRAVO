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
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Grid,
  Slider
} from "@mui/material"

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import BrainSenseStreamingTable from "components/Tables/StreamingTable/BrainSenseStreamingTable";
import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

const StimulationReferenceButton = ({value, onChange}) => {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  return (
    <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}
      sx={{ paddingLeft: 5, paddingRight: 5 }}>
      <MDTypography variant={"h6"} fontSize={18}>
        {dictionaryLookup(dictionary.BrainSenseStreaming.Table, "Reference", language)}{": "}
      </MDTypography>
      <ToggleButtonGroup
        color="info"
        size="small"
        value={value}
        exclusive
        onChange={onChange}
        aria-label="Stimulation Reference: "
        sx={{ paddingLeft: 2, }}
      >
        <ToggleButton value="Ipsilateral" sx={{minWidth: 80}}>
          <MDTypography variant={"h6"} fontSize={15}>
            {"Self"}
          </MDTypography>
        </ToggleButton>
        <ToggleButton value="Contralateral" sx={{minWidth: 80}}>
          <MDTypography variant={"h6"} fontSize={15}>
            {"Others"}
          </MDTypography>
        </ToggleButton>
      </ToggleButtonGroup>
    </MDBox>
  )
}

function BrainSenseStreaming() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [data, setData] = React.useState([]);
  const [configuration, setConfiguration] = React.useState({});
  const [dataToRender, setDataToRender] = React.useState(false);
  const [channelInfos, setChannelInfos] = React.useState([]);
  const [leftHemispherePSD, setLeftHemispherePSD] = React.useState(false);
  const [rightHemispherePSD, setRightHemispherePSD] = React.useState(false);
  const [leftHemisphereBox, setLeftHemisphereBox] = React.useState(false);
  const [rightHemisphereBox, setRightHemisphereBox] = React.useState(false);

  const [centerFrequencyLeft, setCenterFrequencyLeft] = React.useState(0);
  const [centerFrequencyRight, setCenterFrequencyRight] = React.useState(0);

  const [referenceType, setReferenceType] = React.useState(["Ipsilateral","Ipsilateral"]);
  
  const [timeFrequencyPlotHeight, setTimeFrequencyPlotHeight] = React.useState(600)
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryBrainSenseStreaming", {
        id: patientID,
        requestOverview: true,
      }).then((response) => {
        setData(response.data.streamingData);
        setConfiguration(response.data.configuration);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const getRecordingData = (timestamp) => {
    var ChannelInfos = [];
    for (var i in data) {
      if (data[i].RecordingID == timestamp) {
        ChannelInfos = data[i].Channels;
      }
    }
    setRecordingId(timestamp);

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryBrainSenseStreaming", {
      id: patientID, 
      recordingId: timestamp, 
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
  
  const handleMerge = async (toggleMerge) => {
    try {
      let mergeResponse = await SessionController.query("/api/updateBrainSenseStream", {
        mergeRecordings: toggleMerge.merge
      });
      if (mergeResponse.status == 200) {
        const response = await SessionController.query("/api/queryBrainSenseStreaming", {
          id: patientID,
          requestOverview: true,
        });
        setData(response.data.streamingData);
        setConfiguration(response.data.configuration);
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const onCenterFrequencyChange = (side, freq) => {
    var channelName = "";
    var reference = "Ipsilateral";
    if (side === "Left") {
      reference = referenceType[0];
      for (var i in dataToRender.Channels) {
        if (dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
      SessionController.query("/api/queryBrainSenseStreaming", {
        updateStimulationPSD: true,
        id: patientID,
        recordingId: recordingId,
        channel: channelName,
        centerFrequency: freq,
        stimulationReference: reference
      }).then((response) => {
        setLeftHemisphereBox(response.data);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    } else {
      reference = referenceType[1];
      for (var i in dataToRender.Channels) {
        if (!dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
      SessionController.query("/api/queryBrainSenseStreaming", {
        updateStimulationPSD: true,
        id: patientID,
        recordingId: recordingId,
        channel: channelName,
        centerFrequency: freq,
        stimulationReference: reference
      }).then((response) => {
        setRightHemisphereBox(response.data);
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
  };

  const toggleWaveletTransform = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryBrainSenseStreaming", {
      updateWaveletTransform: configuration.SpectrogramMethod.value === "Wavelet" ? "Spectrogram" : "Wavelet",
      id: patientID,
      recordingId: recordingId,
    }).then((response) => {
      setDataToRender(response.data);
      setConfiguration({
        ...configuration,
        SpectrogramMethod: {
          ...configuration.SpectrogramMethod,
          value: configuration.SpectrogramMethod.value === "Wavelet" ? "Spectrogram" : "Wavelet"
        }
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handlePSDUpdate = (reference, side) => {
    if (channelInfos.length == 1) return;
    
    let channelName = "";
    if (side == "Left") {
      for (var i in dataToRender.Channels) {
        if (dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
    } else {
      for (var i in dataToRender.Channels) {
        if (!dataToRender.Channels[i].endsWith("LEFT")) {
          channelName = dataToRender.Channels[i];
        }
      }
    }

    SessionController.query("/api/queryBrainSenseStreaming", {
      updateStimulationPSD: true,
      id: patientID,
      recordingId: recordingId,
      channel: channelName,
      centerFrequency: 22,
      stimulationReference: reference

    }).then((response) => {
      if (side == "Left") {
        console.log(response.data)
        setLeftHemispherePSD(response.data);
        setLeftHemisphereBox(response.data);
      } else {
        setRightHemispherePSD(response.data);
        setRightHemisphereBox(response.data);
      }

      setReferenceType((referenceType) => {
        referenceType[side == "Left" ? 0 : 1] = reference;
        return [...referenceType];
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  const exportCurrentStream = () => {
    var csvData = "Time"
    for (var i = 0; i < dataToRender["Channels"].length; i++) {
      csvData += "," + dataToRender["Channels"][i] + " Raw";
      csvData += "," + dataToRender["Channels"][i] + " Stimulation";
    }
    csvData += "\n";
  
    for (var i = 0; i < dataToRender[dataToRender["Channels"][0]]["Time"].length; i++) {
      csvData += dataToRender[dataToRender["Channels"][0]]["Time"][i] + dataToRender.Timestamp;
      for (var j = 0; j < dataToRender["Channels"].length; j++) {
        csvData += "," + dataToRender[dataToRender["Channels"][j]]["RawData"][i];
        for (var k = 0; k < dataToRender["Stimulation"].length; k++) {
          if (dataToRender["Stimulation"][k]["Name"] == dataToRender["Channels"][j]) {
            for (var l = 0; l < dataToRender["Stimulation"][k]["Amplitude"].length; l++) {
              if (dataToRender["Stimulation"][k]["Time"][l] > dataToRender[dataToRender["Channels"][0]]["Time"][i]) {
                break;
              }
            }
            if (l == dataToRender["Stimulation"][k]["Amplitude"].length) {
              csvData += "," + dataToRender["Stimulation"][k]["Amplitude"][l-1];
            } else {
              csvData += "," + dataToRender["Stimulation"][k]["Amplitude"][l];
            }
          }
        }
      }
      csvData += "\n";
    }
    
    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'BrainSenseStreamExport.csv';
    downloader.click();
  };

  const adaptiveClosedLoopParameters = (therapy) => {
    var adaptiveState = false;
    if (therapy.Left) {
      if (therapy.Left.StreamingAdaptiveMode) {
        adaptiveState = true;
      }
    }
    if (therapy.Right) {
      if (therapy.Right.StreamingAdaptiveMode) {
        adaptiveState = true;
      }
    }

    if (!adaptiveState) {
      return null;
    }
    
    return (
      <MDBox px={3} pb={3}>
        <MDTypography variant={"h5"} fontSize={24}>
          {dictionaryLookup(dictionary.BrainSenseStreaming.Table, "AdaptiveMode", language)}
        </MDTypography>
        <MDBox display={"flex"} flexDirection={"row"}>
          {therapy.Left ? (
            <MDBox flexDirection={"column"}>
              <MDTypography variant={"h5"} fontSize={18}>
                {dictionaryLookup(dictionary.BrainSenseStreaming.Table, "StreamingTableLeftHemisphere", language)}
              </MDTypography>
              <MDTypography variant={"h6"} fontSize={15}>
                {dictionaryLookup(dictionary.BrainSenseStreaming.Table, therapy.Left.AdaptiveTherapyStatus, language)}
              </MDTypography>
              <MDTypography variant={"h6"} fontSize={18}>
                {"Closed-Loop Threshold: "} {}
              </MDTypography>
            </MDBox>
          ) : null}
          {therapy.Right ? (
            <MDBox pt={2} flexDirection={"column"}>
              <MDTypography variant={"h5"} fontSize={21}>
                {channelInfos.filter((channel) => {
                  return channel.Hemisphere.startsWith("Right");
                }).map((channel) => {
                  return channel.CustomName;
                })[0]}
              </MDTypography>
              <MDTypography variant={"h6"} fontSize={18}>
                {dictionaryLookup(dictionary.BrainSenseStreaming.Table, therapy.Right.AdaptiveTherapyStatus, language)}
              </MDTypography>
              <MDTypography variant={"p"} fontSize={18}>
                {"Closed-Loop Threshold: "} {therapy.Right.UpperLfpThreshold == therapy.Right.LowerLfpThreshold ? `Single Threshold - ${therapy.Right.LowerLfpThreshold}` : `Dual Threshold - ${therapy.Right.LowerLfpThreshold} / ${therapy.Right.UpperLfpThreshold}`}
                <br/>
              </MDTypography>
              <MDTypography variant={"p"} fontSize={15}>
                {"Ramp Up Time: "} {`${therapy.Right.TransitionUpInMilliSeconds}ms`} <br/>
              </MDTypography>
              <MDTypography variant={"p"} fontSize={15}>
                {"Ramp Down Time: "} {`${therapy.Right.TransitionDownInMilliSeconds}ms`} <br/>
              </MDTypography>
              <MDTypography variant={"p"} fontSize={15}>
                {"Onset Duration: "} {`${therapy.Right.UpperThresholdOnsetInMilliSeconds}ms`} <br/>
              </MDTypography>
              <MDTypography variant={"p"} fontSize={15}>
                {"Termination Duration: "} {`${therapy.Right.LowerThresholdOnsetInMilliSeconds}ms`} <br/>
              </MDTypography>
            </MDBox>
          ) : null}
        </MDBox>
      </MDBox>
    );
  }

  // Divide all PSDs by day or by channel
  React.useEffect(() => {
    setLeftHemispherePSD(false);
    setLeftHemisphereBox(false);
    setRightHemispherePSD(false);
    setRightHemisphereBox(false);
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
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1}>
                        {data.length > 0 ? (
                          <BrainSenseStreamingTable data={data} getRecordingData={getRecordingData} handleMerge={handleMerge}/>
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
                            <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportCurrentStream()}>
                              {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
                            </MDButton>
                          </MDBox>
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <MDButton size="small" variant="contained" color="info" style={{marginBottom: 3}} onClick={() => toggleCardiacFilter()}>
                              {dictionaryLookup(dictionary.BrainSenseStreaming.Figure.CardiacFilter, dataToRender.Info.CardiacFilter ? "Remove" : "Add", language)}
                            </MDButton>
                            <MDButton size="small" variant="contained" color="info" onClick={() => toggleWaveletTransform()}>
                              {dictionaryLookup(dictionary.BrainSenseStreaming.Figure.Wavelet, configuration.SpectrogramMethod.value === "Wavelet" ? "Remove" : "Add", language)}
                            </MDButton>
                          </MDBox>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <TimeFrequencyAnalysis dataToRender={dataToRender} channelInfos={channelInfos} figureTitle={"TimeFrequencyAnalysis"} height={timeFrequencyPlotHeight}/>
                      </Grid>
                      <Grid item xs={12}>
                        {adaptiveClosedLoopParameters(dataToRender.Info.Therapy)}
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
                        {leftHemispherePSD ? (
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <StimulationReferenceButton value={referenceType[0]} onChange={(event, value) => handlePSDUpdate(value, "Left")} />
                            <StimulationPSD dataToRender={leftHemispherePSD} channelInfos={channelInfos} type={"Left"} figureTitle={"LeftStimulationPSD"} onCenterFrequencyChange={onCenterFrequencyChange} height={600}/>
                          </MDBox>
                        ) : null}
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationBoxPlot dataToRender={leftHemisphereBox} channelInfos={channelInfos} type={"Left"} figureTitle={"LeftStimulationBar"} height={600}/>
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        {rightHemispherePSD ? (
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <StimulationReferenceButton value={referenceType[1]} onChange={(event, value) => handlePSDUpdate(value, "Right")} />
                            <StimulationPSD dataToRender={rightHemispherePSD} channelInfos={channelInfos} type={"Right"} figureTitle={"RightStimulationPSD"} onCenterFrequencyChange={onCenterFrequencyChange} height={600}/>
                          </MDBox>
                        ) : null}
                      </Grid>
                      <Grid item xs={12} lg={6}>
                        <StimulationBoxPlot dataToRender={rightHemisphereBox} channelInfos={channelInfos} type={"Right"} figureTitle={"RightStimulationBar"} height={600}/>
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

export default BrainSenseStreaming;
