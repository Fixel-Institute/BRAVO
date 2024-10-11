/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Box,
  Backdrop,
  Badge,
  IconButton,
  Dialog,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  Grid,
  Table,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
} from "@mui/material"

import TabletAndroidIcon from '@mui/icons-material/TabletAndroid';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// core components
import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import MDBadge from "components/MDBadge";
import MDButton from "components/MDButton";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";
import TherapyHistoryFigure from "./TherapyHistoryFigure";
import ImpedanceHeatmap from "./ImpedanceHeatmap";
import ImpedanceHistory from "./ImpedanceHistory";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function TherapyHistoryTable({therapyHistory}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, language, report } = controller;

  React.useEffect(() => {
    
  }, [therapyHistory]);

  return (
    <MDBox>
      {Object.keys(therapyHistory).map((key) => {
        return <Accordion key={key}>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            id={key}
          >
            <MDTypography variant={"h5"} >
              {key}
            </MDTypography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {therapyHistory[key].map((config) => {
                return <Grid item xs={12} sm={6}>
                  <Card>
                    <MDBox px={2} pt={1}>
                      <MDTypography variant={"h5"} >
                        {config.GroupName}
                      </MDTypography>
                      <MDTypography variant={"subtitle1"} color={"secondary"} fontSize={15} fontWeight={"medium"} lineHeight={1}>
                        {config.StimulationType}
                      </MDTypography>
                      <MDTypography variant={"subtitle1"} color={"error"} fontSize={18} fontWeight={"medium"} lineHeight={1.5}>
                        {config.TherapyConfigurations[0].LeadName}
                      </MDTypography>
                    </MDBox>
                    <MDBox px={2} pt={1} pb={2}>
                      <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
                        <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                          {"Frequency: "}<b>{config.TherapyConfigurations[0].Frequency}</b>{" Hz"}<br/>
                        </MDTypography>
                      </MDBox>
                      <MDBox display={"flex"} flexDirection={"column"} justifyContent={"start"} pt={1}>
                        <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                          {"Pulsewidth: "}<b>{config.TherapyConfigurations[0].Pulsewidth}</b>{" "}{config.TherapyConfigurations[0].PulsewidthUnit}<br/>
                        </MDTypography>
                      </MDBox>
                      <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} justifyContent={"start"} pt={1}>
                        <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                          {"Stimulation: "}
                        </MDTypography>
                        {config.TherapyConfigurations[0].Contact.map((a, index) => {
                          return <Tooltip title={config.TherapyConfigurations[0].Amplitude[index] + " " + config.TherapyConfigurations[0].AmplitudeUnit}>
                            <MDBadge key={a} badgeContent={a} color={"error"} size={"xs"} container sx={{marginLeft: 1, cursor: "pointer"}} />
                          </Tooltip>
                        })}
                      </MDBox>
                      {config.TherapyConfigurations[0].ReturnContact.length > 0 ? (
                      <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} pt={1}>
                        <MDTypography variant={"h6"} fontSize={15} fontWeight={"regular"} lineHeight={1}>
                          {"Return: "}
                        </MDTypography>
                        {config.TherapyConfigurations[0].ReturnContact.map((a) => {
                          return <MDBadge key={a} badgeContent={a} color={"info"} size={"xs"} container sx={{marginLeft: 1}} />
                        })}
                      </MDBox>
                      ) : null}
                    </MDBox>
                  </Card>
                </Grid>
              })}
            </Grid>
          </AccordionDetails>
        </Accordion>
      })}
    </MDBox>
  )
}

export default React.memo(TherapyHistoryTable);
