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

import {
  Autocomplete,
  Card,
  Chip,
  Checkbox,
  Grid,
  Dialog,
  DialogContent,
  DialogActions,
  Divider,
  Tabs,
  Tab,
  TextField,
  Table,
  TableHead,
  TableBody,
  TableCell,
  TableRow
} from "@mui/material";
import { createFilterOptions } from '@mui/material/Autocomplete';

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import FormField from "components/MDInput/FormField.js";
import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import { FaPerson, FaPeopleGroup } from "react-icons/fa6";
import { HiIdentification } from "react-icons/hi2"

import DatabaseLayout from "layouts/DatabaseLayout";
import MedtronicJSONUploader from "./MedtronicJSONUploader";
import BRAVORecordingBinaryStructureUploader from "./BRAVORecordingBinaryStructureUploader";
import BRAVOExportUploader from "./BRAVOExportUploader";
import NeuroimageUploader from "./NeuroimageUploader";
import ExternalCSVUploader from "./ExternalCSVUploader";
import UFMDATUploader from "./UFMDATUploader";
import HPFCSVUploader from "./HPFCSVUploader";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";

import colors from "assets/theme/base/colors";
import AlphaOmegaMPXUploader from "./AlphaOmegaMPXUploader";
import EventCSVUploader from "./EventCSVUploader";
import MATFileUploader from "./MATFileUploader";
import NeuroPacePersystDatUploader from "./NeuroPacePersystDatUploader";
import UFMDATv2Uploader from "./UFMDATv2Uploader";
import UFMDATv3Uploader from "./UFMDATv3Uploader";

const filter = createFilterOptions();

const diagnosisOptions = [
  {value: "None", label: "No Diagnosis"},
  {value: "Parkinson's Disease", label: "Parkinson's Disease"},
  {value: "Essential Tremor", label: "Essential Tremor"},
];

const sexOptions = [
  {value: "Male", label: "Male"},
  {value: "Female", label: "Female"},
  {value: "Other", label: "Other"},
];

export default function UploadDataView() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [useTab, setTab] = useState("Raw")
  
  return (
    <DatabaseLayout>
      <Tabs value={useTab} onChange={(event, newValue) => setTab(newValue)} sx={{paddingTop: 5}} TabIndicatorProps={{
          style: {
            backgroundColor: colors.info.focus,
          }
        }} >
        <Tab value={"Raw"} icon={<FaPeopleGroup size={24} style={useTab==="Raw" ? {color: colors.light.focus} : {}} />} iconPosition={"top"} label={
          <MDTypography fontWeight={"bold"} fontSize={24} style={useTab==="Raw" ? {color: colors.light.focus} : {}}>
            {"Batch Upload Data Files"}
          </MDTypography>
        } />
        <Tab value={"Deidentified"} icon={<FaPerson size={24} style={useTab==="Deidentified" ? {color: colors.light.focus} : {}} />} iconPosition={"top"} label={
          <MDTypography fontWeight={"bold"} fontSize={24} style={useTab==="Deidentified" ? {color: colors.light.focus} : {}}>
            {"Individual Data Upload"}
          </MDTypography>
        } />
      </Tabs>
      {useTab === "Raw" ? (
        <UploadBatchDataView />
      ) : (
        <UploadDeidentifiedDataView />
      )}
    </DatabaseLayout>
  );
}

function UploadBatchDataView() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [alert, setAlert] = useState(null);
  const [availableParticipants, setAvailableParticipants] = useState([]);
  const [uploadDataType, setUploadDataType] = useState("Medtronic JSON Files");
  
  return (
      <MDBox pt={5}>
        <Card>
          {alert}
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <MDTypography variant="h3">
                  {"Batch Upload Data "}
                </MDTypography>
                <MDTypography variant="h6">
                  {"Current Active Institute: " + user.Institute}
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
                    />
                  )}
                  isOptionEqualToValue={(option, value) => {
                    return option === value;
                  }}
                  renderOption={(props, option) => <li {...props}>{option}</li>}
                  value={uploadDataType}
                  options={["Medtronic JSON Files", "NeuroPace Persyst Data Format", "BRAVO Export (v1)"]}
                  onChange={(event, newValue) => setUploadDataType(newValue)}
                />
                {uploadDataType === "Medtronic JSON Files" ? (
                  <MedtronicJSONUploader institute={user.Institute} participant={"batch-upload"}/>
                ) : null}
                {uploadDataType === "BRAVO Export (v1)" ? (
                  <BRAVOExportUploader institute={user.Institute} version={"v1"}/>
                ) : null}
                {uploadDataType === "NeuroPace Persyst Data Format" ? (
                  <NeuroPacePersystDatUploader institute={user.Institute} participant={"batch-upload"}/>
                ) : null}
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
  );
};

function UploadDeidentifiedDataView() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [alert, setAlert] = useState(null);
  const [availableParticipants, setAvailableParticipants] = useState([]);
  const [activeParticipant, setActiveParticipant] = useState({});
  const [participantInformation, setParticipantInformation] = useState({});
  const [uploadDataType, setUploadDataType] = useState("");
  
  useEffect(() => {
    SessionController.query("/api/queryParticipants", {
      ParticipantGroupId: user.InstituteId
    }).then((response) => {
      setAvailableParticipants(response.data);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

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
      setAvailableParticipants((availableParticipants) => [...availableParticipants, response.data]);
      setActiveParticipant({
        ...response.data,
        value: response.data.Id, label: response.data.Name
      });
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  return (
      <MDBox pt={5}>
        <Card>
          {alert}
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <MDTypography variant="h3">
                  {"Upload Data"}
                </MDTypography>
                <MDTypography variant="h6">
                  {"Current Active Institute: " + user.Institute}
                </MDTypography>
              </Grid>
              <Grid item sm={12}>
                <Autocomplete 
                  disableClearable
                  options={[{value: "create", label: "Create New Participant"},
                    ...availableParticipants.map((participant) => ({...participant, value: participant.Id, label: participant.Name})).sort((a,b) => a.label.localeCompare(b.label))]} 
                  value={activeParticipant}
                  onChange={(event, newValue) => {
                    if (newValue.value == "create") {
                      setParticipantInformation({
                        name: "", diagnosis: "", sex: "", dob: null,
                        disease_start_time: null
                      })
                    }
                    setActiveParticipant(newValue);
                  }}
                  getOptionLabel={(option) => {
                    if (typeof option === 'string') { return option; }
                    if (option.inputValue) { return option.label; }
                    if (!option.label) { return "Not Available" }
                    return option.label;
                  }}
                  isOptionEqualToValue={(option, value) => option.value == value.value}
                  renderOption={(props, option) => {
                    const { key, ...optionProps } = props;
                    return (
                      <MDBox key={key} component="li" sx={{ '& > img': { mr: 2, flexShrink: 0 } }} {...optionProps} >
                        {option.value === "batch-upload" || option.value === "create" ? (
                          <MDTypography variant="button" fontWeight="bold">
                            {option.label}
                          </MDTypography>
                        ) : (
                          <MDBox>
                            {option.label}
                          </MDBox>
                        )}
                      </MDBox>
                    );
                  }}
                  renderInput={(params) => (
                    <FormField {...params} label={"Available Participants"} InputLabelProps={{ shrink: true }} fullWidth />
                  )}
                />
              </Grid>
              {activeParticipant.value == "create" ? (
                <Grid item sm={12}>
                  <Divider variant="insert" />
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
                      />
                    </Grid>
                    <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                      <Autocomplete selectOnFocus clearOnBlur
                        renderInput={(params) => (
                          <TextField {...params} variant="standard" placeholder={"Select Sex/Gender (Optional)"} />
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
                          renderInput={(params) => <TextField {...params} fullWidth/>}
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
                          />
                        )}
                        isOptionEqualToValue={(option, value) => {
                          return option === value;
                        }}
                        renderOption={(props, option) => <li {...props}>{option}</li>}
                        value={participantInformation.diagnosis}
                        options={["Parkinson's Disease", "Essential Tremor", "Other"]}
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
                          renderInput={(params) => <TextField {...params} fullWidth/>}
                        />
                      </LocalizationProvider>
                    </Grid>
                    <Grid item xs={12} style={{marginTop: "auto"}}>
                      <MDButton variant={"contained"} color={"success"} style={{marginLeft: "auto"}} onClick={handleCreateParticipant}>
                        {"Create Participant"}
                      </MDButton>
                    </Grid>
                  </Grid>
                </Grid>
              ) : (
                <Grid item sm={12}>
                  <MDTypography variant="h5">
                    {"Upload Data Type"}
                  </MDTypography>
                  <Autocomplete selectOnFocus clearOnBlur
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        variant="standard"
                        placeholder={"Select Data Type (Required)"}
                      />
                    )}
                    isOptionEqualToValue={(option, value) => {
                      return option === value;
                    }}
                    renderOption={(props, option) => <li {...props}>{option}</li>}
                    value={uploadDataType}
                    options={["Medtronic JSON Files", "NeuroPace Persyst Data Format", "AlphaOmega MPX Files", "BRAVO Recording Structure (Binary)", 
                      "BRAVO Offline Synchronized Recordings (v2)", "BRAVO Offline Synchronized Recordings (v3)", "HDF CSV Format", "Event Annotation CSV", "UF MDAT Files", ".MAT Data File", "3D Images"]}
                    onChange={(event, newValue) => setUploadDataType(newValue)}
                  />
                  {uploadDataType === "Medtronic JSON Files" ? (
                    <MedtronicJSONUploader institute={user.Institute} participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "NeuroPace Persyst Data Format" ? (
                    <NeuroPacePersystDatUploader institute={user.Institute} participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "AlphaOmega MPX Files" ? (
                    <AlphaOmegaMPXUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "BRAVO Recording Structure (Binary)" ? (
                    <BRAVORecordingBinaryStructureUploader institute={user.Institute} participant={activeParticipant.value} version={""}/>
                  ) : null}
                  {uploadDataType === "BRAVO Offline Synchronized Recordings (v2)" ? (
                    <UFMDATv2Uploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "BRAVO Offline Synchronized Recordings (v3)" ? (
                    <UFMDATv3Uploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "HDF CSV Format" ? (
                    <HPFCSVUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "Event Annotation CSV" ? (
                    <EventCSVUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "UF MDAT Files" ? (
                    <UFMDATUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === ".MAT Data File" ? (
                    <MATFileUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                  {uploadDataType === "3D Images" ? (
                    <NeuroimageUploader institute={user.Institute}  participant={activeParticipant.value}/>
                  ) : null}
                </Grid>
              )}
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
  );
};

