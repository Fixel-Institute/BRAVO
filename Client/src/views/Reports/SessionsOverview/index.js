import { useEffect, useState } from "react";

import {
  Card,
  Grid,
  Dialog,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SessionOverview() {
  const [controller, dispatch] = usePlatformContext();
  const { user, patientID, language } = controller;

  const [alert, setAlert] = useState(null);
  const [availableSessions, setAvailableSessions] = useState([]);

  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [patients, setPatients] = useState([]);
  const [uploadInterface, setUploadInterface] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    SessionController.query("/api/querySessionOverview", {
      id: patientID
    }).then((response) => {
      setAvailableSessions(response.data.AvailableSessions)
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const deleteSession = (id) => {
    SessionController.query("/api/querySessionOverview", {
      id: patientID,
      deleteSession: id,
    }).then((response) => {
      setAvailableSessions(availableSessions.filter((session) => session.SessionID != id))
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  const currentDate = new Date();

  return (
    <DatabaseLayout>
      {alert}
      <MDBox mt={2}>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {dictionary.SessionOverview.SessionList[language]}
                </MDTypography>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <MDBox style={{overflowX: "auto"}}>
                  <Table size="small">
                    <TableHead sx={{display: "table-header-group"}}>
                      <TableRow>
                        {["SessionDate", "SessionName", "SessionData"].map((col) => {
                          return (
                            <TableCell key={col} variant="head" style={{width: "30%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                              <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                                {dictionaryLookup(dictionary.SessionOverview, col, language)}
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
                      {availableSessions.map((session) => {
                        return (
                          <TableRow key={session.SessionID}>
                            <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                              <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                                {session.DeviceName}
                              </MDTypography>
                              <MDTypography variant="span" fontSize={12} style={{marginBottom: 0}}>
                                {new Date(session.SessionTimestamp*1000).toLocaleString(language)}
                              </MDTypography>
                            </TableCell>
                            <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                              <MDTypography variant="p" fontSize={13} style={{marginBottom: 0}}>
                                {session.SessionFilename}
                              </MDTypography>
                            </TableCell>
                            <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                              {Object.keys(session.AvailableRecording).map((key) => {
                                if (session.AvailableRecording[key] == 0) return;
                                
                                return (
                                  <MDTypography key={key} variant="p" fontSize={12} style={{marginBottom: 0}}>
                                    {dictionary.Routes[key][language]}{":"} {session.AvailableRecording[key]}<br />
                                  </MDTypography>
                                )
                              })}
                            </TableCell>
                            <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                              <MDButton variant={"outlined"} color={"error"} size={"small"} onClick={() => {
                                deleteSession(session.SessionID)
                              }}>
                                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                                  {"DELETE"}
                                </MDTypography>
                              </MDButton>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </MDBox>
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
    </DatabaseLayout>
  );
};

