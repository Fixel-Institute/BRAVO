/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import Papa from "papaparse";

import {
  Card,
  Checkbox,
  Grid,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  TextField,
  Stack,
  Slider,
  RadioGroup,
  Radio
} from "@mui/material";

import { 
  Remove as RemoveIcon,
  Add as AddIcon
} from "@mui/icons-material";

import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import SurveyTable from "components/Tables/SurveyTable";
import LoadingProgress from "components/LoadingProgress";

import SurveyLayout from "layouts/SurveyLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function LocalUpdaterView({match}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    window.electronAPI.onDockerUpdated((message) => {
      setAlert(null);
    });
  }, []);

  return (
    <SurveyLayout viewOnly>
      <MDBox>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card sx={{marginTop: 0}}>
              <MDBox p={2}>
                <Grid container spacing={2}>
                  <Grid item xs={12} >
                    <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItem: "center"}}>
                      <MDTypography variant="h3">
                        {"Local Updater"}
                      </MDTypography>
                    </MDBox>
                    <MDBox p={2} style={{display: "flex", justifyContent: "space-betwen"}}>
                      <MDButton variant={"contained"} color={"info"} size={"large"} style={{marginRight: 30}} onClick={() => {
                        setAlert(<LoadingProgress />);
                        window.electronAPI.updateDocker();
                      }} >
                        <MDTypography variant="h6" color={"white"}>
                          {"Update"}
                        </MDTypography>
                      </MDButton>
                      <MDButton variant={"contained"} color={"info"} size={"large"} onClick={() => {
                        var URL = "https://localhost";
                        var win = window.open(URL, "_blank");
                      }} >
                        <MDTypography variant="h6" color={"white"}>
                          {"Launch"}
                        </MDTypography>
                      </MDButton>
                    </MDBox>
                  </Grid>
                </Grid>
              </MDBox>
            </Card>
          </Grid>
          <Grid item xs={12}>
          </Grid>
        </Grid>
      </MDBox>
      {alert}
    </SurveyLayout>
  )
};

