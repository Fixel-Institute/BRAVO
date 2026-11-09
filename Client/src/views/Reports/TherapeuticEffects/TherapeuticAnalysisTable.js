/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useMemo } from "react"

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
import MultipleRecordingSelect from "./MultipleRecordingSelect";

function TherapeuticAnalysisTable({data, recordings, getRecordingData, updateRecordingData, addNewAnalysis, deleteAnalysis, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [showTable, setShowTable] = React.useState(true);
  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  
  const [filterOptions, setFilterOptions] = React.useState({Type: "", Keyword: "", TypeOptions: []});
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
    var uniqueDates = [];
    let typeOptions = ["All"]; 
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Metadata.Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZoneName: "longGeneric"
      })

      if (!uniqueDates.map((a) => a.label).includes(dateString)) uniqueDates.push({
        label: dateString,
        value: data[i].Date
      });

      if (!typeOptions.includes(data[i].Type)) typeOptions.push(data[i].Type);
    }

    if (uniqueDates.length > 0) {
      setAvailableDates(uniqueDates.sort((a,b) => a.value - b.value));
      setViewDate(uniqueDates[0]);
      setFilterOptions({TypeOptions: typeOptions, Type: "All", Keyword: ""})
    }
  }, [data]);
  
  React.useEffect(() => {
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Metadata.Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZoneName: "longGeneric"
      })

      let filterState = dateString == selectedDate.label && (data[i].Type == filterOptions.Type || filterOptions.Type == "All");
      if (filterState) {
        let recordingList = recordings.filter((a) => data[i].DataId.includes(a.Id))
        if (filterOptions.Keyword.length > 0) {
          let contents = filterOptions.Keyword.split(" ");
          for (let content of contents) {
            if (!data[i].Metadata.Tags) {
              data[i].Metadata.Tags = [];
            }

            const optionLower = content.toLowerCase();
            filterState = filterState && (
              data[i].Type.toLowerCase().includes(optionLower) || 
              data[i].Name.toLowerCase().includes(optionLower) || 
              data[i].Id.toLowerCase().includes(optionLower) || 
              recordingList.filter((b) => b.Metadata.ChannelNames.filter((a) => a.toLowerCase().includes(optionLower)).length > 0).length > 0 || 
              data[i].Metadata.Tags.filter((b) => b.toLowerCase().includes(optionLower)).length > 0
            );

          }
        }
        
        if (filterState) {
          collectiveData.push({...data[i], 
            Recordings: recordingList,
          state: false});
        }
      }
    }
    
    setDisplayData(collectiveData);
  }, [data, filterOptions]);
  
  const setViewDate = (date) => {
    setSelectedDate(date);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Metadata.Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZoneName: "longGeneric"
      })

      if (dateString == date.label) {
        collectiveData.push({...data[i], 
          Recordings: recordings.filter((a) => data[i].DataId.includes(a.Id)),
        state: false});
      }
    }
    setDisplayData(collectiveData);
  };

  const toggleSelection = (value, timestamp) => {
    for (var i in displayData) {
      if (displayData[i].Timestamp == timestamp || !timestamp) {
        displayData[i].state = value;
      }
    }
    setDisplayData([...displayData]);
  };

  const compareSelected = () => {
    let recordingList = [];
    for (var i in displayData) {
      if (displayData[i].state) {
        recordingList.push(displayData[i].RecordingID);
      }
    }
    getRecordingData(recordingList);
  };

  return useMemo(() => (
    <>
      <MDBox p={2}>
        <Autocomplete
          value={selectedDate}
          options={availableDates}
          onChange={(event, value) => setViewDate(value)}
          isOptionEqualToValue={(option, value) => {
            return option.label === value.label;
          }}
          renderOption={(props, option) => <li {...props}>{option.label}</li>}
          renderInput={(params) => (
            <FormField
              {...params}
              label={dictionary.TherapeuticAnalysis.Table.TableTitle[language]}
              InputLabelProps={{ shrink: true }}
            />
          )}
        />
      </MDBox>
      <Collapse in={showTable} >
        <MDBox p={2} sx={{display: "flex", flexDirection: {xs: "column", sm: "row"}, justifyContent: "space-between"}}>
          <MDInput label={"Search for Recording"} value={filterOptions.Keyword} onChange={(value) => setFilterOptions({...filterOptions, Keyword: value.target.value})} fullWidth sx={{marginRight: {xs: 0, sm: 3}, marginBottom: {xs: 3, sm: 0}}}/>
          <Autocomplete
            fullWidth
            value={filterOptions.Type}
            options={filterOptions.TypeOptions}
            onChange={(event, value) => setFilterOptions({...filterOptions, Type: value})}
            renderInput={(params) => (
              <FormField
                {...params}
                label={"Filter by Analysis Type"}
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </MDBox>
        <MDBox style={{overflowX: "auto", maxHeight: "60vh"}}>
          <Table size="large" style={{marginTop: 20, display: "block", height: "fit-content"}}>
            <TableHead sx={{display: "table-header-group", position: "sticky", top: 0, zIndex: 1}}>
              <TableRow sx={{background: "white"}}>
                {tableHeader.map((col) => (
                  <TableCell key={col.title} variant="head" style={{width: col.width, minWidth: col.minWidth, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                    <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                      {dictionary.TherapeuticAnalysis.Table[col.title] ? dictionary.TherapeuticAnalysis.Table[col.title][language] : col.title}
                    </MDTypography>
                  </TableCell>
                ))}
                <TableCell key={"viewedit"} variant="head" style={{width: "100px", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>{" "}</MDTypography>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displayData.sort((a,b) => a.Date - b.Date).map((analysis) => {
                analysis.RecordingChannels = []
                analysis.Therapy = []
                for (let i in analysis.DataId) {
                  const recording = recordings.filter((a) => a.Id == analysis.DataId[i])[0];
                  if (recording.Therapy) {
                    analysis.Therapy.push(...recording.Therapy);
                  } else {
                    analysis.RecordingChannels.push(...recording.Metadata.ChannelNames);
                  }
                }
                
                analysis.RecordingChannels = [...new Set(analysis.RecordingChannels)];
                analysis.Therapy = Array.from(new Set(analysis.Therapy.map((a) => JSON.stringify(a))), JSON.parse)
                return <TableRow key={analysis.Id}>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={18} fontWeight={"bold"}>
                      {analysis.Name}
                    </MDTypography>
                    <MDTypography variant="h5" fontSize={13} style={{marginBottom: 0}}>
                      {new Date(analysis.Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(analysis.Metadata.Timezone),
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        timeZoneName: "longGeneric"
                      })}
                    </MDTypography>
                    <MDButton variant={"contained"} color="secondary" onClick={() => {
                      setEditRecordingName({show: true, analysisId: analysis.Id, tags: analysis.Metadata.Tags, therapy: analysis.Therapy, name: analysis.Name})
                    }} style={{width: 200, padding: 0, marginTop: 3}} fullWidth>
                      {"Edit Recording"}
                    </MDButton>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                    {analysis.Metadata.Tags ? analysis.Metadata.Tags.map((a) => (
                      <MDBadge badgeContent={a} color={"success"} size={"sm"} container sx={{marginLeft: 1}} />
                    )) : null} 
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                    {analysis.RecordingChannels.map((a) => (
                      <MDTypography key={a} variant="h6" fontSize={15} style={{marginBottom: 0}}>
                        {a}
                      </MDTypography>
                    ))} 
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                    {analysis.Therapy.map((a, i) => (
                      <MDBox key={i} style={{display: "flex", flexDirection: "column", marginTop: i == 0 ? 0 : 10}}>
                      <MDTypography variant="subtitle" fontSize={12} style={{marginBottom: 0}}>
                        {a.Contact}{" "}{a.SegmentMode}{": "}
                      </MDTypography>
                      <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                        {a.Frequency.toFixed(1)}{" Hz "}{a.Pulsewidth.toFixed(1)}{" μSec"}
                      </MDTypography>
                      </MDBox>
                    ))} 
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                      {analysis.Recordings[0].Metadata.Duration.toFixed(2)}{" " + dictionary.Time.Seconds[language]} <br/>
                    </MDTypography>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDButton variant={"contained"} color="info" onClick={() => {
                      getRecordingData(analysis);
                      setShowTable(false);
                    }} style={{width: 100, padding: 0, marginTop: 3}} fullWidth>
                      {dictionary.ParticipantOverview.ParticipantInformation.View[language]}
                    </MDButton>
                    {analysis.Type == "TherapeuticAnalysis" ? (
                      <MDButton variant={"contained"} color="primary" onClick={() => {
                        deleteAnalysis(analysis.Id)
                      }} style={{width: 100, padding: 0, marginTop: 3}} fullWidth>
                        {"Remove"}
                      </MDButton>
                    ) : null}
                  </TableCell>
                </TableRow>
              })}
            </TableBody>
          </Table>
          <Dialog open={editRecordingName.show} onClose={() => setEditRecordingName({...editRecordingName, show: false})} PaperProps={{sx: {minWidth: 600}}}>
            <MDBox px={2} pt={2} display={"flex"} flexDirection={"row"} justifyContent={"center"} alignItems={"center"}>
              <MDTypography variant="h5">
                {"Edit Recording Information"}
              </MDTypography>
            </MDBox>
            <DialogContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    id="recording-name"
                    name="recording-name"
                    variant="standard"
                    margin="dense"
                    label="Recording Name"
                    placeholder="Recording Name"
                    value={editRecordingName.name}
                    onChange={(event) => setEditRecordingName({...editRecordingName, name: event.target.value})}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12}>
                  <Autocomplete
                    multiple freeSolo
                    value={editRecordingName.tags}
                    options={[]}
                    onChange={(event, newValue) => setEditRecordingName({...editRecordingName, tags: newValue})}
                    renderInput={(params) => {
                      return <TextField
                        {...params}
                        variant="standard" id="recording_tags"
                        placeholder={dictionary.ParticipantOverview.TagNames[language]}
                      />
                    }}
                  />
                </Grid>
                {editRecordingName.therapy.map((lead, index) => (
                  <Grid key={lead.Contact} item xs={6}>
                    <Autocomplete
                      fullWidth value={lead.SegmentMode}
                      options={["Ring", "Segment A", "Segment B", "Segment C", "Segment AB", "Segment BC", "Segment AC"]}
                      onChange={(event, value) => setEditRecordingName((editRecordingName) => {
                        editRecordingName.therapy[index].SegmentMode = value;
                        return {...editRecordingName};
                      })}
                      renderInput={(params) => (
                        <FormField
                          {...params}
                          label={lead.Contact + " (Default Ring)"}
                          InputLabelProps={{ shrink: true }}
                        />
                      )}
                    />
                  </Grid>
                ))}
              </Grid>
            </DialogContent>
            <DialogActions>
              <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
                <MDButton color={"secondary"} onClick={() => setEditRecordingName({...editRecordingName, show: false})}>
                  {"Cancel"}
                </MDButton>
                <MDButton color={"info"} onClick={() => updateRecordingData(editRecordingName).then(() => {
                  setFilterOptions({...filterOptions})
                  setEditRecordingName({...editRecordingName, show: false});
                })} style={{marginLeft: 10}}>
                  {"Update"}
                </MDButton>
              </MDBox>
            </DialogActions>
          </Dialog>
        </MDBox>
      </Collapse>
      <MDBox p={2}>
        <MDButton variant={"contained"} color="info" onClick={() => setShowTable(!showTable)} >
          {showTable ? "Hide Table" : "Show Table"}
        </MDButton>
        <MDButton variant={"contained"} color="primary" onClick={() => setNewGroupView({show: true, timeseries: [], therapies: []})} style={{marginLeft: 5}}>
          {"Multi-Recording View"}
        </MDButton>
      </MDBox>

      <Dialog open={newGroupView.show} onClose={() => setNewGroupView({...newGroupView, show: false})} PaperProps={{sx: {minWidth: 900}}}>
        <MDBox px={2} pt={2} display={"flex"} flexDirection={"row"} justifyContent={"center"} alignItems={"center"}>
          <MDTypography variant="h5">
            {"New Therapeutic Analysis"}
          </MDTypography>
        </MDBox>
        <MultipleRecordingSelect recordings={recordings.filter((a) => a.Metadata.Duration > 2)} existingGroups={[]} name={""} currentSelect={[]} onSelectRecording={(selected, name) => {
          const selectedRecording = recordings.filter((a) => selected.includes(a.Id));
          addNewAnalysis({
            show: false, timeseries: selectedRecording.filter((a) => ["MedtronicBrainSenseTimeDomain"].includes(a.Type)), 
            therapies: selectedRecording.filter((a) => ["MedtronicBrainSensePowerDomain"].includes(a.Type))
          });
          setNewGroupView({...newGroupView, show: false});
        }} onClose={() => setNewGroupView({...newGroupView, show: false})} />
      </Dialog>
    </>
  ), [data, showTable, displayData, newGroupView, editRecordingName]);
}

export default TherapeuticAnalysisTable;