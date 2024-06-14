import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, TextField } from "@mui/material";

const FilterEditor = ({currentState, newProcess, availableRecordings, updateConfiguration}) => {
  const [filterOptions, setFilterOptions] = useState(newProcess ? {
    targetRecording: "",
    highpass: "",
    lowpass: "",
    output: ""
  } : currentState);

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
        onChange={(event, newValue) => setFilterOptions({...filterOptions, targetRecording: newValue})}
      />
      <MDTypography fontSize={15} style={{paddingTop: 30}}>
        {"Filter Range: "}
      </MDTypography>
      <MDBox style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.highpass}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, highpass: event.target.value})}
          label={"Highpass Filter (Default Disable)"} type={"number"}
          autoComplete={"off"}
          fullWidth
        />
        <TextField
          variant="standard"
          margin="dense"
          value={filterOptions.lowpass}
          placeholder={"Disable"}
          onChange={(event) => setFilterOptions({...filterOptions, lowpass: event.target.value})}
          label={"Lowpass Filter (Default Disable)"} type={"number"}
          autoComplete={"off"}
          fullWidth
        />
      </MDBox>
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


export default FilterEditor;