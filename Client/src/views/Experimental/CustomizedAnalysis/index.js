/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
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

import MuiAlertDialog from "components/MuiAlertDialog";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import LoadingProgress from "components/LoadingProgress";

// core components

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import AnalysisBuilder from "./AnalysisBuilder";
import PreciseTimeAlignmentTab from "./PreciseTimeAlignmentTab";
import CreateProcessingTab from "./CreateProcessingTab";
import AnalysisResultViewer from "./AnalysisResultViewer";

function CustomizedAnalysis() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);

  const [analysisList, setAnalysisList] = useState([]);
  const [analysisId, setAnalysisId] = useState(null);
  const analysisIdRef = useRef();
  analysisIdRef.current = analysisId;
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisStep, setAnalysisStep] = useState({
    index: 0,
    step: "DataInclusion"
  });

  const [editAnalysis, setEditAnalysis] = useState({
    show: false,
    name: ""
  });

  const [eventList, setEventList] = useState([]);
  const [availableDevice, setAvailableDevices] = useState({current: null, list: []});

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    let client = new WebSocket(SessionController.getServer().replace("http","ws") + "/socket/notification");
    client.onerror = function() {
      console.log('Connection Error');
    };
    client.onopen = () => {
      
    };
    client.onclose = () => {
      console.log('Connection Closed');
    };

    client.onmessage = (event) => {
      let content = JSON.parse(event.data);
      if (content["Notification"] === "AnalysisUpdate") {
        if (content["State"] === "StartProcessing") {
          if (analysisIdRef.current == content["TaskID"]) {
            setAnalysisData((analysisData) => {
              analysisData.Analysis.ProcessingQueued = true;
              return {...analysisData};
            });
          }
        } else if (content["State"] === "EndProcessing") {
          if (analysisIdRef.current == content["TaskID"]) {
            setAnalysisData((analysisData) => {
              analysisData.Analysis.ProcessingQueued = false;
              analysisData.Configuration.Results = content["Message"];
              return {...analysisData};
            });
          }
        }
      }
    };

    return () => {
      client.close();
    }
  }, []);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryCustomizedAnalysis", {
        id: patientID, 
        requestOverview: true, 
      }).then((response) => {
        setAnalysisList(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  useEffect(() => {
    if (analysisId) {
      setAlert(<LoadingProgress/>);
      setAnalysisStep({index: 0, step: "DataInclusion"});
      SessionController.query("/api/queryCustomizedAnalysis", {
        id: patientID, 
        requestAnalysis: analysisId, 
      }).then((response) => {
        setAnalysisData(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [analysisId]);

  const handleAddAnalysis = () => {
    SessionController.query("/api/queryCustomizedAnalysis", {
      requestNewAnalysis: true, 
      id: patientID, 
    }).then((response) => {
      setAnalysisList([...analysisList, response.data]);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleDeleteAnalysis = (analysisId) => {
    setAlert(<MuiAlertDialog 
      title={"Remove Analysis"}
      message={"Are you sure you want to remove the analysis? All configurations for this analysis will be removed and is not recoverable"}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        SessionController.query("/api/queryCustomizedAnalysis", {
          requestNewAnalysis: false, 
          id: patientID, 
          analysisId: analysisId
        }).then((response) => {
          setAnalysisList([...analysisList.filter((analysis) => analysis.AnalysisID != analysisId)]);
          setAlert(null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />);
  };

  useEffect(() => {
    
  }, [analysisData]);

  const analysisSteps = [{
    label: "Data Inclusion",
    value: "DataInclusion",
  },{
    label: "Precise Time Alignment",
    value: "TimeAlignment",
    optional: true
  },{
    label: "Analysis Processing",
    value: "AnalysisProcessing",
  },{
    label: "View Current Results",
    value: "ViewResult",
  }];

  const handleChangeView = (step, index) => {
    setAnalysisStep({index: index, step: step});
  };

  const handleEditAnalysis = (id) => {
    SessionController.query("/api/queryCustomizedAnalysis", {
      editAnalysis: true, 
      id: patientID, 
      analysisId: id,
      name: editAnalysis.name
    }).then((response) => {
      setAnalysisList((analysisList) => {
        for (let i in analysisList) {
          if (analysisList[i].AnalysisID == id) {
            analysisList[i].AnalysisName = editAnalysis.name;
          }
        }
        return [...analysisList];
      });
      if (analysisId == id) {
        setAnalysisData((analysisData) => {
          analysisData.Analysis.AnalysisName = editAnalysis.name;
          return {...analysisData};
        });
      }
      setEditAnalysis({...editAnalysis, show: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  return (
    <>
      {alert}
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              {analysisList.map((analysis) => {
                return (
                  <Grid key={analysis.AnalysisID} item xs={6} md={4}>
                    <Card sx={{width: "100%", padding: 3, display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "start"}}>
                      <MDBox>
                        <MDTypography fontWeight={"bold"}>
                          {analysis.AnalysisName}
                        </MDTypography>
                        <MDTypography fontSize={15}>
                          {new Date(analysis.AnalysisDate*1000).toLocaleDateString()}
                        </MDTypography>
                      </MDBox>

                      <Dialog open={editAnalysis.show} onClose={() => setEditAnalysis({...editAnalysis, show: false})}>
                        <MDBox px={2} pt={2}>
                          <MDTypography variant="h5">
                            {"Edit Analysis Name"}
                          </MDTypography>
                        </MDBox>
                        <DialogContent>
                          <TextField
                            variant="standard"
                            margin="dense" id="name"
                            value={editAnalysis.name}
                            onChange={(event) => setEditAnalysis({...editAnalysis, name: event.target.value})}
                            fullWidth
                          />
                        </DialogContent>
                        <MDBox style={{paddingLeft: 15, paddingRight: 15, paddingBottom: 15}}>
                          <MDButton color={"secondary"} 
                            onClick={() => setEditAnalysis({...editAnalysis, show: false})}
                          >
                            Cancel
                          </MDButton>
                          <MDButton color={"info"} 
                            onClick={() => handleEditAnalysis(analysis.AnalysisID)} style={{marginLeft: 10}}
                          >
                            Update
                          </MDButton>
                        </MDBox>
                      </Dialog>
                      <MDBox>
                        <IconButton color="info" size="small" onClick={() => setEditAnalysis({name: analysis.AnalysisName, show: true})} sx={{paddingX: 1}}>
                          <SettingsIcon fontSize={"large"} />
                        </IconButton>
                        <IconButton color="info" size="small" onClick={() => setAnalysisId(analysis.AnalysisID)} sx={{paddingX: 1}}>
                          <OpenInBrowserIcon fontSize={"large"} />
                        </IconButton>
                        <IconButton color="error" size="small" onClick={() => handleDeleteAnalysis(analysis.AnalysisID)} sx={{paddingX: 1}}>
                          <DeleteForeverIcon fontSize={"large"} />
                        </IconButton>
                      </MDBox>
                    </Card>
                  </Grid>
                );
              })}
              <Grid item xs={6} md={3}>
                <Card sx={{width: "100%", height: "100%", borderStyle: "dashed", borderWidth: 1, padding: 3, justifyContent: "center", alignItems: "center", cursor: "pointer"}} onClick={handleAddAnalysis}>
                  <MDTypography>
                    {"Add New Analysis"}
                  </MDTypography>
                </Card>
              </Grid>
            </Grid>
          </MDBox>
          {analysisId ? (
            <MDBox pt={3}>
              <Stepper nonLinear activeStep={analysisStep.index}>
                {analysisSteps.map((step, index) => (
                  <Step key={step.value} completed={false}>
                    <StepButton optional={step.optional ? (
                      <MDTypography variant="caption">Optional</MDTypography>
                    ) : null} onClick={() => {
                      handleChangeView(step.value, index);
                    }}>{step.label}</StepButton>
                  </Step>
                ))}
              </Stepper>
            </MDBox>
          ) : null}

          {analysisId && analysisData && analysisStep.step == "DataInclusion" ? (
            <MDBox pt={3}>
              <AnalysisBuilder analysisId={analysisId} analysisData={analysisData} updateAnalysisData={(data) => {
                setAnalysisData({...data});
              }} />
            </MDBox>
          ) : null}
          {analysisId && analysisData && analysisStep.step == "TimeAlignment" ? (
            <MDBox pt={3}>
              <PreciseTimeAlignmentTab analysisId={analysisId} analysisData={analysisData} updateAnalysisData={(data) => {
                setAnalysisData({...data});
              }} />
            </MDBox>
          ) : null}
          {analysisId && analysisData && analysisStep.step == "AnalysisProcessing" ? (
            <MDBox pt={3}>
              <CreateProcessingTab analysisId={analysisId} analysisData={analysisData} updateProcessingSteps={(steps) => {
                setAnalysisData((analysisData) => {
                  analysisData.Configuration.AnalysisSteps = steps;
                  return {...analysisData};
                });
              }} updateProcessingResult={(results) => {
                setAnalysisData((analysisData) => {
                  analysisData.Configuration.Results = results;
                  return {...analysisData};
                });
              }}/>
            </MDBox>
          ) : null}
          {analysisId && analysisData && analysisStep.step == "ViewResult" ? (
            <MDBox pt={3}>
              <AnalysisResultViewer analysisId={analysisId} analysisData={analysisData} />
            </MDBox>
          ) : null}
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default CustomizedAnalysis;
