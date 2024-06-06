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
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";
import TherapyHistoryFigure from "./TherapyHistoryFigure";
import ImpedanceHeatmap from "./ImpedanceHeatmap";
import ImpedanceHistory from "./ImpedanceHistory";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";
import MDButton from "components/MDButton";
import MDBadge from "components/MDBadge";
import TherapyHistoryRow from "./TherapyHistoryRow";

function TherapyHistoryTable({therapyHistory}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, language, report } = controller;

  const [activeDevice, setActiveDevice] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState(null);
  const [filteredTherapy, setFilteredTherapy] = React.useState([]);
  const [uniqueDates, setUniqueDates] = React.useState([]);
  const [electrodes, setElectrodes] = React.useState([]);

  React.useEffect(() => {
    if (therapyHistory.length > 0) {
      setActiveDevice(therapyHistory[0].device);
      setActiveTab("Post-visit Therapy");
    }
  }, [therapyHistory]);

  React.useEffect(() => {
    for (let i in therapyHistory) {
      if (therapyHistory[i].device == activeDevice) {
        setElectrodes(therapyHistory[i].electrodes);
        setFilteredTherapy(() => {
          let uniqueDates = [];
          const filteredTherapy = therapyHistory[i].therapy.filter((a) => {
            if (a.type == activeTab) {
              if (!uniqueDates.includes(a.date)) uniqueDates.push(a.date);
              return true;
            }
            return false;
          });
          uniqueDates.reverse();
          setUniqueDates(uniqueDates);
          return [...filteredTherapy];
        });
        
      }
    }
  }, [activeDevice, activeTab]);

  return (
    <Card>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <MDBox p={2}>
            <MDTypography variant="h5" fontWeight="bold" fontSize={24}>
              {dictionary.TherapyHistory.Table.TableTitle[language]}
            </MDTypography>
          </MDBox>
        </Grid>

        <Grid item xs={12} md={3} display={"flex"} flexDirection={{
          xs: "row",
          md: "column"
        }}>
          {therapyHistory.map((history) => {
            let deviceName = SessionController.decodeMessage(history.device);
            if (deviceName.length > 30) deviceName = deviceName.slice(0,10) + " " + deviceName.slice(10,20) + " " + deviceName.slice(20,30) + "...";
            return <MDBox key={history.device} p={2}>
              <MDButton variant={activeDevice == history.device ? "contained" : "outlined"} color="info" fullWidth onClick={() => setActiveDevice(history.device)}>
                <TabletAndroidIcon sx={{marginRight: 1}} />
                <MDTypography variant="h5" fontWeight="bold" fontSize={15} color={activeDevice == history.device ? "white" : "black"}>
                  {deviceName}
                </MDTypography>
              </MDButton>
            </MDBox>
          })}
        </Grid>
        <Grid item xs={12} md={9} sx={{maxHeight: "1000px", overflowY: "auto"}} display={"flex"} flexDirection={{
          xs: "row",
          md: "column"
        }}>
          <MDBox display={"flex"} flexDirection={"row"}>
            {["Pre-visit Therapy", "Post-visit Therapy", "Past Therapy"].map((type) => {
              return <MDBox key={type} p={2}>
                <MDButton variant={activeTab == type ? "contained" : "outlined"} color="warning" onClick={() => setActiveTab(type)} sx={{borderRadius: 30}}>
                  <TabletAndroidIcon sx={{marginRight: 1}} />
                  <MDTypography variant="h5" fontWeight="bold" fontSize={15} color={activeTab == type ? "white" : "black"}>
                    {dictionaryLookup(dictionary.TherapyHistory.Table, type, language)}
                  </MDTypography>
                </MDButton>
              </MDBox>;
            })}
          </MDBox>
          <MDBox style={{overflowY: "auto"}}>
          {uniqueDates.map((date) => {
            return <MDBox display={"flex"} flexDirection={"column"} pb={2} pr={2}>
                <Accordion key={date} TransitionProps={{ unmountOnExit: true }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />} >
                  <MDTypography>
                    {new Date(SessionController.decodeTimestamp(date*1000)).toLocaleDateString(language, SessionController.getDateTimeOptions("DateFull"))}
                    <br></br>
                    {new Date(SessionController.decodeTimestamp(date*1000)).toLocaleTimeString(language)}
                  </MDTypography>
                </AccordionSummary>
                <TherapyHistoryRow contents={filteredTherapy.filter((a) => a.date == date)} electrodes={electrodes} />
              </Accordion>
            </MDBox>
          })}
          </MDBox>
        </Grid>
      </Grid>
    </Card>
  );
}

export default React.memo(TherapyHistoryTable);
