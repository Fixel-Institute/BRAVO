import React from "react"
import { useHistory } from "react-router-dom";

import {
  Autocomplete,
  Box,
  Card,
  Grid,
  FormControl,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  InputLabel,
  IconButton,
  Select,
  MenuItem,
  LinearProgress,
  Tooltip,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import FormField from "components/MDInput/FormField.js";
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDProgress from "components/MDProgress";

function TherapeuticPredictionTable({data, getRecordingData, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, therapeuticPredictionTableDate } = controller;

  const [selectedDate, setSelectedDate] = React.useState([]);
  const [availableDates, setAvailableDates] = React.useState([]);
  
  const [displayData, setDisplayData] = React.useState([]);
  const [optimalSettings, setOptimalSettings] = React.useState({});

  const tableHeader = [{
    title: "StreamingTableDate",
    minWidth: 100,
    width: "30%"
  },{
    title: "RecordingDetails", 
    minWidth: 200,
    width: "25%"
  },{
    title: "ModelOutcome", 
    minWidth: 200,
    width: "15%"
  },{
    title: "PredictedConfidence", 
    minWidth: 200,
    width: "35%"
  }]

  React.useEffect(() => {
    var uniqueDates = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);

      var found = false
      for (var date of uniqueDates) {
        if (date.value == timestruct.toLocaleDateString(language)) {
          found = true;
          break;
        }
      }
      if (!found) {
        uniqueDates.push({
          value: timestruct.toLocaleDateString(language),
          label: timestruct.toLocaleDateString(language)
        });
      }
    }

    if (uniqueDates.length > 0) {
      setAvailableDates(uniqueDates);
      if (!therapeuticPredictionTableDate) setViewDate(uniqueDates[0]);
    }
  }, [data]);
  
  const setViewDate = (date) => {
    //setSelectedDate(date);
    setContextState(dispatch, "therapeuticPredictionTableDate", date);

    var collectiveData = [];
    for (var i = 0; i < data.length; i++) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      if (timestruct.toLocaleDateString(language) == date.value) {
        collectiveData.push(data[i]);
      }
    }
    setDisplayData(collectiveData);
  };

  const setStimMode = (recordingID, index, event) => {
    for (var i in displayData) {
      if (displayData[i].RecordingID == recordingID) {
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
  };

  const extractOptimalSettings = (settings) => {
    var predictions = [];
    for (var i in settings) {
      for (var j in settings[i].Prediction) {
        if (!settings[i].Prediction[j].NoPrediction) {
          var stimulation = "-E01-E02";
          var midContact = (settings[i].Channels[j].Contacts[0] + settings[i].Channels[j].Contacts[1]) / 2;
          if (midContact != 1.5) {
            stimulation = `-E0${midContact}`;
          }

          predictions.push({
            ...settings[i].Prediction[j],
            contactType: settings[i].ContactType[j],
            channels: settings[i].Channels[j],
            stimContact: stimulation,
            therapy: settings[i].Channels[j].Hemisphere.startsWith("Left") ? settings[i].Therapy.Left : settings[i].Therapy.Right
          });
        }
      }
    }

    var finalResult = {};
    for (var type of ["Ring", "Segment"]) {
      for (var side of ["Left", "Right"]) {
        var targetRecordings = [];
  
        for (var i in predictions) {
          if (predictions[i].channels.Hemisphere.startsWith(side) && predictions[i].contactType.startsWith(type)) {
            targetRecordings.push(predictions[i]);
          }
        }
  
        if (targetRecordings.length > 0) {
          const bestGroup = getBestSettings(targetRecordings, type);
          finalResult[side + " " + type] = bestGroup;
        }
      }
    }
    
    setOptimalSettings({...finalResult});
  };

  const getBestSettings = (predictions, type) => {
    var bestPercent = 0;
    var therapy = {};
    for (var i in predictions) {
      if (predictions[i].Score > bestPercent) {
        bestPercent = predictions[i].Score;
        therapy["Frequency"] = predictions[i].therapy.RateInHertz;
        therapy["Pulsewidth"] = predictions[i].therapy.PulseWidthInMicroSecond;
        therapy["Amplitude"] = predictions[i].PredictedAmplitude;
        therapy["Range"] = predictions[i].AmplitudeRange;
      }
    }

    if (bestPercent < 0.5) {
      return null;
    }

    // Find all settings that reach the same prediction model accuracy.
    var goodModelFits = [];
    for (var i in predictions) {
      if (predictions[i].Score > (type == "Ring" ? bestPercent - 0.05 : bestPercent - 0.15)) {
        if (predictions[i].therapy.RateInHertz == therapy["Frequency"] && predictions[i].therapy.PulseWidthInMicroSecond == therapy["Pulsewidth"]) {
          goodModelFits.push(predictions[i]);
        }
      }
    }

    // If more than one exist, identify the ones with best beta desync (Ring)
    if (type == "Ring") {
      const bestBetaDesync = Math.max(...goodModelFits.map((value) => value.ChangesInPower));
      goodModelFits = goodModelFits.filter((value) => {
        return (value.ChangesInPower / bestBetaDesync) > 0.8;
      });
    }
    
    return {...therapy, 
      Amplitude: goodModelFits.map((value) => value.PredictedAmplitude),
      Range: goodModelFits.map((value) => value.AmplitudeRange),
      contactType: goodModelFits.map((value) => value.contactType),
      channels: goodModelFits[0].channels,
      stimContact: goodModelFits.map((value) => value.stimContact)
    };
  };

  React.useEffect(() => {
    if (displayData.length > 0) {
      extractOptimalSettings(displayData);
    }
  }, [displayData]);

  return (
    <>
      <MDBox p={2}>
        <Autocomplete
          value={therapeuticPredictionTableDate}
          options={availableDates}
          onChange={(event, value) => setViewDate(value)}
          getOptionLabel={(option) => {
            return option.label || "";
          }}
          isOptionEqualToValue={(option, value) => {
            return option.value == value.value;
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
      
      {displayData.length > 0 && Object.keys(optimalSettings).length > 0 ? (
        <MDBox>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Card sx={{width: "100%", background: "#a7ffeb"}}>
                <MDBox p={3}>
                  <MDTypography variant={"h2"} fontSize={20}>
                    {dictionary.TherapeuticPrediction.Table.SuggestedSettings[language]}
                  </MDTypography>
                </MDBox>
                <MDBox px={3} pb={3}>
                  <Grid container spacing={2}>
                    {["Left Ring", "Right Ring", "Left Segment", "Right Segment"].map((type) => {
                      if (!optimalSettings[type]) return null;
                      
                      const [side, target] = optimalSettings[type].channels.Hemisphere.split(" ");
                      return <Grid key={type} item xs={12} md={6} style={{marginBottom: 3}}>
                          <MDTypography variant="h6" color={"info"} fontSize={15} style={{marginBottom: 0}}>
                            {dictionaryLookup(dictionary.TherapeuticPrediction.Table, type, language)} 
                          </MDTypography>
                          <MDTypography variant={"h5"} fontSize={18}>
                            {dictionaryLookup(dictionary.FigureStandardText, side, language)} {dictionaryLookup(dictionary.BrainRegions, target, language)}
                          </MDTypography>
                          
                          <MDTypography variant={"h6"} fontSize={20} color={"error"}>
                            {optimalSettings[type].Frequency} {dictionary.FigureStandardUnit.Hertz[language]} {" "}
                            {optimalSettings[type].Pulsewidth} {dictionary.FigureStandardUnit.uS[language]}
                          </MDTypography>
                          {optimalSettings[type].stimContact.length == 1 ? (
                            <MDTypography variant={"h5"} fontSize={18} color={"primary"} >
                              {dictionary.TherapeuticPrediction.Table.Monopolar[language]} {" "} {optimalSettings[type].stimContact[0]} {" "}
                              {optimalSettings[type].Amplitude[0].toFixed(2)} {dictionary.FigureStandardUnit.mA[language]} {" "}
                              {"("}{optimalSettings[type].Range[0][0].toFixed(1)}-{optimalSettings[type].Range[0][1].toFixed(1)} {dictionary.FigureStandardUnit.mA[language]}{")"}
                            </MDTypography>
                          ) : (
                            <>
                              {optimalSettings[type].stimContact.map((value, index) => {
                                return <MDTypography key={index} variant={"h5"} fontSize={18} color={"primary"}>
                                  {optimalSettings[type].stimContact[index]} {" "} {optimalSettings[type].contactType[index]} {" "}
                                  {optimalSettings[type].Amplitude[index].toFixed(2)} {dictionary.FigureStandardUnit.mA[language]} {" "}
                                  {"("}{optimalSettings[type].Range[index][0].toFixed(1)}-{optimalSettings[type].Range[index][1].toFixed(1)} {dictionary.FigureStandardUnit.mA[language]}{")"}
                                </MDTypography>
                              })}
                            </>
                          )}
                        </Grid>
                    })}
                    {Object.keys(optimalSettings).filter((key) => optimalSettings[key]).length == 0 ? (
                      <Grid item xs={12} style={{marginBottom: 3}}>
                        <MDTypography variant={"h4"} fontSize={20} color={"primary"}>
                          {dictionary.TherapeuticPrediction.Table.NoOptimalSettings[language]}
                        </MDTypography>
                      </Grid>
                    ) : null}
                  </Grid>
                </MDBox>
              </Card>
            </Grid>
          </Grid>
        </MDBox>
      ) : null}

      <MDBox style={{overflowX: "auto"}}>
        <Table size="large" style={{marginTop: 20}}>
          <TableHead sx={{display: "table-header-group"}}>
            <TableRow>
              {tableHeader.map((col) => (
                <TableCell key={col.title} variant="head" style={{width: col.width, minWidth: col.minWidth, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionary.TherapeuticPrediction.Table[col.title][language]}
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
              var recordingDetails = null;
              var indexOfInterest = 0;
              for (var i in recording.Prediction) {
                if (!recording.Prediction[i].NoPrediction) {
                  const [side, target] = recording.Channels[i].Hemisphere.split(" ");
                  recordingDetails = <>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {dictionaryLookup(dictionary.FigureStandardText, side, language)} {dictionaryLookup(dictionary.BrainRegions, target, language)}
                    </MDTypography>
                    <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                      {formatSegmentString(recording.Channels[i].Contacts)}
                    </MDTypography>
                  </>;
                  indexOfInterest = i;
                  break;
                }
              }

              if (!recordingDetails) {
                return null;
              }

              const [side, target] = recording.Channels[indexOfInterest].Hemisphere.split(" ");
              
              return <TableRow key={recording.RecordingID}>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDTypography variant="h5" fontSize={15} style={{marginBottom: 0}}>
                    {new Date(recording.Timestamp*1000).toLocaleString(language)}
                  </MDTypography>
                  <MDTypography variant="h6" style={{marginBottom: 0}} fontSize={12} fontWeight={"bold"}>
                    {recording.DeviceName}
                  </MDTypography>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox style={{display: "flex", flexDirection: "column"}}>
                      {recordingDetails}
                      <FormControl sx={{
                        marginTop: 1
                      }} fullWidth>
                        <InputLabel id="left-hemisphere-stim-mode-label">
                          {dictionary.BrainSenseStreaming.Table.StimMode[language]}
                        </InputLabel>
                        <Select
                          labelId={"left-hemisphere-stim-mode-label"}
                          label={dictionary.BrainSenseStreaming.Table.StimMode[language]}
                          value={recording.ContactType[indexOfInterest]}
                          onChange={(event) => setStimMode(recording.RecordingID, 0, event)}
                          sx={{
                            paddingY: "6px"
                          }}
                        >
                          {recording.ContactTypes[0].map((value) => {
                            return <MenuItem key={value} value={value}> {dictionaryLookup(dictionary.Segments, value, language)} </MenuItem>
                          })}
                        </Select>
                      </FormControl>
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox sx={{ width: '100%' }}>
                    <MDTypography variant="h6">
                      {recording.Therapy[side].RateInHertz} {dictionary.FigureStandardUnit.Hertz[language]} {" "}
                      {recording.Therapy[side].PulseWidthInMicroSecond} {dictionary.FigureStandardUnit.uS[language]}
                    </MDTypography>
                    <MDTypography variant="h5">
                      {recording.Prediction[indexOfInterest].PredictedAmplitude.toFixed(2) + " " + dictionary.FigureStandardUnit.mA[language]}
                    </MDTypography>
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDBox sx={{ width: '100%' }}>
                    <MDTypography variant="p" fontSize={15}>
                      {"Beta Supression"} {recording.Prediction[indexOfInterest].ChangesInPower.toFixed(2)} {<br/>}
                    </MDTypography>
                    <MDTypography variant="p" fontSize={15}>
                      {"Final Beta Power"} {recording.Prediction[indexOfInterest].FinalPower.toFixed(2)}
                    </MDTypography>
                  </MDBox>
                  <MDBox sx={{ width: '100%' }}>
                    <MDTypography display="block" variant="caption" fontWeight="medium" color="text">
                      {(recording.Prediction[indexOfInterest].Score*100).toFixed(1)}%
                    </MDTypography>
                    <MDBox mt={0.25}>
                      <MDProgress variant="gradient" color={recording.Prediction[indexOfInterest].Score > 0.6 ? "info" : "warning"} value={recording.Prediction[indexOfInterest].Score*100} />
                    </MDBox>
                  </MDBox>
                </TableCell>
                <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                  <MDButton variant={"contained"} color="info" onClick={() => getRecordingData(recording.RecordingID)} style={{padding: 0}}>
                    {dictionary.PatientOverview.PatientInformation.View[language]}
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

export default TherapeuticPredictionTable;