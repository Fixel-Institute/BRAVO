/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo } from "react";
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

function TherapyHistoryTable({therapyHistory, viewConfigurationTable}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { language, report } = controller;

  const [therapyTable, setTherapyTable] = React.useState({});
  const [interleavingSwitch, setInterleavingSwitch] = React.useState({});

  React.useEffect(() => {
    setTherapyTable(() => {
      let therapyTable = {};
      for (let i in therapyHistory) {
        if (!Object.keys(therapyTable).includes(therapyHistory[i].Device.Id + "(" + therapyHistory[i].Type + ")")) {
          therapyTable[therapyHistory[i].Device.Id + "(" + therapyHistory[i].Type + ")"] = []
        }
        therapyTable[therapyHistory[i].Device.Id + "(" + therapyHistory[i].Type + ")"].push(therapyHistory[i]);
      }

      for (let i in therapyTable) {
        therapyTable[i] = therapyTable[i].sort((a,b) => {
          if (a.GroupId == b.GroupId) {
            return a.Date - b.Date
          } else {
            return a.GroupId.localeCompare(b.GroupId)
          }
        })
      }
      return therapyTable;
    });
  }, [therapyHistory])

  return useMemo(() => (
    {}
  ), [therapyTable]);
}

export default TherapyHistoryTable;
