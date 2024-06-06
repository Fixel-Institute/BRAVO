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
  CardActions
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

function TimeseriesPreview({dataToRender}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, report, BrainSensestreamLayout, language } = controller;

  const [activeChannel, setActiveChannel] = React.useState("");
  const [channelData, setChannelData] = React.useState(false);
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    
  }, [dataToRender]);

  React.useEffect(() => {
    if (!activeChannel) return;

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryTimeSeriesRecording", {
      participant_uid: participant_uid,
      report_type: report,
      request_type: "view",
      recording_uid: dataToRender.uid,
      channel: activeChannel,
    }).then((response) => {
      setChannelData(response.data);
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, [activeChannel]);

  return (
    <MDBox>
      {alert}
      <Autocomplete 
        selectOnFocus clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard" id="channel"
            placeholder={"Choose Channel to View"}
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
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
          return option === value;
        }}
        renderOption={(props, option) => <li {...props}>{option}</li>}

        options={dataToRender.ChannelNames}
        value={activeChannel}
        onChange={(event, newValue) => {
          setActiveChannel(newValue);
        }}
      />
      <TimeFrequencyAnalysis dataToRender={channelData} annotations={[]} figureTitle={"TimeseriesPreview"} height={600}/>
    </MDBox>
  );
}

export default React.memo(TimeseriesPreview);
