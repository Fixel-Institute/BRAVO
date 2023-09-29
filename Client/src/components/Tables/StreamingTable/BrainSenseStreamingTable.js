/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react"
import { useHistory } from "react-router-dom";

import {
  Autocomplete,
  Box,
  FormControl,
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
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import FormField from "components/MDInput/FormField.js";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

function BrainSenseStreamingTable({data, getRecordingData, handleMerge, toggle, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [toggleMerge, setToggleMerge] = React.useState({show: false, merge: []});
  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  
  const [displayData, setDisplayData] = React.useState([]);

  const tableHeader = [{
    title: "StreamingTableDate",
    minWidth: 100,
    width: "30%"
  },{
    title: "StreamingTableLeftHemisphere", 
    minWidth: 200,
    width: "25%"
  },{
    title: "StreamingTableRightHemisphere", 
    minWidth: 200,
    width: "25%"
  },{
    title: "StreamingTableRecordingDuration",
    minWidth: 100,
    width: "15%"
  }]

  React.useEffect(() => {
    var uniqueDates = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      if (data[i].Duration >= 30) {
        var found = false
        for (var date of uniqueDates) {
          if (date.value == timestruct.toLocaleDateString(language)) {
            found = true;
            break;
          }
        }
        if (!found) {
          uniqueDates.push({
            time: data[i]["Timestamp"]*1000,
            value: timestruct.toLocaleDateString(language),
            label: timestruct.toLocaleDateString(language)
          });
        }
      }
    }

    if (uniqueDates.length > 0) {
      setAvailableDates(uniqueDates.sort((a,b) => b.time - a.time));
      setViewDate(uniqueDates[0]);
    }
  }, [data])
  
  const setViewDate = (date) => {
    setSelectedDate(date);
    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      if (timestruct.toLocaleDateString(language) == date.value && data[i].Duration >= (toggle ? 0 : 30)) {
        collectiveData.push({...data[i], state: false});
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

  return (
    <>
      <MDBox p={2}>
        <Autocomplete
          value={selectedDate}
          options={availableDates}
          onChange={(event, value) => setViewDate(value)}
          getOptionLabel={(option) => {
            return option.label || "";
          }}
          renderInput={(params) => (
            <FormField
              {...params}
              label={dictionary.BrainSenseStreaming.Table.TableTitle[language]}
              InputLabelProps={{ shrink: true }}
            />
          )}
        />
      </MDBox>
      <MDBox style={{overflowX: "auto"}}>
        <MDButton variant={"contained"} color={!toggleMerge.show ? "info" : "error"} style={{marginLeft: 10, display: "none"}} onClick={() => {
          if (toggleMerge.show) {
            if (toggleMerge.merge.length == 0) {
              setToggleMerge({merge: [], show: false});
              return;
            }

            handleMerge(toggleMerge).then(() => {
              setToggleMerge({merge: [], show: false});
            });
          } else {
            setToggleMerge({...toggleMerge, merge: [], show: true});
          }
        }}>
          {"Merge Recordings"}
        </MDButton>
        <Table size="large" style={{marginTop: 20}}>
          <TableHead sx={{display: "table-header-group"}}>
            <TableRow>
              {tableHeader.map((col) => (
                <TableCell key={col.title} variant="head" style={{width: col.width, minWidth: col.minWidth, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionary.BrainSenseStreaming.Table[col.title][language]}
                  </MDTypography>
                </TableCell>
              ))}
              <TableCell key={"viewedit"} variant="head" style={{width: "100px", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>{" "}</MDTypography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayData.map((recording) => {
              var leftHemisphere = [], rightHemisphere = [];
              for (var channel of recording.Channels) {
                const channelName = formatSegmentString(channel.Contacts);
                if (channel.Hemisphere.startsWith("Left")) {
                  const [side, target] = channel.Hemisphere.split(" ");
                  leftHemisphere.push(<MDBox key={channelName}>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {channel.CustomName!=channel.Hemisphere ? channel.CustomName : dictionaryLookup(dictionary.FigureStandardText, side, language) + " " + dictionaryLookup(dictionary.BrainRegions, target, language)}
                    </MDTypography>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {channelName} {recording.Therapy ? ("@ " + recording.Therapy.Left.RateInHertz + " Hz " + recording.Therapy.Left.PulseWidthInMicroSecond + " μS") : ""}
                    </MDTypography>
                  </MDBox>)
                } else {
                  const [side, target] = channel.Hemisphere.split(" ");
                  rightHemisphere.push(<MDBox key={channelName}>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {channel.CustomName!=channel.Hemisphere ? channel.CustomName : dictionaryLookup(dictionary.FigureStandardText, side, language) + " " + dictionaryLookup(dictionary.BrainRegions, target, language)}
                    </MDTypography>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {channelName} {recording.Therapy ? ("@ " + recording.Therapy.Left.RateInHertz + " Hz " + recording.Therapy.Left.PulseWidthInMicroSecond + " μS") : ""}
                    </MDTypography>
                  </MDBox>)
                }
              }

              return <TableRow key={recording.AnalysisID}>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="h5" fontSize={15} style={{marginBottom: 0}}>
                    {new Date(recording.Timestamp*1000).toLocaleString(language)}
                  </MDTypography>
                  <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                    {recording.DeviceName}
                  </MDTypography>
                  {toggleMerge.show ? (
                    <Checkbox label={"Merge"} style={{padding: 0}} onClick={() => {
                      if (!toggleMerge.merge.includes(recording.RecordingID)) {
                        setToggleMerge((toggleMerge) => {
                          toggleMerge.merge.push(recording.RecordingID);
                          return toggleMerge;
                        })
                      } else {
                        setToggleMerge((toggleMerge) => {
                          toggleMerge.merge = toggleMerge.merge.filter((id) => id != recording.RecordingID);
                          return toggleMerge;
                        })
                      }
                    }} />
                  ) : null}
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox style={{display: "flex", flexDirection: "column"}}>
                    {leftHemisphere ? (
                      <MDBox>
                        {leftHemisphere}
                        {recording.ContactType ? (
                          <FormControl sx={{
                            marginTop: 1
                          }} fullWidth>
                            <InputLabel id="left-hemisphere-stim-mode-label">
                              {dictionary.BrainSenseStreaming.Table.StimMode[language]}
                            </InputLabel>
                            <Select
                              labelId={"left-hemisphere-stim-mode-label"}
                              label={dictionary.BrainSenseStreaming.Table.StimMode[language]}
                              value={recording.ContactType[0]}
                              onChange={(event) => setStimMode(recording.RecordingIDs, 0, event)}
                              sx={{
                                paddingY: "6px"
                              }}
                            >
                              {recording.ContactTypes[0].map((value) => {
                                return <MenuItem key={value} value={value}> {dictionaryLookup(dictionary.Segments, value, language)} </MenuItem>
                              })}
                            </Select>
                          </FormControl>
                        ) : null}
                      </MDBox>
                    ) : null}
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  {rightHemisphere ? (
                    <MDBox>
                      {rightHemisphere}
                      {recording.ContactType ? (
                        <FormControl sx={{
                        marginTop: 1
                      }} fullWidth>
                        <InputLabel id="right-hemisphere-stim-mode-label">
                          {dictionary.BrainSenseStreaming.Table.StimMode[language]}
                        </InputLabel>
                        <Select
                          labelId={"right-hemisphere-stim-mode-label"}
                          label={dictionary.BrainSenseStreaming.Table.StimMode[language]}
                          value={recording.ContactType.length == 2 ? recording.ContactType[1] : recording.ContactType[0]}
                          onChange={(event) => setStimMode(recording.RecordingIDs, recording.ContactType.length == 2 ? 1 : 0, event)}
                          sx={{
                            paddingY: "6px"
                          }}
                        >
                          {recording.ContactType.length == 2 ? recording.ContactTypes[1].map((value) => {
                            return <MenuItem key={value} value={value}> {dictionaryLookup(dictionary.Segments, value, language)} </MenuItem>
                          }) : recording.ContactTypes[0].map((value) => {
                            return <MenuItem key={value} value={value}> {dictionaryLookup(dictionary.Segments, value, language)} </MenuItem>
                          })}
                        </Select>
                      </FormControl>
                      ) : null}
                    </MDBox>
                  ) : null}
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="p" fontSize={15} style={{marginBottom: 0}}>
                    {recording.Duration.toFixed(2)} {" " + dictionary.Time.Seconds[language]}  
                  </MDTypography>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDButton variant={"contained"} color="info" onClick={() => getRecordingData(recording.AnalysisID)} style={{padding: 0}}>
                      {dictionary.PatientOverview.PatientInformation.View[language]}
                  </MDButton>
                </TableCell>
              </TableRow>
            })}
          </TableBody>
        </Table>
      </MDBox>
      {toggle ? (
        <MDBox p={2}>
          <MDButton variant={"contained"} color="info" onClick={() => compareSelected()}>
            {dictionary.MultipleSegmentAnalysis.Table.Compare[language]}
          </MDButton>
        </MDBox>
      ) : null}
    </>
  );
}

export default BrainSenseStreamingTable;