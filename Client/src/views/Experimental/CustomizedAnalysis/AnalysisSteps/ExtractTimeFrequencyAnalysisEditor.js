import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField, Switch, FormControlLabel } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const ExtractTimeFrequencyAnalysisEditor = ({currentState, newProcess, availableRecordings, defaultConfigs, updateConfiguration}) => {
  const [filterOptions, setFilterOptions] = useState(newProcess ? {
    ...defaultConfigs,
    targetRecording: "",
    output: "",
    new: true
  } : {...currentState, new: false});

  const checkInputComplete = () => {
    return filterOptions.targetRecording !== "" && filterOptions.output !== "";
  }

  const availableMethods = ["Short-time Fourier Transform", "Welch's Periodogram", "Autoregressive (AR) Model"];

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
          filterOptions.output = newValue + "_Spectrogram";
          return {...filterOptions};
        })}
      />

      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            placeholder={"Select PSD Method"}
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
        value={filterOptions.psdMethod}
        options={availableMethods}
        onChange={(event, newValue) => setFilterOptions({...filterOptions, psdMethod: newValue})}
        style={{paddingTop: 30}}
      />

      {filterOptions.psdMethod === "Autoregressive (AR) Model" ? (
      <MDBox style={{display: "flex", paddingLeft: 5, paddingRight: 5, justifyContent: "space-between"}}>
        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.window}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, window: event.target.value})}
          label={"Window (ms)"} type={"number"}
          autoComplete={"off"}
        />

        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.overlap}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, overlap: event.target.value})}
          label={"Overlap (ms)"} type={"number"}
          autoComplete={"off"}
        />

        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.modelOrder}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, modelOrder: event.target.value})}
          label={"Model Order"} type={"number"}
          autoComplete={"off"}
        />
      </MDBox>
      ) : (
      <MDBox style={{display: "flex", paddingLeft: 5, paddingRight: 5, justifyContent: "space-between"}}>
        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.window}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, window: event.target.value})}
          label={"Window (ms)"} type={"number"}
          autoComplete={"off"}
        />

        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.overlap}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, overlap: event.target.value})}
          label={"Overlap (ms)"} type={"number"}
          autoComplete={"off"}
        />

        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.frequencyResolution}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, frequencyResolution: event.target.value})}
          label={"Frequency Resolution (Hz)"} type={"number"}
          autoComplete={"off"}
        />
      </MDBox>
      )}
      

      <FormControlLabel 
        control={<Switch checked={filterOptions.dropMissing} 
        onChange={() => setFilterOptions({...filterOptions, dropMissing: !filterOptions.dropMissing})} />} 
        label="Drop Missing" />

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

export default ExtractTimeFrequencyAnalysisEditor;