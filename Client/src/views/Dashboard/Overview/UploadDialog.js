/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, memo } from "react";

import {
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";

import { v4 as uuidv4 } from 'uuid';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function UploadDialog({show, deidentified, onCancel}) {
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

      const batchSessionId = uuidv4() + new Date().toISOString();

      const myDropzone = dropzoneRef.current.dropzone;
      myDropzone.on("processing", function() {
        this.options.autoProcessQueue = true;
      });
      myDropzone.on("sendingmultiple", function(file, xhr, formData) {
        formData.append("deviceId", response.data.deviceID);
        formData.append("patientId", response.data.newPatient.ID);
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

    }).catch((error) => {
      console.log(error);
    });
  }

  const uploadSessions = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.on("processing", function() {
      this.options.autoProcessQueue = false;
    });

    const batchSessionId = uuidv4() + new Date().toISOString();

    if (batchUpload) {
      myDropzone.on("sending", function(file, xhr, formData) { 
        formData.append("decryptionKey", decryptionKey);
        formData.append("batchSessionId", batchSessionId);  
      });
    } else {
      myDropzone.on("sending", function(file, xhr, formData) { 
        formData.append("batchSessionId", batchSessionId);  
      });
    }

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
            maxFiles: batchUpload ? 2000 : 50
          }} ref={dropzoneRef}>
          </DropzoneUploader>
        </MDBox>
      </DialogContent>
    ) : (
      <DialogContent>
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
            maxFiles: 2000
          }} ref={dropzoneRef}>
          </DropzoneUploader>
        </MDBox>
      </DialogContent>
    )}
    <DialogActions>
      <MDButton color="secondary" onClick={() => cancelUpload()}>Cancel</MDButton>
      <MDButton color="info" onClick={() => (deidentified && !batchUpload) ? uploadSessionsDeidentified() : uploadSessions()}>Upload</MDButton>
    </DialogActions>
  </Dialog>
  </>
}

export default memo(UploadDialog);