/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useRef, useState, useEffect, memo } from "react";

import {
  Autocomplete,
  Button,
  Checkbox,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Divider,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

import { FilePond } from 'react-filepond';
import 'filepond/dist/filepond.min.css'

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import { SessionController } from "database/session-control";

const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

function NeuroPacePersystDatUploader({institute, participant}) {
  const [metadata, setMetadata] = useState({loaded: false});
  const [files, setFiles] = useState([]);
  const pond = useRef(null);

  useEffect(() => {
    setFiles([]);
    setMetadata({loaded: false});
  }, [participant]);

  useEffect(() => {
    if (!pond.current) return;

    let existingUpload = files.map((a) => a.filename);
    let layoutToRemove = [];
    for (let i in files) {
      if (files[i].filename.endsWith(".dat")) {
        if (existingUpload.includes(files[i].filename.replace(".dat", ".lay"))) {
          //pond.current.process(files[i].filename)
          
          const layoutFile = files.filter((a) => a.filename == files[i].filename.replace(".dat", ".lay"))[0];
          const reader = new FileReader();
          reader.onload = (evt) => {
            const content = evt.target.result;
            const lines = content.split("\r\n");
            
            let metadata = {Raw: content, PatientInformation: {}};
            let sectionHeader = "";
            for (let i = 0; i < lines.length; i++) {
              if (lines[i].startsWith("[")) sectionHeader = "";

              if (lines[i].startsWith("[N_Config_String]")) {
                sectionHeader = "ConfigCSV";
                const parameters = lines[i+1].split(",");
                metadata["ParameterArray"] = parameters;

              } else if (lines[i].startsWith("[N_Patient]")) {
                sectionHeader = "PatientInformation";
                metadata["PatientInformation"] = {};
                
              } else if (lines[i].startsWith("[N_Comments]")) {
                sectionHeader = "Comments";
                metadata["Comments"] = {};
                
              } else if (lines[i].startsWith("[N_Configuration]")) {
                sectionHeader = "Configurations";
                metadata["Configurations"] = {};
                
              } else if (lines[i].startsWith("[ChannelMap]")) {
                sectionHeader = "ChannelMap";
                metadata["ChannelNames"] = {};
                
              } else {
                if (sectionHeader == "PatientInformation") {
                  if (lines[i].startsWith("GMT / UTC=")) {
                    const sublines = lines[i].split(":");
                    metadata["PatientInformation"]["SessionDate"] = parseInt(sublines[sublines.length-1]);
                  } else if (lines[i].startsWith("PatientIdentifier=")) {
                    metadata["PatientInformation"]["Identifier"] = lines[i].replace("PatientIdentifier=","");
                  } else if (lines[i].startsWith("PatientInitials=")) {
                    metadata["PatientInformation"]["Initials"] = lines[i].replace("PatientInitials=","");
                  } else if (lines[i].startsWith("PatientGender=")) {
                    metadata["PatientInformation"]["Gender"] = lines[i].replace("PatientGender=","");
                  } else if (lines[i].startsWith("PatientIdentifierTimeStamp=")) {
                    metadata["PatientInformation"]["Timestamp"] = parseFloat(lines[i].replace("PatientIdentifierTimeStamp=",""));
                    if (!metadata["PatientInformation"]["Timestamp"]) {
                      metadata["PatientInformation"]["Timestamp"] = 0;
                    }
                  } else if (lines[i].startsWith("ProgrammingParameterFile=")) {
                    metadata["PatientInformation"]["ProgrammingParameterFile"] = lines[i].replace("ProgrammingParameterFile=","");
                  } else if (lines[i].startsWith("NPFileType=")) {
                    metadata["PatientInformation"]["NPFileType"] = lines[i].replace("NPFileType=","");
                  } else if (lines[i].startsWith("DeviceType=")) {
                    metadata["PatientInformation"]["DeviceType"] = lines[i].replace("DeviceType=","");
                  } else if (lines[i].startsWith("DeviceIdentifier=")) {
                    metadata["PatientInformation"]["DeviceIdentifier"] = lines[i].replace("DeviceIdentifier=","");
                  }
                } else if (sectionHeader == "Comments") {
                  if (lines[i].startsWith("TriggerReason=")) {
                    metadata["Comments"]["TriggerReason"] = lines[i].replace("TriggerReason=","");
                  } else if (lines[i].startsWith("Comments=")) {
                    metadata["Comments"]["Comments"] = lines[i].replace("Comments=","");
                  } 
                } else if (sectionHeader == "Configurations") {
                  const sublines = lines[i].split("=");
                  if (sublines.length > 1) {
                    metadata["Configurations"][sublines[0]] = lines[i].replace(sublines[0]+"=","");
                  }
                } else if (sectionHeader == "ChannelMap") {
                  const sublines = lines[i].split("=");
                  if (sublines.length > 1) {
                    metadata["ChannelNames"][sublines[0]] = lines[i].replace(sublines[0]+"=","");
                  }
                }
              }

            }

            pond.current.removeFile(layoutFile);
            files[i].setMetadata("layout", metadata);
            pond.current.processFile(files[i]);
          }
          reader.onerror = error => console.log(error);
          reader.readAsText(layoutFile.file);
        }
      }
    }
  }, [files, pond.current])

  const handleFileUpload = (fieldName, file, file_metadata, load, error, progress, abort, transfer, options) => {
    const formData = new FormData();
    formData.append(fieldName, file, file.name);
    formData.append("DataType", "NeuroPacePersystDAT");  
    formData.append("ParticipantId", participant);  
    formData.append("Institute", institute);
    formData.append("Metadata", JSON.stringify(file_metadata));

    const request = new XMLHttpRequest();
    request.open('POST', "/api/uploadData");
    request.setRequestHeader("X-CSRFToken", document.querySelector('[name=csrfmiddlewaretoken]').value);

    // Should call the progress method to update the progress to 100% before calling load
    // Setting computable to false switches the loading indicator to infinite mode
    request.upload.onprogress = (e) => {
        progress(e.lengthComputable, e.loaded, e.total);
    };

    // Should call the load method when done and pass the returned server file id
    // this server file id is then used later on when reverting or restoring a file
    // so your server knows which file to return without exposing that info to the client
    request.onload = function () {
        if (request.status >= 200 && request.status < 300) {
            // the load method accepts either a string (id) or an object
            load(request.responseText);
        } else {
            // Can call the error method if something is wrong, should exit after
            if (request.status == 301) {
              error("Duplicate File Received");
            } else if (request.status == 400) {
              try {
                const data = JSON.parse(request.response);
                error(data.message);
              } catch (error) {
                error("Exception 400 Received");
              }
            } else if (request.status == 403) {
              error("Permission Denied");
            } else {
              error("Unknown Error Code: " + request.status.toFixed(0));
            }
        }
    };

    request.send(formData);

    // Should expose an abort method so the request can be cancelled
    return {
        abort: () => {
            // This function is entered if the user has tapped the cancel button
            request.abort();

            // Let FilePond know the request has been cancelled
            abort();
        },
    };
  }

  return (
    <MDBox pt={2}>
    <Divider variant="insert" />
      <MDTypography variant="h6">
        {"Metadata"}
      </MDTypography>
      <MDBox pt={2} px={3}>
        <MDTypography variant="h6">
          {"Please upload .lay file along with .dat file. When both file, with the same name, are present in database, DataProcessing will start."}
        </MDTypography>
        <MDBox pt={2} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
          <Button
            component="label"
            variant="contained"
            tabIndex={-1}
            startIcon={<CloudUploadIcon color={"white"} />}
            style={{display: "none"}}
          >
            <MDTypography variant="p" color={"white"}>
              {"Upload Layout File"}
            </MDTypography>
            <VisuallyHiddenInput type="file" onChange={(event) => {
            }} />
          </Button>
        </MDBox>
      </MDBox>
      <Divider variant="insert" />
      <MDBox pt={2} style={{display: "flex", flexDirection: "row", justifyContent: "space-between"}}>
        <MDTypography variant="h6">
          {"Data Uploader"}
        </MDTypography>
        <MDButton color="info" onClick={() => setFiles([])} style={{marginLeft: "auto"}}>{"Clear Upload Queue"}</MDButton>
      </MDBox>
      
      <MDBox pt={2}>
        <FilePond
          ref={(ref) => (pond.current = ref)}
          name="File"
          files={files} allowMultiple allowRevert={false}
          acceptedFileTypes={[".lay", ".dat"]}
          onupdatefiles={setFiles}
          maxFiles={1000}
          maxParallelUploads={10}
          server={{
            url: SessionController.getServer(),
            instantUpload: false,
            process: handleFileUpload
          }}
          labelFileProcessingError={(error) => {
            return error.body
          }}
          labelIdle='Drag & Drop your files or <span class="filepond--label-action">Browse</span>'
        />
      </MDBox>
    </MDBox>
  )
};

export default memo(NeuroPacePersystDatUploader);