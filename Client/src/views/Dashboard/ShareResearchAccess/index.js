/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, memo } from "react";

import {
  Card,
  Chip,
  Checkbox,
  Grid,
  Dialog,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableHead,
  TableBody,
  TableCell,
  TableRow
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import TextFilter from "./TextFilter";
import DatabaseLayout from "layouts/DatabaseLayout";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";
import { setAnimated } from "@react-spring/animated";

export default function ResearchAccessView() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [alert, setAlert] = useState(null);
  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [patients, setPatients] = useState([]);
  const [patientsToExport, setPatientsToExport] = useState([]);
  const [addPatientInterface, setAddPatientInterface] = useState({show: false});
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    SessionController.query("/api/queryPatientAccessTable").then((response) => {
      if (response.status == 200) {
        setPatients(response.data);
        setFilteredPatients(response.data);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const handlePatientFilter = (options) => {
    if (patients.length > 0) {
      if (options.length == 0) setFilteredPatients(patients);
      else setFilteredPatients(patients.filter((patient) => {
        var state = true;
        const diagnosis = dictionaryLookup(dictionary.PatientOverview.PatientInformation, patient.Diagnosis, language).toLowerCase();
        for (var option of options) {
          const optionLower = option.toLowerCase();
          state = state && (
            patient.FirstName.toLowerCase().includes(optionLower) || 
            patient.LastName.toLowerCase().includes(optionLower) || 
            diagnosis.includes(optionLower)
          );
        }
        return state;
      }));
    }
  };

  const handleExportPatients = () => {
    setAlert(<MuiAlertDialog title={"Export Selected Patients?"} message={`${patientsToExport.length} Patient${patientsToExport.length > 1 ? "s" : ""} Selected`} 
      cancelButton
      handleClose={() => setAlert(null)}
      handleCancel={() => setAlert(null)}
      handleConfirm={() => {
        SessionController.query("/api/updatePatientAccess", {
          createLink: true,
          patientList: patientsToExport
        }).then((response) => {
          setAlert(<MuiAlertDialog title={"Export Success"} message={`Please share the following one-time access code to others: ${response.data.shareLink}`}
            handleConfirm={() => setAlert(null)}
            handleClose={() => setAlert(null)}
          />)
        }).catch((error) => {
          SessionController.displayError(error, setAlert);
        })
      }}
    />)
  };

  const handleImportPatients = () => {
    SessionController.query("/api/updatePatientAccess", {
      requestAccess: true,
      accessCode: addPatientInterface.accessCode
    }).then((response) => {
      setAlert(<MuiAlertDialog title={"Import Success"} message={""}
        handleConfirm={() => setAlert(null)}
        handleClose={() => setAlert(null)}
      />)
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    })
  };

  const handleDeleteAuthorization = (authorizedId, patientId) => {
    SessionController.query("/api/updatePatientAccess", {
      deleteAccess: true,
      patientId: patientId,
      authorizedId: authorizedId
    }).then((response) => {
      setPatients((patients) => {
        patients = patients.map((patient) => {
          if (patient.ID == patientId) patient.Authorized = patient.Authorized.filter((authorized) => authorized.ID != authorizedId);
          return patient;
        })
        return patients;
      })
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    })
  };

  return (
    <DatabaseLayout>
      {alert}
      <MDBox pt={5}>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {dictionary.ResearchAccess.AccessTable[language]}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6} display="flex" sx={{
                justifyContent: {
                  sm: "space-between",
                  md: "end"
                }
              }}>
                <TextFilter onFilter={handlePatientFilter} language={language} />
                <MDButton variant="contained" color="info" onClick={() => setAddPatientInterface({accessCode: "", show: true})}>
                  {dictionary.ResearchAccess.AddViewAccess[language]} 
                </MDButton>
              </Grid>
              <Grid item xs={12} style={{display: "flex", justifyContent: "space-between"}}>
                <MDBox>
                <MDButton variant={"contained"} color={"success"} style={{marginLeft: 10}} onClick={() => {
                  setPatientsToExport((patientsToExport) => {
                    for (let patient of filteredPatients) {
                      if (!patientsToExport.includes(patient.ID) && patient.Uploader == user.Institute) patientsToExport.push(patient.ID);
                    }
                    return [...patientsToExport];
                  });
                }}>
                  {"Check All"}
                </MDButton>
                <MDButton variant={"contained"} color={"error"} style={{marginLeft: 10}} onClick={() => {
                  setPatientsToExport((patientsToExport) => {
                    const filteredIDs = filteredPatients.map((patient) => patient.ID)
                    patientsToExport = patientsToExport.filter((id) => !filteredIDs.includes(id));
                    return [...patientsToExport];
                  });
                }}>
                  {"Uncheck All"}
                </MDButton>
                </MDBox>
                <MDBox>
                <MDButton variant={"contained"} color={"info"} style={{marginLeft: 10}} onClick={handleExportPatients}>
                  {"Export Selected"}
                </MDButton>
                </MDBox>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <MDBox style={{overflowX: "auto", overflowY: "auto", maxHeight: "70vh"}}>
                  <Table size="small">
                    <TableHead sx={{display: "table-header-group"}}>
                      <TableRow>
                        {["PatientTableName", "PatientTableDiagnosis", "UploaderInfo", "SharedInfo"].map((col) => {
                          return (
                            <TableCell key={col} variant="head" style={{width: "25%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                              <MDTypography variant="span" fontSize={12} fontWeight={"bold"}>
                                {dictionaryLookup(dictionary.ResearchAccess, col, language)}
                              </MDTypography>
                            </TableCell>
                        )})}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredPatients.map((patient) => {
                        return <TableRow key={patient.ID}>
                          <TableCell style={{paddingBottom: 1, display: "flex", flexDirection: "row", borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                            <Checkbox label={"Merge"} checked={patientsToExport.includes(patient.ID)} disabled={user.Institute != patient.Uploader} style={{padding: 0, paddingRight: 5}} onClick={() => {
                              setPatientsToExport((patientsToExport) => {
                                if (patientsToExport.includes(patient.ID)) patientsToExport = patientsToExport.filter((id) => id != patient.ID);
                                else patientsToExport.push(patient.ID);
                                return [...patientsToExport];
                              })
                            }} />
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
                            <MDTypography variant="h6" fontSize={12} style={{marginBottom: 0}}>
                              {patient.Uploader}
                            </MDTypography>
                          </TableCell>
                          <TableCell style={{paddingBottom: 1, borderBottom: "0px solid rgba(224, 224, 224, 0.4)"}}>
                            {patient.Authorized.map((authorizedUser) => {
                              return <Chip key={authorizedUser.ID} label={authorizedUser.Email} size={"small"} sx={{marginRight: 0.5}} onDelete={() => handleDeleteAuthorization(authorizedUser.ID, patient.ID)} />
                            })}
                          </TableCell>
                        </TableRow>
                      })}
                    </TableBody>
                  </Table>
                </MDBox>
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
      
      <Dialog open={addPatientInterface.show} onClose={() => setAddPatientInterface({...addPatientInterface, accessCode: "", show: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Enter Access Code to Grant Research Access"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <TextField
            variant="standard"
            margin="dense" id="name"
            value={addPatientInterface.accessCode}
            onChange={(event) => setAddPatientInterface({...addPatientInterface, accessCode: event.target.value})}
            label={"Access Code"} type="text"
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setAddPatientInterface({...addPatientInterface, accessCode: "", show: false})}>{"Cancel"}</MDButton>
          <MDButton color="info" onClick={handleImportPatients}>{"Request"}</MDButton>
        </DialogActions>
      </Dialog>
    </DatabaseLayout>
  );
};

