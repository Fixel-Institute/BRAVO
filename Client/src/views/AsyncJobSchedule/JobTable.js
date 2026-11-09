/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo, useState, useEffect } from "react"

import {
  Autocomplete,
  Box,
  FormControl,
  Dialog, 
  DialogContent,
  Grid,
  TextField,
  DialogActions,
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
import { usePlatformContext, setContextState } from "context.js";

import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

function JobTable({data, updateJobStatus}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  return useMemo(() => (
    <>
      <MDBox px={2} style={{overflowX: "auto", maxHeight: "100vh"}}>
        <Table size="large" style={{marginTop: 20, display: "block", height: "fit-content"}}>
          <TableHead sx={{display: "table-header-group", position: "sticky", top: 0, zIndex: 1}}>
            <TableRow sx={{background: "white"}}>
              <TableCell variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"PID"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Start Date"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "20%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Script Name"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "10%", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Status"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "10%", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.sort((a,b) => b.Date-a.Date).map((job) => {
              return (
                <TableRow key={job.Id}>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}} >
                    <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={15} fontWeight={"bold"}>
                      {job.Metadata.pid ? job.Metadata.pid : job.Metadata.Id}
                    </MDTypography>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {new Date(job.Date * 1000).toLocaleString()}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {job.Metadata.script_name}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {job.State}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDButton variant="outlined" color="primary" size="small" onClick={() => {
                        updateJobStatus(job.Id);
                      }}>
                        {"Refresh State"}
                      </MDButton>
                    </MDBox>
                  </TableCell>
                </TableRow>
                )
            })}
          </TableBody>
        </Table>
      </MDBox>
    </>
  ), [data]);
}

export default JobTable;