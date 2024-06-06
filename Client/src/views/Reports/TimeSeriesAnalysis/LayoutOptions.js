/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import {
  Backdrop,
  Dialog,
  DialogContent,
  DialogActions,
  Grid,
  Divider,
  Switch
} from "@mui/material"

import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";

import { usePlatformContext, setContextState } from "context";

function LayoutOptions({setAlert}) {
  const [controller, dispatch] = usePlatformContext();  
  const { patientID, BrainSensestreamLayout, language } = controller;
  
  const handleStateChange = (type, state) => {
    setContextState(dispatch, "BrainSensestreamLayout", {...BrainSensestreamLayout, [type]: state});
  };

  return (
    <Dialog open={true} onClose={() => setAlert(null)}>
      <MDBox px={2} pt={2}>
        <MDTypography variant="h5">
          {"Realtime Streaming Layout Toggles"} 
        </MDTypography>
      </MDBox>
      <DialogContent>
        <MDBox px={2} pt={2}>
          <Grid container spacing={0}>
            <Grid item xs={6} sx={{
              wordWrap: "break-word",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word"
            }}>
              <MDTypography fontSize={18} fontWeight={"bold"}>
                {"Neural Response from Effect of Stimulation"}
              </MDTypography>
              <Switch checked={!BrainSensestreamLayout.StimulationPSDs} onChange={(event, checked) => handleStateChange("StimulationPSDs", !checked)} />
              <Divider variant="middle" />
            </Grid>
            <Grid item xs={6} sx={{
              wordWrap: "break-word",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word"
            }}>
              <MDTypography fontSize={18} fontWeight={"bold"}>
                {"Event-Onset Spectrogram"}
              </MDTypography>
              <Switch checked={!BrainSensestreamLayout.EventOnsetSpectrogram} onChange={(event, checked) => handleStateChange("EventOnsetSpectrogram", !checked)} />
              <Divider variant="middle" />
            </Grid>
            <Grid item xs={6} sx={{
              wordWrap: "break-word",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word"
            }}>
              <MDTypography fontSize={18} fontWeight={"bold"}>
                {"Event-State PSD"}
              </MDTypography>
              <Switch checked={!BrainSensestreamLayout.EventStatePSD} onChange={(event, checked) => handleStateChange("EventStatePSD", !checked)} />
              <Divider variant="middle" />
            </Grid>
          </Grid>
        </MDBox>
      </DialogContent>
      <DialogActions>
        <MDButton color="secondary" onClick={() => setAlert(null)}>{"Close"}</MDButton>
      </DialogActions>
    </Dialog>
  )
};

export default LayoutOptions;