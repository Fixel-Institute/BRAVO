/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect, memo } from "react"
import { useNavigate } from "react-router-dom";

import {
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
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

const DeidentificationTable = ({data}) => {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const navigate = useNavigate();

  const viewPerPage = 10;
  const [displayData, setDisplayData] = useState([]);
  const [paginationControl, setPagination] = useState({
    currentPage: 0,
    totalPages: 0
  });

  useEffect(() => {
    setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)})
  }, [data]);

  useEffect(() => {
    setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
  }, [paginationControl]);

  return (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["Deidentifier", "Tags", "Alias"].map((col) => {
              return (
                <TableCell key={col} variant="head" style={{width: "33%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionaryLookup(dictionary.Dashboard, col, language)}
                  </MDTypography>
                </TableCell>
            )})}
          </TableRow>
        </TableHead>
        <TableBody>
          {displayData.map((row, index) => {
            return <TableRow key={index}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                  {row.study_deidentifier} {row.patient_deidentifier}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {row.tags}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {row.identifier}
                </MDTypography>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
      <TablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} />
    </MDBox>
  );
};

export default memo(DeidentificationTable);