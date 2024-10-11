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

function TherapeuticAnalysisTable({data, recordings, getRecordingData, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  
  const [displayData, setDisplayData] = React.useState([]);

  const tableHeader = [{
    title: "StreamingTableDate",
    minWidth: 100,
    width: "30%"
  },{
    title: "StreamingTableChannels", 
    minWidth: 200,
    width: "25%"
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
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["date"]*1000);
      var found = false
      for (var date of uniqueDates) {
        if (date.value == timestruct.toLocaleDateString(language)) {
          found = true;
          break;
        }
      }
      if (!found) {
        uniqueDates.push({
          time: data[i]["date"]*1000,
          value: timestruct.toLocaleDateString(language),
          label: timestruct.toLocaleDateString(language)
        });
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
      var timestruct = new Date(data[i]["date"]*1000);
      if (timestruct.toLocaleDateString(language) == date.value) {
        collectiveData.push({...data[i], 
          recordings: recordings.filter((a) => data[i].recordings.includes(a.uid)),
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
              label={dictionary.TherapeuticAnalysis.Table.TableTitle[language]}
              InputLabelProps={{ shrink: true }}
            />
          )}
        />
      </MDBox>
      <MDBox style={{overflowX: "auto"}}>
        <Table size="large" style={{marginTop: 20}}>
          <TableHead sx={{display: "table-header-group"}}>
            <TableRow>
              {tableHeader.map((col) => (
                <TableCell key={col.title} variant="head" style={{width: col.width, minWidth: col.minWidth, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionary.TherapeuticAnalysis.Table[col.title][language]}
                  </MDTypography>
                </TableCell>
              ))}
              <TableCell key={"viewedit"} variant="head" style={{width: "100px", minWidth: 100, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>{" "}</MDTypography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayData.map((analysis) => {
              return <TableRow key={analysis.uid}>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="h5" fontSize={15} style={{marginBottom: 0}}>
                    {new Date(analysis.date*1000).toLocaleString(language)}
                  </MDTypography>
                  <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                    {analysis.name}
                  </MDTypography>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox style={{display: "flex", flexDirection: "column"}}>
                    
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox style={{display: "flex", flexDirection: "column"}}>
                    
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                    {analysis.duration.toFixed(2)}{" " + dictionary.Time.Seconds[language]} <br/>
                  </MDTypography>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDButton variant={"contained"} color="info" onClick={() => getRecordingData(analysis.uid)} style={{padding: 0}}>
                    {dictionary.ParticipantOverview.ParticipantInformation.View[language]}
                  </MDButton>
                </TableCell>
              </TableRow>
            })}
          </TableBody>
        </Table>
      </MDBox>
    </>
  );
}

export default TherapeuticAnalysisTable;