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
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import { FaPerson, FaPeopleGroup } from "react-icons/fa6";
import { HiIdentification } from "react-icons/hi2"

import DatabaseLayout from "layouts/DatabaseLayout";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import MedtronicJSONUploader from "./MedtronicJSONUploader";
import MRImagesUploader from "./MRImagesUploader";
import colors from "assets/theme/base/colors";

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
  const [availableParticipants, setAvailableParticipants] = useState({studies: [], participants: []});
  const [currentStudy, setCurrentStudy] = useState({study: null, participants: [], experiments: []});
  const [uploadDataType, setUploadDataType] = useState("Medtronic JSON Files");
  
  useEffect(() => {
    SessionController.query("/api/queryStudyParticipant").then((response) => {
      if (response.status == 200) {
        setAvailableParticipants(() => {
          for (let i in response.data.studies) {
            for (let j in response.data.participants[response.data.studies[i].uid]) {
              response.data.participants[response.data.studies[i].uid][j].name = SessionController.decodeMessage(response.data.participants[response.data.studies[i].uid][j].name);
            }
          }
          
          if (response.data.studies.length > 0) setCurrentStudy({study: {value: response.data.studies[0].uid, label: response.data.studies[0].name}, participants: [], currentParticipant: "batch-upload"});
          return response.data;
        });
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  return (
      <MDBox pt={5}>
        <Card>
          {alert}
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <MDTypography variant="h3">
                  {"Batch Upload Data"}
                </MDTypography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Autocomplete 
                  disableClearable
                  options={availableParticipants.studies.map((study) => ({value: study.uid, label: study.name}))} value={currentStudy.study}
                  onChange={(event, newValue) => {
                    if (newValue.inputValue) {
                      setAvailableParticipants((prev) => {
                        return {studies: [...prev.studies, {uid: "", name: newValue.inputValue}], participants: {...prev.participants, [newValue.inputValue]: []}}
                      })
                      setCurrentStudy({study: {value: newValue.inputValue, label: newValue.inputValue}, participants: [], currentParticipant: "batch-upload"});
                    } else {
                      for (let i = 0; i < availableParticipants.studies.length; i++) {
                        if (availableParticipants.studies[i].uid == newValue.value) {
                          setCurrentStudy({study: newValue, participants: availableParticipants.participants[newValue.value], currentParticipant: "batch-upload"});
                        }
                      }
                    }
                  }}
                  getOptionLabel={(option) => {
                    if (typeof option === 'string') { return option; }
                    if (option.inputValue) { return option.label; }
                    if (!option.label) { return "Not Available" }
                    return option.label;
                  }}
                  filterOptions={(options, params) => {
                    const filtered = filter(options, params);
                    const { inputValue } = params;
                    const isExisting = options.some((option) => inputValue === option.label);
                    if (inputValue !== '' && !isExisting) {
                      filtered.push({ inputValue, label: `Add "${inputValue}"`, });
                    }
                    return filtered;
                  }}
                  renderInput={(params) => (
                    <FormField {...params} label={"Accessible Studies"} InputLabelProps={{ shrink: true }} fullWidth />
                  )}
                />
              </Grid>
              {currentStudy.study ? (
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
                    options={["Medtronic JSON Files"]}
                    onChange={(event, newValue) => setUploadDataType(newValue)}
                  />
                  {uploadDataType === "Medtronic JSON Files" ? (
                    <MedtronicJSONUploader study={currentStudy.study.value} participant={"batch-upload"} experiment={"DefaultExperiment"}/>
                  ) : null}
                </Grid>
              ) : null}
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
  const [availableParticipants, setAvailableParticipants] = useState({studies: [], participants: []});
  const [currentStudy, setCurrentStudy] = useState({study: null, participants: [], experiments: []});
  const [participantInformation, setParticipantInformation] = useState({});
  const [uploadDataType, setUploadDataType] = useState("");
  
  useEffect(() => {
    SessionController.query("/api/queryStudyParticipant").then((response) => {
      if (response.status == 200) {
        setAvailableParticipants(() => {
          for (let i in response.data.studies) {
            for (let j in response.data.participants[response.data.studies[i].uid]) {
              response.data.participants[response.data.studies[i].uid][j].name = SessionController.decodeMessage(response.data.participants[response.data.studies[i].uid][j].name);
            }
          }
          return response.data;
        });
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const handleCreateParticipant = () => {
    if (!participantInformation.name) {
      SessionController.displayError("Name is required.", setAlert);
      return;
    }

    SessionController.query("/api/createStudyParticipant", {
      study: currentStudy.study.value,
      name: participantInformation.name,
      sex: participantInformation.sex,
      dob: participantInformation.dob ? (participantInformation.dob.toDate().getTime() / 1000) : null,
      diagnosis: participantInformation.diagnosis,
      disease_start_time: participantInformation.disease_start_time ? (participantInformation.disease_start_time.toDate().getTime() / 1000) : null
    }).then((response) => {
      if (response.status == 200) {
        for (let i in availableParticipants.studies) {
          if (availableParticipants.studies[i].uid === "" && availableParticipants.studies[i].name == currentStudy.study.value) {
            availableParticipants.studies[i].uid = response.data.study;
            availableParticipants.participants[response.data.study] = [{uid: response.data.uid, name: participantInformation.name}];
          } else if (availableParticipants.studies[i].uid == response.data.study) {
            availableParticipants.participants[response.data.study] = [...availableParticipants.participants[response.data.study], {uid: response.data.uid, name: participantInformation.name}];
          }
          setCurrentStudy({study: {value: response.data.study, label: currentStudy.study.label}, 
            participants: availableParticipants.participants[response.data.study],
            currentParticipant: {value: response.data.uid, label: participantInformation.name, experiments: [], currentExperiment: {}},
          });
        }
        setAvailableParticipants({...availableParticipants});
      }
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
              </Grid>
              <Grid item xs={12} md={6}>
                <Autocomplete 
                  disableClearable
                  options={availableParticipants.studies.map((study) => ({value: study.uid, label: study.name}))} value={currentStudy.study}
                  onChange={(event, newValue) => {
                    if (newValue.inputValue) {
                      setAvailableParticipants((prev) => {
                        return {studies: [...prev.studies, {uid: "", name: newValue.inputValue}], participants: {...prev.participants, [newValue.inputValue]: []}}
                      })
                      setCurrentStudy({study: {value: newValue.inputValue, label: newValue.inputValue}, participants: [], currentParticipant: null});
                    } else {
                      for (let i = 0; i < availableParticipants.studies.length; i++) {
                        if (availableParticipants.studies[i].uid == newValue.value) {
                          setCurrentStudy({study: newValue, participants: availableParticipants.participants[newValue.value], currentParticipant: null});
                        }
                      }
                    }
                  }}
                  getOptionLabel={(option) => {
                    if (typeof option === 'string') { return option; }
                    if (option.inputValue) { return option.label; }
                    if (!option.label) { return "Not Available" }
                    return option.label;
                  }}
                  filterOptions={(options, params) => {
                    const filtered = filter(options, params);
                    const { inputValue } = params;
                    const isExisting = options.some((option) => inputValue === option.label);
                    if (inputValue !== '' && !isExisting) {
                      filtered.push({ inputValue, label: `Add "${inputValue}"`, });
                    }
                    return filtered;
                  }}
                  renderInput={(params) => (
                    <FormField {...params} label={"Accessible Studies"} InputLabelProps={{ shrink: true }} fullWidth />
                  )}
                />
              </Grid>
              <Grid item sm={12} md={6}>
                {currentStudy.study ? <Autocomplete 
                  disableClearable
                  options={[{value: "create", label: "Create New Participant"}, 
                            {value: "batch-upload", label: "Batch Upload Multiple Participants"}, 
                    ...currentStudy.participants.map((participant) => ({...participant, value: participant.uid, label: participant.name}))]} 
                  value={currentStudy.currentParticipant}
                  onChange={(event, newValue) => {
                    setCurrentStudy((currentStudy) => {
                      currentStudy.currentParticipant = newValue;
                      if (currentStudy.currentParticipant.value === "batch-upload") {
                        currentStudy.currentParticipant.experiments = [{
                          uid: "default",
                          name: "Default Experiment"
                        }]
                        currentStudy.currentParticipant.currentExperiment = {
                          value: "default",
                          label: "Default Experiment"
                        }
                      } else if (currentStudy.currentParticipant.experiments) {
                        currentStudy.currentParticipant.currentExperiment = currentStudy.currentParticipant.experiments.length > 0 ? {
                          value: currentStudy.currentParticipant.experiments[0].uid,
                          label: currentStudy.currentParticipant.experiments[0].name
                        } : {}
                      } else {
                        currentStudy.currentParticipant.experiments = [];
                        currentStudy.currentParticipant.currentExperiment = {}
                      }
                      return {...currentStudy};
                    });
                  }}
                  getOptionLabel={(option) => {
                    if (typeof option === 'string') { return option; }
                    if (option.inputValue) { return option.label; }
                    if (!option.label) { return "Not Available" }
                    return option.label;
                  }}
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
                /> : null}
              </Grid>
              {currentStudy.currentParticipant ? <>
                {currentStudy.currentParticipant.value == "create" ? (
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
                        <Autocomplete selectOnFocus clearOnBlur
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
                    <Autocomplete 
                      disableClearable disabled={currentStudy.currentParticipant.value === "batch-upload"}
                      options={currentStudy.currentParticipant.experiments.map((experiment) => ({value: experiment.uid, label: experiment.name}))} 
                      value={currentStudy.currentParticipant.currentExperiment}
                      onChange={(event, newValue) => {
                        if (newValue.inputValue) {
                          SessionController.query("/api/queryParticipantExperiments", {
                            request_type: "Create",
                            participant_uid: currentStudy.currentParticipant.value,
                            study: currentStudy.study.value,
                            experiment: newValue.inputValue,
                            metadata: "{}"
                          }).then((response) => {
                            setCurrentStudy({...currentStudy, currentParticipant: {
                              ...currentStudy.currentParticipant,
                              experiments: [...currentStudy.currentParticipant.experiments, {uid: response.data.value, name: response.data.label}],
                              currentExperiment: response.data
                            }});
                          }).catch((error) => SessionController.displayError(error, setAlert));

                        } else {
                          setCurrentStudy({...currentStudy, currentParticipant: {
                            ...currentStudy.currentParticipant,
                            currentExperiment: newValue
                          }});
                        }
                      }}
                      getOptionLabel={(option) => {
                        if (typeof option === 'string') { return option; }
                        if (option.inputValue) { return option.label; }
                        if (!option.label) { return "Not Available" }
                        return option.label;
                      }}
                      filterOptions={(options, params) => {
                        const filtered = filter(options, params);
                        const { inputValue } = params;
                        const isExisting = options.some((option) => inputValue === option.label);
                        if (inputValue !== '' && !isExisting) {
                          filtered.push({ inputValue, label: `Add "${inputValue}"`, });
                        }
                        return filtered;
                      }}
                      renderInput={(params) => (
                        <FormField {...params} label={"Participant Experiments"} InputLabelProps={{ shrink: true }} fullWidth />
                      )}
                    />
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
                      options={["Medtronic JSON Files", "3D Images"]}
                      onChange={(event, newValue) => setUploadDataType(newValue)}
                    />
                    {uploadDataType === "Medtronic JSON Files" ? (
                      <MedtronicJSONUploader study={currentStudy.study.value} participant={currentStudy.currentParticipant.value} experiment={currentStudy.currentParticipant.currentExperiment.value}/>
                    ) : null}
                    {uploadDataType === "3D Images" ? (
                      <MRImagesUploader study={currentStudy.study.value} participant={currentStudy.currentParticipant.value} experiment={currentStudy.currentParticipant.currentExperiment.value}/>
                    ) : null}
                  </Grid>
                )}
              </> : null}
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
  );
};

