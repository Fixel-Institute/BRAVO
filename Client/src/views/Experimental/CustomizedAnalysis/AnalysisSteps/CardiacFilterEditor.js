import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField } from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

const CardiacFilterEditor = ({currentState, newProcess, availableRecordings, defaultConfigs, updateConfiguration}) => {
  const [filterOptions, setFilterOptions] = useState(newProcess ? {
    ...defaultConfigs,
    targetRecording: "",
    output: "",
    new: true
  } : {...currentState, new: false});

  const availableMethods = ["LMS Decoupler", "Fixed Height Peak Detection Template Matching", "Kurtosis-peak Detection Template Matching"];

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
          filterOptions.output = newValue + "_CardiacFiltered";
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
            placeholder={"Select Cardiac Filter Method"}
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
        value={filterOptions.cardiacFilterMethod}
        options={availableMethods}
        onChange={(event, newValue) => setFilterOptions({...filterOptions, cardiacFilterMethod: newValue})}
        style={{paddingTop: 30}}
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
            if (checkInputComplete()) updateConfiguration(filterOptions);
          }} style={{marginLeft: 10}}
        >
          {newProcess ? "Add" : "Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};


export default CardiacFilterEditor;