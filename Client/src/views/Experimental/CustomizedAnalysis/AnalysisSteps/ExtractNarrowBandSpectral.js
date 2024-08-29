import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const ExtractNarrowBandSpectralEditor = ({currentState, newProcess, availableRecordings, defaultConfigs, updateConfiguration}) => {
  const [filterOptions, setFilterOptions] = useState(newProcess ? {
    ...defaultConfigs,
    targetRecording: "",
    output: "",
    new: true
  } : {...currentState, new: false});
  
  const checkInputComplete = () => {
    return filterOptions.targetRecording !== "" && filterOptions.output !== "";
  }

  return (
    <MDBox style={{marginTop: 20, paddingTop: 5, paddingBottom: 15}}>
      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            placeholder={"Select Target Recording Type"}
          />
        )}
        sx={{marginBottom: 2}}
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
        onChange={(event, newValue) => setFilterOptions({...filterOptions, targetRecording: newValue})}
      />
      
      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            placeholder={"Select Label Recording Type (Default None)"}
          />
        )}
        sx={{marginBottom: 2}}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          return filtered;
        }}
        isOptionEqualToValue={(option, value) => {
          return option === value;
        }}
        renderOption={(props, option) => <li {...props}>{option}</li>}
        value={filterOptions.labelRecording}
        options={availableRecordings}
        onChange={(event, newValue) => setFilterOptions({...filterOptions, labelRecording: newValue})}
      />

      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.averageDuration}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, averageDuration: event.target.value})}
        label={"Spectral Window Size (seconds)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />
      
      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.frequencyRangeStart}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, frequencyRangeStart: event.target.value})}
        label={"Minimum Frequency for Search (Hz)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />
      
      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.frequencyRangeEnd}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, frequencyRangeEnd: event.target.value})}
        label={"Maximum Frequency for Search (Hz)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />
      
      <TextField
        variant="standard"
        margin="dense"
        value={filterOptions.threshold}
        placeholder={"Disable"}
        onChange={(event) => setFilterOptions({...filterOptions, threshold: event.target.value})}
        label={"Peak Selection Threshold (a.u.)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />
      
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
            if (checkInputComplete()) updateConfiguration({...filterOptions});
          }} style={{marginLeft: 10}}
        >
          {newProcess ? "Add" : "Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};

export default ExtractNarrowBandSpectralEditor;