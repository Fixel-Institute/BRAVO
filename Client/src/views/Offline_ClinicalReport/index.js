/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Autocomplete,
  Box,
  Backdrop,
  IconButton,
  Dialog,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  Grid,
  Tabs,
  Tab,
  Table,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
} from "@mui/material"

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";

import { FilePond } from 'react-filepond';
import 'filepond/dist/filepond.min.css'

import FullPageLayout from "layouts/FullPageLayout";

import SessionOverview from "./SessionOverview.js";
import TherapyChangeHistory from "./TherapyChangeHistory.js";
import ChronicTimeline from "./ChronicTimeline.js";
import TherapyTable from "./TherapyTable.js";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function OfflineClinicalReport() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { language, report } = controller;

  const [files, setFiles] = React.useState([]);
  const [alert, setAlert] = React.useState(null);

  const [JSONData, setJSONData] = React.useState(null);
  const [sessionInfo, setSessionInfo] = React.useState(null);
  const [timeline, setTimeline] = React.useState(null);

  const handleFileUpload = (fieldName, file, file_metadata, load, error, progress, abort, transfer, options) => {
    const reader = new FileReader();

    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        setJSONData(parsed);
        progress(true, 1, 1);
        load('ok');
      } catch (e) {
        console.error('Invalid JSON', e);
        error('Invalid JSON file');
      }
    };

    reader.onerror = () => {
      console.error('File read error');
      error('File read error');
    };

    // optional: forward read progress to FilePond
    reader.onprogress = (evt) => {
      if (evt.lengthComputable) {
        progress(true, evt.loaded, evt.total);
      }
    };

    reader.readAsText(file); // `file` is the File/Blob from FilePond

    return {
      abort: () => {
        try { reader.abort(); } catch(e) {}
        abort(); // notify FilePond the process was aborted
      }
    };
  };

  return (
    <FullPageLayout>
      {alert}
      <MDBox py={2}>
        <Card>
          <MDBox p={2}>
            <MDTypography variant="h4">
              {"Offline Clinical Report"}
            </MDTypography>
            <MDTypography variant="body" fontSize={15}>
              {"Completely offline clinical report generation from a JSON file export. Feel free to disconnect internet to confirm no data is uploaded."}
              {" Dropzone is used to handle file uploads hence the way it is displayed."}
            </MDTypography>
          </MDBox>
          <MDBox p={2}>
            <FilePond
              name="File" files={files} allowRevert={false}
              acceptedFileTypes={[".json"]}
              onupdatefiles={setFiles}
              maxFiles={1}
              maxParallelUploads={1}
              server={{
                url: "http://localhost",
                process: handleFileUpload
              }}
              labelFileProcessingError={(error) => {
                return error.body
              }}
              labelIdle='Drag & Drop your files or <span class="filepond--label-action">Browse</span>'
            />
          </MDBox>
        </Card>
      </MDBox>
      <Grid container spacing={3}>
        {JSONData && (
          <Grid item xs={12} md={6}>
            <SessionOverview JSONData={JSONData} onUpdateSession={setSessionInfo} />
          </Grid>
        )}
        {JSONData && sessionInfo && (
          <Grid item xs={12} md={6}>
            <TherapyChangeHistory JSONData={JSONData} sessionDate={sessionInfo.SessionDate*1000} onUpdateTimeline={setTimeline} />
          </Grid>
        )}
        {JSONData && timeline && (
          <Grid item xs={12}>
            <ChronicTimeline JSONData={JSONData} therapyModifications={timeline[0].History} />
          </Grid>
        )}
      </Grid>
      <MDBox pt={2}>
        
      </MDBox>
    </FullPageLayout>
  );
}

export default OfflineClinicalReport;
