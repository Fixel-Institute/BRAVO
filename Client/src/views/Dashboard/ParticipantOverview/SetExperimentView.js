/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, memo, useEffect } from "react";

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

function SetExperimentView({show, participant, onUpdate, onCancel}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, participant_uid } = controller;

  const [alert, setAlert] = useState(null);
  const [experiments, setExperiments] = useState([]);
  
  useEffect(() => {

  }, []);

  return (
    <Dialog open={show} onClose={() => {
      onCancel();
      
    }}>
      {alert}
      <MDBox px={2} pt={2}>
        <MDTypography variant="h5">
          {"Experiment List"}
        </MDTypography>
        <MDTypography variant="h5">
          {"Test"}
        </MDTypography>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            
          </Grid>
          
        </Grid>
      </DialogContent>
      <DialogActions>
        <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
          
        </MDBox>
      </DialogActions>
    </Dialog>
  )
}

export default memo(SetExperimentView);