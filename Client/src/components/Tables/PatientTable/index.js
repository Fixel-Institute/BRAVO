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
import PatientTablePagination from "./PatientTablePagination.js";

const PatientTable = ({data}) => {
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

  const viewPatientData = (id) => {
    SessionController.setPatientID(id).then((result) => {
      if (result) {
        setContextState(dispatch, "patientID", id);
        navigate("/patient-overview", {replace: false});
      }
    });
  };

  return (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["PatientTableName", "PatientTableDiagnosis", "PatientTableDevice", "PatientTableLastVisit"].map((col) => {
              return (
                <TableCell key={col} variant="head" style={{width: "25%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
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
            return <TableRow key={patient.ID}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                  {patient.LastName}, {patient.FirstName}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {dictionaryLookup(dictionary.PatientOverview.PatientInformation, patient.Diagnosis, language)}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
              {patient.DaysSinceImplant.map((device) => {
                return <MDTypography key={device.Name} variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {device.Name} {<br></br>}
                  </MDTypography>
              })}
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {new Date(patient.LastSeen * 1000).toLocaleString(language, SessionController.getDateTimeOptions("DateFull"))}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <Tooltip title="View Patient" placement="top">
                  <MDButton variant="contained" color="info" size="small" onClick={() => viewPatientData(patient.ID)}>
                    <i className="fa-solid fa-eye"></i>
                  </MDButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
      <PatientTablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} />
    </MDBox>
  );
};

export default memo(PatientTable);