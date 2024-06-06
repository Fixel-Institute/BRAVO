/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, useEffect, memo } from "react";

import {
  Autocomplete,
  Grid,
  Dialog,
  DialogContent,
  TextField,
  Chip,
} from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function EditRecordingLabels({show, currentLabels, onUpdate, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, participant_uid } = controller;

  const [recordingLabels, setRecordingLabels] = useState([]);

  useEffect(() => {
    setRecordingLabels([...currentLabels.labels]);
  }, [currentLabels])

  return (
    <Dialog open={show} onClose={() => {
      onCancel();
    }}>
      
      <MDBox px={2} pt={2}>
        <MDTypography variant="h5">
          Edit Recording Labels
        </MDTypography>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
          <Autocomplete
            multiple freeSolo
            id="labels" options={[]}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip variant="outlined" label={option} {...getTagProps({ index })} />
              ))
            }
            value={recordingLabels} onChange={(event, newValue) => setRecordingLabels(newValue)}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Type to Create Labels for Recording"
                placeholder="Add Labels"
              />
            )}
          />
          </Grid>
          <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
            <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
              <MDButton color={"secondary"} style={{marginLeft: 10}} 
                onClick={onCancel}
              >
                Cancel
              </MDButton>
              <MDButton color={"info"} 
                onClick={() => onUpdate(recordingLabels)} style={{marginLeft: 10}}
              >
                Update
              </MDButton>
            </MDBox>
          </Grid>
        </Grid>
      </DialogContent>
    </Dialog>
  )
}

export default memo(EditRecordingLabels);