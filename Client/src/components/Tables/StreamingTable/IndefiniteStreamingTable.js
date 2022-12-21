import React from "react"
import { useHistory } from "react-router-dom";

import {
  Autocomplete,
  Box,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Switch,
  IconButton,
  Tooltip,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";

import MDBox from "components/MDBox/index.js";
import FormField from "components/MDInput/FormField.js";
import MDTypography from "components/MDTypography";
import PatientTablePagination from "../PatientTable/PatientTablePagination.js";
import MDButton from "components/MDButton/index.js";

function IndefiniteStreamingTable({data, requestDataForRender, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;
  
  const [viewSessions, setViewSessions] = React.useState([]);
  const [dateOfView, setDateOfView] = React.useState(null);
  const [displayData, setDisplayData] = React.useState([]);

  const tableHeader = [{
    title: "IndefiniteStreamTableCheck",
    minWidth: 50,
    width: "10%"
  },{
    title: "IndefiniteStreamTableDate",
    minWidth: 100,
    width: "50%"
  },{
    title: "IndefiniteStreamTableDuration", 
    minWidth: 50,
    width: "40%"
  }];

  React.useEffect(() => {
    var uniqueSession = [];
    var existingDates = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      const dateString = timestruct.toLocaleDateString(language);

      var found = false
      for (var session of uniqueSession) {
        if (existingDates.includes(dateString) && session.device == data[i]["DeviceName"]) {
          found = true;
          break;
        }
      }
      if (!found) {
        existingDates.push(dateString);
        uniqueSession.push({
          timestamp: dateString,
          device: data[i]["DeviceName"],
          time: data[i]["Timestamp"],
          value: "[" + data[i]["DeviceName"] + "] " + dateString,
          label: "[" + data[i]["DeviceName"] + "] " + dateString
        });
      }
    }

    if (uniqueSession.length > 0) {
      setViewSessions(uniqueSession.sort((a,b) => b.time - a.time));
      setViewDate(uniqueSession[0])
    }

  }, [data]);

  const setViewDate = (value) => {
    setDateOfView(value)

    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      const dateString = timestruct.toLocaleDateString(language);

      if (dateString == value.timestamp && data[i]["DeviceName"] == value.device) {
        collectiveData.push(data[i]);
      }
    }
    setDisplayData(collectiveData);
  }

  const toggleSelection = (value, timestamp) => {
    for (var i in displayData) {
      if (displayData[i].Timestamp == timestamp) {
        displayData[i].state = value;
      }
    }
    setDisplayData([...displayData]);
  }

  return (
    <>
      <MDBox p={2}>
        <Autocomplete
          value={dateOfView}
          options={viewSessions}
          onChange={(event, value) => setViewDate(value)}
          getOptionLabel={(option) => {
            return option.label || "";
          }}
          renderInput={(params) => (
            <FormField
              {...params}
              label={dictionary.IndefiniteStreaming.Table.TableTitle[language]}
              InputLabelProps={{ shrink: true }}
            />
          )}
        />
      </MDBox>
      <MDBox style={{overflowX: "auto"}}>
        <Table size="large" style={{marginTop: 20}}>
          <TableHead sx={{display: "table-header-group"}}>
            <TableRow key={"headerrow"}>
            {tableHeader.map((col) => {
              return (
                <TableCell key={col.title} variant="head" style={{width: col.width, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionary.IndefiniteStreaming.Table[col.title][language]}
                  </MDTypography>
                </TableCell>
            )})}
            </TableRow>
          </TableHead>
          <TableBody>
            {displayData.map((recording) => {
              return <TableRow key={recording.Timestamp.toString()}>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <Switch value={recording.state} onChange={(event, value) => toggleSelection(value, recording.Timestamp)} />
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="h5" fontSize={15} style={{marginBottom: 0}}>
                    {new Date(recording.Timestamp*1000).toLocaleString(language)}
                  </MDTypography>
                  <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                    {recording.DeviceName}
                  </MDTypography>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography fontSize={15} style={{marginBottom: 0}}>
                    {recording.Duration.toFixed(2)} {" " + dictionary.Time.Seconds[language]}  
                  </MDTypography>
                </TableCell>
              </TableRow>
            })}
          </TableBody>
        </Table>
      </MDBox>
      <MDBox>
        <MDButton variant="outlined" color="info" style={{marginTop: 20, paddingTop: 10, paddingBottom: 5}} onClick={() => requestDataForRender(displayData)}>
          {dictionary.IndefiniteStreaming.Table.IndefiniteStreamTableRequestData[language]}
        </MDButton>
      </MDBox>
    </>
  );
}

// <Checkbox onClick={(event) => toggleSelection(event, recording.Timestamp)} />
export default IndefiniteStreamingTable;