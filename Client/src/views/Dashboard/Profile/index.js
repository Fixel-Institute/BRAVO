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
import { Link, useNavigate } from "react-router-dom";

import {
  Card,
  Divider,
  Dialog,
  DialogContent,
  DialogActions,
  Grid,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Tooltip,
  TextField,
  Icon,
  IconButton,
  Input,
} from "@mui/material";

import Papa from "papaparse";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";
import { AccessAlarm } from "@mui/icons-material";
import DeidentificationTable from "components/Tables/DeidentificationTable";
import LoadingProgress from "components/LoadingProgress";

export default function Profile() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { user, language, patientID } = controller;

  const [deidentificationTable, setDeidentificationTable] = useState([]);
  const [profile, setProfile] = useState(false);
  const [tableDialog, setTableDialog] = useState({passcode: "", show: false});
  const inputFile = useRef(null) 

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    setAlert(<LoadingProgress />);
    SessionController.query("/api/queryProfile").then((response) => {
      setProfile(response.data);
      setAlert();
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  return (
    <DatabaseLayout>
      <MDBox py={3}>
        {alert}
        {profile ? (
          <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={12}>
                <MDTypography variant="h3">
                  {"Profile"}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={12} style={{display: "flex", flexDirection: "row"}}>
                <TextField
                  variant="standard"
                  value={profile.key ? profile.key : "NOT AVAILABLE"}
                  label={"Rest API Secure Key (Individually Linked. DO NOT SHARE)"} type="text"
                  fullWidth disabled
                />
                <MDButton color={"info"} onClick={() => {
                  SessionController.query("/api/requestSecureKey").then((response) => {
                    setProfile({...profile, key: response.data.key})
                  }).catch((error) => {
                    SessionController.displayError(error, setAlert);
                  });
                }} style={{marginLeft: 15}}>{"Request New Key"}</MDButton>
              </Grid>
            </Grid>
          </MDBox>
          </Card>
        ) : null}
      </MDBox>
    </DatabaseLayout>
  );
};
