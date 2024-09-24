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

import SettingsIcon from '@mui/icons-material/Settings';
import OpenInBrowserIcon from '@mui/icons-material/OpenInBrowser';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import ChangeCircleIcon from '@mui/icons-material/ChangeCircle';

import MuiAlertDialog from "components/MuiAlertDialog";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import LoadingProgress from "components/LoadingProgress";

import { availableProcessings, AnalysisSteps } from "./AnalysisSteps";
import { availableTemplates, ProcessingTemplates } from "./ProcessingTemplates";

import { v4 as uuidv4 } from 'uuid';

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";

import { createFilterOptions } from "@mui/material/Autocomplete";
const filter = createFilterOptions();

function CreateProcessingTab({analysisId, analysisData, updateProcessingSteps, updateProcessingResult}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [alert, setAlert] = useState(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [processingTemplate, setProcessingTemplate] = useState({show: false, value: "None", label: "None", options: availableTemplates});
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

      for (let i in processingSteps) {
        availableRecordings.push(processingSteps[i].config.output);
      }
      setAvailableRecordings(availableRecordings);
    }
  }, [analysisId, analysisData]);

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
    setAvailableRecordings([...availableRecordings, processingConfig.config.output]);
  }

  const handleEditStep = (processingConfig) => {
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
      for (let i in processingSteps) {
        if (processingSteps[i].id == processingConfig.id) {
          processingSteps[i] = {...processingSteps[i], ...processingConfig};
        }
      }

      setAvailableRecordings(() => {
        let availableRecordings = [];
        let recordingIds = Object.keys(analysisData.Configuration.Descriptor);
        for (let i in recordingIds) {
          if (!availableRecordings.includes(analysisData.Configuration.Descriptor[recordingIds[i]].Type)) {
            availableRecordings.push(analysisData.Configuration.Descriptor[recordingIds[i]].Type);
          }
        }
        for (let i in processingSteps) {
          availableRecordings.push(processingSteps[i].config.output);
        }
        return [...availableRecordings]
      });

      return [...processingSteps];
    })
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
      if (!config.new) {
        handleEditStep({...editProcessingStep, config: config});
      } else {
        handleAddStep({...editProcessingStep, config: config});
      }
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

  const handleSetTemplate = (options) => {
    if (!options) setProcessingTemplate({show: false, value: "None", label: "None", options: availableTemplates});

    setProcessingSteps(options.map((option) => ({id: uuidv4(), type: option.type, config: option})));
    setAvailableRecordings(() => {
      let availableRecordings = [];
      let recordingIds = Object.keys(analysisData.Configuration.Descriptor);
      for (let i in recordingIds) {
        if (!availableRecordings.includes(analysisData.Configuration.Descriptor[recordingIds[i]].Type)) {
          availableRecordings.push(analysisData.Configuration.Descriptor[recordingIds[i]].Type);
        }
      }
      return [...availableRecordings, ...options.map((option) => option.output)]
    });
    setProcessingTemplate({...processingTemplate, show: false});
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
    });
    updateProcessingResult([]);
  };

  return (
    <MDBox pt={3}>
      {alert}
      <MDBox>
        <MDBox style={{marginBottom: 25}}>
          <Autocomplete selectOnFocus clearOnBlur
            renderInput={(params) => (
              <TextField
                {...params}
                variant="standard"
                label={"Use Template: "}
                placeholder={"Use Template"}
              />
            )}
            filterOptions={(options, params) => {
              const filtered = filter(options, params);
              const { inputValue } = params;
              return filtered;
            }}
            isOptionEqualToValue={(option, value) => option.value === value.value}
            renderOption={(props, option) => <li {...props}>{option.label}</li>}
            value={processingTemplate.label}
            options={processingTemplate.options}
            onChange={(event, newValue) => {
              if (newValue) {
                setProcessingTemplate({...processingTemplate, ...newValue, show: true});
              } else {
                setEditProcessingStep({...editProcessingStep, ...{value: "None", label: "None"}});
              }
            }}/>
        </MDBox>
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
                        <MDBox style={{flexDirection: "column"}}>
                          <MDBox>
                            <MDTypography variant={"h4"} fontFamily={"lato"} fontWeight={"bold"}>
                              {step.type.label}
                            </MDTypography>
                          </MDBox>
                        </MDBox>
                      </MDBox>
                      <MDBox style={{paddingTop: 5}}>
                        <MDTypography variant={"h6"} fontFamily={"lato"} fontWeight={"bold"}>
                          {"Output Data: "} {step.config.output}
                        </MDTypography>
                      </MDBox>
                      <MDBox style={{display: "flex", flexDirection: "row"}}>
                        <IconButton color="info" size="small" onClick={() => setChangeOrder({show: true, currentStep: index, step: index})} sx={{paddingX: 1}}>
                          <ChangeCircleIcon fontSize={"large"} />
                        </IconButton>
                        <IconButton color="info" size="small" onClick={() => {
                          setEditProcessingStep({show: true, new: false, id: step.id, type: step.type, config: step.config})
                        }} sx={{paddingX: 1}}>
                          <SettingsIcon fontSize={"large"} />
                        </IconButton>
                        <IconButton color="error" size="small" onClick={() => handleDeleteStep(step.id)} sx={{paddingX: 1}}>
                          <DeleteForeverIcon fontSize={"large"} />
                        </IconButton>
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
              options={availableProcessings.map((a) => a.type)}
              onChange={(event, newValue) => {
                if (newValue) {
                  setEditProcessingStep({...editProcessingStep, type: newValue});
                } else {
                  setEditProcessingStep({...editProcessingStep, type: {value: "", label: ""}});
                }
              }}
            />
            <AnalysisSteps type={editProcessingStep.type.value} currentState={editProcessingStep.config} availableRecordingChannels={analysisData.Configuration.Descriptor} availableRecordings={availableRecordings} newProcess={editProcessingStep.new} 
              updateConfiguration={updateConfiguration}
            />

            {editProcessingStep.type.value === "" ? (
              <MDButton color={"secondary"}  style={{marginTop: 15}}
                onClick={() => setEditProcessingStep({...editProcessingStep, show: false})}
              >
                {"Cancel"}
              </MDButton>
            ) : null}

          </DialogContent>
        </Dialog>

        <Dialog open={processingTemplate.show} onClose={() => setProcessingTemplate({...processingTemplate, show: false})}>
          <MDBox px={2} pt={2}>
            <MDTypography variant="h5">
              {processingTemplate.label}
            </MDTypography>
          </MDBox>
          <DialogContent sx={{minWidth: 500}} >
            <ProcessingTemplates type={processingTemplate.value} availableRecordings={availableRecordings} setConfiguration={handleSetTemplate}/>

            {processingTemplate.value === "None" ? (
              <MDButton color={"secondary"}  style={{marginTop: 15}}
                onClick={() => setProcessingTemplate({...processingTemplate, show: false})}
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
