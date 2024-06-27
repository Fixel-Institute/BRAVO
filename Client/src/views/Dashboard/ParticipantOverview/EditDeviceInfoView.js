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
  Autocomplete,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
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

function EditDeviceInfoView({show, deviceInfo, onUpdate, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, participant_uid } = controller;

  const [editDeviceInfo, setEditDeviceInfo] = useState({...deviceInfo});
  
  if (!deviceInfo) return;

  return (
    <Dialog open={show} onClose={() => {
      onCancel();
      setEditDeviceInfo({...deviceInfo});
    }}>
      <MDBox px={2} pt={2}>
        <MDTypography variant="h5">
          Edit Device Information
        </MDTypography>
        <MDTypography variant="h5">
          {editDeviceInfo.uid}
        </MDTypography>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              id="device-name"
              variant="standard"
              margin="dense"
              label="Device Name"
              placeholder="Device Name"
              value={editDeviceInfo.name}
              onChange={(event) => setEditDeviceInfo({...editDeviceInfo, name: event.target.value})}
              fullWidth
            />
          </Grid>
          {editDeviceInfo.leads.map((lead, index) => (
            <Grid key={lead.name} item xs={6}>
              <TextField
                id="lead-name"
                variant="standard"
                margin="dense"
                label={`Lead #${index+1}`}
                placeholder={lead.name}
                value={lead.custom_name}
                onChange={(event) => setEditDeviceInfo({...editDeviceInfo, leads: editDeviceInfo.leads.map((oldLead, oldIndex) => {
                  if (index == oldIndex) return {...oldLead, custom_name: event.target.value};
                  return oldLead;
                })})}
                fullWidth
              />
            </Grid>
          ))}
        </Grid>
      </DialogContent>
      <DialogActions>
        <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
          <MDButton color={"secondary"} 
            onClick={onCancel}
          >
            Cancel
          </MDButton>
          <MDButton color={"info"} 
            onClick={() => onUpdate(editDeviceInfo)} style={{marginLeft: 10}}
          >
            Update
          </MDButton>
        </MDBox>
      </DialogActions>
    </Dialog>
  )
}

export default memo(EditDeviceInfoView);