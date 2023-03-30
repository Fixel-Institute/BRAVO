/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Card,
  Divider,
  Dialog,
  DialogContent,
  DialogActions,
  Grid,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Tooltip,
  TextField,
  Icon,
  IconButton,
  Input,
} from "@mui/material";

import Papa from "papaparse";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";
import { AccessAlarm } from "@mui/icons-material";
import DeidentificationTable from "components/Tables/DeidentificationTable";

const csvParser = (text) => {
  var data = Papa.parse(text, {
    header: true
  });
  return data.data;
}

export default function PatientLookupTable() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { user, language, patientID } = controller;

  const [deidentificationTable, setDeidentificationTable] = useState([]);
  const [tableAvailable, setTableAvailable] = useState(false);
  const [tableDialog, setTableDialog] = useState({passcode: "", show: false});
  const inputFile = useRef(null) 

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    SessionController.query("/api/deidentificationTable").then((response) => {
      setTableAvailable(response.data["Exist"]);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  return (
    <DatabaseLayout>
      <MDBox py={3}>
        {alert}
        <Card>
          <MDBox p={2} display={"flex"} flexDirection={"row"} justifyContent={"space-between"}>
            <MDTypography variant={"h5"}>
              {"De-identification Table"}
            </MDTypography>

            <MDButton variant={"outlined"} color={"info"} onClick={() => {
              setTableDialog({...tableDialog, show: "UploadTable"})
            }}>
              {"Add Table Here"}
            </MDButton>
          </MDBox>
          {deidentificationTable.length > 0 ? (
            <DeidentificationTable data={deidentificationTable}/>
          ) : (
            tableAvailable ? (
              <MDBox p={2}>
                <MDBox px={2} pb={2} style={{display: "flex", flexDirection: "column", justifyContent: "center"}}>
                  <MDTypography variant={"h6"} fontSize={25} textAlign={"center"}>
                    {"Existing Lookup Table Found"}
                  </MDTypography>
                  <MDButton variant={"outlined"} color={"info"} onClick={() => {
                    setTableDialog({...tableDialog, show: "DecryptTable"})
                  }}>
                    {"Decrypt Table Here"}
                  </MDButton>
                </MDBox>
              </MDBox>
            ) : (
              <MDBox p={2}>
                <MDBox px={2} pb={2} style={{display: "flex", flexDirection: "column", justifyContent: "center"}}>
                  <MDTypography variant={"h6"} fontSize={25} textAlign={"center"}>
                    {"Existing Lookup Table Not Found"}
                  </MDTypography>
                </MDBox>
              </MDBox>
            )
          )}
        </Card>

        <Dialog open={tableDialog.show === "DecryptTable"} onClose={() => setTableDialog({passcode: "", show: false})}>
          <Card>
            <MDBox p={2} style={{display: "flex", flexDirection: "column", justifyContent: "center"}}>
              <MDTypography variant={"h5"}>
                {"Decrypt Deidentification Table"}
              </MDTypography>

              <MDTypography variant={"h6"} style={{paddingTop: 15}}>
                {"Secure Passcode"}
              </MDTypography>
              <TextField
                margin="dense" id="name"
                type={"password"}
                value={tableDialog.passcode}
                onChange={(event) => setTableDialog({...tableDialog, passcode: event.target.value})}
                label={"Secure Passcode"}
                fullWidth
              />

              <MDButton variant={"contained"} color={"warning"} onClick={() => {
                if (tableDialog.passcode.length >= 4) {
                  SessionController.query("/api/deidentificationTable", {
                    passkey: tableDialog.passcode,
                    QueryTable: true
                  }).then((response) => {
                    setDeidentificationTable(response.data);
                    setTableDialog({...tableDialog, show: false});
                  }).catch((error) => {
                    SessionController.displayError(error, setAlert);
                  })
                } else {
                  SessionController.displayError({
                    response: {
                      status: 400,
                      data: {
                        code: 3001
                      }
                    }
                  }, setAlert);
                }
              }}>
                {"Decrypt Identification Table for Edit"}
              </MDButton>

            </MDBox>
          </Card>
        </Dialog>

        <Dialog open={tableDialog.show === "UploadTable"} onClose={() => setTableDialog({passcode: "", show: false})}>
          <Card>
            <MDBox p={2} style={{display: "flex", flexDirection: "column", justifyContent: "center"}}>
              <MDTypography variant={"h5"}>
                {"Upload Deidentification Table"}
              </MDTypography>

              <MDTypography variant={"h6"} style={{paddingTop: 15}}>
                {"Secure Deidentification Table with Passcode"}
              </MDTypography>
              <TextField
                margin="dense" id="name"
                value={tableDialog.passcode}
                onChange={(event) => setTableDialog({...tableDialog, passcode: event.target.value})}
                label={"Secure Passcode"} type="text"
                fullWidth
              />

              <MDButton variant={"contained"} color={"warning"} onClick={() => {
                if (tableDialog.passcode.length >= 4) {
                  inputFile.current.click();
                } else {
                  SessionController.displayError({
                    response: {
                      status: 400,
                      data: {
                        code: 3001
                      }
                    }
                  }, setAlert);
                }
              }}>
                {"Select File to Upload"}
              </MDButton>

              <Input inputRef={inputFile} type={"file"} inputProps={{accept: ".csv"}} style={{display: "none"}} onChange={(event) => {
                const reader = new FileReader();
                reader.onload = () => {
                  const table = csvParser(reader.result);
                  if (table.length > 0) {
                    if (table[0].identifier && table[0].patient_deidentifier && table[0].tags) {

                      let lookupTable = [];
                      for (let row of table) {
                        if (row.study_deidentifier && row.patient_deidentifier && row.identifier && row.tags) {
                          lookupTable.push({
                            tags: JSON.parse(row.tags),
                            identifier: row.identifier,
                            study_deidentifier: row.study_deidentifier,
                            patient_deidentifier: row.patient_deidentifier
                          })
                        }
                      }

                      SessionController.query("/api/deidentificationTable", {
                        passkey: tableDialog.passcode,
                        UpdateTable: lookupTable
                      }).then((response) => {
                        setTableAvailable(true);
                        setTableDialog({...tableDialog, show: false});
                      }).catch((error) => {
                        SessionController.displayError(error, setAlert);
                      });
                    }
                  }
                };
                reader.readAsBinaryString(event.target.files[0]);
              }} />
            </MDBox>
          </Card>
        </Dialog>
      </MDBox>
    </DatabaseLayout>
  );
};
