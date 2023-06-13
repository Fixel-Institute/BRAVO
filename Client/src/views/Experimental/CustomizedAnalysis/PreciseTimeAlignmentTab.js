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
  IconButton,
  InputLabel,
  Input,
} from "@mui/material"

import { createFilterOptions } from "@mui/material/Autocomplete";

import OpenInBrowserIcon from '@mui/icons-material/OpenInBrowser';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

// core components
import PreciseTimeAlignmentView from "./PreciseTimeAlignmentView";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import MDButton from "components/MDButton";

const filter = createFilterOptions();

const TimeShiftController = ({data, handleUpdateConfig, handleRemoveRecording}) => {
  const [dataToRender, setDataToRender] = useState(data);

  useEffect(() => {
    setDataToRender((dataToRender) => {
      let existingData = dataToRender.map((item) => item.RecordingId);
      for (let i in data) {
        if (!existingData.includes(data[i].RecordingId)) {
          dataToRender.push(data[i]);
        }
      }
      return [...dataToRender];
    });
  }, [data]);

  return dataToRender.map((recording, index) => {
    return <MDBox key={recording.RecordingId} style={{display: "flex", flexDirection: "row", alignItems: "center", justifyContent: "flex-start"}}>
      <MDTypography fontSize={15} style={{marginRight: 10}}>
        {`#${index+1}: `}
      </MDTypography>
      <MDTypography fontSize={15} fontWeight={"bold"}>
        {recording.title}
      </MDTypography>
      <TextField
        variant="standard"
        margin="dense"
        value={recording.TimeShift}
        placeholder={"0"}
        onChange={(event) => setDataToRender((dataToRender) => {
          dataToRender[index].TimeShift = event.target.value;
          return [...dataToRender];
        })}
        label={"Time Adjustment (msec)"} type={"number"}
        autoComplete={"off"}
        style={{marginLeft: 15, paddingBottom: 15}}
      />
      <MDButton variant={"gradient"} color={"info"} style={{marginLeft: 15}} onClick={() => {
        handleUpdateConfig(dataToRender);
      }}>
        {"Update"}
      </MDButton>
      <MDButton variant={"gradient"} color={"error"} style={{marginLeft: 15}} onClick={() => {
        setDataToRender([...dataToRender.filter((data) => data.RecordingId != recording.RecordingId)]);
        handleRemoveRecording([...dataToRender.filter((data) => data.RecordingId != recording.RecordingId)])
      }}>
        {"Remove"}
      </MDButton>
    </MDBox>
  })
}

function PreciseTimeAlignmentTab({analysisId, analysisData, updateAnalysisData}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [dataToRender, setDataToRender] = useState([]);
  const [availableRecordings, setAvailableRecordings] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState(null);

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setData(analysisData);
      setAvailableRecordings(analysisData.Recordings.sort((a,b) => {
        if (a.RecordingLabel == b.RecordingLabel) {
          return b.Time - a.Time;
        } else {
          return a.RecordingLabel < b.RecordingLabel ? -1 : 1;
        }
      }).map((recording) => {
        const descriptor = analysisData.Configuration.Descriptor[recording.RecordingId];
        
        return {
          key: recording.RecordingId,
          title: "[" + descriptor.Type + "] - " + descriptor.Label,
          value: recording.RecordingId
        }
      }));
    }
  }, [patientID, analysisId]);

  const downloadDataAsync = async (dataToRender) => {
    let newData = false;
    for (let i in dataToRender) {
      if (!dataToRender[i].data) {
        try {
          const response = await SessionController.query("/api/queryRecordingsForAnalysis", {
            id: patientID, 
            analysisId: analysisId,
            requestRawData: dataToRender[i].RecordingId,  
          });
          dataToRender[i].data = response.data;
          newData = true;
        } catch (error) {
          SessionController.displayError(error, setAlert);
          return error;
        }
      }
    }
    if (newData) setDataToRender([...dataToRender]);
  }

  useEffect(() => {
    setAlert(<LoadingProgress/>);
    downloadDataAsync(dataToRender).then((error) => {
      if (!error) {
        setAlert(null);
      } else {
        SessionController.displayError(error, setAlert);
      }
    });
  }, [dataToRender]);

  useEffect(() => {
    console.log(analysisData)
  }, [analysisData]);

  const handleAddDataToDisplay = () => {
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
    
    if (selectedRecording) {
      if (dataToRender.filter((data) => data.RecordingId == selectedRecording.value).length > 0) return;
      let selectedData = analysisData.Recordings.filter((recording) => recording.RecordingId == selectedRecording.value)[0];
      selectedData.title = selectedRecording.title;
      selectedData.TimeShift = analysisData.Configuration.Descriptor[selectedData.RecordingId].TimeShift;
      setDataToRender([...dataToRender, selectedData]);
    }
  }

  return data ? (
    <Card width={"100%"} style={{paddingTop: 15, paddingBottom: 15, paddingLeft: 15, paddingRight: 15}}>
      {alert}
      <MDBox>
        <MDTypography fontWeight={"bold"} fontSize={30}>
          {data.Analysis.AnalysisName} {" - Precise Time Alignment"}
        </MDTypography>
        <MDTypography fontSize={18}>
          {"Last Modified: "}{new Date(data.Analysis.AnalysisDate*1000).toLocaleDateString()}
        </MDTypography>
      </MDBox>
      <MDBox pt={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <TimeShiftController data={dataToRender} handleUpdateConfig={(dataToRender) => {
              let changed = false;
              for (let i in dataToRender) {
                if (parseInt(dataToRender[i].TimeShift) != analysisData.Configuration.Descriptor[dataToRender[i].RecordingId].TimeShift) {
                  changed = true;
                  analysisData.Configuration.Descriptor[dataToRender[i].RecordingId].TimeShift = parseInt(dataToRender[i].TimeShift);
                  SessionController.query("/api/queryCustomizedAnalysis", {
                    id: patientID, 
                    analysisId: analysisId,
                    updateRecording: dataToRender[i].RecordingId, 
                    configuration: analysisData.Configuration.Descriptor[dataToRender[i].RecordingId], 
                  }).then((response) => {

                  }).catch((error) => {
                    SessionController.displayError(error, setAlert);
                  });
                }
              }
              if (changed) updateAnalysisData(analysisData);

            }} handleRemoveRecording={(dataToRender) => {
              setDataToRender([...dataToRender]);
            }} />
          </Grid>
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
              renderOption={(props, option) => <li {...props}>{option.title}</li>}
              value={selectedRecording}
              options={availableRecordings}
              onChange={(event, newValue) => setSelectedRecording(newValue)}
            />
            <MDButton variant={"gradient"} color={"success"} style={{minWidth: 300, marginTop: 15}} onClick={handleAddDataToDisplay}>
              {"Add to Display"}
            </MDButton>
          </Grid>
          <Grid item xs={12}>
            <PreciseTimeAlignmentView dataToRender={dataToRender} configuration={analysisData} height={600} figureTitle={"PreciseTimeAlignmentView"} />
          </Grid>
        </Grid>
      </MDBox>
    </Card>
  ) : null;
}

export default PreciseTimeAlignmentTab;
