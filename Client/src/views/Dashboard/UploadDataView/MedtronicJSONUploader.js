/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, useEffect, memo } from "react";

import {
  Autocomplete,
  Checkbox,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Divider,
} from "@mui/material";

import { v4 as uuidv4 } from 'uuid';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";
import { SessionController } from "database/session-control";

function MedtronicJSONUploader({study, participant, experiment}) {
  const [metadata, setMetadata] = useState({device_location: "", infer_from_device: true});

  useEffect(() => {
    
  }, [participant]);

  const uploadSessions = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    if (myDropzone.files.length == 0) {
      return;
    }
    
    myDropzone.on("sending", function(file, xhr, formData) { 
      formData.append("data_type", "MedtronicJSON");  
      formData.append("participant", participant);  
      formData.append("study", study);
      formData.append("experiment", experiment);
      formData.append("metadata", JSON.stringify(metadata));
    });

    myDropzone.on("processing", function() {
      this.options.autoProcessQueue = false;
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
        
      }
    });
    myDropzone.processQueue();
  }

  const cancelUpload = () => {
    const myDropzone = dropzoneRef.current.dropzone;
    myDropzone.removeAllFiles();
  };

  const dropzoneRef = createRef();

  return (
    <MDBox pt={2}>
      <Divider variant="insert" />
      {participant === "batch-upload" ? null : <>
        <MDTypography variant="h6">
          {"Metadata"}
        </MDTypography>
        <MDBox pt={2} px={3}>
          <Autocomplete selectOnFocus clearOnBlur
            renderInput={(params) => (
              <TextField
                {...params}
                variant="standard"
                placeholder={"Device Location"}
              />
            )}
            isOptionEqualToValue={(option, value) => {
              return option === value;
            }}
            renderOption={(props, option) => <li {...props}>{option}</li>}
            value={metadata.device_location}
            options={["Right IPG", "Left IPG"]}
            onChange={(event, newValue) => {
              if (typeof newValue === 'string') {
                setMetadata({...metadata, device_location: newValue});
              } else if (newValue && newValue.inputValue) {
                setMetadata({...metadata, device_location: newValue.inputValue});
              }
            }}
          />
          <MDBox pt={2} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
            <Checkbox checked={metadata.infer_from_device} onClick={() => setMetadata({...metadata, infer_from_device: !metadata.infer_from_device})} />
            <MDTypography variant="h6">
              {"Infer Metadata from JSON Contents"}
            </MDTypography>
          </MDBox>
        </MDBox>
        <Divider variant="insert" />
      </>}
      <MDTypography variant="h6">
        {"Data Uploader"}
      </MDTypography>
      <DropzoneUploader options={{
        url: SessionController.getServer() + "/api/uploadData",
        paramName: "file",
        addRemoveLinks: true,
        acceptedFiles: ".json",
        autoDiscover: false,
        autoProcessQueue: false,
        uploadMultiple: true,
        parallelUploads: 50,
        maxFiles: 50
      }} ref={dropzoneRef}>
      </DropzoneUploader>
      <MDBox pt={2} style={{display: "flex", flexDirection: "row"}}>
        <MDButton color="info" onClick={() => uploadSessions()} style={{marginLeft: "auto"}}>{"Upload"}</MDButton>
      </MDBox>
    </MDBox>
  )
};

export default memo(MedtronicJSONUploader);