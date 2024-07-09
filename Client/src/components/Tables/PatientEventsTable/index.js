/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom";

import {
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Checkbox,
  IconButton,
  Tooltip,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import MDTypography from 'components/MDTypography';
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import TablePagination from "./TablePagination.js";
import { e } from "mathjs";

const PatientEventsTable = ({data, deleteRecords}) => {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const navigate = useNavigate();

  const viewPerPage = 300;
  const [displayData, setDisplayData] = useState([]);
  const [paginationControl, setPagination] = useState({
    currentPage: 0,
    totalPages: 0
  });
  const [toggleMerge, setToggleMerge] = useState({show: true, merge: []});

  useEffect(() => {
    setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)})
  }, [data]);

  useEffect(() => {
    setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
  }, [paginationControl]);

  const deleteRecordsOnClick = () => {
    deleteRecords(toggleMerge.merge);
  }

  return useMemo(() => (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["Checked", "EventName", "EventTime", "EventType"].map((col) => {
              return (
                <TableCell key={col} variant="head" style={{width: "33%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}} >
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={() => {
                    if (col == "Checked") {
                      setToggleMerge((toggleMerge) => {
                        let notChecked = [];
                        for (let i in displayData) {
                          if (!toggleMerge.merge.includes(displayData[i].ID)) {
                            notChecked.push(displayData[i].ID);
                          }
                        }
                        if (notChecked.length == 0) {
                          toggleMerge.merge = toggleMerge.merge.filter((id) => notChecked.includes(id));
                          console.log(toggleMerge.merge)
                        } else {
                          toggleMerge.merge.push(...notChecked);
                        }
                        console.log(notChecked)
                        return {...toggleMerge};
                      })
                    }
                  }}>
                    {dictionaryLookup(dictionary.PatientEvents.Table, col, language)}
                  </MDTypography>
                </TableCell>
            )})}
          </TableRow>
        </TableHead>
        <TableBody>
          {displayData.map((row, index) => {
            return <TableRow key={index}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)", paddingTop: 0, paddingBottom: 0}}>
                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                  <Checkbox label={"Merge"} checked={toggleMerge.merge.includes(row.ID)} style={{padding: 0}} onClick={() => {
                    if (!toggleMerge.merge.includes(row.ID)) {
                      setToggleMerge((toggleMerge) => {
                        toggleMerge.merge.push(row.ID);
                        return {...toggleMerge};
                      })
                    } else {
                      setToggleMerge((toggleMerge) => {
                        toggleMerge.merge = toggleMerge.merge.filter((id) => id != row.ID);
                        return {...toggleMerge};
                      })
                    }
                  }} />
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)", paddingTop: 0, paddingBottom: 0}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                   {row.Name}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)", paddingTop: 0, paddingBottom: 0}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {new Date(row.Time*1000).toLocaleString({
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                  })}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)", paddingTop: 0, paddingBottom: 0}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {row.Type}
                </MDTypography>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
      <TablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} deleteRecords={deleteRecordsOnClick} />
    </MDBox>
  ), [displayData, toggleMerge]);
};

export default PatientEventsTable;