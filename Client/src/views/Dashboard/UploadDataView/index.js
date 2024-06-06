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
  TextField,
  Table,
  TableHead,
  TableBody,
  TableCell,
  TableRow
} from "@mui/material";

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import CreatableSelect from 'react-select/creatable'
import Select from 'react-select'

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import DatabaseLayout from "layouts/DatabaseLayout";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import PerceptJSONUploader from "./PerceptJSONUploader";
import MRImagesUploader from "./MRImagesUploader";

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

  const [alert, setAlert] = useState(null);
  const [availableParticipants, setAvailableParticipants] = useState({studies: [], participants: []});
  const [currentStudy, setCurrentStudy] = useState({study: null, participants: []});
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
            availableParticipants.participants[response.data.study] = [{uid: response.data.participant, name: participantInformation.name}];
          } else if (availableParticipants.studies[i].uid == response.data.study) {
            availableParticipants.participants[response.data.study] = [...availableParticipants.participants[response.data.study], {uid: response.data.participant, name: participantInformation.name}];
          }
          setCurrentStudy({study: {value: response.data.study, label: currentStudy.study.label}, 
            participants: availableParticipants.participants[response.data.study],
            currentParticipant: {value: response.data.participant, label: participantInformation.name}});
        }
        setAvailableParticipants({...availableParticipants});
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  return (
    <DatabaseLayout>
      {alert}
      <MDBox pt={5}>
        <Card>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={12}>
                <MDTypography variant="h3">
                  {"Upload Data"}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h6">
                  {"Accessible Studies"}
                </MDTypography>
                <CreatableSelect options={availableParticipants.studies.map((study) => ({value: study.uid, label: study.name}))} 
                  value={currentStudy.study}
                  onChange={(newValue) => {
                    for (let i = 0; i < availableParticipants.studies.length; i++) {
                      if (availableParticipants.studies[i].uid == newValue.value) {
                        setCurrentStudy({study: newValue, participants: availableParticipants.participants[newValue.value], currentParticipant: null});
                      }
                    }
                  }}
                  onCreateOption={(created) => {
                    setAvailableParticipants((prev) => {
                      return {studies: [...prev.studies, {uid: "", name: created}], participants: [...prev.participants, []]}
                    })
                    setCurrentStudy({study: {value: created, label: created}, participants: [], currentParticipant: null});
                  }}
                  placeholder={"Type to create new Study"}
                  />
              </Grid>
              <Grid item sm={12} md={6}>
                {currentStudy.study ? <>
                  <MDTypography variant="h6">
                    {"Available Participants"}
                  </MDTypography>
                  <Select options={[{value: "create", label: "Create New Participant"}, 
                      ...currentStudy.participants.map((participant) => ({value: participant.uid, label: participant.name}))]} 
                    value={currentStudy.currentParticipant}
                    onChange={(newValue) => {
                      setCurrentStudy((currentStudy) => {
                        currentStudy.currentParticipant = newValue;
                        return {...currentStudy};
                      });
                    }}
                    placeholder={"Select Participant"}
                    />
                </> : null}
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
                          variant="standard"
                          margin="dense" id="name"
                          value={participantInformation.name}
                          onChange={(event) => setParticipantInformation({...participantInformation, name: event.target.value})}
                          label={"Study Participant Name (Required)"} type="text"
                          fullWidth
                        />
                      </Grid>
                      <Grid item xs={12} md={3} style={{marginTop: "auto"}}>
                        <Autocomplete selectOnFocus clearOnBlur
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              variant="standard"
                              placeholder={"Select Sex/Gender (Optional)"}
                            />
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
                    <Divider variant="insert" />
                    <MDTypography variant="h5">
                      {"Metadata and Data Files"}
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
                      options={["Medtronic Percept PC/RC JSONs", "3D Images (CT/MRI)"]}
                      onChange={(event, newValue) => setUploadDataType(newValue)}
                    />
                    {uploadDataType === "Medtronic Percept PC/RC JSONs" ? (
                      <PerceptJSONUploader study={currentStudy.study.value} participant={currentStudy.currentParticipant.value}/>
                    ) : null}
                    {uploadDataType === "3D Images (CT/MRI)" ? (
                      <MRImagesUploader study={currentStudy.study.value} participant={currentStudy.currentParticipant.value}/>
                    ) : null}
                  </Grid>
                )}
              </> : null}
            </Grid>
          </MDBox>
        </Card>
      </MDBox>
      
    </DatabaseLayout>
  );
};

