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
  Dialog,
  DialogContent,
  TextField,
  Card,
  Grid,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Checkbox,
  IconButton,
  InputLabel,
  Input,
} from "@mui/material"

import { FixedSizeList } from 'react-window';

import { createFilterOptions } from "@mui/material/Autocomplete";

import { Edit as EditIcon } from "@mui/icons-material"

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

// core components
import AnalysisBuilderOverview from "./AnalysisBuilderOverview";
import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import MDButton from "components/MDButton";

const filter = createFilterOptions();

function AnalysisBuilder({analysisId, analysisData, updateAnalysisData}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [availableRecordings, setAvailableRecordings] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState({
    value: "",
    type: "Signal",
    show: false
  });

  const [configureRecording, setConfigureRecording] = useState({
    configuration: {},
    show: false
  });

  const [editChannelName, setEditChannelName] = useState({
    show: false,
    name: "",
    id: ""
  });

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setData(analysisData);
      setAvailableRecordings(analysisData.AvailableRecordings.sort((a,b) => {
        if (a.RecordingLabel == b.RecordingLabel) {
          return b.Time - a.Time;
        } else {
          return a.RecordingLabel < b.RecordingLabel ? -1 : 1;
        }
      }).map((recording) => {
        let descriptor = new Date(recording.Time*1000).toLocaleString();
        if (recording.RecordingType == "ChronicLFPs") {
          descriptor = "";
        } else {
          descriptor = "(" + descriptor + " / " + recording.Duration.toFixed(0) + " seconds) "
        }
        
        return {
          key: recording.RecordingId,
          title: "[" + recording.RecordingLabel + "] - " + descriptor + recording.RecordingType,
          value: recording.RecordingId
        }
      }));
    }
  }, [patientID, analysisId]);

  useEffect(() => {

  }, [availableRecordings]);

  const handleNewRecordingForAnalysis = (recordingInfo) => {
    if (!recordingInfo.value) return;

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
    
    SessionController.query("/api/queryCustomizedAnalysis", {
      id: patientID, 
      analysisId: analysisId,
      addRecording: recordingInfo.value.value, 
      recordingType: recordingInfo.type, 
    }).then((response) => {
      setData((data) => {
        data.Recordings = [...data.Recordings, response.data.recording];
        data.Configuration.Descriptor[response.data.recording.RecordingId] = response.data.configuration;
        updateAnalysisData(data);
        return {...data};
      });
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const handleStreamConfiguration = (plotlyPoint) => {
    let recording = data.Recordings[plotlyPoint.points[0].pointIndex];
    let configuration = data.Configuration.Descriptor[recording.RecordingId] || {};
    setConfigureRecording({...configureRecording, 
      title: "[" + recording.RecordingLabel + "] - " + recording.RecordingType, 
      recordingId: recording.RecordingId, 
      configuration: configuration, 
      channels: recording.RecordingChannels,
      show: true});
  }

  const handleDeleteVerification = () => {
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
      title={"Remove Recording"}
      message={"Are you sure you want to remove the recording from analysis? All configurations for this recording will be removed."}
      confirmText={"YES"}
      denyText={"NO"}
      denyButton
      handleClose={() => setAlert(null)}
      handleDeny={() => setAlert(null)}
      handleConfirm={() => {
        SessionController.query("/api/queryCustomizedAnalysis", {
          id: patientID, 
          analysisId: analysisId,
          removeRecording: configureRecording.recordingId, 
        }).then((response) => {
          setData((data) => {
            data.Recordings = data.Recordings.filter((recording) => recording.RecordingId != configureRecording.recordingId);
            data.Configuration.Descriptor[configureRecording.recordingId] = null;
            updateAnalysisData(data);
            return {...data};
          });
          setConfigureRecording({...configureRecording, show: false});
          setAlert(null);
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        });
      }}
    />)
  };

  const handleUpdateConfiguration = () => {
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

    configureRecording.configuration.TimeShift = configureRecording.configuration.TimeShift === "" ? 0 : parseInt(configureRecording.configuration.TimeShift);
    SessionController.query("/api/queryCustomizedAnalysis", {
      id: patientID, 
      analysisId: analysisId,
      updateRecording: configureRecording.recordingId, 
      configuration: configureRecording.configuration, 
    }).then((response) => {
      setData((data) => {
        data.Configuration.Descriptor[configureRecording.recordingId] = configureRecording.configuration;
        updateAnalysisData(data);
        return {...data};
      });
      setConfigureRecording({...configureRecording, show: false})
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const renderChannelLists = ({index, style}) => {
    let show = true;
    let customName = configureRecording.channels[index];
    if (Object.keys(configureRecording.configuration.Channels).includes(configureRecording.channels[index])) {
      show = configureRecording.configuration.Channels[configureRecording.channels[index]].show
      customName = configureRecording.configuration.Channels[configureRecording.channels[index]].name
    }

    const handleToggleSingle = () => {
      if (!Object.keys(configureRecording.configuration.Channels).includes(configureRecording.channels[index])) {
        configureRecording.configuration.Channels[configureRecording.channels[index]] = {
          show: true,
          name: configureRecording.channels[index]
        };
      }
      configureRecording.configuration.Channels[configureRecording.channels[index]].show = !configureRecording.configuration.Channels[configureRecording.channels[index]].show;
      setConfigureRecording({...configureRecording});
    };

    const handleDoubleClick = () => {
      for (let i in configureRecording.channels) {
        if (i == index) continue;

        if (!Object.keys(configureRecording.configuration.Channels).includes(configureRecording.channels[i])) {
          configureRecording.configuration.Channels[configureRecording.channels[i]] = {
            show: true,
            name: configureRecording.channels[i]
          };
        }
        configureRecording.configuration.Channels[configureRecording.channels[i]].show = !configureRecording.configuration.Channels[configureRecording.channels[i]].show;
      }
      setConfigureRecording({...configureRecording});
    }

    var updateTimeout = null;
    var singleClicked = false;
    const onClick = () => {
      if (singleClicked) {
        singleClicked = false;
        handleDoubleClick();
        clearTimeout(updateTimeout);
      } else {
        singleClicked = true;
        updateTimeout = setTimeout(function() {
          handleToggleSingle();
          singleClicked = false
        }, 200);
      }
    };

    return (
      <ListItem style={style} key={index} 
        secondaryAction={
          <IconButton edge="end" aria-label="comments" onClick={() => {
            setEditChannelName({...editChannelName, id: index, name: customName, show: true});
          }} sx={{marginRight: 1}}>
            <EditIcon />
          </IconButton>
        }
        disablePadding>
        <ListItemButton onClick={onClick} dense>
          <ListItemIcon>
            <Checkbox
              edge="start"
              checked={show}
              tabIndex={-1}
              disableRipple
            />
          </ListItemIcon>
          <ListItemText primary={customName} />
        </ListItemButton>
      </ListItem>
    )
  };

  return data ? (
    <Card width={"100%"} style={{paddingTop: 15, paddingBottom: 15, paddingLeft: 15, paddingRight: 15}}>
      {alert}

      <Dialog open={editChannelName.show} onClose={() => setEditChannelName({...editChannelName, show: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Edit Channel Name"}
          </MDTypography>
        </MDBox>
        <DialogContent>
          <TextField
            variant="standard"
            margin="dense" id="name"
            value={editChannelName.name}
            onChange={(event) => setEditChannelName({...editChannelName, name: event.target.value})}
            fullWidth
          />
        </DialogContent>
        <MDBox style={{paddingLeft: 15, paddingRight: 15, paddingBottom: 15}}>
          <MDButton color={"secondary"} 
            onClick={() => setEditChannelName({...editChannelName, show: false})}
          >
            Cancel
          </MDButton>
          <MDButton color={"info"} 
            onClick={() => {
              if (!Object.keys(configureRecording.configuration.Channels).includes(configureRecording.channels[editChannelName.id])) {
                configureRecording.configuration.Channels[configureRecording.channels[editChannelName.id]] = {
                  show: true,
                  name: configureRecording.channels[editChannelName.id]
                };
              }
              configureRecording.configuration.Channels[configureRecording.channels[editChannelName.id]].name = editChannelName.name;
              setConfigureRecording({...configureRecording});
              setEditChannelName({...editChannelName, show: false});
            }} style={{marginLeft: 10}}
          >
            Update
          </MDButton>
        </MDBox>
      </Dialog>


      <Dialog open={configureRecording.show} onClose={() => setConfigureRecording({...configureRecording, show: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Configure Recording for Analysis"}
          </MDTypography>
          <MDTypography variant="p" fontSize={15}>
            {configureRecording.title || ""}
          </MDTypography>
        </MDBox>
        <DialogContent style={{minWidth: 500}} >
          <MDBox>
            <TextField
              variant="standard"
              margin="dense"
              value={configureRecording.configuration.TimeShift}
              placeholder={"0"}
              onChange={(event) => setConfigureRecording((configureRecording) => {
                configureRecording.configuration.TimeShift = event.target.value;
                return {...configureRecording};
              })}
              label={"Time Adjustment (msec)"} type={"number"}
              autoComplete={"off"}
              fullWidth
            />
            <TextField
              variant="standard"
              margin="dense"
              value={configureRecording.configuration.Label}
              placeholder={configureRecording.title}
              onChange={(event) => setConfigureRecording((configureRecording) => {
                configureRecording.configuration.Label = event.target.value;
                return {...configureRecording};
              })}
              label={"Recording Label (Description)"} type={"text"}
              autoComplete={"off"}
              fullWidth
            />
            <TextField
              variant="standard"
              margin="dense"
              value={configureRecording.configuration.Type}
              placeholder={"Signal"}
              onChange={(event) => setConfigureRecording((configureRecording) => {
                configureRecording.configuration.Type = event.target.value;
                return {...configureRecording};
              })}
              label={"Data Type (Grouping)"} type={"text"}
              autoComplete={"off"}
              fullWidth
            />
          </MDBox>
          {configureRecording.channels ? (
          <MDBox style={{ width: '100%', height: 400, bgcolor: 'background.paper', marginTop: 15}}>
            <MDTypography variant="h5">
              {"Channels Selection"}
            </MDTypography>
            <FixedSizeList height={380} width={"100%"} itemSize={36} itemCount={configureRecording.channels.length} overscanCount={5}>
              {renderChannelLists}
            </FixedSizeList>
          </MDBox>
          ) : null}
        </DialogContent>
        <MDBox px={2} py={2} style={{display: "flex", justifyContent: "space-between"}}>
          <MDBox px={2} py={2} style={{display: "flex", justifyContent: "space-between"}}>
            <MDButton variant={"gradient"} color={"error"} onClick={handleDeleteVerification}>
              {"Delete"}
            </MDButton>
          </MDBox>
          <MDBox px={2} py={2} style={{display: "flex", justifyContent: "space-around"}}>
            <MDButton variant={"gradient"} color={"secondary"} onClick={() => setConfigureRecording({...configureRecording, show: false})}>
              {"Cancel"}
            </MDButton>
            <MDButton variant={"gradient"} color={"success"} onClick={handleUpdateConfiguration}>
              {"Update"}
            </MDButton>
          </MDBox>
        </MDBox>
      </Dialog>
      <MDBox>
        <MDTypography fontWeight={"bold"} fontSize={30}>
          {analysisData.Analysis.AnalysisName}
        </MDTypography>
        <MDTypography fontSize={18}>
          {"Last Modified: "}{new Date(analysisData.Analysis.AnalysisDate*1000).toLocaleDateString()}
        </MDTypography>
      </MDBox>
      <MDBox pt={5}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Autocomplete 
              selectOnFocus 
              clearOnBlur
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="standard"
                  placeholder={"Select Recordings"}
                />
              )}
              filterOptions={(options, params) => {
                const filtered = filter(options, params);
                const { inputValue } = params;
                return filtered;
              }}
              getOptionLabel={(option) => {
                if (typeof option === 'string') {
                  return option;
                }
                if (option.inputValue) {
                  return option.inputValue;
                }
                return option.title;
              }}
              isOptionEqualToValue={(option, value) => {
                return option.value === value.value;
              }}
              freeSolo
              renderOption={(props, option) => <li {...props}>{option.title}</li>}
              value={selectedRecording.value}
              options={availableRecordings}
              onChange={(event, newValue) => setSelectedRecording({...selectedRecording, value: newValue})}
            />
            <TextField
              variant="standard"
              margin="dense"
              value={selectedRecording.type}
              placeholder={"Signal"}
              onChange={(event) => setSelectedRecording({...selectedRecording, type: event.target.value})}
              label={"Input Data Type"} type={"text"}
              autoComplete={"off"}
              fullWidth
            />

            <MDButton variant={"gradient"} color={"success"} style={{minWidth: 300, marginTop: 15}} onClick={() => handleNewRecordingForAnalysis(selectedRecording)}>
              {"Add"}
            </MDButton>
          </Grid>
          <Grid item xs={12}>
            <AnalysisBuilderOverview dataToRender={data} onStreamClicked={handleStreamConfiguration} height={500} figureTitle={"Data To Analyze"} />
          </Grid>
        </Grid>
      </MDBox>
    </Card>
  ) : null;
}

export default AnalysisBuilder;
