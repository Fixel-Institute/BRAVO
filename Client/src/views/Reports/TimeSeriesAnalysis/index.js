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
  Dialog,
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
  Dashboard as DashboardIcon,
  Cached as CachedIcon
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
import ConfigurationDialog from "components/ConfigurationDialog";

import TimeSeriesAnalysisTable from "./TimeSeriesAnalysisTable";
import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import EventPSDs from "../TherapeuticEffects/EventPSDs";
import BurstDynamics from "./BurstDynamics";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";
import TimeseriesPlayback from "./TimeseriesPlayback";

function TimeSeriesAnalysis() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { experiment, TimeSeriesAnalysisLayout, language } = controller;
  const { participant_uid } = useParams();

  const [recordingId, setRecordingId] = useState([]);

  const [availableAnalysis, setAvailableAnalysis] = useState({Analyses: [], Recordings: []});
  const [data, setData] = useState(false);
  const [dataToRender, setDataToRender] = useState(false);

  const [annotations, setAnnotations] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState({open: false, config: {}});
  const [layoutOptions, setLayoutOptions] = useState({open: false, config: {}});
  const [channel, setChannel] = useState({active: [], options: []});
  const [processConfig, setProcessConfig] = useState({});

  const [timeseriesPlayback, setTimeseriesPlayback] = useState({data: [], playing: false});
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!participant_uid) {
      navigate("/database", {replace: false});
      return;
    }
    setContextState(dispatch, "report", "GeneralReports");

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeseriesAnalysis", {
      RequestType: "Overview",
      ParticipantId: participant_uid
    }).then((response) => {
      let availableAnalysis = response.data;
      availableAnalysis.Recordings = availableAnalysis.Recordings.filter((a) => a.Type != "DBS Snapshots");
      setAvailableAnalysis(availableAnalysis);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
    
  }, [participant_uid]);

  const getRecordingData = async (analysisList, channel) => {
    let newQueryChannel = [];
    for (let i in channel) {
      if (!data.CachedChannel.includes(channel[i])) {
        newQueryChannel.push(channel[i])
      }
    }

    setAlert(<LoadingProgress />);
    if (!channel || newQueryChannel.length > 0) {
      try {
        let allResponses = [];
        for (let l in analysisList) {
          const subResponse = await SessionController.query("/api/queryTimeseriesAnalysis", {
            RequestType: "RequestData",
            ParticipantId: participant_uid,
            AnalysisId: analysisList[l].Id,
            ActiveChannels: newQueryChannel,
            TherapyId: analysisList[l].Therapy ? analysisList[l].Therapy[0].Id : null
          });
          allResponses.push(subResponse.data);
        }

        for (let l in allResponses) {
          for (let trial in allResponses[l].Signal) {
            allResponses[l].Signal[trial].SignalSeries.Spectrum.Power = allResponses[l].Signal[trial].SignalSeries.Spectrum.Power.map((a) => a.map((b) => b === null ? -100 : b));
          }
        }

        if (!channel) {
          setProcessConfig(allResponses[0].ProcessingConfiguration.TimeSeriesRecording);
          setAnnotations(allResponses[0].Annotations);
          setData({...allResponses[0], CachedChannel: allResponses[0].ActiveChannel, Analysis: analysisList});
          setChannel({active: allResponses[0].ActiveChannel, options: allResponses[0].AllChannels});
        } else {
          setData((data) => {
            data.CachedChannel.push(...newQueryChannel);
            data.ActiveChannel = channel;
            for (let l in allResponses) {
              data.Signal.push(...allResponses[l].Signal);
              if (allResponses[l].Therapy) {
                data.Therapy.push(...allResponses[l].Therapy);
              }
            }
            setChannel((oldChannel) => {
              oldChannel.active = channel;
              return {...oldChannel}
            });
            setAnnotations((annotations) => {
              for (let l in allResponses) {
                annotations.push(...allResponses[l].Annotations);
              }
              return [...new Set(annotations)];
            });
            return {...data};
          });
        }
        setAlert(null);
      } catch (error) {
        SessionController.displayError(error, setAlert);
      }
    } else {
      setChannel((oldChannel) => {
        oldChannel.active = channel;
        return {...oldChannel}
      });
      setAlert(null);
    }
  };
  
  const addRecordingData = async (analysis, channel) => {
    const response = await SessionController.query("/api/queryTimeseriesAnalysis", {
      RequestType: "RequestData",
      ParticipantId: participant_uid,
      AnalysisId: analysis.Id,
      TherapyId: analysis.Therapy ? analysis.Therapy[0].Id : null,
      ActiveChannels: data.ActiveChannel ? data.ActiveChannel : []
    });

    for (let trial in response.data.Signal) {
      response.data.Signal[trial].SignalSeries.Spectrum.Power = response.data.Signal[trial].SignalSeries.Spectrum.Power.map((a) => a.map((b) => b === null ? -100 : b));
    }

    setAlert(<LoadingProgress />);
    setData((data) => {
      if (data) {
        for (let i in response.data.ActiveChannel) {
          if (!data.CachedChannel.includes(response.data.ActiveChannel[i])) {
            data.CachedChannel.push(response.data.ActiveChannel[i]);
          }
        }
        for (let i in response.data.ActiveChannel) {
          if (!data.ActiveChannel.includes(response.data.ActiveChannel[i])) {
            data.ActiveChannel.push(response.data.ActiveChannel[i]);
          }
        }
        data.Signal.push(...response.data.Signal);
        
        if (response.data.Therapy) {
          if (!data.Therapy) {
            data.Therapy = [];
          }
          data.Therapy.push(...response.data.Therapy);
        }
        if (!data.Analysis.includes(analysis)) {
          data.Analysis.push(analysis);
        }
      } else {
        data = {...response.data, CachedChannel: response.data.ActiveChannel, Analysis: [analysis]};
      }

      setChannel((channel) => {
        for (let i in response.data.AllChannels) {
          if (!channel.options.includes(response.data.AllChannels[i])) {
            channel.options.push(response.data.AllChannels[i]);
          }
        }
        return {...channel, active: data.ActiveChannel};
      });
      setAnnotations((annotations) => {
        annotations.push(...response.data.Annotations);
        return [...new Set(annotations)];
      });
      return {...data};
    });  
    setAlert(null);
    
  };
  
  const exportCurrentStream = () => {
    for (let i in data.Analysis) {
      let downloader = document.createElement('a');
      downloader.href = SessionController.getDownloadLink("/api/downloadData", {
        ParticipantId: participant_uid,
        CacheType: "queryTimeseriesAnalysis",
        RecordingId: data.Analysis[i].Id
      });
      downloader.target = '_blank';
      downloader.click();
    }
  };

  const handleAddEvent = async (eventInfo) => {
    setAlert(<LoadingProgress />);
    try {
      const response = await SessionController.query("/api/addParticipantAnnotation", {
        ParticipantId: participant_uid,
        EventName: eventInfo.name,
        EventTime: eventInfo.time / 1000,
        EventDuration: parseFloat(eventInfo.duration),
        EventType: "RecordingCustomEvent"
      });
      setAlert(null);

      if (response.status == 200) {
        setAnnotations([...annotations, response.data]);
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const handleDeleteEvent = async (eventInfo) => {
    if (annotations.length > 0) {
      eventInfo.targetInfo = eventInfo;
      eventInfo.targetInfo.timeDiff = 10;
    }

    for (let i = 0; i < annotations.length; i++) {
      let absoluteDiffTime = Math.abs(annotations[i].Date - eventInfo.time/1000);
      if (absoluteDiffTime < eventInfo.targetInfo.timeDiff) {
        eventInfo.targetInfo = annotations[i];
        eventInfo.targetInfo.timeDiff = absoluteDiffTime;
      }
    }
    
    if (eventInfo.targetInfo.timeDiff < 10) {
      setAlert(<MuiAlertDialog 
        title={`Remove ${eventInfo.targetInfo.Name} Event`}
        message={`Are you sure you want to delete the entry [${eventInfo.targetInfo.Name}] @ ${new Date(eventInfo.targetInfo.Date*1000)} ?`}
        confirmText={"YES"}
        denyText={"NO"}
        denyButton
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => {
          SessionController.query("/api/deleteParticipantAnnotation", {
            ParticipantId: participant_uid,
            EventId: eventInfo.targetInfo.Id
          }).then(() => {
            setAnnotations((annotations) => {
              return [...annotations.filter((a) => a.Id != eventInfo.targetInfo.Id)];
            });
            setAlert(null);
          }).catch((error) => {
            SessionController.displayError(error, setAlert);
          });
        }}
      />)
    }
  }

  const handleAdjustAlignment = async (alignment, eventInfo) => {
    setAlert(<LoadingProgress />)
    const Alignment = parseFloat(alignment.alignment)/1000;
    try {
      const response = await SessionController.query("/api/setRecordingTimeShift", {
        ParticipantId: participant_uid,
        RequestType: "Recording",
        RecordingId: eventInfo.channel,
        Alignment: Alignment
      })
      setAlert(null);
      
      if (response.status == 200) {
        setData((data) => {
          for (let i in data.Signal) {
            if (data.Signal[i].RecordingId == eventInfo.channel) {
              data.Signal[i].Alignment = Alignment
            }
          }
          for (let i in data.Therapy) {
            if (data.Therapy[i].RecordingId == eventInfo.channel) {
              data.Therapy[i].Alignment = Alignment
            }
          }
          return {...data};
        });
      }
      return response
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  }
  
  const updateRecordingData = async (analysisUpdate) => {
    setAlert(<LoadingProgress />)
    try {
      for (let i in analysisUpdate.analysisId) {
        const response = await SessionController.query("/api/queryTimeseriesAnalysis", {
          RequestType: "UpdateData",
          ParticipantId: participant_uid,
          AnalysisId: analysisUpdate.analysisId[i],
          RecordingName: analysisUpdate.name,
          RecordingTags: analysisUpdate.tags ? analysisUpdate.tags : []
        });
      }
      
      setAvailableAnalysis((availableAnalysis) => {
        for (let i in availableAnalysis.Recordings) { 
          if (availableAnalysis.Recordings[i].Id == analysisUpdate.analysisId[0]) {
            availableAnalysis.Recordings[i].Name = analysisUpdate.name;
            availableAnalysis.Recordings[i].Metadata.Tags = analysisUpdate.tags ? analysisUpdate.tags : [];
            break;
          }
        }
        return {...availableAnalysis};
      });
      setAlert(null);
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  return (
    <DatabaseLayout>
      {alert}
      <MDBox pt={3}>
        <MDBox>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                      {availableAnalysis.Recordings.length > 0 ? (
                        <TimeSeriesAnalysisTable data={availableAnalysis.Recordings} getRecordingData={getRecordingData} 
                          updateRecordingData={updateRecordingData} addRecordingData={addRecordingData}
                        />
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
                            {"Time-Series Analysis"}
                          </MDTypography>
                        </MDBox>
                        <MDBox display={"flex"} flexDirection={"row"}>
                          <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportCurrentStream()}>
                            {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
                          </MDButton>
                          <MDButton size="large" variant="contained" color="info" style={{marginBottom: 3}} onClick={() => {
                            for (let i in data.Analysis) {
                              SessionController.query("/api/queryTimeseriesAnalysis", {
                                RequestType: "DeleteCache",
                                ParticipantId: participant_uid,
                                AnalysisId: data.Analysis[i].Id,
                              }).then((response) => {
                                getRecordingData([data.Analysis[i]])
                              });
                            }
                          }}>
                            {"Clear Cache"}
                          </MDButton>
                        </MDBox>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox px={3} pb={3} pt={0}>
                        <MDTypography variant="h6" fontWeight={"bold"} fontSize={18}>
                          {"Current Configurations"}
                        </MDTypography>
                        <MDTypography variant="h6" fontWeight={"bold"} fontSize={12}>
                          {"Standard Filter: "}{processConfig.StandardFilter.value}
                        </MDTypography>
                        <MDTypography variant="h6" fontWeight={"bold"} fontSize={12}>
                          {"Cardiac Filter: "}{processConfig.CardiacFilter.value}
                        </MDTypography>
                        <MDTypography variant="h6" fontWeight={"bold"} fontSize={12}>
                          {"Wiener Filter: "}{processConfig.WienerFilter.value}
                        </MDTypography>
                      </MDBox>
                      
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox px={3} pb={3} pt={0}>
                        <Autocomplete
                          multiple
                          value={channel.active}
                          options={channel.options}
                          onChange={(event, value) => {
                            getRecordingData(data.Analysis, value);
                          }}
                          renderOption={(props, option) => <li {...props}>{option.includes(":") ? option.split(": ")[1] : option}</li>}
                          getOptionLabel={(option) => {
                            return option.includes(":") ? option.split(": ")[1] : option;
                          }}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Channel Selector"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <TimeFrequencyAnalysis dataToRender={data} activeChannels={channel.active} annotations={annotations}
                        handleAddEvent={handleAddEvent} handleDeleteEvent={handleDeleteEvent} handleAdjustAlignment={handleAdjustAlignment} 
                        setTimeseriesPlayback={setTimeseriesPlayback}
                        figureTitle={"TimeFrequencyAnalysis"} height={300}/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
            ) : null}
            {!TimeSeriesAnalysisLayout.StimulationPSDs && data.Therapy ? (
              <Grid item xs={12}>
                <Card>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox display={"flex"} flexDirection={"column"}>
                        <StimulationPSD dataToRender={data} activeChannels={channel.active} figureTitle={"StimulationPSDs"} />
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
            ) : null}
            {!TimeSeriesAnalysisLayout.EventStatePSD && annotations.length > 0 ? (
              <Grid item xs={12} lg={6}>
                <Card>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox display={"flex"} flexDirection={"column"}>
                        <EventPSDs dataToRender={data} annotations={annotations} figureTitle={"Event PSDs"} />
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
            ) : null}
          </Grid>
          
          <Dialog open={timeseriesPlayback.playing} onClose={() => setTimeseriesPlayback({...timeseriesPlayback, playing: false})} 
            PaperProps={{ sx: {minWidth: { xs: "100vw", sm: 1000 }} }}
          >
            <TimeseriesPlayback dataToRender={timeseriesPlayback.data} />
          </Dialog>
          <LayoutOptions show={layoutOptions.open} close={() => setLayoutOptions({...layoutOptions, open: false})} setAlert={setAlert} />
          <ConfigurationDialog show={drawerOpen.open} setShow={(state) => setDrawerOpen({open: false})} setAlert={setAlert} />
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
                key={"ChangeSettings"}
                icon={<SettingsIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Edit Processing Configurations"}
                onClick={() => setDrawerOpen({...drawerOpen, open: true})}
              />
              <SpeedDialAction
                key={"EditLayout"}
                icon={<DashboardIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Edit Layout"}
                onClick={() => setLayoutOptions({...layoutOptions, open: true})}
              />
              <SpeedDialAction
                key={"ClearCache"}
                icon={<CachedIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Clear Cache (Reprocessing)"}
                onClick={() => {
                  for (let i in data.Analysis) {
                    SessionController.query("/api/queryTimeseriesAnalysis", {
                      RequestType: "DeleteCache",
                      ParticipantId: participant_uid,
                      AnalysisId: data.Analysis[i].Id,
                    }).then((response) => {
                      getRecordingData([data.Analysis[i]])
                    });
                  }
                }}
              />
            </SpeedDial>
          </MDBox>
        </MDBox>
      </MDBox>
    </DatabaseLayout>
  );
}

export default TimeSeriesAnalysis;
