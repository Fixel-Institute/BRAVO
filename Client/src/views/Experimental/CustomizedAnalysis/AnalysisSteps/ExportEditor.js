import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import { TextField } from "@mui/material";

const ExportEditor = ({currentState, newProcess, updateConfiguration}) => {
  const [outputOptions, setOutputOptions] = useState(newProcess ? {
    output: ""
  } : currentState);

  return (
    <MDBox style={{marginTop: 20, paddingTop: 5, paddingBottom: 15}}>
      <TextField
        variant="standard"
        margin="dense"
        value={outputOptions.output}
        placeholder={"Disable"}
        onChange={(event) => setOutputOptions({...outputOptions, output: event.target.value})}
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
            updateConfiguration({
              output: outputOptions.output
            });
          }} style={{marginLeft: 10}}
        >
          {newProcess ? "Add" : "Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};

export default ExportEditor;