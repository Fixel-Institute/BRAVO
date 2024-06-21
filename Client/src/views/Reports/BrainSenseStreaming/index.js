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
import LayoutOptions from "./LayoutOptions";

import BrainSenseStreamingTable from "components/Tables/StreamingTable/BrainSenseStreamingTable";
import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";
import EventPSDs from "./EventPSDs";
import EventOnsetSpectrogram from "./EventOnsetSpectrum";

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
  const { patientID, BrainSensestreamLayout, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [data, setData] = React.useState([]);
  const [annotations, setAnnotations] = React.useState([]);
  const [drawerOpen, setDrawerOpen] = React.useState({open: false, config: {}});
  const [dataToRender, setDataToRender] = React.useState(false);
  const [channelInfos, setChannelInfos] = React.useState([]);

  const [channelPSDs, setChannelPSDs] = React.useState([]);
  
  const [eventPSDs, setEventPSDs] = React.useState(false);
  const [eventPSDSelector, setEventPSDSelector] = React.useState({
    type: "Channels",
    options: [],
    value: ""
  });
  const [eventSpectrograms, setEventSpectrograms] = React.useState(false);
  const [eventSpectrogramSelector, setEventSpectrogramSelector] = React.useState({
    options: [],
    value: ""
  });

  const [referenceType, setReferenceType] = React.useState([]);
  
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryNeuralActivityStreaming", {
        id: patientID,
        requestOverview: true,
      }).then((response) => {
        setAnnotations(response.data.annotations)
        setData(response.data.streamingData);
        setDrawerOpen({...drawerOpen, config: response.data.configuration});
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const getRecordingData = (timestamp) => {
    var ChannelInfos = [];
    for (var i in data) {
      if (data[i].AnalysisID == timestamp) {
        ChannelInfos = data[i].Channels;
      }
    }
    setRecordingId(timestamp);

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryNeuralActivityStreaming", {
      id: patientID, 
      recordingId: timestamp, 
      requestData: true
    }).then((response) => {
      setChannelInfos(ChannelInfos);
      setReferenceType(ChannelInfos.map((value) => "Ipsilateral"));
      setDataToRender(response.data);

      if (Object.keys(response.data.EventPSDs).length > 0) {
        setEventPSDs(response.data.EventPSDs)
      } else {
        setEventPSDs(false);
      }
      if (Object.keys(response.data.EventOnsetSpectrum).length > 0) {
        setEventSpectrograms(response.data.EventOnsetSpectrum);
      } else {
        setEventSpectrograms(false);
      }

      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };
  
  React.useEffect(() => {
    if (!eventPSDs) return;

    if (eventPSDSelector.type == "Events") {
      eventPSDSelector.options = Object.keys(eventPSDs).map((value) => (
        {text: value, value: value}
      ));
      eventPSDSelector.value = eventPSDSelector.options[0];
      setEventPSDSelector({...eventPSDSelector});
    } else {
      const Events = Object.keys(eventPSDs);
      if (Events.length > 0) {
        eventPSDSelector.options = eventPSDs[Events[0]].map((value, i) => {
          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          let titleText = (channelInfos[i].Hemisphere == channelInfos[i].CustomName) ? dictionaryLookup(dictionary.FigureStandardText, side, language) + " " + dictionaryLookup(dictionary.FigureStandardText, target, language) : channelInfos[i].CustomName;
          titleText += (typeof channelInfos[i].Contacts) == "string" ? " " + channelInfos[i].Contacts : ` E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
          return {
            text: titleText,
            value: value.Channel
          };
        });
        eventPSDSelector.value = eventPSDSelector.options[0];
        setEventPSDSelector({...eventPSDSelector});
      } else {
        setEventPSDSelector({...eventPSDSelector, options: [], value: ""});
      }
    }
  }, [eventPSDSelector.type, eventPSDs]);
  
  React.useEffect(() => {
    if (!eventSpectrograms) return;

    const Events = Object.keys(eventSpectrograms);
    if (Events.length > 0) {
      eventSpectrogramSelector.options = Events;
      eventSpectrogramSelector.value = eventSpectrogramSelector.options[0];
      eventSpectrogramSelector.type = "Non-Normalized";
      setEventSpectrogramSelector({...eventSpectrogramSelector});
    } else {
      setEventSpectrogramSelector({options: [], value: ""});
    }
  }, [eventSpectrograms]);

  const handleMerge = async (toggleMerge) => {
    try {
      let mergeResponse = await SessionController.query("/api/queryNeuralActivityStreaming", {
        mergeRecordings: toggleMerge.merge
      });
      if (mergeResponse.status == 200) {
        const response = await SessionController.query("/api/queryNeuralActivityStreaming", {
          id: patientID,
          requestOverview: true,
        });
        setData(response.data.streamingData);
        setDrawerOpen({...drawerOpen, config: response.data.configuration});
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const onCenterFrequencyChange = (side, freq) => {
    var reference = "Ipsilateral";
    for (let i in channelInfos) {
      if (channelInfos[i] == side) {
        reference = referenceType[i];
      }
    }

    SessionController.query("/api/queryNeuralActivityStreaming", {
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

  const toggleCardiacFilter = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryNeuralActivityStreaming", {
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
    SessionController.query("/api/queryNeuralActivityStreaming", {
      updateWaveletTransform: drawerOpen.config.SpectrogramMethod.value === "Wavelet" ? "Spectrogram" : "Wavelet",
      id: patientID,
      recordingId: recordingId,
    }).then((response) => {
      setDataToRender(response.data);
      setDrawerOpen({
        ...drawerOpen,
        config: {
          ...drawerOpen.config,
          SpectrogramMethod: {
            ...drawerOpen.config.SpectrogramMethod,
            value: drawerOpen.config.SpectrogramMethod.value === "Wavelet" ? "Spectrogram" : "Wavelet"
          }
        }
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handlePSDUpdate = (reference, side) => {
    if (!reference) return;
    if (channelInfos.length == 1) return;
    
    SessionController.query("/api/queryNeuralActivityStreaming", {
      updateStimulationPSD: true,
      id: patientID,
      recordingId: recordingId,
      channel: side,
      centerFrequency: 22,
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

      setReferenceType((referenceType) => {
        for (let i in channelInfos) {
          if (channelInfos[i] == side) {
            referenceType[i] = reference;
          }
        }
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
  
    for (var i = 0; i < dataToRender.Stream[0]["Time"].length; i++) {
      csvData += dataToRender.Stream[0]["Time"][i] + dataToRender.Timestamp;
      for (var j = 0; j < dataToRender["Channels"].length; j++) {
        csvData += "," + dataToRender.Stream[j]["RawData"][i];
        for (var k = 0; k < dataToRender["Stimulation"].length; k++) {
          if (dataToRender["Stimulation"][k]["Name"] == dataToRender["Channels"][j]) {
            for (var l = 0; l < dataToRender["Stimulation"][k]["Amplitude"].length; l++) {
              if (dataToRender["Stimulation"][k]["Time"][l] >= dataToRender.Stream[j]["Time"][i]+dataToRender.Timestamp-dataToRender.PowerTimestamp) {
                break;
              }
            }
            if (l == 0) {
              csvData += "," + dataToRender["Stimulation"][k]["Amplitude"][l];
            } else {
              csvData += "," + dataToRender["Stimulation"][k]["Amplitude"][l-1];
            }
          }
        }
      }
      csvData += "\n";
    }
    
    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'NeuralRecordingsExport.csv';
    downloader.click();
  };

  const adaptiveClosedLoopParameters = (therapy) => {
    if (!therapy) return null;

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
    if (dataToRender.Stream) {
      setChannelPSDs(dataToRender.Stream.map((data) => data.StimPSD));
    } else {
      setChannelPSDs([]);
    }
  }, [dataToRender]);

  const handleAddEvent = async (eventInfo) => {
    if (eventInfo.name === "") return;
    
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
                              {dictionaryLookup(dictionary.BrainSenseStreaming.Figure.Wavelet, drawerOpen.config.SpectrogramMethod.value === "Wavelet" ? "Remove" : "Add", language)}
                            </MDButton>
                          </MDBox>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <TimeFrequencyAnalysis dataToRender={dataToRender} channelInfos={channelInfos} 
                          handleAddEvent={handleAddEvent} handleDeleteEvent={handleDeleteEvent} handleAdjustAlignment={handleAdjustAlignment} annotations={annotations}
                          figureTitle={"TimeFrequencyAnalysis"} height={700}/>
                      </Grid>
                      <Grid item xs={12}>
                        {adaptiveClosedLoopParameters(dataToRender.Info.Therapy)}
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {!BrainSensestreamLayout.StimulationPSDs && dataToRender && channelInfos.length > 0 ? (
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
                              <StimulationReferenceButton value={referenceType[index]} onChange={(event, value) => handlePSDUpdate(value, channelInfos[index])} />
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
              {(!BrainSensestreamLayout.EventStatePSD && eventPSDs) ? (
                <Grid item xs={12} md={6}> 
                  <Card sx={{width: "100%"}}>
                    <Grid container p={2}>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} flexDirection={"row"} justifyContent={"space-between"}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {"Event-State Power Spectrum"}
                          </MDTypography>
                          <ToggleButtonGroup
                            value={eventPSDSelector.type}
                            exclusive
                            onChange={(event, newSelector) => setEventPSDSelector({...eventPSDSelector, type: newSelector})}
                            aria-label="Event Comparisons"
                          >
                            <ToggleButton value="Channels" aria-label="by channels">
                              <MDTypography variant="p" fontWeight={"bold"} fontSize={12}>
                                {"Channels"}
                              </MDTypography>
                            </ToggleButton>
                            <ToggleButton value="Events" aria-label="by events">
                              <MDTypography variant="p" fontWeight={"bold"} fontSize={12}>
                                {"Events"}
                              </MDTypography>
                            </ToggleButton>
                          </ToggleButtonGroup>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <MDBox lineHeight={1}>
                          <Autocomplete
                            value={eventPSDSelector.value}
                            options={eventPSDSelector.options}
                            onChange={(event, value) => setEventPSDSelector({...eventPSDSelector, value: value})}
                            getOptionLabel={(option) => {
                              return option.text;
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={"Comparison Selector"}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                            disableClearable
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <EventPSDs dataToRender={eventPSDs} selector={eventPSDSelector} height={500} figureTitle={"EventPSDComparison"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {(!BrainSensestreamLayout.EventOnsetSpectrum && eventSpectrograms) ? (
                <Grid item xs={12} md={6}> 
                  <Card sx={{width: "100%"}}>
                    <Grid container p={2}>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} flexDirection={"row"} justifyContent={"space-between"}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {"Event-Onset Spectrogram"}
                          </MDTypography>
                          <ToggleButtonGroup
                            value={eventSpectrogramSelector.type}
                            exclusive
                            onChange={(event, newSelector) => setEventSpectrogramSelector({...eventSpectrogramSelector, type: newSelector})}
                            aria-label="Event Comparisons"
                          >
                            <ToggleButton value="Non-Normalized" aria-label="by events">
                              <MDTypography variant="p" fontWeight={"bold"} fontSize={12}>
                                {"Non-Normalized"}
                              </MDTypography>
                            </ToggleButton>
                            <ToggleButton value="Normalized" aria-label="by channels">
                              <MDTypography variant="p" fontWeight={"bold"} fontSize={12}>
                                {"Normalized"}
                              </MDTypography>
                            </ToggleButton>
                          </ToggleButtonGroup>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <MDBox lineHeight={1}>
                          <Autocomplete
                            value={eventSpectrogramSelector.value}
                            options={eventSpectrogramSelector.options}
                            onChange={(event, value) => setEventSpectrogramSelector({...eventSpectrogramSelector, value: value})}
                            getOptionLabel={(option) => {
                              return option;
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={"Comparison Selector"}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                            disableClearable
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <EventOnsetSpectrogram dataToRender={eventSpectrograms} selector={eventSpectrogramSelector} height={500} normalize={eventSpectrogramSelector.type=="Normalized"} figureTitle={"EventSpectrogramComparison"}/>
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
                    disableClearable
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
                  "RealtimeStream": drawerOpen.config
                }).then(() => {
                  setDrawerOpen({...drawerOpen, open: false});
                  setAlert(null);
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
                hidden={false}
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
                  key={"EditLayout"}
                  icon={<DashboardIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                  tooltipTitle={"Edit Layout"}
                  onClick={() => setAlert(<LayoutOptions setAlert={setAlert} />)}
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

export default BrainSenseStreaming;
