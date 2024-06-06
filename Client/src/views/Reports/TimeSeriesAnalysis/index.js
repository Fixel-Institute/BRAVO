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
  Collapse,
  Drawer,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Grid,
  TextField,
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
import TimeseriesPreview from "./TimeseriesPreview";
import AnalysisConfiguration from "./AnalysisConfiguration";

import RecordingSelection from "./RecordingSelection";
import BrainSenseStreamingTable from "components/Tables/StreamingTable/BrainSenseStreamingTable";
import TimeFrequencyAnalysis from "./TimeFrequencyAnalysis";
import StimulationPSD from "./StimulationPSD";
import StimulationBoxPlot from "./StimulationBoxPlot";
import EventPSDs from "./EventPSDs";
import EventOnsetSpectrogram from "./EventOnsetSpectrum";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";
import TimeSeriesVisualization from "./TimeSeriesVisualization";
import SpectrogramVisualization from "./SpectrogramVisualization";

const filter = createFilterOptions();

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

function TimeSeriesAnalysis() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, report, BrainSensestreamLayout, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [activeAnalysis, setActiveAnalysis] = React.useState({analysis: "", recordings: []});
  const [availableAnalysis, setAvailableAnalysis] = React.useState({analyses: [], recordings: []});
  const [annotations, setAnnotations] = React.useState([]);
  const [drawerOpen, setDrawerOpen] = React.useState({open: false, config: {}});
  const [dataToRender, setDataToRender] = React.useState(false);
  const [collapseState, setCollapseState] = React.useState(true);
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    if (!participant_uid) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryTimeSeriesAnalysis", {
        participant_uid: participant_uid,
        request_type: "overview",
        report_type: report
      }).then((response) => {
        setAvailableAnalysis(response.data);
        setAlert();
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [participant_uid]);

  const handleAddEvent = async (eventInfo) => {
    try {
      const response = await SessionController.query("/api/queryTimeSeriesRecording", {
        participant_uid: participant_uid,
        request_type: "new_annotation",
        report_type: report,
        recording_uid: eventInfo.recording_uid,
        name: eventInfo.name,
        time: eventInfo.time / 1000,
        duration: parseFloat(eventInfo.duration)
      });

      if (response.status == 200) {
        
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const handleNewAnalysis = (name) => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeSeriesAnalysis", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "create",
      name: name,
    }).then((response) => {
      setActiveAnalysis({analysis: response.data, recordings: []});
      setAvailableAnalysis((availableAnalysis) => {
        availableAnalysis.analyses.push(response.data);
        return {...availableAnalysis};
      });
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handlePreview = (recording_uid) => {
    setCollapseState(false);
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeSeriesRecording", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "view",
      recording_uid: recording_uid,
    }).then((response) => {
      setDataToRender(response.data);
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleLabelUpdate = (recording_uid, labels) => {
    setAvailableAnalysis((availableAnalysis) => {
      for (let i in availableAnalysis.recordings) {
        if (availableAnalysis.recordings[i].uid == recording_uid) {
          availableAnalysis.recordings[i].labels = labels;
        }
      }
      return {...availableAnalysis};
    })
  };

  const handleAnalysisUpdate = (label) => {
    setActiveAnalysis((activeAnalysis) => {
      activeAnalysis.analysis.status = label;
      return {...activeAnalysis};
    });

    if (label === "Complete") {
      setDataToRender(false);
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryTimeSeriesAnalysis", {
        participant_uid: participant_uid,
        report_type: report,
        analysis_uid: activeAnalysis.analysis.uid,
        request_type: "get_result",
      }).then((response) => {
        setDataToRender(response.data);
        setAlert();
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
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
                      <MDTypography
                        variant="h4"
                        fontWeight="bold"
                      >
                        {"Time-series Analysis"}
                      </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1}>
                        <Autocomplete 
                          selectOnFocus clearOnBlur
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              variant="standard" id="analysis"
                              placeholder={"Choose Analysis to View"}
                            />
                          )}
                          filterOptions={(options, params) => {
                            const filtered = filter(options, params);
                            const { inputValue } = params;

                            // Suggest the creation of a new value
                            const isExisting = options.some((option) => inputValue === option.name);
                            if (inputValue !== '' && !isExisting) {
                              filtered.push({
                                inputValue,
                                title: `Create New Analysis: "${inputValue}"`,
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
                            return option.name === value.name;
                          }}
                          renderOption={(props, option) => <li {...props}>{option.title ? option.title : option.name}</li>}

                          options={availableAnalysis.analyses}
                          value={activeAnalysis.analysis}
                          onChange={(event, newValue) => {
                            if (newValue.inputValue) {
                              handleNewAnalysis(newValue.inputValue);
                            } else {
                              setActiveAnalysis({analysis: newValue, recordings: newValue.recordings});
                            }
                            //
                          }}
                        />
                      </MDBox>
                    </Grid>
                    {!activeAnalysis.analysis.status ? (
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
                        <MDTypography
                          variant="h4"
                          fontWeight="bold"
                        >
                          {"Available Recordings "}
                        </MDTypography>
                        <MDButton color={"success"} onClick={() => setCollapseState(!collapseState)} style={{marginLeft: 5}}>
                          {collapseState ? "Hide" : "Show"}
                        </MDButton>
                      </MDBox>
                      <Collapse in={collapseState}>
                      <MDBox p={2} lineHeight={1}>
                        <RecordingSelection activeAnalysis={activeAnalysis} allRecordings={availableAnalysis.recordings} onAnalysisUpdate={handleAnalysisUpdate} onLabelUpdate={handleLabelUpdate} onPreview={handlePreview}/>
                      </MDBox>
                      </Collapse>
                    </Grid>
                    ) : null}
                    {activeAnalysis.analysis.status === "InProgress" || activeAnalysis.analysis.status === "Complete" ? (
                      <AnalysisConfiguration activeAnalysis={activeAnalysis} allRecordings={availableAnalysis.recordings} onAnalysisUpdate={handleAnalysisUpdate}/>
                    ) : null}
                  </Grid>
                </Card>
              </Grid>
              {dataToRender && activeAnalysis.analysis.status !== "Complete" ? (
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <MDBox p={3}>
                  <MDTypography
                    variant="h4"
                    fontWeight="bold"
                  >
                    {"Channel Selection"}
                  </MDTypography>
                  <TimeseriesPreview dataToRender={dataToRender}/>
                  </MDBox>
                </Card>
              </Grid>
              ) : null}
              {activeAnalysis.analysis.status === "Complete" ? (
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <MDBox p={3}>
                  <MDTypography
                    variant="h4"
                    fontWeight="bold"
                  >
                    {"Visualization"}
                  </MDTypography>
                  <TimeSeriesVisualization dataToRender={dataToRender} annotations={[]} 
                    handleAddEvent={handleAddEvent}
                    height={600} figureTitle={"Timeseries-Visualization"} />
                  <SpectrogramVisualization dataToRender={dataToRender} annotations={[]} 
                    handleAddEvent={handleAddEvent}
                    height={600} figureTitle={"Spectrogram-Visualization"} />
                  </MDBox>
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

export default TimeSeriesAnalysis;
