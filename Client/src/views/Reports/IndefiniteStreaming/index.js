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
  Card,
  Drawer,
  Divider,
  Grid,
  IconButton,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  ToggleButton,
  ToggleButtonGroup
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
import FormField from "components/MDInput/FormField";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import IndefiniteStreamingTable from "components/Tables/StreamingTable/IndefiniteStreamingTable";
import TimeDomainFigure from "./TimeDomainFigure";
import TimeFrequencyFigure from "./TimeFrequencyFigure";
import LayoutOptions from "./LayoutOptions";
import EventPSDs from "./EventPSDs";
import EventOnsetSpectrum from "./EventOnsetSpectrum";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function IndefiniteStreaming() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, IndefiniteStreamLayout, language } = controller;

  const [data, setData] = React.useState([]);
  const [dataList, setDataList] = React.useState({});
  const [annotations, setAnnotations] = React.useState([]);
  const [dataToRender, setDataToRender] = React.useState(false);

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
  const [alert, setAlert] = React.useState(null);

  const [drawerOpen, setDrawerOpen] = React.useState({open: false, config: {}});

  const [figureHeight, setFigureHeight] = React.useState(0);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryIndefiniteStreaming", {
        id: patientID, 
        requestOverview: true
      }).then((response) => {
        if (response.data.length > 0) {
          setAnnotations(response.data[0].annotations);
        }
        setData(response.data.data);
        setDrawerOpen({...drawerOpen, config: response.data.config});
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const requestDataForRender = (dataList) => {
    var devices = [];
    var timestamps = [];
    var channelInfos = [];
    for (var i in dataList) {
      if (dataList[i].state) {
        devices.push(dataList[i].DeviceID);
        timestamps.push(dataList[i].Timestamp);
        channelInfos.push(dataList[i].Channels);
      }
    }
    if (devices.length == 0) return;
    setDataList({devices, timestamps, channelInfos});

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryIndefiniteStreaming", {
      id: patientID, 
      requestData: true, 
      devices: devices, 
      timestamps: timestamps
    }).then((response) => {
      var axLength = 0;
      for (var i in response.data.data) {
        if (response.data.data[i].Channels.length > axLength) {
          axLength = response.data.data[i].Channels.length;
        }
      }
      setFigureHeight(200*axLength);
      setDataToRender({data: response.data.data, ChannelInfos: channelInfos}); 
      if (Object.keys(response.data.eventPSDs).length > 0) {
        setEventPSDs(response.data.eventPSDs)
      } else {
        setEventPSDs(false);
      }
      if (Object.keys(response.data.eventOnsetSpectrum).length > 0) {
        setEventSpectrograms(response.data.eventOnsetSpectrum);
      } else {
        setEventSpectrograms(false);
      }
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const refreshEventAnalysis = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryIndefiniteStreaming", {
      id: patientID, 
      requestEventData: true, 
      devices: dataList.devices, 
      timestamps: dataList.timestamps
    }).then((response) => {
      var axLength = 0;
      for (var i in response.data.data) {
        if (response.data.data[i].Channels.length > axLength) {
          axLength = response.data.data[i].Channels.length;
        }
      }
      if (Object.keys(response.data.eventPSDs).length > 0) {
        setEventPSDs(response.data.eventPSDs)
      } else {
        setEventPSDs(false);
      }

      if (Object.keys(response.data.eventOnsetSpectrum).length > 0) {
        setEventSpectrograms(response.data.eventOnsetSpectrum);
      } else {
        setEventSpectrograms(false);
      }
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  const exportCurrentStream = () => {
    /*
    var csvData = "Time";
    for (var i = 0; i < dataToRender.data[0]["Channels"].length; i++) {
      csvData += "," + dataToRender.data[0]["Channels"][i] + " Raw";
    }
    csvData += "\n";
    
    for (var section in dataToRender.data) {
      for (var i = 0; i < dataToRender.data[section]["Stream"][0].length; i++) {
        csvData += (i*1/250 + dataToRender.data[section].Timestamp);
        for (var j = 0; j < dataToRender.data[section]["Channels"].length; j++) {
          csvData += "," + dataToRender.data[section]["Stream"][j][i];
        }
        csvData += "\n";
      }
    }
    
    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'IndefiniteStreamExport.json';
    downloader.click();
    */
    var csvData = JSON.stringify(dataToRender);

    var downloader = document.createElement('a');
    downloader.href = 'data:text/json;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'IndefiniteStreamExport.json';
    downloader.click();
    
    csvData = JSON.stringify(eventPSDs);

    downloader = document.createElement('a');
    downloader.href = 'data:text/json;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'IndefiniteStreamEventPSDs.json';
    downloader.click();
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
          dataToRender.data[0].Annotations = [...dataToRender.data[0].Annotations, {
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
    for (let i in dataToRender.data) {
      if (dataToRender.data[i].Annotations.length > 0) {
        eventInfo.targetInfo = eventInfo;
        eventInfo.targetInfo.timeDiff = 10;
      }
    }
      
    for (let j in dataToRender.data) {
      for (let i = 0; i < dataToRender.data[j].Annotations.length; i++) {
        let absoluteDiffTime = Math.abs(dataToRender.data[j].Annotations[i].Time - eventInfo.time/1000);
        if (absoluteDiffTime < eventInfo.targetInfo.timeDiff) {
          eventInfo.targetInfo = dataToRender.data[j].Annotations[i];
          eventInfo.targetInfo.timeDiff = absoluteDiffTime;
        }
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
              for (let j in dataToRender.data) {
                dataToRender.data[j].Annotations = dataToRender.data[j].Annotations.filter((a) => {
                  if (a.Name == eventInfo.targetInfo.Name && a.Time == eventInfo.targetInfo.Time && a.Duration == eventInfo.targetInfo.Duration) {
                    return false;
                  }
                  return true;
                })
              }
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

  React.useEffect(() => {
    if (!eventPSDs) return;

    if (eventPSDSelector.type == "Events") {
      eventPSDSelector.options = Object.keys(eventPSDs);
      eventPSDSelector.value = eventPSDSelector.options[0];
      setEventPSDSelector({...eventPSDSelector});
    } else {
      const Events = Object.keys(eventPSDs);
      if (Events.length > 0) {
        eventPSDSelector.options = eventPSDs[Events[0]].map((value) => value.Channel);
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
      eventSpectrogramSelector.options = Events
      eventSpectrogramSelector.value = eventSpectrogramSelector.options[0];
      setEventSpectrogramSelector({...eventSpectrogramSelector});
    } else {
      setEventSpectrogramSelector({options: [], value: ""});
    }
  }, [eventSpectrograms]);

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
                          <IndefiniteStreamingTable data={data} requestDataForRender={requestDataForRender}/>
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
              {dataToRender ? (
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
                          <MDButton size="large" variant="contained" color="info" style={{marginBottom: 3}} onClick={() => refreshEventAnalysis()}>
                            {"Refresh Event Analysis"}
                          </MDButton>
                        </MDBox>
                      </MDBox>
                      <TimeDomainFigure dataToRender={dataToRender} height={figureHeight} 
                        handleAddEvent={handleAddEvent} handleDeleteEvent={handleDeleteEvent} annotations={annotations}
                        figureTitle={"IndefiniteStreamTimeDomain"}/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              ) : null}
              {!IndefiniteStreamLayout.TimeFrequencyAnalysis ? (
                <Grid item xs={12}> 
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <TimeFrequencyFigure dataToRender={dataToRender} height={figureHeight} figureTitle={"IndefiniteStreamTimeFrequency"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {(!IndefiniteStreamLayout.EventStatePSD && eventPSDs) ? (
                <Grid item xs={6}> 
                  <Card sx={{width: "100%"}}>
                    <Grid container p={2}>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} flexDirection={"row"} justifyContent={"space-between"}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "RawData", language)}
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
                        <EventPSDs dataToRender={eventPSDs} selector={eventPSDSelector} height={500} figureTitle={"EventPSDComparison"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {(!IndefiniteStreamLayout.EventStatePSD && eventSpectrograms) ? (
                <Grid item xs={6}> 
                  <Card sx={{width: "100%"}}>
                    <Grid container p={2}>
                      <Grid item xs={12}>
                        <MDBox display={"flex"} flexDirection={"row"} justifyContent={"space-between"}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "RawData", language)}
                          </MDTypography>
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
                        <EventOnsetSpectrum dataToRender={eventSpectrograms} selector={eventSpectrogramSelector} height={500} figureTitle={"EventOnsetSpectrum"}/>
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
                  return <Grid key={key} item xs={12} sx={{
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
                    
                    SessionController.query("/api/queryBrainSenseSurveys", {
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

export default IndefiniteStreaming;
