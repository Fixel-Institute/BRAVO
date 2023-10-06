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
  Grid,
  Dialog,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import UploadDialog from "./UploadDialog";
import PatientTable from "components/Tables/PatientTable";
import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function DatabaseStatistic({title, description, value}) {
  return (
    <Card>
      <MDBox p={2}>
        <Grid container>
          <Grid item xs={7}>
            <MDBox mb={0.5} lineHeight={1}>
              <MDTypography
                variant="button"
                fontWeight="medium"
                color="text"
                textTransform="capitalize"
              >
                {title}
              </MDTypography>
            </MDBox>
            <MDBox lineHeight={1}>
              <MDTypography variant="h5" fontWeight="bold">
                {value}
              </MDTypography>
            </MDBox>
          </Grid>
          <Grid item xs={5}>
            <MDBox width="100%" textAlign="right" lineHeight={1}>
              <MDTypography
                variant="caption"
                color="secondary"
                fontWeight="regular"
                sx={{ cursor: "pointer" }}
              >
                {description}
              </MDTypography>
            </MDBox>
          </Grid>
        </Grid>
      </MDBox>
    </Card>
  );
}

export default function DashboardOverview() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [databaseInfo, setDatabaseInfo] = useState({
    patients: 0,
    totalRecordings: 0,
    totalStorage: "0 Bytes",
  });

  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [patients, setPatients] = useState([]);
  const [uploadInterface, setUploadInterface] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    SessionController.query("/api/queryDatabaseInfo").then((response) => {
      if (response.status == 200) {
        setDatabaseInfo(response.data);
      }
    });

    SessionController.query("/api/queryPatients").then((response) => {
      if (response.status == 200) {
        setPatients(response.data);
        setFilteredPatients(response.data);
      }
    });
    
    let client = new WebSocket(SessionController.getServer().replace("http","ws") + "/socket/notification");
    client.onerror = function() {
      console.log('Connection Error');
    };
    client.onopen = () => {
      client.send(JSON.stringify({
        "Authorization": SessionController.getRefreshToken()
      }));
    };
    client.onclose = () => {
      console.log('Connection Closed');
    };

    let currentPatientList = [];
    client.onmessage = (event) => {
      let content = JSON.parse(event.data);
      if (content["Notification"] === "PatientTableUpdate") {
        if (content["UpdateType"] === "NewPatient") {
          setPatients(currentPatients => {
            return [content["NewPatient"], ...currentPatients];
          });
        }
      }
    };

    return () => {
      client.close();
    }

  }, []);

  const handlePatientFilter = (event) => {
    setFilterOptions({value: event.currentTarget.value});
  }

  const onNewPatient = (data) => {
    if (data.newPatient) {
      setPatients([data.newPatient, ...patients]);
    } else if (data.Refresh) {
      SessionController.query("/api/queryPatients").then((response) => {
        if (response.status == 200) {
          setPatients(response.data);
          setFilteredPatients(response.data);
        }
      });
    }
  };

  useEffect(() => {
    const filterTimer = setTimeout(() => {
      if (filterOptions.value) {
        const options = filterOptions.value.split(" ");
        setFilteredPatients(patients.filter((patient) => {
          var state = true;
          const diagnosis = dictionaryLookup(dictionary.PatientOverview.PatientInformation, patient.Diagnosis, language).toLowerCase();
          for (var option of options) {
            const optionLower = option.toLowerCase();
            state = state && (
              patient.ID.toLowerCase().includes(optionLower) || 
              patient.FirstName.toLowerCase().includes(optionLower) || 
              patient.LastName.toLowerCase().includes(optionLower) || 
              patient.DaysSinceImplant.filter((device) => device.Name.toLowerCase().includes(optionLower)).length > 0 || 
              patient.Tags.filter((tag) => tag.toLowerCase().includes(optionLower)).length > 0 || 
              diagnosis.includes(optionLower)
            );
          }
          return state;
        }));
      } else {
        if (patients.length > 0) setFilteredPatients(patients);
      }
    }, 200);
    return () => clearTimeout(filterTimer);
  }, [filterOptions, patients]);

  const currentDate = new Date();

  return (
    <DatabaseLayout>
      <MDBox py={3}>
        <MDBox mb={3}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <DatabaseStatistic 
                title={dictionary.Dashboard.TotalPatients[language]} 
                value={databaseInfo.patients} 
                description={currentDate.toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"))} />
            </Grid>
            <Grid item xs={12} sm={4}>
              <DatabaseStatistic 
                title={dictionary.Dashboard.TotalStorage[language]} 
                value={databaseInfo.totalStorage} 
                description={currentDate.toLocaleDateString(language, SessionController.getDateTimeOptions("DateLong"))} />
            </Grid>
          </Grid>
        </MDBox>
      </MDBox>
      <MDBox>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {dictionary.Dashboard.PatientTable[language]}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6} display="flex" sx={{
                justifyContent: {
                  sm: "space-between",
                  md: "end"
                }
              }}>
                <MDInput label={dictionary.Dashboard.SearchPatient[language]} value={filterOptions.text} onChange={(value) => handlePatientFilter(value)} sx={{paddingRight: 2}}/>
                <MDButton variant="contained" color="info" onClick={() => setUploadInterface({patientId: "", deviceId: "", diagnosis: ""})}>
                  {dictionary.Dashboard.AddNewSession[language]} 
                </MDButton>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <PatientTable data={filteredPatients} />
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
              
      <UploadDialog show={Boolean(uploadInterface)} deidentified={!user.Clinician} onCancel={() => setUploadInterface(null)} />
    </DatabaseLayout>
  );
};

