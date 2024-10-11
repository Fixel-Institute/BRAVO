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

import TherapeuticAnalysisTable from "./TherapeuticAnalysisTable";
import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";
import EventPSDs from "./EventPSDs";
import EventOnsetSpectrogram from "./EventOnsetSpectrum";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapeuticEffects() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, experiment, TherapeuticEffectLayout, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [availableAnalysis, setAvailableAnalysis] = React.useState({analyses: [], recordings: []})
  const [data, setData] = React.useState(false);
  const [annotations, setAnnotations] = React.useState([]);
  const [drawerOpen, setDrawerOpen] = React.useState({open: false, config: {}});
  const [dataToRender, setDataToRender] = React.useState(false);
  const [channel, setChannel] = React.useState({active: "", options: []})
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
    if (!participant_uid) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryTherapeuticEffectAnalysis", {
        request_type: "Overview",
        participant_uid: participant_uid,
        experiment_uid: experiment
      }).then((response) => {
        setAvailableAnalysis(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [participant_uid]);

  const getRecordingData = (analysisId, channel=null) => {
    setAlert(<LoadingProgress />)
    SessionController.query("/api/queryTherapeuticEffectAnalysis", {
      request_type: channel ? "QueryChannel" : "QueryData",
      participant_uid: participant_uid,
      experiment_uid: experiment,
      analysis_uid: analysisId,
      channel: channel
    }).then((response) => {
      setData({...response.data, AnalysisID: analysisId});
      setChannel({active: response.data.ActiveChannel, options: response.data.ChannelNames})
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };
  
  React.useEffect(() => {

  }, []);
  
  React.useEffect(() => {
    
  }, []);

  const onCenterFrequencyChange = (side, freq) => {
    
  };

  const toggleCardiacFilter = () => {
    
  };

  const toggleWaveletTransform = () => {
    
  };

  const handlePSDUpdate = (reference, side) => {
    
  }

  const exportCurrentStream = () => {
    
  };

  const adaptiveClosedLoopParameters = (therapy) => {
    
  }

  // Divide all PSDs by day or by channel
  React.useEffect(() => {
    
  }, [dataToRender]);

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
    const Alignment = parseFloat(alignment)/1000;
    SessionController.query("/api/updateRecordings", {
      request_type: "Alignment",
      participant: participant_uid,
      analysis_uid: data.AnalysisID,
      recording_uid: data.Therapy.RecordingId,
      alignment: Alignment
    }).then((response) => {
      setData((data) => {
        data.Therapy.AlignmentOffset = Alignment;
        return {...data};
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
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
                        {availableAnalysis.analyses.length > 0 ? (
                          <TherapeuticAnalysisTable data={availableAnalysis.analyses} recordings={availableAnalysis.recordings} getRecordingData={getRecordingData}/>
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
              {data ? (
                <Grid item xs={12}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} justifyContent={"space-between"} p={3}>
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                              {"Therapeutic Effect Analysis"}
                            </MDTypography>
                          </MDBox>
                          <MDBox display={"flex"} flexDirection={"column"}>
                            <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportCurrentStream()}>
                              {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
                            </MDButton>
                          </MDBox>
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <MDBox p={3}>
                        <Autocomplete
                          value={channel.active}
                          options={channel.options}
                          onChange={(event, value) => {
                            setChannel({...channel, active: value});
                            getRecordingData(data.AnalysisID, value);
                          }}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Channel Selector"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                          disableClearable
                        />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <TimeFrequencyAnalysis dataToRender={data}
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
              {(eventPSDs) ? (
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
              {(eventSpectrograms) ? (
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

export default TherapeuticEffects;
