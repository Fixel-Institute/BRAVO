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

export default function UploadDialog({show, availableDevices, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language, patientID } = controller;

  const [deidentifiedInfo, setDeidentifiedInfo] = useState({patientId: "", studyId: "", diagnosis: "", deviceName: ""});
  const [decryptionKey, setDecryptionKey] = useState("");
  const [selectedDevice, setSelectedDevice] = useState({label: "New Device", value: "NewDevice"});

  React.useEffect(() => {
    if (availableDevices.length > 0) setSelectedDevice(availableDevices[0]);
  }, [availableDevices])

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
      if (myDropzone.getUploadingFiles().length === 0 && myDropzone.getQueuedFiles().length === 0) {
        SessionController.query("/api/requestProcessing", {
          batchSessionId: batchSessionId
        }).then((response) => {
          if (myDropzone.getRejectedFiles().length === 0) onCancel();
        });
      }
    });
    myDropzone.processQueue();
  }

  const cancelUpload = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.removeAllFiles();
    onCancel();
  };

  const dropzoneRef = createRef();

  return <>
  <Dialog open={show} onClose={cancelUpload}>
    <MDBox px={2} pt={2}>
      <MDTypography variant="h5">
        {"Upload New JSON Session Files"} 
      </MDTypography>
    </MDBox>
    <DialogContent>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Autocomplete
            value={selectedDevice}
            options={[...availableDevices, {label: "New Device", value: "NewDevice"}]}
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
      </Grid>
        
      <MDBox pt={2}>
        <DropzoneUploader options={{
          url: SessionController.getServer() + "/api/uploadSessionFiles",
          paramName: "file",
          addRemoveLinks: true,
          acceptedFiles: ".json",
          autoDiscover: false,
          autoProcessQueue: false,
          uploadMultiple: true,
          headers: { 'Authorization': "Bearer " + SessionController.getAuthToken() },
          parallelUploads: 50,
          maxFiles: 50
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