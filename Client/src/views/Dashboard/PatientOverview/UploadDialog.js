import { createRef, useState } from "react";

import {
  Autocomplete,
  Grid,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import MDDropzone from "components/MDDropzone";
import FormField from "components/MDInput/FormField.js";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function UploadDialog({availableDevices, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [deidentifiedInfo, setDeidentifiedInfo] = useState({patientId: "", studyId: "", diagnosis: "", deviceName: ""});
  const [decryptionKey, setDecryptionKey] = useState("");
  const [selectedDevice, setSelectedDevice] = useState(availableDevices[0]);
  
  const uploadSessionsDeidentified = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.on("processing", function() {
      this.options.autoProcessQueue = true;
    });
    myDropzone.on("sending", function(file, xhr, formData) { 
      formData.append("deviceId", selectedDevice.value);  
    });
    myDropzone.on("success", function(file, response) {
      this.removeFile(file);
    });
    myDropzone.on("complete", function(file, response) {
      if (myDropzone.getUploadingFiles().length === 0 && myDropzone.getQueuedFiles().length === 0) {
        onCancel();
      }
    });
    myDropzone.processQueue();
  }

  const dropzoneRef = createRef();

  return <>
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
            options={availableDevices}
            onChange={(event, value) => setSelectedDevice(value)}
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
        <MDDropzone options={{
          url: window.location.origin + "/api/uploadSessionFiles",
          paramName: "file",
          addRemoveLinks: true,
          acceptedFiles: ".json",
          autoDiscover: false,
          autoProcessQueue: false,
          uploadMultiple: false,
          headers: { 'Authorization': "Token " + SessionController.getAuthToken() },
          parraleleupload: 1,
        }} ref={dropzoneRef}>
        </MDDropzone>
      </MDBox>
    </DialogContent>
    <DialogActions>
      <MDButton color="secondary" onClick={() => onCancel()}>Cancel</MDButton>
      <MDButton color="info" onClick={() => uploadSessionsDeidentified()}>Upload</MDButton>
    </DialogActions>
  </>
}