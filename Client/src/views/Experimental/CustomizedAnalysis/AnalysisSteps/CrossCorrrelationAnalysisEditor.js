import { useState, useEffect } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField, Divider, Switch, FormControlLabel } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const CrossCorrrelationAnalysisEditor = ({currentState, newProcess, availableRecordings, availableChannels, defaultConfigs, updateConfiguration}) => {
  const [filterOptions, setFilterOptions] = useState(newProcess ? {
    ...defaultConfigs,
    targetRecording: "",
    targetChannel: "",
    secondTargetRecording: "",
    secondTargetChannel: "",
    output: "",
    new: true
  } : {...currentState, new: false});

  const checkInputComplete = () => {
    return filterOptions.targetRecording !== "" && filterOptions.secondTargetRecording !== "" && filterOptions.output !== "";
  };

  const [availablePrimaryChannels, setAvailablePrimaryChannels] = useState([]);
  const [availableSecondaryChannels, setAvailableSecondaryChannels] = useState([]);
  
  useEffect(() => {
    if (filterOptions.targetRecording) {
      let channels = [];
      for (let key in availableChannels) {
        if (availableChannels[key].Type == filterOptions.targetRecording) {
          for (let channel of Object.keys(availableChannels[key].Channels)) {
            if (!channels.includes(availableChannels[key].Channels[channel].name)) {
              channels.push(availableChannels[key].Channels[channel].name);
            }
          }
        }
      }
      setAvailablePrimaryChannels(channels)
    }
  }, [filterOptions.targetRecording]);

  useEffect(() => {
    if (filterOptions.secondTargetRecording) {
      let channels = [];
      for (let key in availableChannels) {
        if (availableChannels[key].Type == filterOptions.secondTargetRecording) {
          for (let channel of Object.keys(availableChannels[key].Channels)) {
            if (!channels.includes(availableChannels[key].Channels[channel].name)) {
              channels.push(availableChannels[key].Channels[channel].name);
            }
          }
        }
      }
      setAvailableSecondaryChannels(channels)
    }
  }, [filterOptions.secondTargetRecording]);

  return (
    <MDBox style={{marginTop: 20, paddingTop: 5, paddingBottom: 15}}>
      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            label={"Primary Target Signal"}
            placeholder={"Select Target Recording Type"}
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          return filtered;
        }}
        isOptionEqualToValue={(option, value) => {
          return option === value;
        }}
        renderOption={(props, option) => <li {...props}>{option}</li>}
        value={filterOptions.targetRecording}
        options={availableRecordings}
        onChange={(event, newValue) => setFilterOptions((filterOptions) => {
          filterOptions.targetRecording = newValue;
          filterOptions.output = newValue + "_CrossCorrelationAnalysis";
          return {...filterOptions};
        })}
      />

      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.targetChannel}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, targetChannel: event.target.value})}
        label={"Primary Target Channel"} type={"text"}
        autoComplete={"off"}
        fullWidth
      />


      <Divider />
      
      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            label={"Secondary Target Signal (Must be same data-type as Primary)"}
            placeholder={"Select Target Recording Type"}
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          return filtered;
        }}
        isOptionEqualToValue={(option, value) => {
          return option === value;
        }}
        renderOption={(props, option) => <li {...props}>{option}</li>}
        value={filterOptions.secondTargetRecording}
        options={availableRecordings}
        onChange={(event, newValue) => setFilterOptions((filterOptions) => {
          filterOptions.secondTargetRecording = newValue;
          return {...filterOptions};
        })}
      />

      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.secondTargetChannel}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, secondTargetChannel: event.target.value})}
        label={"Secondary Target Channel"} type={"text"}
        autoComplete={"off"}
        fullWidth
      />

      <Divider />
      
      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.output}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, output: event.target.value})}
        label={"Output Result Label"} type={"text"}
        autoComplete={"off"}
        fullWidth
      />
      <MDBox style={{display: "flex", paddingLeft: 15, paddingRight: 15, paddingTop: 15, justifyContent: "flex-end"}}>
        <MDButton color={"secondary"} 
          onClick={() => updateConfiguration(false)}
        >
          {"Cancel"}
        </MDButton>
        <MDButton color={"info"} 
          onClick={() => {
            if (checkInputComplete()) updateConfiguration(filterOptions);
          }} style={{marginLeft: 10}}
        >
          {newProcess ? "Add" : "Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};

export default CrossCorrrelationAnalysisEditor;