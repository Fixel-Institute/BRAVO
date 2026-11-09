/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, memo } from "react";
import { useNavigate } from "react-router-dom";

import {
  Card,
  Grid,
  Divider,
  Dialog,
  Autocomplete,
  TextField,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import FormField from "components/MDInput/FormField.js";
import SessionPasswordView from "./SessionPasswordView";
import ParticipantTable from "./ParticipantTable";
import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";
import LoadingProgress from "components/LoadingProgress";

import BRAVOExportUploader from "../UploadDataView/BRAVOExportUploader";
import NeuroPacePersystDatUploader from "../UploadDataView/NeuroPacePersystDatUploader";
import MedtronicJSONUploader from "../UploadDataView/MedtronicJSONUploader";
import BRAVOExportV2Uploader from "../UploadDataView/BRAVOExportV2Uploader";

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
  const [alert, setAlert] = useState(null);

  const navigate = useNavigate();
  
  const [newParticipantEditor, setNewParticipantEditor] = useState(false);
  const [participantInformation, setParticipantInformation] = useState({});
  const [filteredParticipants, setFilteredParticipants] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [availableParticipants, setAvailableParticipants] = useState([]);
  const [uploadInterface, setUploadInterface] = useState({ show: false, uploadDataType: "Medtronic JSON Files" });

  const [showDecryptionPassword, setShowDecryptionPassword] = useState(false);

  const handleCreateParticipant = () => {
    if (!participantInformation.name) {
      SessionController.displayError("Name is required.", setAlert);
      return;
    }

    SessionController.query("/api/createParticipantInformation", {
      Name: participantInformation.name,
      Sex: participantInformation.sex,
      DOB: participantInformation.dob ? (participantInformation.dob.toDate().getTime() / 1000) : 0,
      Diagnosis: participantInformation.diagnosis,
      DiseaseStartTime: participantInformation.disease_start_time ? (participantInformation.disease_start_time.toDate().getTime() / 1000) : 0
    }).then((response) => {
      setContextState(dispatch, "participant_uid", response.data.Id);
      navigate("/participant-overview/" + response.data.Id, {replace: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  useEffect(() => {
    SessionController.query("/api/queryParticipants", {
      ParticipantGroupId: user.InstituteId
    }).then((response) => {
      setAvailableParticipants(response.data);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
    //setContextState(dispatch, "report", "");
  }, []);

  const handleParticipantFilter = (event) => {
    setFilterOptions({value: event.currentTarget.value});
  };

  useEffect(() => {
    const filterTimer = setTimeout(() => {
      if (availableParticipants.length == 0) return;
      
      if (filterOptions.value) {
        const options = filterOptions.value.split(" ");
        setFilteredParticipants(availableParticipants.filter((participant) => {
          let state = true;
          for (var option of options) {
            const optionLower = option.toLowerCase();
            state = state && (
              participant.Id.toLowerCase().includes(optionLower) || 
              participant.MRN.toLowerCase().includes(optionLower) || 
              participant.Name.toLowerCase().includes(optionLower) || 
              participant.Diagnosis.toLowerCase().includes(optionLower) || 
              participant.Tags.filter((tag) => tag.toLowerCase().includes(optionLower)).length > 0 || 
              participant.DBSDevices.filter((device) => {
                if (device.Type.toLowerCase().includes(optionLower)) return true;
                if (device.Id.toLowerCase().includes(optionLower)) return true;
                if (device.Electrodes.filter((electrode) => {
                  if (electrode.CustomName.toLowerCase().includes(optionLower)) return true;
                  if (electrode.Type.toLowerCase().includes(optionLower)) return true;
                }).length > 0) return true;
              }).length > 0
            );
          }
          return state;
        }));
      } else {
        setFilteredParticipants([...availableParticipants]);
      }
    }, 200);
    return () => clearTimeout(filterTimer);
  }, [filterOptions, availableParticipants]);

  return (
    <DatabaseLayout>
      {alert}
      <MDBox mt={2}>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <MDBox display="flex" flexDirection="column">
                  <MDTypography variant="h3">
                    {dictionary.Dashboard.ParticipantTable[language]}
                  </MDTypography>
                  <MDInput label={dictionary.Dashboard.SearchParticipant[language]} value={filterOptions.text} onChange={(value) => handleParticipantFilter(value)} autoComplete="off" sx={{paddingRight: 2, marginTop: 2, width: "100%"}}/>
                </MDBox>
              </Grid>
              <Grid item xs={12} md={4}>
                <MDBox display="flex" flexDirection="column">
                  <MDButton variant="gradient" color="info" style={{margin: 2}} onClick={() => setUploadInterface({show: true, uploadDataType: "Medtronic JSON Files"})}>
                    <MDTypography variant="h5" color="white">
                      {"Upload Data"}
                    </MDTypography>
                  </MDButton>
                  <MDButton variant="gradient" color="success" style={{margin: 2}} onClick={() => setNewParticipantEditor(true)}>
                    <MDTypography variant="h5" color="white">
                      {"Add New Participant"}
                    </MDTypography>
                  </MDButton>
                </MDBox>
              </Grid>
              {availableParticipants.length > 0 ? (
                <Grid item xs={12} sx={{marginTop: 2}}>
                  <ParticipantTable data={filteredParticipants} />
                </Grid>
              ) : ( <LoadingProgress /> )}
            </Grid>
          </MDBox>
        </Card>

        <Dialog open={uploadInterface.show} onClose={() => setUploadInterface({show: false, uploadDataType: "Medtronic JSON Files"})} maxWidth="md" fullWidth>
          <Grid container spacing={2} p={3}>
            <Grid item xs={12}>
              <MDTypography variant="h3">
                {"Upload Data to Database"}
              </MDTypography>
            </Grid>
            <Grid item sm={12} md={12}>
              <Divider variant="insert" />
              <MDTypography variant="h5">
                {"Upload Data Type"}
              </MDTypography>
              <Autocomplete selectOnFocus clearOnBlur
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="standard"
                    placeholder={"Select Data Type (Required)"}
                    autoComplete="off"
                  />
                )}
                isOptionEqualToValue={(option, value) => {
                  return option === value;
                }}
                renderOption={(props, option) => <li {...props}>{option}</li>}
                value={uploadInterface.uploadDataType}
                options={["Medtronic JSON Files", "NeuroPace Persyst Data Format", "BRAVO Export (v1)", "BRAVO Export (v2)"]}
                onChange={(event, newValue) => setUploadInterface(prev => ({...prev, uploadDataType: newValue}))}
              />
              {uploadInterface.uploadDataType === "Medtronic JSON Files" ? (
                <MedtronicJSONUploader institute={user.Institute} participant={"batch-upload"}/>
              ) : null}
              {uploadInterface.uploadDataType === "BRAVO Export (v1)" ? (
                <BRAVOExportUploader institute={user.Institute} version={"v1"}/>
              ) : null}
              {uploadInterface.uploadDataType === "BRAVO Export (v2)" ? (
                <BRAVOExportV2Uploader institute={user.Institute}  participant={"batch-upload"}/>
              ) : null}
              {uploadInterface.uploadDataType === "NeuroPace Persyst Data Format" ? (
                <NeuroPacePersystDatUploader institute={user.Institute} participant={"batch-upload"}/>
              ) : null}
            </Grid>
          </Grid>
        </Dialog>

        <Dialog open={newParticipantEditor} onClose={() => setNewParticipantEditor(false)} maxWidth="md" fullWidth>
          <MDBox p={3}>
            <MDTypography variant="h5">
              {"New Participant Information"}
            </MDTypography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  variant="standard" margin="dense" id="study-participant-name"
                  value={participantInformation.name}
                  onChange={(event) => setParticipantInformation({...participantInformation, name: event.target.value})}
                  label={"Study Participant Name (Required)"} type="text"
                  fullWidth
                  autoComplete="off"
                />
              </Grid>
              <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                <Autocomplete selectOnFocus clearOnBlur
                  renderInput={(params) => (
                    <TextField {...params} variant="standard" placeholder={"Select Sex/Gender (Optional)"} autoComplete="off" />
                  )}
                  isOptionEqualToValue={(option, value) => {
                    return option === value;
                  }}
                  renderOption={(props, option) => <li {...props}>{option}</li>}
                  value={participantInformation.sex}
                  options={["Male", "Female", "Other"]}
                  onChange={(event, newValue) => setParticipantInformation({...participantInformation, sex: newValue})}
                />
              </Grid>
              <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
                  <DatePicker
                    id="study-participant-dob"
                    label="Date of Birth (Optional)"
                    value={participantInformation.dob}
                    onChange={(newDate) => {
                      setParticipantInformation({...participantInformation, dob: newDate});
                    }}
                    renderInput={(params) => <TextField {...params} fullWidth autoComplete="off"/>}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                <Autocomplete selectOnFocus freeSolo
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      variant="standard"
                      placeholder={"Select Diagnosis (Optional)"}
                      autoComplete="off"
                    />
                  )}
                  isOptionEqualToValue={(option, value) => {
                    return option === value;
                  }}
                  renderOption={(props, option) => <li {...props}>{option}</li>}
                  value={participantInformation.diagnosis}
                  options={["Parkinson's Disease", "Essential Tremor", "SCA6", "Other"]}
                  onChange={(event, newValue) => setParticipantInformation({...participantInformation, diagnosis: newValue})}
                />
              </Grid>
              <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
                  <DatePicker
                    id="study-participant-dod"
                    label="Date of Diagnosis (Optional)"
                    value={participantInformation.disease_start_time}
                    onChange={(newDate) => {
                      setParticipantInformation({...participantInformation, disease_start_time: newDate});
                    }}
                    renderInput={(params) => <TextField {...params} fullWidth autoComplete="off"/>}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} style={{marginTop: "auto"}}>
                <MDButton variant={"contained"} color={"success"} style={{marginLeft: "auto"}} onClick={handleCreateParticipant}>
                  {"Create Participant"}
                </MDButton>
              </Grid>
            </Grid>
          </MDBox>
        </Dialog>
      </MDBox>
    </DatabaseLayout>
  );
};

