/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo } from "react"

import {
  Autocomplete,
  Box,
  FormControl,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  InputLabel,
  IconButton,
  Select,
  Switch,
  MenuItem,
  Tooltip,
  Checkbox,
  Collapse,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import FormField from "components/MDInput/FormField.js";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";

function BRAVORecordingTable({data, deleteData, downloadData,}) {
  const tableHeader = [{
    title: "Recording Time",
    minWidth: 100,
    width: "95%"
  }]

  return useMemo(() => (
    <MDBox style={{overflowX: "auto", maxHeight: "60vh"}}>
      <Table size="large" style={{marginTop: 20, display: "block", height: "fit-content"}}>
        <TableHead sx={{display: "table-header-group", position: "sticky", top: 0, zIndex: 1}}>
          <TableRow sx={{background: "white"}}>
            {tableHeader.map((col) => (
              <TableCell key={col.title} variant="head" style={{width: col.width, minWidth: col.minWidth, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                  {col.title}
                </MDTypography>
              </TableCell>
            ))}
            <TableCell key={"viewedit"} variant="head" style={{width: "100px", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
              <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>{" "}</MDTypography>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.sort((a,b) => a.Date - b.Date).map((source) => {
            return <TableRow key={source.Id}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={18} fontWeight={"bold"}>
                  {source.Name}
                </MDTypography>
                <MDTypography variant="h5" fontSize={12} style={{marginBottom: 0}}>
                  {new Date(source.DateOfRecording*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(source.Timezone),
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    timeZoneName: "longGeneric"
                  })}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)", display: "flex", flexDirection: "column", justifyContent: "center"}}>
                <MDButton variant="contained" color="success" size="small" onClick={() => downloadData(source.Id)}>
                  {"Download"}
                </MDButton>
                <MDButton variant="contained" color="error" size="small" onClick={() => deleteData(source.Id)}>
                  {"Delete"}
                </MDButton>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
    </MDBox>
  ), [data]);
}

export default BRAVORecordingTable;