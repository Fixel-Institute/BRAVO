/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo, Fragment } from "react"

import {
  Autocomplete,
  Box,
  FormControl,
  Dialog, 
  DialogContent,
  Grid,
  TextField,
  DialogActions,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  InputLabel,
  IconButton,
  Select,
  Switch,
  MenuItem,
  Tooltip,
  Checkbox,
  Collapse,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import FormField from "components/MDInput/FormField.js";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDBadge from "components/MDBadge";

function ParticipantListTable({data, getRecordingData}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [participantData, setParticipantData] = React.useState([]);
  const [showTable, setShowTable] = React.useState("");
  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  
  const [filterOptions, setFilterOptions] = React.useState({Keyword: "", Electrodes: [], ElectrodeOptions: [], 
                                                                          Targets: [], TargetOptions: [], 
                                                                          Diagnosis: [], DiagnosisOptions: []});
  const [displayData, setDisplayData] = React.useState([]);
  const [editRecordingName, setEditRecordingName] = React.useState({show: false, name: "", tags: [], therapy: [], analysisId: ""});

  const [newGroupView, setNewGroupView] = React.useState({show: false, timeseries: [], therapies: []});

  const tableHeader = [{
    title: "StreamingTableDate",
    minWidth: 100,
    width: "25%"
  },{
    title: "Recording Tags", 
    minWidth: 200,
    width: "20%"
  },{
    title: "StreamingTableChannels", 
    minWidth: 200,
    width: "15%"
  },{
    title: "StreamingTableTherapy", 
    minWidth: 200,
    width: "25%"
  },{
    title: "StreamingTableRecordingDuration", 
    minWidth: 200,
    width: "15%"
  }]

  React.useEffect(() => {
    filterOptions.DiagnosisOptions = [];
    filterOptions.TargetOptions = [];
    filterOptions.ElectrodeOptions = [];
    
    var collectiveData = [];
    var uniqueParticipants = [];
    for (var i = 0; i < data.length; i++) {
      if (!uniqueParticipants.includes(data[i].ParticipantId)) {
        uniqueParticipants.push(data[i].ParticipantId);
        let electrodes = [];
        let target = [];
        for (let j in data[i].Participant.DBSDevices) {
          for (let k in data[i].Participant.DBSDevices[j].Electrodes) {
            if (!electrodes.includes(data[i].Participant.DBSDevices[j].Electrodes[k].Type)) {
              electrodes.push(data[i].Participant.DBSDevices[j].Electrodes[k].Type);
            }
            if (!target.includes(data[i].Participant.DBSDevices[j].Electrodes[k].Target.split(" ")[1])) {
              target.push(data[i].Participant.DBSDevices[j].Electrodes[k].Target.split(" ")[1])
            }
          }
        }

        for (let j in electrodes) {
          if (!filterOptions.ElectrodeOptions.includes(electrodes[j])) {
            filterOptions.ElectrodeOptions.push(electrodes[j])
          }
        }
        for (let j in target) {
          if (!filterOptions.TargetOptions.includes(target[j])) {
            filterOptions.TargetOptions.push(target[j])
          }
        }
        if (!filterOptions.DiagnosisOptions.includes(data[i].Participant.Diagnosis)) {
          filterOptions.DiagnosisOptions.push(data[i].Participant.Diagnosis)
        }

        collectiveData.push({
          ...data[i].Participant,
          Recordings: data.filter((a) => a.ParticipantId == data[i].ParticipantId),
          ElectrodeTypes: electrodes,
          Targets: target
        });
      }
    }

    collectiveData.sort((a,b) => {
      return a.Name.localeCompare(b.Name);
    });

    setFilterOptions({...filterOptions})
    setParticipantData(collectiveData);
  }, [data]);
  
  React.useEffect(() => {
    var collectiveData = [];
    for (var i = 0; i < participantData.length; i++) {
      if (filterOptions.Keyword.length > 0) {
        if (!participantData[i].Name.toLowerCase().includes(filterOptions.Keyword.toLowerCase()) && !participantData[i].Id.toLowerCase().includes(filterOptions.Keyword.toLowerCase())) {
          continue;
        }
      }
      
      let data = {...participantData[i], state: false};

      let toInclude = true;
      if (filterOptions.Diagnosis.length > 0) {
        if (!filterOptions.Diagnosis.includes(participantData[i].Diagnosis)) {
          toInclude = false;
          continue;
        }
      }
      
      if (filterOptions.Electrodes.length > 0) {
        toInclude = false;
        for (let j in participantData[i].ElectrodeTypes) {
          if (filterOptions.Electrodes.includes(participantData[i].ElectrodeTypes[j])) {
            toInclude = true;
          }
        }
        if (!toInclude) continue;

        data.Recordings = data.Recordings.filter((a) => {
          for (let j in data.DBSDevices) {
            for (let k in data.DBSDevices[j].Electrodes) {
              if (a.Contact.startsWith(data.DBSDevices[j].Electrodes[k].Target)) {
                if (filterOptions.Electrodes.includes(data.DBSDevices[j].Electrodes[k].Type)) return true;
              }
            }
          }
          return false;
        });
      }

      if (filterOptions.Targets.length > 0) {
        toInclude = false;
        for (let j in participantData[i].Targets) {
          if (filterOptions.Targets.includes(participantData[i].Targets[j])) {
            toInclude = true;
          }
        }
        if (!toInclude) continue;
        
        data.Recordings = data.Recordings.filter((a) => {
          for (let j in data.DBSDevices) {
            for (let k in data.DBSDevices[j].Electrodes) {
              if (a.Contact.startsWith(data.DBSDevices[j].Electrodes[k].Target)) {
                if (filterOptions.Targets.includes(data.DBSDevices[j].Electrodes[k].Target.split(" ")[1])) return true;
              }
            }
          }
          return false;
        });
      }

      collectiveData.push(data);
    }

    setDisplayData(collectiveData);
  }, [participantData, filterOptions]);
  
  const setViewDate = (date) => {
    setSelectedDate(date);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      collectiveData.push({...data[i], 
      state: false});
    }
    setDisplayData(collectiveData);
  };

  const exportTable = () => {
      var csvData = "Id,Diagnosis,Date,Target,Therapy,StimulationArtifacts,Gamma Detected,First Amplitude with Gamma,Max Gamma Power (95%CI)\n";
      for (let i in displayData) {
        for (let j in displayData[i].Recordings) {
          csvData += displayData[i].Id + "," + displayData[i].Diagnosis + "," + displayData[i].Recordings[j].Date + "," + displayData[i].Recordings[j].Contact + "," + displayData[i].Recordings[j].TherapyParameters + ",";
          csvData += (displayData[i].Recordings[j].StimulationCorrelation.PercentSignificant > 70 ? "TRUE," : "FALSE,");
          csvData += (displayData[i].Recordings[j].FTGStats.FirstAppearance > 0 ? "TRUE," : "FALSE,");
          csvData += (displayData[i].Recordings[j].FTGStats.FirstAppearance > 0 ? displayData[i].Recordings[j].FTGStats.FirstAppearance.toFixed(1) : "") + ",";
          csvData += (displayData[i].Recordings[j].FTGStats.FirstAppearance > 0 ? (displayData[i].Recordings[j].FTGStats.MaxGamma[0].toFixed(2) + " - " + displayData[i].Recordings[j].FTGStats.MaxGamma[1].toFixed(2)) : "") + ",";
          csvData += "\n";
        }
      }

      var downloader = document.createElement('a');
      downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
      downloader.target = '_blank';
      downloader.download = 'SpectralAnalysisExamination.csv';
      downloader.click();
  }

  const exportTableRaw = () => {
      let downloader = document.createElement('a');
      downloader.href = SessionController.getDownloadLink("/api/queryGroupAnalysis", {
        AnalysisName: "ExtractSpectralFeaturesDuringStimulation"
      });
      downloader.download = 'SpectralAnalysisExamination.pkl';
      downloader.target = '_blank';
      downloader.click();
  }

  return useMemo(() => (
    <>
      <MDBox px={2} style={{overflowX: "auto", maxHeight: "100vh"}}>
        <MDBox display="flex" flexDirection="row" justifyContent="space-between" alignItems="start" style={{marginBottom: 10}}>
          <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportTable()}>
            {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
          </MDButton>
          <MDButton size="large" variant="contained" color="secondary" style={{marginBottom: 3}} onClick={() => exportTableRaw()}>
            {"Export Raw Data"}
          </MDButton>
        </MDBox>
        <Table size="large" style={{marginTop: 20, display: "block", height: "fit-content"}}>
          <TableHead sx={{display: "table-header-group", position: "sticky", top: 0, zIndex: 1}}>
            <TableRow sx={{background: "white"}}>
              <TableCell variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Name"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "15%", minWidth: 150, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Diagnosis"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "20%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Electrode Type"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "10%", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Targets"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "25%", minWidth: 300, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"This is what we called, Rainbow"}
                </MDTypography>
              </TableCell>
              <TableCell variant="head" style={{width: "25%", minWidth: 300, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>{}}>
                  {"Stimulation Induced Gamma-Change"}
                </MDTypography>
              </TableCell>
            </TableRow>
            <TableRow sx={{background: "white"}}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}} >
                <MDInput label={"Search for Recording"} value={filterOptions.Keyword} 
                          onChange={(value) => setFilterOptions({...filterOptions, Keyword: value.target.value})} fullWidth 
                          sx={{marginRight: {xs: 0, sm: 3}, marginBottom: {xs: 3, sm: 0}}}/>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDBox style={{display: "flex", flexDirection: "column"}}>
                  <Autocomplete
                    fullWidth multiple
                    value={filterOptions.Diagnosis}
                    options={filterOptions.DiagnosisOptions}
                    onChange={(event, value) => setFilterOptions({...filterOptions, Diagnosis: value})}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        label={"Filter by Diagnosis Type"}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                </MDBox>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDBox style={{display: "flex", flexDirection: "column"}}>
                  <Autocomplete
                    fullWidth multiple
                    value={filterOptions.Electrodes}
                    options={filterOptions.ElectrodeOptions}
                    onChange={(event, value) => setFilterOptions({...filterOptions, Electrodes: value})}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        label={"Filter by Electrode Type"}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                </MDBox>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDBox style={{display: "flex", flexDirection: "column"}}>
                  <Autocomplete
                    fullWidth multiple
                    value={filterOptions.Targets}
                    options={filterOptions.TargetOptions}
                    onChange={(event, value) => setFilterOptions({...filterOptions, Targets: value})}
                    renderInput={(params) => (
                      <FormField
                        {...params}
                        label={"Filter by Targets"}
                        InputLabelProps={{ shrink: true }}
                      />
                    )}
                  />
                </MDBox>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDBox style={{display: "flex", flexDirection: "column"}}>
                  
                </MDBox>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayData.map((participant) => {
              let GammaInfo = [];
              for (let i in participant.Recordings) {
                if (participant.Recordings[i].FTGStats.FirstAppearance > 0) {
                  GammaInfo.push({
                    Therapy: participant.Recordings[i].TherapyParameters,
                    Contact: participant.Recordings[i].Contact,
                    MaxGamma: participant.Recordings[i].FTGStats.MaxGamma
                  })
                } 
              }
              
              let RainbowInfo = [];
              for (let i in participant.Recordings) {
                if (participant.Recordings[i].StimulationCorrelation.PercentSignificant > 70) {
                  RainbowInfo.push({
                    Therapy: participant.Recordings[i].TherapyParameters,
                    Contact: participant.Recordings[i].Contact,
                    Rainbow: participant.Recordings[i].StimulationCorrelation.MeanSlope.toFixed(2) + " (" + participant.Recordings[i].StimulationCorrelation.PercentSignificant.toFixed(2) + "%)"
                  });
                }
              }

              return (
                <TableRow key={participant.Id} onClick={() => getRecordingData(participant.Id)}>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}} >
                    <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={15} fontWeight={"bold"}>
                      {participant.Name}
                    </MDTypography>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {participant.Diagnosis}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {participant.ElectrodeTypes.join(" | ")}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {participant.Targets.join(" - ")}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    {RainbowInfo.map((a) => {
                      return <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {a.Contact + " " + a.Therapy}
                      </MDTypography>
                      <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {a.Rainbow}
                      </MDTypography>
                    </MDBox>
                    })}
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    {GammaInfo.map((a) => {
                      return <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {a.Contact + " " + a.Therapy}
                      </MDTypography>
                      <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {a.MaxGamma[0].toFixed(2) + " - " + a.MaxGamma[1].toFixed(2)}
                      </MDTypography>
                    </MDBox>
                    })}
                  </TableCell>
                </TableRow>
                )
            })}
          </TableBody>
        </Table>
      </MDBox>
    </>
  ), [data, showTable, displayData, newGroupView, editRecordingName]);
}

export default ParticipantListTable;