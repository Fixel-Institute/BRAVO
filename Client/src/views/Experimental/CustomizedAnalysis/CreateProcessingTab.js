/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Badge,
  Grid,
  IconButton,
  Stepper,
  Step,
  StepButton,
  Dialog,
  DialogContent,
  TextField
} from "@mui/material"

import { createFilterOptions } from "@mui/material/Autocomplete";

import SettingsIcon from '@mui/icons-material/Settings';
import OpenInBrowserIcon from '@mui/icons-material/OpenInBrowser';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import ChangeCircleIcon from '@mui/icons-material/ChangeCircle';

import MuiAlertDialog from "components/MuiAlertDialog";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import LoadingProgress from "components/LoadingProgress";

import { v4 as uuidv4 } from 'uuid';

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import AnalysisBuilder from "./AnalysisBuilder";
import PreciseTimeAlignmentTab from "./PreciseTimeAlignmentTab";

const filter = createFilterOptions();

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

const ViewEditor = ({currentState, newProcess, updateConfiguration}) => {
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
            updateConfiguration({view: true});
          }} style={{marginLeft: 10}}
        >
          {newProcess ? "Add" : "Update"}
        </MDButton>
      </MDBox>
    </MDBox>
  );
};

function CreateProcessingTab({analysisId, analysisData, updateProcessingSteps, updateProcessingResult}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [alert, setAlert] = useState(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState(analysisData.Configuration.AnalysisSteps || []);
  const [editProcessingStep, setEditProcessingStep] = useState({
    show: false,
    new: false,
    type: {value: "", label: ""},
    config: {}
  });
  const [changeOrder, setChangeOrder] = useState({
    show: false,
    step: 0,
    currentStep: 0
  });

  const [availableRecordings, setAvailableRecordings] = useState([]);

  useEffect(() => {
    if (analysisId) {
      let availableRecordings = [];
      let recordingIds = Object.keys(analysisData.Configuration.Descriptor);
      for (let i in recordingIds) {
        if (!availableRecordings.includes(analysisData.Configuration.Descriptor[recordingIds[i]].Type)) {
          availableRecordings.push(analysisData.Configuration.Descriptor[recordingIds[i]].Type);
        }
      }
      setAvailableRecordings(availableRecordings);
    }
  }, [analysisId]);

  const handleAddStep = (processingConfig) => {
    if (analysisData.Analysis.ProcessingQueued) {
      setAlert(<MuiAlertDialog 
        title={"Currently Processing"}
        message={"Cannot update analysis until current queue is finished."}
        confirmText={"Confirm"}
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => setAlert(null)}
      />);
      return;
    }

    delete processingConfig["show"];
    delete processingConfig["new"];
    setProcessingSteps([...processingSteps, {
      ...processingConfig,
      id: uuidv4()
    }]);
  }

  const handleDeleteStep = (processId) => {
    if (analysisData.Analysis.ProcessingQueued) {
      setAlert(<MuiAlertDialog 
        title={"Currently Processing"}
        message={"Cannot update analysis until current queue is finished."}
        confirmText={"Confirm"}
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => setAlert(null)}
      />);
      return;
    }

    setAlert(<MuiAlertDialog 
      title={"Remove Step"}
      message={"Are you sure you want to remove this step from analysis?"}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        setProcessingSteps((processingSteps) => {
          processingSteps = processingSteps.filter((step) => step.id != processId);
          return [...processingSteps];
        });
        setAlert(null);
      }}
    />);
  }

  const updateConfiguration = (config) => {
    setEditProcessingStep({...editProcessingStep, show: false});
    if (!config) return;

    if (analysisData.Analysis.ProcessingQueued) {
      setAlert(<MuiAlertDialog 
        title={"Currently Processing"}
        message={"Cannot update analysis until current queue is finished."}
        confirmText={"Confirm"}
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => setAlert(null)}
      />);
      return;
    }
    
    if (config) {
      delete config["show"];
      delete config["new"];
      handleAddStep({...editProcessingStep, config: config});
      setEditProcessingStep({...editProcessingStep, show: false});
    }
  };

  const handleChangeOrder = () => {
    if (analysisData.Analysis.ProcessingQueued) {
      setAlert(<MuiAlertDialog 
        title={"Currently Processing"}
        message={"Cannot update analysis until current queue is finished."}
        confirmText={"Confirm"}
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => setAlert(null)}
      />);
      return;
    }

    setProcessingSteps((processingSteps) => {
      let to = Math.min(processingSteps.length-1, changeOrder.step);
      let from = changeOrder.currentStep;
      processingSteps.splice(to, 0, processingSteps.splice(from, 1)[0]);
      return [...processingSteps];
    });
    setChangeOrder({...changeOrder, show: false});
  };

  useEffect(() => {
    if (processingSteps === analysisData.Configuration.AnalysisSteps) return;
    
    SessionController.query("/api/queryCustomizedAnalysis", {
      updateAnalysisSteps: true, 
      id: patientID, 
      analysisId: analysisId,
      processingSteps: processingSteps
    }).then((response) => {
      updateProcessingResult([]);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
    updateProcessingSteps(processingSteps);
  }, [processingSteps]);

  const requestProcessing = () => {
    SessionController.query("/api/queryCustomizedAnalysis", {
      startAnalysis: true, 
      id: patientID, 
      analysisId: analysisId,
    })
  };

  const availableProcessings = [{
    value: "filter",
    label: "Apply Filter"
  }, {
    value: "export",
    label: "Export Data"
  }, {
    value: "view",
    label: "View Data"
  }]

  return (
    <MDBox pt={3}>
      {alert}
      <MDBox>
        <MDBox style={{marginBottom: 25}}>
          <MDButton fullWidth color={"success"} style={{fontSize: 25}} onClick={requestProcessing} disabled={analysisData.Analysis.ProcessingQueued}>
            {analysisData.Analysis.ProcessingQueued ? "Currently Processing" : "Start Processing"}
          </MDButton>
        </MDBox>
        <Grid container spacing={2}>
          {processingSteps.map((step, index) => {
            return (
              <Grid key={step.id} item xs={12} md={4}>
                <Badge badgeContent={`${index+1}`} color="primary" anchorOrigin={{vertical: "top", horizontal: "left"}} sx={{width: "100%"}}>
                    <Card sx={{width: "100%", padding: 3}}>
                      <MDBox style={{display: "flex", flexDirection: "row", justifyContent: "space-between", alignItems: "start"}}>
                        {step.type.value === "filter" ? (
                          <MDBox style={{flexDirection: "column"}}>
                            <MDBox>
                              <MDTypography variant={"h4"} fontFamily={"lato"} fontWeight={"bold"}>
                                {step.type.label}
                              </MDTypography>
                              <MDTypography variant={"p"} fontFamily={"lato"} fontWeight={"regular"}>
                                {step.config.targetRecording}
                              </MDTypography>
                            </MDBox>
                            <MDBox>
                              <MDTypography variant={"p"} fontFamily={"lato"} fontWeight={"regular"}>
                                {'Highpass: ' + (step.config.highpass === "" ? "Disabled" : step.config.highpass + " Hz")}
                                <br></br>
                                {'Lowpass: ' + (step.config.lowpass === "" ? "Disabled" : step.config.lowpass + " Hz")}
                              </MDTypography>
                            </MDBox>
                          </MDBox>
                        ) : null}
                        {step.type.value === "export" ? (
                          <MDBox style={{flexDirection: "column"}}>
                            <MDBox>
                              <MDTypography variant={"h4"} fontFamily={"lato"} fontWeight={"bold"}>
                                {step.type.label}
                              </MDTypography>
                            </MDBox>
                          </MDBox>
                        ) : null}
                        {step.type.value === "view" ? (
                          <MDBox style={{flexDirection: "column"}}>
                            <MDBox>
                              <MDTypography variant={"h4"} fontFamily={"lato"} fontWeight={"bold"}>
                                {"View Data and Annotations"}
                              </MDTypography>
                            </MDBox>
                          </MDBox>
                        ) : null}
                        <MDBox style={{display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"}}>
                          <IconButton color="info" size="small" onClick={() => setChangeOrder({show: true, currentStep: index, step: index})} sx={{paddingX: 1}}>
                            <ChangeCircleIcon fontSize={"large"} />
                          </IconButton>
                          <IconButton color="error" size="small" onClick={() => handleDeleteStep(step.id)} sx={{paddingX: 1}}>
                            <DeleteForeverIcon fontSize={"large"} />
                          </IconButton>
                        </MDBox>
                      </MDBox>
                      <MDBox style={{paddingTop: 5}}>
                        <MDTypography variant={"h4"} fontFamily={"lato"} fontWeight={"bold"}>
                          {"Output Data: "} {step.config.output}
                        </MDTypography>
                      </MDBox>
                    </Card>
                </Badge>
              </Grid>
            );
          })}
          <Grid item xs={12} md={4}>
            <Card sx={{width: "100%", height: "100%", borderStyle: "dashed", borderWidth: 1, padding: 3, justifyContent: "center", alignItems: "center", cursor: "pointer"}} 
              onClick={() => setEditProcessingStep({show: true, new: true, type: {value: "", label: ""}, config: {}})}>
              <MDTypography>
                {"Add New Step"}
              </MDTypography>
            </Card>
          </Grid>
        </Grid>

        <Dialog open={editProcessingStep.show} onClose={() => setEditProcessingStep({...editProcessingStep, show: false})}>
          <MDBox px={2} pt={2}>
            <MDTypography variant="h5">
              {"Processing Configuration"}
            </MDTypography>
          </MDBox>
          <DialogContent sx={{minWidth: 500}} >
            <Autocomplete 
              selectOnFocus 
              clearOnBlur
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="standard"
                  placeholder={"Select Processing Type"}
                />
              )}
              filterOptions={(options, params) => {
                const filtered = filter(options, params);
                const { inputValue } = params;
                return filtered;
              }}
              isOptionEqualToValue={(option, value) => {
                return option.value === value.value;
              }}
              renderOption={(props, option) => <li {...props}>{option.label}</li>}
              value={editProcessingStep.type}
              options={availableProcessings}
              onChange={(event, newValue) => {
                if (newValue) {
                  setEditProcessingStep({...editProcessingStep, type: newValue});
                } else {
                  setEditProcessingStep({...editProcessingStep, type: {value: "", label: ""}});
                }
              }}/>
            {editProcessingStep.type.value === "filter" ? (
              <FilterEditor currentState={editProcessingStep.config} availableRecordings={availableRecordings} newProcess={editProcessingStep.new} 
              updateConfiguration={updateConfiguration}
              />
            ) : null}
            {editProcessingStep.type.value === "export" ? (
              <ExportEditor newProcess={editProcessingStep.new} 
              updateConfiguration={updateConfiguration}
              />
            ) : null}
            {editProcessingStep.type.value === "view" ? (
              <ViewEditor newProcess={editProcessingStep.new} 
              updateConfiguration={updateConfiguration}
              />
            ) : null}

            {editProcessingStep.type.value === "" ? (
              <MDButton color={"secondary"}  style={{marginTop: 15}}
                onClick={() => setEditProcessingStep({...editProcessingStep, show: false})}
              >
                {"Cancel"}
              </MDButton>
            ) : null}

          </DialogContent>
        </Dialog>
        <Dialog open={changeOrder.show} onClose={() => setChangeOrder({...changeOrder, show: false})}>
          <MDBox px={2} pt={2}>
            <MDTypography variant="h5">
              {"Set Processing Order"}
            </MDTypography>
          </MDBox>
          <DialogContent sx={{minWidth: 500}} >
            <TextField
              variant="standard"
              margin="dense"
              value={changeOrder.step}
              placeholder={"Unchange"}
              onChange={(event) => setChangeOrder({...changeOrder, step: parseInt(event.target.value ? event.target.value : "0")})}
              label={"Change Processing Order ID"} type={"number"}
              autoComplete={"off"}
              fullWidth
            />
          </DialogContent>
          <MDBox style={{display: "flex", paddingLeft: 15, paddingRight: 15, paddingTop: 15, paddingBottom: 15, justifyContent: "flex-end"}}>
            <MDButton color={"secondary"} onClick={() => setChangeOrder({...changeOrder, show: false})} >
              {"Cancel"}
            </MDButton>
            <MDButton color={"info"} onClick={handleChangeOrder} style={{marginLeft: 10}} >
              {"Update"}
            </MDButton>
          </MDBox>
        </Dialog>
      </MDBox>
    </MDBox>
  );
}

export default CreateProcessingTab;
