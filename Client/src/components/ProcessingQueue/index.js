/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect } from "react";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  Table,
  TableRow,
  TableCell,
  DialogContentText,
  DialogActions,
  Button,
  TableBody,
  CircularProgress,
  TableHead,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

import { usePlatformContext } from "context";
import { dictionary } from "assets/translation";
import { SessionController } from "database/session-control";
import { TaskAlt } from "@mui/icons-material";

export default function ProcessingQueue({queues, clearQueue}) {
  const [ context, dispatch ] = usePlatformContext();
  const { language } = context;

  return <MDBox style={{
    minHeight: 500
  }}>
    <MDTypography variant="h2" align="center" fontSize={30} style={{paddingTop: 15}}>
      {"Processing Queue"}
    </MDTypography>
    <MDBox px={5} style={{display: "flex", justifyContent: "space-around"}}>
      <MDButton variant="contained" color="success" onClick={() => {
        clearQueue("Complete");
      }}>
        {"Clear Completed"}
      </MDButton>
      <MDButton variant="contained" color="error" onClick={() => {
        clearQueue("All");
      }}>
        {"Clear All"}
      </MDButton>
    </MDBox>
    <DialogContent sx={{paddingLeft: 5, paddingRight: 5}}>
      <Table>
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            <TableCell variant="head" style={{width: "50%"}}>
              <MDTypography variant="p" align="center" fontSize={12}>
                {"Queue Filename"}
              </MDTypography>
            </TableCell>
            <TableCell variant="head" style={{width: "30%"}}>
              <MDTypography variant="p" align="center" fontSize={12}>
                {"Queue Time Since"}
              </MDTypography>
            </TableCell>
            <TableCell variant="head" style={{width: "20%"}}>
              <MDTypography variant="p" align="center" fontSize={12}>
                {"Job State"}
              </MDTypography>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {queues.map((queue) => {
            return <TableRow key={queue.taskId}>
              <TableCell>
                <MDTypography variant="p" align="center" fontSize={9}>
                  {queue.descriptor.filename}
                </MDTypography>
              </TableCell>
              <TableCell>
                <MDTypography variant="p" align="center" fontSize={12}>
                  {new Date(queue.since*1000).toLocaleString({
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                  })}
                </MDTypography>
              </TableCell>
              <TableCell>
                {queue.state === "InProgress" ? <CircularProgress size={"20px"}/> : null}
                {queue.state === "Complete" ? <TaskAlt color={"success"} fontSize="large"/> : null}
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
    </DialogContent>
  </MDBox>;
}