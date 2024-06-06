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

const filter = createFilterOptions();

function RecordingSelection({allRecordings, activeAnalysis, onAnalysisUpdate, onLabelUpdate, onPreview}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, report, BrainSensestreamLayout, language } = controller;

  const [uniqueDates, setUniqueDates] = React.useState([]);
  const [selectedRecordings, setSelectedRecordings] = React.useState([]);
  const [recordingLabels, setRecordingLabels] = React.useState({show: false, recording_uid: "", labels: []})
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    let uniqueDates = [];
    for (let i in allRecordings) {
      const dateString = new Date(SessionController.decodeTimestamp(allRecordings[i].date*1000)).toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"));
      if (!uniqueDates.includes(dateString)) {
        uniqueDates.push(dateString);
      }
    }
    setUniqueDates(uniqueDates);

  }, [allRecordings]);

  React.useEffect(() => {
    setSelectedRecordings(activeAnalysis.recordings);
  }, [activeAnalysis])

  const handleLabelUpdate = (labels) => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeSeriesRecording", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "update_labels",
      recording_uid: recordingLabels.recording_uid,
      labels: labels
    }).then((response) => {
      onLabelUpdate(recordingLabels.recording_uid, labels);
      setRecordingLabels({...recordingLabels, labels: [], show: false});
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleCreateAnalysis = () => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeSeriesAnalysis", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "select_recordings",
      recording_uids: selectedRecordings,
      analysis_uid: activeAnalysis.analysis.uid
    }).then((response) => {
      onAnalysisUpdate("InProgress");
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  return (
    <MDBox>
      <MDBox pb={2} pl={2} pr={2} lineHeight={1}>
        <MDButton color={"secondary"} onClick={handleCreateAnalysis}>
          {"Create Analysis Result"}
        </MDButton>
      </MDBox>
      <EditRecordingLabels show={recordingLabels.show} currentLabels={recordingLabels} onUpdate={handleLabelUpdate} onCancel={() => setRecordingLabels({...recordingLabels, show: false})} />
      <Grid container spacing={2}>
        {uniqueDates.map((date) => (<React.Fragment key={date}>
          <Divider key={date} flexItem sx={{width: "100%", display: "flex", alignItems: "center"}}>
            <Chip label={date} size="large" sx={{color: "#FFFFFF", background: "#000000"}}/>
          </Divider>
          {allRecordings.map((recording) => {
            const datetime = new Date(SessionController.decodeTimestamp(recording.date*1000));
            const dateString = datetime.toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"));
            if (dateString === date) {
              return <Grid key={recording.type + recording.date} item xs={6} md={3}>
              <Card>
                <MDBox p={2} mx={3} display="flex" justifyContent="center" onClick={() => {
                  setSelectedRecordings((selectedRecordings) => {
                    if (selectedRecordings.includes(recording.uid)) {
                      selectedRecordings = selectedRecordings.filter((a) => a!=recording.uid);
                    } else {
                      selectedRecordings.push(recording.uid);
                    }
                    return [...selectedRecordings];
                  })
                }}>
                  <MDBox
                    display="grid"
                    justifyContent="center"
                    alignItems="center"
                    color="white"
                    width="4rem"
                    height="4rem"
                    shadow="md"
                    borderRadius="lg"
                    variant="gradient"
                  >
                    <Icon fontSize="default">{selectedRecordings.includes(recording.uid) ? <TaskAlt color={"success"} fontSize="medium"/> : null}</Icon>
                  </MDBox>
                </MDBox>
                <MDBox pb={2} px={2} textAlign="center" lineHeight={1.25}>
                  <MDTypography variant="h6" fontWeight="medium" textTransform="capitalize">
                    {recording.type}
                  </MDTypography>
                  <MDTypography variant="h5" color="text" fontWeight="regular">
                    {datetime.toLocaleTimeString()}
                  </MDTypography>
                  <MDTypography variant="caption" fontWeight="medium">
                    {"Duration: "}{recording.duration.toFixed(1)}{" seconds"}
                  </MDTypography>
                  <Divider />
                  <MDBox>
                    <Tooltip title={recording.labels.length > 0 ? <MDBox style={{ border: 1 }}>
                      {recording.labels.map((label, i) => (
                        <MDTypography key={label} variant="caption" fontWeight="medium" color={"white"}>
                          {label}{i == recording.labels.length-1 ? "" : ", "}
                        </MDTypography>
                      ))}
                    </MDBox> : null} style={{background: "#FFFFFF"}}>
                      <MDButton fontWeight="medium" onClick={() => setRecordingLabels({recording_uid: recording.uid, labels: recording.labels, show: true})}>
                        <Icon fontSize="default">{<LabelIcon color={"error"} fontSize="medium"/>}</Icon>
                        {"Labels"}
                      </MDButton>
                    </Tooltip>
                    <MDButton variant="contained" color={"info"} fontWeight="medium" onClick={() => onPreview(recording.uid)}>
                      {"Preview"}
                    </MDButton>
                  </MDBox>
                </MDBox>
              </Card>
            </Grid>
            }
            return null;
          })}
        </React.Fragment>))}
      </Grid>
    </MDBox>
  );
}

export default React.memo(RecordingSelection);
