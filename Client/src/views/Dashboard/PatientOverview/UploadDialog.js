/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { createRef, useState } from "react";

import {
  Autocomplete,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";
import FormField from "components/MDInput/FormField.js";

import { v4 as uuidv4 } from 'uuid';

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const formatAsDate = (datetime) => {
  return datetime.getFullYear() + "-" + (datetime.getMonth()+1).toFixed(0).padStart(2, "0") + "-" + datetime.getDate().toFixed(0).padStart(2, "0");
};

const formatAsTime = (datetime) => {
  return datetime.getHours().toFixed(0).padStart(2, "0") + ":" + datetime.getMinutes().toFixed(0).padStart(2, "0") + ":" + datetime.getSeconds().toFixed(0).padStart(2, "0");
};

export default function UploadDialog({show, availableDevices, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language, patientID } = controller;

  const [deidentifiedInfo, setDeidentifiedInfo] = useState({patientId: "", studyId: "", diagnosis: "", deviceName: ""});
  const [decryptionKey, setDecryptionKey] = useState("");
  const [selectedDevice, setSelectedDevice] = useState({label: "New Device", value: "NewDevice"});
  const [externalDataInfo, setExternalDataInfo] = useState({
    format: "CSV",
    label: "External Recording",
    samplingRate: "100",
    startDate: formatAsDate(new Date()),
    startTime: formatAsTime(new Date())
  });

  const dropzoneRef = createRef();

  React.useEffect(() => {
    if (availableDevices.length > 0) setSelectedDevice(availableDevices[0]);
  }, [availableDevices]);

  React.useEffect(() => {
    if (dropzoneRef.current) {
      const myDropzone = dropzoneRef.current.dropzone;
      //myDropzone.hiddenFileInput.setAttribute("webkitdirectory", true);
    }
  }, [dropzoneRef]);

  const uploadSessionsDeidentified = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    let deviceId = selectedDevice.value;
    if (deviceId === "NewDevice") {
      deviceId = uuidv4();
    }
    
    const batchSessionId = uuidv4() + new Date().toISOString();

    myDropzone.on("processing", function() {
      this.options.autoProcessQueue = true;
    });
    myDropzone.on("sending", function(file, xhr, formData) {
      formData.append("deviceId", deviceId);  
      formData.append("patientId", patientID);
      formData.append("batchSessionId", batchSessionId);
      if (deviceId === "ExternalRecordings") {
        formData.append("Format", externalDataInfo.format);
        formData.append("SamplingRate", externalDataInfo.samplingRate);
        formData.append("StartTime", new Date(externalDataInfo.startDate + " " + externalDataInfo.startTime).getTime());
        formData.append("RecordingLabel", externalDataInfo.label);
      }
    });
    myDropzone.on("success", function(file, response) {
      this.removeFile(file);
    });
    myDropzone.on("successmultiple", function(file, response) {
      if (myDropzone.files.length > 0) {
        myDropzone.processQueue();
      }
    });
    myDropzone.on("complete", function(file, response) {
      if (myDropzone.getUploadingFiles().length === 0 && myDropzone.getQueuedFiles().length === 0 && myDropzone.files.length === 0) {
        SessionController.query("/api/requestProcessing", {
          batchSessionId: batchSessionId
        }).then((response) => {
          onCancel();
        }).catch((error) => {
          console.log(error);
        })
      }
    });
    myDropzone.processQueue();
  }

  const cancelUpload = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.removeAllFiles();
    onCancel();
  };

  const getDeviceType = (selectedDeviceConfig, externalDataInfoConfig) => {
    console.log(selectedDeviceConfig)
    if (selectedDeviceConfig.value === "ExternalRecordings") {
      if (externalDataInfoConfig.format === "CSV") {
        return ".csv";
      } else if (externalDataInfoConfig.format === "MDAT") {
        return ".mdat";
      }
    } else {
      return ".json,.zip";
    }
    return ".json,.zip";
  }

  return <>
  <Dialog open={show} onClose={cancelUpload}>
    <MDBox px={2} pt={2}>
      <MDTypography variant="h5">
        {"Upload New Recordings"} 
      </MDTypography>
    </MDBox>
    <DialogContent>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Autocomplete
            value={selectedDevice}
            options={[...availableDevices, {label: "New Device", value: "NewDevice"}, {label: "External Recording", value: "ExternalRecordings"}]}
            onChange={(event, value) => setSelectedDevice(value)}
            isOptionEqualToValue={(option, value) => {
              return option.value == value.value;
            }}
            renderInput={(params) => (
              <FormField
                {...params}
                label={"Device to Upload To"}
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </Grid>
        {selectedDevice.value === "ExternalRecordings" ? (
          <Grid item xs={12} style={{display: "flex", flexDirection: "column"}}>
            <Autocomplete
              value={externalDataInfo.format}
              options={[{label: "CSV", value: "CSV"}, {label: "UF MDAT Format", value: "MDAT"}]}
              onChange={(event, value) => {
                setExternalDataInfo({...externalDataInfo, format: value.value})
              }}
              isOptionEqualToValue={(option, value) => {
                return option.value == value;
              }}
              renderInput={(params) => (
                <FormField
                  {...params}
                  label={"External Recording Format"}
                  InputLabelProps={{ shrink: true }}
                />
              )}
              disableClearable
            />
            {externalDataInfo.format === "CSV" ? (
              <>
                <TextField
                  variant="standard"
                  margin="dense"
                  label="Recording Name"
                  placeholder="External Recording"
                  value={externalDataInfo.label}
                  onChange={(event) => setExternalDataInfo({...externalDataInfo, label: event.target.value})}

                />
                <TextField
                  variant="standard"
                  margin="dense"
                  label="Sampling Rate (Hz)"
                  placeholder="Sampling Rate (Hz)"
                  value={externalDataInfo.samplingRate}
                  type="number"
                  onChange={(event) => setExternalDataInfo({...externalDataInfo, samplingRate: event.target.value})}
                />
                <MDBox style={{display: "flex", flexDirection: "row", justifyContent: "space-between"}}>
                  <TextField
                    variant="standard"
                    margin="dense"
                    label="Recording Date"
                    placeholder="Recording Time"
                    value={externalDataInfo.startDate}
                    type={"date"}
                    onChange={(event) => setExternalDataInfo({...externalDataInfo, startDate: event.target.value})}
                    fullWidth
                  />
                  <TextField
                    variant="standard"
                    margin="dense"
                    label="Recording Time"
                    placeholder="Recording Time"
                    value={externalDataInfo.startTime}
                    type={"time"}
                    onChange={(event) => setExternalDataInfo({...externalDataInfo, startTime: event.target.value})}
                    fullWidth
                  />
                </MDBox>
              </>
            ) : null }
            
          </Grid>
        ) : null}
      </Grid>
        
      <MDBox pt={2}>
        <DropzoneUploader options={{
          url: SessionController.getServer() + (selectedDevice.value === "ExternalRecordings" ? "/api/uploadExternalFiles" : "/api/uploadSessionFiles"),
          paramName: "file",
          addRemoveLinks: true,
          acceptedFiles: getDeviceType(selectedDevice, externalDataInfo),
          autoDiscover: false,
          autoProcessQueue: false,
          uploadMultiple: true,
          headers: { 'Authorization': "Bearer " + SessionController.getAuthToken() },
          parallelUploads: 500,
          maxFiles: 500,
          maxFilesize: 500
        }} ref={dropzoneRef}>
        </DropzoneUploader>
      </MDBox>
    </DialogContent>
    <DialogActions>
      <MDButton color="secondary" onClick={() => cancelUpload()}>Cancel</MDButton>
      <MDButton color="info" onClick={() => uploadSessionsDeidentified()}>Upload</MDButton>
    </DialogActions>
  </Dialog>
  </>
}