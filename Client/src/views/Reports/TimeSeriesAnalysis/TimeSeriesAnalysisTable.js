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
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TextField,
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

function TimeSeriesAnalysisTable({data, getRecordingData, updateRecordingData, addRecordingData, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [showTable, setShowTable] = React.useState(true);
  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  const [activeRecording, setActiveRecording] = React.useState([]);
  
  const [filterOptions, setFilterOptions] = React.useState({Type: "", Keyword: "", TypeOptions: []});
  const [displayData, setDisplayData] = React.useState([]);
  const [editRecordingName, setEditRecordingName] = React.useState({show: false, name: "", tags: [], analysisId: ""});

  const tableHeader = [{
    title: "Recording Time",
    minWidth: 100,
    width: "30%"
  },{
    title: "Recording Tags", 
    minWidth: 200,
    width: "15%"
  },{
    title: "Recording Channels", 
    minWidth: 200,
    width: "25%"
  },{
    title: "Associated Therapy", 
    minWidth: 200,
    width: "25%"
  },{
    title: "Recording Duration", 
    minWidth: 200,
    width: "10%"
  }]

  React.useEffect(() => {
    var uniqueDates = [];
    let typeOptions = ["All"]; 
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
      })

      if (!uniqueDates.map((a) => a.label).includes(dateString)) uniqueDates.push({
        label: dateString,
        value: data[i].Date
      });

      if (!typeOptions.includes(data[i].Type)) typeOptions.push(data[i].Type);
    }

    if (uniqueDates.length > 0) {
      setAvailableDates(uniqueDates.sort((a,b) => b.value - a.value));
      setViewDate(uniqueDates[0]);
      setFilterOptions({TypeOptions: typeOptions, Type: "All", Keyword: ""})
    }
  }, [data]);
  
  React.useEffect(() => {
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
      })

      let filterState = dateString == selectedDate.label && (data[i].Type == filterOptions.Type || filterOptions.Type == "All");
      if (filterState) {
        if (filterOptions.Keyword.length > 0) {
          let contents = filterOptions.Keyword.split(" ");
          for (let content of contents) {
            const optionLower = content.toLowerCase();
            filterState = filterState && (
              data[i].Type.toLowerCase().includes(optionLower) || 
              data[i].Name.toLowerCase().includes(optionLower) || 
              data[i].Id.toLowerCase().includes(optionLower)
            );
          }
        }
        
        if (filterState) {
          collectiveData.push({...data[i], 
          state: false});
        }
      }
    }
    setDisplayData(collectiveData);
  }, [filterOptions]);
  
  const setViewDate = (date) => {
    setSelectedDate(date);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      const dateString = new Date(data[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(data[i].Timezone),
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
      })

      if (dateString == date.label) {
        collectiveData.push({...data[i],
        state: false});
      }
    }
    setDisplayData(collectiveData);
  };

  const setStimMode = (recordingID, index, event) => {
    for (var i in displayData) {
      if (displayData[i].RecordingIDs == recordingID) {
        displayData[i].ContactType[index] = event.target.value;
        SessionController.query("/api/updateBrainSenseStream", {
          requestData: displayData[i].DeviceID,
          updateRecordingContactType: recordingID,
          contactIndex: index,
          contactType: event.target.value
        }).then((response) => {
          setDisplayData([...displayData]);
        }).catch((error) => {
          console.log(error);
        });
      }
    }
  }
  
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
                label={"Filter by Recording Type"}
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
                      {col.title}
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
                return <TableRow key={analysis.Id}>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDTypography variant="h5" style={{marginBottom: 0}} fontSize={18} fontWeight={"bold"}>
                      {analysis.Name}
                    </MDTypography>
                    <MDTypography variant="h5" fontSize={13} style={{marginBottom: 0}}>
                      {new Date(analysis.Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(analysis.Timezone),
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit"
                      })}
                    </MDTypography>
                    <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                      {analysis.Type}
                    </MDTypography>
                    <MDButton variant={"contained"} color="secondary" onClick={() => {
                      if (analysis.Therapy) {
                        setEditRecordingName({show: true, analysisId: [analysis.Id, analysis.Therapy[0].Id], tags: analysis.Metadata.Tags, name: analysis.Name})
                      } else {
                        setEditRecordingName({show: true, analysisId: [analysis.Id], tags: analysis.Metadata.Tags, name: analysis.Name})
                      }
                    }} style={{width: 200, padding: 0, marginTop: 3}} fullWidth>
                      {"Rename Recording"}
                    </MDButton>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column", justifyContent: "center"}}>
                    {analysis.Metadata.Tags ? analysis.Metadata.Tags.map((a) => (
                      <MDBadge badgeContent={a} color={"success"} size={"sm"} container />
                    )) : null} 
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      {analysis.Metadata.ChannelNames.filter((a,i) => i < 6).map((a) => (
                        <MDTypography key={a} variant="h6" fontSize={12} style={{marginBottom: 0}}>
                          {a}
                        </MDTypography>
                      ))} 
                      {analysis.Metadata.ChannelNames.length > 6 ? (
                        <MDTypography variant="h6" fontSize={12} style={{marginBottom: 0}}>
                          {"... Total "}{analysis.Metadata.ChannelNames.length.toFixed(0)}{" Channels"}
                        </MDTypography>
                      ) : null}
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                    {analysis.Therapy ? analysis.Therapy.map((a, i) => (
                      <MDBox key={i} style={{display: "flex", flexDirection: "column", marginTop: i == 0 ? 0 : 10}}>
                      <MDTypography variant="subtitle" fontSize={12} style={{marginBottom: 0}}>
                        {a.Contact}{" "}{a.SegmentMode}{": "}
                      </MDTypography>
                      <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                        {a.Frequency.toFixed(1)}{" Hz "}{a.Pulsewidth.toFixed(1)}{" μSec"}
                      </MDTypography>
                      <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                        {a.Amplitudes[0].toFixed(1)}{" - "}{a.Amplitudes[1].toFixed(1)}{" mA"}
                      </MDTypography>
                      </MDBox>
                    )) : (
                      <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                        {"No Therapy Data"}
                      </MDTypography>
                    )} 
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDBox style={{display: "flex", flexDirection: "column"}}>
                      <MDTypography variant="p" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                        {analysis.Metadata.Duration.toFixed(0)}{" seconds"}
                      </MDTypography>
                    </MDBox>
                  </TableCell>
                  <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                    <MDButton variant={"contained"} color="info" disabled={activeRecording.includes(analysis.Id)} onClick={() => {
                      getRecordingData([analysis]);
                      setActiveRecording([analysis.Id]);
                      setShowTable(false);
                    }} style={{width: 100, padding: 0, marginTop: 3}} fullWidth>
                      {dictionary.ParticipantOverview.ParticipantInformation.View[language]}
                    </MDButton>
                    <MDButton variant={"contained"} color="warning" disabled={activeRecording.includes(analysis.Id)} onClick={() => {
                      addRecordingData(analysis);
                      setActiveRecording((ids) => ids.includes(analysis.Id) ? ids : [...ids, analysis.Id]);
                      //setShowTable(false);
                    }} style={{width: 100, padding: 0, marginTop: 3}} fullWidth>
                      {"Add To View"}
                    </MDButton>
                    
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
          {showTable ? "Hide Available Recordings" : "Show Available Recordings"}
        </MDButton>
      </MDBox>
    </>
  ), [data, showTable, activeRecording, editRecordingName, displayData]);
}

export default TimeSeriesAnalysisTable;