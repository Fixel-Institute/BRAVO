import { createRef, useState } from "react";

import {
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

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function UploadDialog({deidentified, onUpdate, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [deidentifiedInfo, setDeidentifiedInfo] = useState({patientId: "", studyId: "", diagnosis: "", deviceName: ""});
  const [decryptionKey, setDecryptionKey] = useState("");
  const [batchUpload, setBatchUpload] = useState(false);
  
  const uploadSessionsDeidentified = () => {
    SessionController.query("/api/updatePatientInformation", {
      createNewPatientInfo: true,
      PatientID: deidentifiedInfo.patientId,
      StudyID: deidentifiedInfo.studyId,
      Diagnosis: deidentifiedInfo.diagnosis,
      DeviceName: deidentifiedInfo.deviceName
    }).then((response) => {
      const newPatient = response.data;

      const myDropzone = dropzoneRef.current.dropzone;
      myDropzone.on("processing", function() {
        this.options.autoProcessQueue = true;
      });
      myDropzone.on("sending", function(file, xhr, formData) { 
        formData.append("deviceId", response.data.deviceID);  
      });
      myDropzone.on("success", function(file, response) {
        this.removeFile(file);
      });
      myDropzone.on("complete", function(file, response) {
        if (myDropzone.getUploadingFiles().length === 0 && myDropzone.getQueuedFiles().length === 0) {
          onUpdate(newPatient);
          onCancel();
        }
      });
      myDropzone.processQueue();

    }).catch((error) => {
      console.log(error);
    });
  }

  const uploadSessions = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.on("processing", function() {
      this.options.autoProcessQueue = true;
    });

    if (batchUpload) {
      myDropzone.on("sending", function(file, xhr, formData) { 
        formData.append("decryptionKey", decryptionKey);  
      });
    }
    myDropzone.on("success", function(file, response) {
      this.removeFile(file);
    });
    myDropzone.on("complete", function(file, response) {
      if (myDropzone.getUploadingFiles().length === 0 && myDropzone.getQueuedFiles().length === 0) {
        onUpdate({Refresh: true});
        onCancel();
      }
    });
    myDropzone.processQueue();
  }

  const dropzoneRef = createRef();

  return <>
    <MDBox px={2} pt={2}>
      <MDTypography variant="h5">
        {deidentified ? dictionary.SessionUpload.ResearchTitle[language] : dictionary.SessionUpload.ClinicTitle[language]} 
      </MDTypography>
    </MDBox>
    {deidentified ? (
      <DialogContent>
        {!batchUpload ? (<>
          <MDTypography variant="p">
            To upload data in Research-account (Deidentified), a deidentified patient ID must be created, or use {" "}
          </MDTypography>
          <MDButton style={{padding: 0}} onClick={() => setBatchUpload(true)}> {"Batch Upload with Patient Lookup Table"} </MDButton>
        </>
        ) : (<>
          <MDTypography variant="p">
            Upload Multiple Files with identifier that will automatically deidentified by Lookup Table, or use {" "}
          </MDTypography>
          <MDButton style={{padding: 0}} onClick={() => setBatchUpload(false)}> {"Manual Patient Data Upload"} </MDButton>
        </>
        )}

        {batchUpload ? (
          <TextField
            variant="standard"
            margin="dense" id="name"
            value={decryptionKey}
            onChange={(event) => setDecryptionKey(event.target.value)}
            label={"Decryption Key for Lookup Table"} type="password"
            fullWidth
          />
        ) : (
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                variant="standard"
                margin="dense" id="name"
                value={deidentifiedInfo.patientId}
                onChange={(event) => setDeidentifiedInfo({...deidentifiedInfo, patientId: event.target.value})}
                label={dictionary.SessionUpload.PatientIdentifier[language]} type="text"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                variant="standard"
                margin="dense" id="name"
                value={deidentifiedInfo.studyId}
                onChange={(event) => setDeidentifiedInfo({...deidentifiedInfo, studyId: event.target.value})}
                label={dictionary.SessionUpload.StudyIdentifier[language]} type="text"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                variant="standard"
                margin="dense" id="name"
                value={deidentifiedInfo.diagnosis}
                onChange={(event) => setDeidentifiedInfo({...deidentifiedInfo, diagnosis: event.target.value})}
                label={dictionary.SessionUpload.Diagnosis[language]} type="text"
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                variant="standard"
                margin="dense" id="name"
                value={deidentifiedInfo.deviceName}
                onChange={(event) => setDeidentifiedInfo({...deidentifiedInfo, deviceName: event.target.value})}
                label={dictionary.SessionUpload.DeviceName[language]} type="text"
                fullWidth
              />
            </Grid>
          </Grid>
        )}
        <MDBox pt={2}>
          <MDDropzone options={{
            url: SessionController.getServer() + "/api/uploadSessionFiles",
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
    ) : (
      <DialogContent>
        <MDBox pt={2}>
          <MDDropzone options={{
            url: SessionController.getServer() + "/api/uploadSessionFiles",
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
    )}
    <DialogActions>
      <MDButton color="secondary" onClick={() => onCancel()}>Cancel</MDButton>
      <MDButton color="info" onClick={() => (deidentified && !batchUpload) ? uploadSessionsDeidentified() : uploadSessions()}>Upload</MDButton>
    </DialogActions>
  </>
}