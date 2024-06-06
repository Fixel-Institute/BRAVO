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
  Chip,
  Drawer,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Icon,
  Grid,
  TextField,
  IconButton,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Slider,
  CardContent,
  CardActions,
  Tooltip,
  Popper
} from "@mui/material"

import { 
  ChevronRight as ChevronRightIcon, 
  TaskAlt,
  Label as LabelIcon,
  Settings as SettingsIcon,
  KeyboardDoubleArrowUp as KeyboardDoubleArrowUpIcon, 
  Dashboard as DashboardIcon
} from "@mui/icons-material";

import { createFilterOptions } from "@mui/material/Autocomplete";

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
import EditRecordingLabels from "./EditRecordingLabels";
import MDInput from "components/MDInput";

const filter = createFilterOptions();

function AnalysisConfiguration({activeAnalysis, allRecordings, onAnalysisUpdate}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, report, BrainSensestreamLayout, language } = controller;

  const [analysisConfig, setAnalysisConfig] = React.useState([]);
  const [availableChannels, setAvailableChannels] = React.useState([]);
  const [availableRecordingTypes, setAvailableRecordingTypes] = React.useState([]);
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    setAlert(<LoadingProgress />);
    SessionController.query("/api/queryTimeSeriesAnalysis", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "get_config",
      analysis_uid: activeAnalysis.analysis.uid,
    }).then((response) => {
      setAnalysisConfig(response.data);
      let availableChannels = [];
      let channelTypes = [];
      for (let i in response.data) {
        for (let j in response.data[i].channels) {
          if (!availableChannels.includes(response.data[i].channels[j])) {
            availableChannels.push(response.data[i].channels[j]);
            channelTypes.push(response.data[i].data_type ? response.data[i].data_type[j] : null);
          }
        }
      }
      setAvailableRecordingTypes(() => {
        let types = [];
        for (let i in channelTypes) {
          if (!types.includes(channelTypes[i])) {
            types.push(channelTypes[i]);
          }
        }
        return types.map((type) => {
          if (type === null) {
            return {name: "None", value: null};
          } else {
            return {name: type, value: type};
          }
        });
      });
      setAvailableChannels(availableChannels.map((channel, index) => ({
        channel: channel,
        type: channelTypes[index]
      })));
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    })
  }, [activeAnalysis]);

  const saveConfiguration = () => {
    let config = {};
    for (let i in analysisConfig) {
      config[analysisConfig[i].uid] = {shift: analysisConfig[i].shift, data_type: []};
      for (let j in analysisConfig[i].channels) {
        for (let k in availableChannels) {
          if (availableChannels[k].channel == analysisConfig[i].channels[j]) {
            config[analysisConfig[i].uid].data_type.push(availableChannels[k].type);
            break;
          }
        }
      }
    }
    
    setAlert(<LoadingProgress />);
    SessionController.query("/api/queryTimeSeriesAnalysis", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "set_config",
      analysis_uid: activeAnalysis.analysis.uid,
      config: config,
    }).then((response) => {
      onAnalysisUpdate("Complete")
      setAlert()
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    })
  }

  return (
    <Grid item xs={12}>
      <MDBox p={2} lineHeight={1} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
        <MDTypography
          variant="h4"
          fontWeight="bold"
        >
          {"Recordings in Analysis: "}
        </MDTypography>
      </MDBox>
      <MDBox p={2} lineHeight={1}>
        <Grid container spacing={2}>
          {analysisConfig.map((recording, index) => {
            const datetime = new Date(SessionController.decodeTimestamp(recording.date*1000));
            return <Grid key={index} item xs={12}>
              <Card>
                <MDBox p={2}>
                  <Grid container>
                    <Grid item xs={7}>
                      <MDBox mb={0.5} lineHeight={1}>
                        <MDTypography
                          variant="button"
                          fontWeight="medium"
                          color="text"
                          textTransform="capitalize"
                        >
                          {recording.type}
                        </MDTypography>
                      </MDBox>
                      <MDBox lineHeight={1}>
                        <MDTypography variant="h5" fontWeight="bold">
                          {datetime.toLocaleString()}
                        </MDTypography>
                      </MDBox>
                      <MDBox lineHeight={1}>
                        <Autocomplete 
                          selectOnFocus clearOnBlur
                          renderInput={(params) => (
                            <TextField {...params} variant="standard" id="recording_type" placeholder={"Set All Channel as Type"} />
                          )}
                          filterOptions={(options, params) => {
                            const filtered = filter(options, params);
                            const { inputValue } = params;

                            // Suggest the creation of a new value
                            const isExisting = options.some((option) => inputValue === option.name);
                            if (inputValue !== '' && !isExisting) {
                              filtered.push({
                                inputValue,
                                name: `New Recording Type: "${inputValue}"`,
                              });
                            }
                            return filtered;
                          }}
                          getOptionLabel={(option) => {
                            if (typeof option === 'string') {
                              return option;
                            }
                            if (option.inputValue) {
                              return option.inputValue;
                            }
                            return option.name;
                          }}
                          isOptionEqualToValue={(option, value) => {
                            return option.value === value.value;
                          }}
                          renderOption={(props, option) => <li {...props}>{option.name}</li>}

                          options={availableRecordingTypes}
                          onChange={(event, newValue) => {
                            if (newValue.inputValue) {
                              setAvailableRecordingTypes([...availableRecordingTypes, {value: newValue.inputValue, name: newValue.inputValue}]);
                              setAvailableChannels((availableChannels) => {
                                for (let i in availableChannels) {
                                  if (recording.channels.includes(availableChannels[i].channel)) {
                                    availableChannels[i].type = newValue.inputValue;
                                  }
                                }
                                return [...availableChannels]
                              })
                            } else {
                              setAvailableChannels((availableChannels) => {
                                for (let i in availableChannels) {
                                  if (recording.channels.includes(availableChannels[i].channel)) {
                                    availableChannels[i].type = newValue.name;
                                  }
                                }
                                return [...availableChannels]
                              })
                            }
                          }}
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={5}>
                      <MDBox mb={0.5} lineHeight={1} style={{textAlign: "end"}}>
                        <MDTypography
                          variant="button"
                          fontWeight="medium"
                          color="text"
                          textTransform="capitalize"
                        >
                          {"Time Shift (milliseconds): "}
                        </MDTypography>
                      </MDBox>
                      <MDBox width="100%" textAlign="right" lineHeight={1}>
                        <MDInput type="number" value={recording.shift} onChange={(event) => {
                          setAnalysisConfig((analysisConfig) => {
                            analysisConfig[index].shift = event.target.value;
                            return [...analysisConfig];
                          })
                        }} />
                      </MDBox>
                    </Grid>
                  </Grid>
                </MDBox>
              </Card>
            </Grid>
          })}
        </Grid>
      </MDBox>
      <MDBox p={2} lineHeight={1} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
        <MDTypography
          variant="h4"
          fontWeight="bold"
        >
          {"Recording Channels Available: "}
        </MDTypography>
      </MDBox>
      <MDBox p={2} lineHeight={1}>
        <Grid container spacing={2} sx={{maxHeight: "900px", overflowY: "auto"}}>
          {availableChannels.map((channel, index) => {
            return <Grid key={index} item xs={12}>
              <Card>
                <MDBox p={2}>
                  <Grid container>
                    <Grid item xs={7}>
                      <MDBox mb={0.5} lineHeight={1}>
                        <MDTypography
                          variant="button"
                          fontWeight="medium"
                          color="text"
                          textTransform="capitalize"
                        >
                          {channel.channel}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={5}>
                      <MDBox width="100%" textAlign="right" lineHeight={1}>
                        <Autocomplete 
                            selectOnFocus clearOnBlur
                            renderInput={(params) => (
                              <TextField {...params} variant="standard" id="recording_type" placeholder={"Set Channel as Recording Type"} />
                            )}
                            filterOptions={(options, params) => {
                              const filtered = filter(options, params);
                              const { inputValue } = params;

                              // Suggest the creation of a new value
                              const isExisting = options.some((option) => inputValue === option.name);
                              if (inputValue !== '' && !isExisting) {
                                filtered.push({
                                  inputValue,
                                  name: `New Recording Type: "${inputValue}"`,
                                });
                              }
                              return filtered;
                            }}
                            getOptionLabel={(option) => {
                              if (typeof option === 'string') {
                                return option;
                              }
                              if (option.inputValue) {
                                return option.inputValue;
                              }
                              return option.name;
                            }}
                            isOptionEqualToValue={(option, value) => {
                              return option.value === value.value;
                            }}
                            renderOption={(props, option) => <li {...props}>{option.name}</li>}

                            options={availableRecordingTypes}
                            value={channel.type || null}
                            onChange={(event, newValue) => {
                              if (newValue.inputValue) {
                                setAvailableRecordingTypes([...availableRecordingTypes, {value: newValue.inputValue, name: newValue.inputValue}]);
                                setAvailableChannels((availableChannels) => {
                                  for (let i in availableChannels) {
                                    if (availableChannels[i].channel === channel.channel) {
                                      availableChannels[i].type = newValue.inputValue
                                    }
                                  }
                                  return [...availableChannels];
                                })
                              } else {
                                setAvailableChannels((availableChannels) => {
                                  for (let i in availableChannels) {
                                    if (availableChannels[i].channel === channel.channel) {
                                      availableChannels[i].type = newValue.name
                                    }
                                  }
                                  return [...availableChannels];
                                })
                              }
                            }}
                          />
                      </MDBox>
                    </Grid>
                  </Grid>
                </MDBox>
              </Card>
            </Grid>
          })}
        </Grid>
      </MDBox>
      <MDBox pb={2} pl={2} pr={2} lineHeight={1}>
        <MDButton color={"primary"} onClick={saveConfiguration}>
          {"Save Analysis Configuration"}
        </MDButton>
      </MDBox>
    </Grid>
  );
}

export default React.memo(AnalysisConfiguration);
