/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect, memo, Fragment } from "react"
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
  Chip,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import MDTypography from 'components/MDTypography';
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import PatientTablePagination from "./PatientTablePagination.js";

const PatientTable = ({data}) => {
  const [controller, dispatch] = usePlatformContext();
  const { language, PatientTablePageIndex, lastActive } = controller;

  const navigate = useNavigate();

  const viewPerPage = 20;
  const [sortedData, setSortedData] = useState([]);
  const [sortType, setSortType] = useState({
    key: "PatientTableName",
    direction: 1
  });

  const [displayData, setDisplayData] = useState([]);
  const [paginationControl, setPagination] = useState({
    currentPage: 0,
    totalPages: 0
  });

  useEffect(() => {
    setSortedData(data);
    setSortType({
      key: "PatientTableName",
      direction: 1
    });

    if (paginationControl.totalPages != Math.ceil(data.length / viewPerPage) && paginationControl.totalPages != 0) {
      SessionController.setPageIndex("PatientTable", 0);
      setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)});
      return;
    }

    if (new Date().getTime() - lastActive > 600000) {
      SessionController.setPageIndex("PatientTable", 0);
      setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)});
    } else {
      setPagination({currentPage: PatientTablePageIndex ? PatientTablePageIndex : 0, totalPages: Math.ceil(data.length / viewPerPage)});
    }
  }, [data]);

  useEffect(() => {
    setDisplayData(sortedData.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
  }, [paginationControl, sortedData]);

  useEffect(() => {
    switch (sortType.key) {
      case "PatientTableName": 
        if (sortType.direction == 1) {
          setSortedData([...data.sort((a,b) => (a.LastName + ", " + a.FirstName).localeCompare(b.LastName + ", " + b.FirstName))]);
        } else {
          setSortedData([...data.sort((a,b) => (b.LastName + ", " + b.FirstName).localeCompare(a.LastName + ", " + a.FirstName))]);
        }
        break;
      case "PatientTableDiagnosis": 
        if (sortType.direction == 1) {
          setSortedData([...data.sort((a,b) => (a.Diagnosis).localeCompare(b.Diagnosis))]);
        } else {
          setSortedData([...data.sort((a,b) => (b.Diagnosis).localeCompare(a.Diagnosis))]);
        }
        break;
      case "PatientTableLastVisit": 
        if (sortType.direction == 1) {
          setSortedData([...data.sort((a,b) => (a.LastSeen) - (b.LastSeen))]);
        } else {
          setSortedData([...data.sort((a,b) => (b.LastSeen) - (a.LastSeen))]);
        }
        break;
      case "PatientTableLastModified": 
        if (sortType.direction == 1) {
          setSortedData([...data.sort((a,b) => (a.LastChange) - (b.LastChange))]);
        } else {
          setSortedData([...data.sort((a,b) => (b.LastChange) - (a.LastChange))]);
        }
        break;
      default:
        setSortedData([...data]);
        break
    }
  }, [sortType]);

  const viewPatientData = (id) => {
    SessionController.setPatientID(id).then((result) => {
      if (result) {
        setContextState(dispatch, "patientID", id);
        navigate("/patient-overview", {replace: false});
      }
    });
  };

  const sortPatientList = (col) => {
    setSortType((currentType) => {
      if (col == currentType.key) {
        currentType.direction *= -1; 
      } else {
        currentType = {
          key: col,
          direction: 1
        }
      }
      return {...currentType}
    });
  };

  return (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["PatientTableName", "PatientTableDiagnosis", "PatientTableDevice", "PatientTableLastVisit", "PatientTableLastModified"].map((col) => {
              return (
                <TableCell key={col} variant="head" style={{width: "25%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>sortPatientList(col)}>
                    {dictionaryLookup(dictionary.Dashboard, col, language)}
                  </MDTypography>
                </TableCell>
            )})}
            <TableCell key={"viewedit"} variant="head" style={{width: "100px", verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
              <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>
                {" "}
              </MDTypography>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {displayData.map((patient) => {
            return <Fragment key={patient.ID}>
              <TableRow>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                    {patient.LastName}, {patient.FirstName}
                  </MDTypography>
                </TableCell>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                    {dictionaryLookup(dictionary.PatientOverview.PatientInformation, patient.Diagnosis, language)}
                  </MDTypography>
                </TableCell>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                {patient.DaysSinceImplant.map((device) => {
                  return <MDTypography key={device.Name} variant="p" fontSize={12} style={{marginBottom: 0}}>
                    {device.Name} {<br></br>}
                    </MDTypography>
                })}
                </TableCell>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                    {new Date(patient.LastSeen * 1000).toLocaleString(language, SessionController.getDateTimeOptions("DateFull"))}
                  </MDTypography>
                </TableCell>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                    {new Date(patient.LastChange * 1000).toLocaleString(language, SessionController.getDateTimeOptions("DateFull"))}
                  </MDTypography>
                </TableCell>
                <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                  <Tooltip title="View Patient" placement="top">
                    <MDButton variant="contained" color="info" size="small" onClick={() => viewPatientData(patient.ID)}>
                      <i className="fa-solid fa-eye"></i>
                    </MDButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={5} style={{paddingTop: 0, borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  {patient.Tags.map((tag) => {
                    return <Chip key={patient.ID + " " + tag} label={tag} size={"small"} sx={{marginRight: 0.5}} />
                  })}
                </TableCell>
              </TableRow>
            </Fragment>
          })}
        </TableBody>
      </Table>
      <PatientTablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} />
    </MDBox>
  );
};

export default memo(PatientTable);