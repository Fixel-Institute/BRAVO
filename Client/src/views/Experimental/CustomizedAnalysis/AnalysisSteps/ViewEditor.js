import { useState } from "react";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";

const ViewEditor = ({currentState, newProcess, updateConfiguration}) => {
  const [outputOptions, setOutputOptions] = useState(newProcess ? {
    output: "View Data"
  } : currentState);
  
  return (
    <MDBox style={{marginTop: 20, paddingTop: 5, paddingBottom: 15}}>
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

export default ViewEditor;