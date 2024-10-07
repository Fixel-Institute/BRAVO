import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField, Switch, FormControlLabel } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const ExtractNarrowBandSpectralTemplate = ({availableRecordings, setConfiguration}) => {
  const [options, setOptions] = useState({
    targetRecording: "",
    labelRecording: "",
    cardiacRemoved: false,
    wiener: false,
    filtered: false,
    normalized: false,
    averageDuration: 10,
    threshold: 5,
    psdMethod: "Welch's Periodogram",
    output: "Gamma Features Output"
  });

  const checkInputComplete = () => {
    return options.targetRecording !== "" && options.output !== "";
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
        value={options.targetRecording}
        options={availableRecordings}
        onChange={(event, newValue) => setOptions({...options, targetRecording: newValue})}
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
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          return filtered;
        }}
        isOptionEqualToValue={(option, value) => {
          return option === value;
        }}
        renderOption={(props, option) => <li {...props}>{option}</li>}
        value={options.labelRecording}
        options={availableRecordings}
        onChange={(event, newValue) => setOptions({...options, labelRecording: newValue})}
      />

      <FormControlLabel 
        control={<Switch checked={options.cardiacRemoved} 
        onChange={() => setOptions({...options, cardiacRemoved: !options.cardiacRemoved})} />} 
        label="Apply Cardiac Filter? " />

      <FormControlLabel 
        control={<Switch checked={options.wiener} 
        onChange={() => setOptions({...options, wiener: !options.wiener})} />} 
        label="Apply Wiener Filter? (Exploratory Option for Artifacts) " />

      <FormControlLabel 
        control={<Switch checked={options.filtered} 
        onChange={() => setOptions({...options, filtered: !options.filtered})} />} 
        label="Filtered between 1-100Hz? " />

      <FormControlLabel 
        control={<Switch checked={options.normalized} 
        onChange={() => setOptions({...options, normalized: !options.normalized})} />} 
        label="Normalize PSDs?" />

      <Autocomplete 
        selectOnFocus 
        clearOnBlur
        renderInput={(params) => (
          <TextField
            {...params}
            variant="standard"
            label={"Select PSD Method: "}
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
        value={options.psdMethod}
        options={["Short-time Fourier Transform", "Welch's Periodogram", "Autoregressive (AR) Model"]}
        onChange={(event, newValue) => setOptions({...options, psdMethod: newValue})}
        style={{paddingTop: 30}}
        />

      <TextField
        variant="standard"
        margin="dense"
        value={options.averageDuration}
        placeholder={"Disable"}
        onChange={(event) => setOptions({...options, averageDuration: event.target.value})}
        label={"Spectral Window Size (seconds)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />

      <TextField
        variant="standard"
        margin="dense"
        value={options.threshold}
        placeholder={"Disable"}
        onChange={(event) => setOptions({...options, threshold: event.target.value})}
        label={"Peak Detection Threshold (a.u.)"} type={"number"}
        autoComplete={"off"}
        fullWidth
      />

      <TextField
        variant="standard"
        margin="dense"
        value={options.output}
        placeholder={"Disable"}
        onChange={(event) => setOptions({...options, output: event.target.value})}
        label={"Output Result Label"} type={"text"}
        autoComplete={"off"}
        fullWidth
      />
      <MDBox style={{display: "flex", paddingLeft: 15, paddingRight: 15, paddingTop: 15, justifyContent: "flex-end"}}>
        <MDButton color={"secondary"} 
          onClick={() => setConfiguration(false)}
        >
          {"Cancel"}
        </MDButton>
        <MDButton color={"info"} 
          onClick={() => {
            if (checkInputComplete()) {
              setConfiguration(options);
            }
          }} style={{marginLeft: 10}}
        >
          {"Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};

export default ExtractNarrowBandSpectralTemplate;