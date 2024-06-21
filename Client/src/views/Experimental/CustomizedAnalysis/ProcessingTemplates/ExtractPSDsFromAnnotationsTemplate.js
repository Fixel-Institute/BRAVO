import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField, Switch, FormControlLabel } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const ExtractPSDsFromAnnotationsTemplate = ({availableRecordings, setConfiguration}) => {
  const [options, setOptions] = useState({
    targetRecording: "",
    filtered: false,
    normalized: true,
    averageFeatures: true,
    output: "Spectral Features Output"
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

      <FormControlLabel 
        control={<Switch checked={options.filtered} 
        onChange={() => setOptions({...options, filtered: !options.filtered})} />} 
        label="Filtered between 1-100Hz? " />

      <FormControlLabel 
        control={<Switch checked={options.normalized} 
        onChange={() => setOptions({...options, normalized: !options.normalized})} />} 
        label="Normalize PSDs?" />

      <FormControlLabel 
        control={<Switch checked={options.averageFeatures} 
        onChange={() => setOptions({...options, averageFeatures: !options.averageFeatures})} />} 
        label="Average PSDs within Each Events? " />

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


export default ExtractPSDsFromAnnotationsTemplate;