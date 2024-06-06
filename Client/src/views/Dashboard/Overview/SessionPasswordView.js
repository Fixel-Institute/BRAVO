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

function SessionPasswordView({show, onUpdate, onCancel}) {
  const [password, setPassword] = useState("");

  return (
    <Dialog open={show} onClose={() => {
      setPassword("");
      onCancel();
    }}>
      <MDBox px={2} pt={2} sx={{minWidth: 500}}>
        <MDTypography variant="h5">
          {"Set Client-side Decryption Password"}
        </MDTypography>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              variant="standard"
              margin="dense"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              fullWidth
            />
          </Grid>
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
            onClick={() => {
              onUpdate(password);
            }} style={{marginLeft: 10}}
          >
            Enable Decryption
          </MDButton>
        </MDBox>
      </DialogActions>
    </Dialog>
  )
}

export default memo(SessionPasswordView);