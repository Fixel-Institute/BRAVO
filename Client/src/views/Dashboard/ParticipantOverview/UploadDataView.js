/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, memo, useMemo, useEffect } from "react";

import {
  Autocomplete,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Icon,
  IconButton,
  Tooltip,
} from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";

import DefaultUploader from "../UploadDataView/DefaultUploader";
import MedtronicJSONUploader from "../UploadDataView/MedtronicJSONUploader";
import AlphaOmegaMPXUploader from "../UploadDataView/AlphaOmegaMPXUploader";
import HPFCSVUploader from "../UploadDataView/HPFCSVUploader";
import UFMDATUploader from "../UploadDataView/UFMDATUploader";
import UFMDATv2Uploader from "../UploadDataView/UFMDATv2Uploader";
import UFMDATv3Uploader from "../UploadDataView/UFMDATv3Uploader";
import BRAVORecordingBinaryStructureUploader from "../UploadDataView/BRAVORecordingBinaryStructureUploader";
import NeuroimageUploader from "../UploadDataView/NeuroimageUploader";
import EventCSVUploader from "../UploadDataView/EventCSVUploader";
import MATFileUploader from "../UploadDataView/MATFileUploader";

import { FaCopy } from "react-icons/fa";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function UploadDataView({show, participant_uid, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { user } = controller;

  const [uploadDataType, setUploadDataType] = useState("");

  useEffect(() => {
    
  }, [])

  return useMemo(() => (
    <Dialog open={show} PaperProps={{sx: {minWidth: 600}}}>
      <MDBox px={2} pt={2} display={"flex"} flexDirection={"row"} justifyContent={"center"} alignItems={"center"}>
        <MDTypography variant="h5">
          {"Upload Participant Data"}
        </MDTypography>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
            <Autocomplete selectOnFocus clearOnBlur fullWidth
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="standard"
                  placeholder={"Select Data Type"}
                />
              )}
              isOptionEqualToValue={(option, value) => {
                return option === value;
              }}
              renderOption={(props, option) => <li {...props}>{option}</li>}
              value={uploadDataType}
              options={["Default", "Medtronic JSON Files", "AlphaOmega MPX Files", "BRAVO Recording Structure (Binary)", 
                "BRAVO Offline Synchronized Recordings (v2)", "BRAVO Offline Synchronized Recordings (v3)", "HDF CSV Format", "Event Annotation CSV", "UF MDAT Files", ".MAT Data File", "3D Images"]}
              onChange={(event, newValue) => setUploadDataType(newValue == "Default" ? "" : newValue)}
            />
          </Grid>
          <Grid item xs={12}>
            {uploadDataType === "" ? (
              <DefaultUploader institute={user.Institute} participant={participant_uid}/>
            ) : null}
            {uploadDataType === "Medtronic JSON Files" ? (
              <MedtronicJSONUploader institute={user.Institute} participant={participant_uid}/>
            ) : null}
            {uploadDataType === "AlphaOmega MPX Files" ? (
              <AlphaOmegaMPXUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "BRAVO Offline Synchronized Recordings (v2)" ? (
              <UFMDATv2Uploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "BRAVO Offline Synchronized Recordings (v3)" ? (
              <UFMDATv3Uploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "BRAVO Recording Structure (Binary)" ? (
              <BRAVORecordingBinaryStructureUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "HDF CSV Format" ? (
              <HPFCSVUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "Event Annotation CSV" ? (
              <EventCSVUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "UF MDAT Files" ? (
              <UFMDATUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === ".MAT Data File" ? (
              <MATFileUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
            {uploadDataType === "3D Images" ? (
              <NeuroimageUploader institute={user.Institute}  participant={participant_uid}/>
            ) : null}
          </Grid>
          <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
            <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
              <MDButton color={"secondary"} style={{marginLeft: 10}} 
                onClick={onCancel}
              >
                Close
              </MDButton>
            </MDBox>
          </Grid>
        </Grid>
      </DialogContent>
    </Dialog>
  ), [uploadDataType, show])
}

export default UploadDataView;