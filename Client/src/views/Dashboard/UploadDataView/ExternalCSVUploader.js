/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
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

import { FilePond } from 'react-filepond';
import 'filepond/dist/filepond.min.css'

import { v4 as uuidv4 } from 'uuid';

import moment from "moment";
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { TimePicker } from "@mui/x-date-pickers";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import { SessionController } from "database/session-control";

function ExternalCSVUploader({institute, participant}) {
  const [files, setFiles] = useState([]);
  const [metadata, setMetadata] = useState({});

  useEffect(() => {
    setFiles([]);
  }, [participant]);

  const handleFileUpload = (fieldName, file, upload_metadata, load, error, progress, abort, transfer, options) => {
    let date = 0;
    if (metadata.date && metadata.time) {
      date = new Date(metadata.date.toISOString().split("T")[0] + "T" + metadata.time.toISOString().split("T")[1]).getTime();
      date -= (metadata.date.utcOffset() - metadata.time.utcOffset()) * 60000;
    }

    const formData = new FormData();
    formData.append(fieldName, file, file.name);
    formData.append("DataType", "ExternalCSV");  
    formData.append("ParticipantId", participant);  
    formData.append("Institute", institute);
    formData.append("Metadata", JSON.stringify({
      StartTime: date
    }));

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
      <MDTypography variant="h5" fontSize={15} lineHeight={1}>
        {"Accept CSV Files. The CSV format must follow a specific convention for the parser to understand what you uploaded."}
        {"The CSV must contain a column header named 'Time', with unit in seconds (decimals for milliseconds precisions)."}
        {"If the first index of Time is not 0, it will use the Metadata Recording Time as the starting time, otherwise it will interpret Time column as Unix Timestamp."}
        {"Other column names will be interpreted as the Recording Channel Names."}
      </MDTypography>

      <Divider variant="insert" />
      <MDTypography variant="h6">
        {"Metadata"}
      </MDTypography>
      <MDBox pt={2}>
        <MDTypography variant="h5" fontSize={15} style={{marginBottom: 15}}>
          {"Recording Time: "}
        </MDTypography>
        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
          <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
            <DatePicker
              style={{marginRight: 3}}
              label="Date"
              value={metadata.date}
              onChange={(newDate) => {
                setMetadata({...metadata, date: newDate});
              }}
              renderInput={(params) => <TextField {...params} />}
            />
          </LocalizationProvider>
          <LocalizationProvider dateAdapter={AdapterMoment}>
            <TimePicker
              label="Time"
              value={metadata.time}
              onChange={(newDate) => {
                setMetadata({...metadata, time: newDate});
              }}
              renderInput={(params) => <TextField {...params} />}
            />
          </LocalizationProvider>
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
          name="File" 
          files={files} allowMultiple allowRevert={false}
          acceptedFileTypes={[".csv"]}
          onupdatefiles={setFiles}
          maxFiles={1000}
          server={{
            url: SessionController.getServer(),
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

export default memo(ExternalCSVUploader);