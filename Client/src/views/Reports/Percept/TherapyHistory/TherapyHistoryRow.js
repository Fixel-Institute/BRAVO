/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useState } from "react";
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

function TherapyHistoryRow({contents, electrodes}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { participant_uid, language, report } = controller;
  
  const [groups, setGroups] = React.useState([]);

  React.useEffect(() => {
  }, [contents]);

  return (
    <AccordionDetails>
      <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} px={2} style={{overflowX: "auto"}}>
      <Table>
        <TableBody>
        {contents.sort((a,b) => a.name.localeCompare(b.name)).map((content) => {
          let channel_names = []
          for (let i in electrodes) {
            if (electrodes[i].name.startsWith(content.channel.split(" ")[0])) {
              channel_names = electrodes[i].channel_names;
              content.channel = electrodes[i].custom_name;
              break
            }
          }

          return <TableRow key={content.name + content.channel}>
            <TableCell>
              <MDTypography fontWeight={"bold"} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {content.name}
              </MDTypography>
              <MDTypography fontWeight={"medium"} fontSize={15} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {content.channel.startsWith("Left") ? (
                  <MDBadge badgeContent="L" color={"info"} size={"xs"} container sx={{marginRight: 1}} />
                ) : (
                  <MDBadge badgeContent="R" color={"error"} size={"xs"} container sx={{marginRight: 1}} />
                )}
                {content.channel}
              </MDTypography>
              <MDTypography fontWeight={"bold"} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                {content.mode}
              </MDTypography>
            </TableCell>
            <TableCell>
              <MDBox display={"flex"} flexDirection={"column"} alignItems={"center"}>
                {content.settings.map((setting, index) => (
                  <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} p={"2px"}>
                    {setting.contact.map((contact, cIndex) => {
                        return <Tooltip key={"setting" + index + contact} title={setting.amplitude[cIndex] + " " + setting.amplitude_unit} placement="top">
                          <MDBadge badgeContent={channel_names[contact]} color={"success"} size={"xs"} container sx={{marginRight: 0}} />
                        </Tooltip>
                    })}
                    {setting.return_contact.map((contact, cIndex) => (
                      <MDBadge badgeContent={contact > -1 ? channel_names[contact] : "CAN"} color={"secondary"} size={"xs"} container sx={{marginRight: 0}} />
                    ))}
                  </MDBox>
                ))}
              </MDBox>
            </TableCell>
            <TableCell style={{minWidth: "200px"}}>
              <MDBox display={"flex"} flexDirection={"column"} alignItems={"center"}>
                {content.settings.map((setting, index) => (
                  <MDTypography key={"program" + index.toString()} fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                    {setting.frequency} {" Hz"} {setting.pulsewidth} {" μSec"}
                  </MDTypography>
                ))}
              </MDBox>
            </TableCell>

            <TableCell style={{minWidth: "100px"}}>
              <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                {content.settings[0].cycling == 1 ? (
                  <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                    {`${(content.settings[0].cycling*100).toFixed(1)}% Duty Cycle (Period: ${(content.settings[0].cycling_period / 1000).toFixed(1) + " " + dictionary.Time.Seconds[language]})`}
                  </MDTypography>
                ) : (
                  <MDTypography fontSize={12} style={{paddingBottom: 0, paddingTop: 0, marginBottom: 0}}>
                    {dictionary.TherapyHistory.Table.CyclingOff[language]}
                  </MDTypography>
                )}
              </MDBox>
            </TableCell>
          </TableRow>
        })}
        </TableBody>
      </Table>
      </MDBox>
    </AccordionDetails>
  );
}

export default React.memo(TherapyHistoryRow);
