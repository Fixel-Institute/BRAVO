import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Grid,
} from "@mui/material"

import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import ChronicPowerTrend from "./ChronicPowerTrend";
import CircadianRhythm from "./CircadianRhythm";
import EventLockedPower from "./EventLockedPower";
import EventPowerSpectrum from "./EventPowerSpectrum";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function ChronicBrainSense() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [availableDevice, setAvailableDevices] = useState({current: null, list: []});

  const [eventList, setEventList] = useState([]);
  const [circadianData, setCircadianData] = useState({});
  const [eventLockedPowerData, setEventLockedPowerData] = useState({});
  const [eventPSDData, setEventPSDData] = useState({});

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryChronicBrainSense", {
        id: patientID, 
        requestData: true, 
        timezoneOffset: new Date().getTimezoneOffset()*60
      }).then((response) => {
        if (response.data.ChronicData.length > 0) {
          setData(response.data);
          setAvailableDevices({
            current: response.data.ChronicData[0].Device,
            list: response.data.ChronicData.map((channel) => channel.Device).filter((value, index, array) => array.indexOf(value) === index)
          });
        }
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const populateCircadianRhythmSelector = (data) => {
    const options = [];
    for (var i = 0; i < data.length; i++) {
      for (var j = 0; j < data[i]["CircadianPowers"].length; j++) {
        if (data[i]["CircadianPowers"][j]["Power"].length > 144*3) {
          options.push({
            label: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["CircadianPowers"][j]["Therapy"],
            hemisphere: data[i]["Device"] + " " + data[i]["Hemisphere"],
            therapyName: data[i]["CircadianPowers"][j]["Therapy"],
            value: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["CircadianPowers"][j]["Therapy"]
          });
        }
      }
    }

    if (options.length > 0) {
      setCircadianData({...circadianData, selector: options, currentValue: options[0]});
    } else {
      setCircadianData({});
    }
  };
  
  const populateEventLockedPowerSelector = (data) => {
    const options = [];
    for (var i = 0; i < data.length; i++) {
      for (var j = 0; j < data[i]["EventLockedPower"].length; j++) {
        if (data[i]["EventLockedPower"][j].hasOwnProperty("PowerChart")) {
          options.push({
            label: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["EventLockedPower"][j]["Therapy"],
            hemisphere: data[i]["Device"] + " " + data[i]["Hemisphere"],
            therapyName: data[i]["EventLockedPower"][j]["Therapy"],
            value: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["EventLockedPower"][j]["Therapy"]
          });
        }
      }
    }

    if (options.length > 0) {
      setEventLockedPowerData({...eventLockedPowerData, selector: options, currentValue: options[0]});
    } else {
      setEventLockedPowerData({});
    }
  };
  
  const populateEventPSDSelector = (data) => {
    const options = [];
    for (var i = 0; i < data.length; i++) {
      for (var j = 0; j < data[i]["Render"].length; j++) {
        if (data[i]["Render"][j].hasOwnProperty("Events")) {
          options.push({
            label: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["Render"][j]["Therapy"],
            hemisphere: data[i]["Device"] + " " + data[i]["Hemisphere"],
            therapyName: data[i]["Render"][j]["Therapy"],
            value: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["Render"][j]["Therapy"]
          });
        }
      }
    }

    if (options.length > 0) {
      setEventPSDData({...eventPSDData, selector: options, currentValue: options[0]});
    } else {
      setEventPSDData({});
    }
  };
  
  useEffect(() => {
    if (data) {
      const eventNames = [];
      for (var i = 0; i < data.ChronicData.length; i++) {
        for (var j = 0; j < data.ChronicData[i].EventName.length; j++) {
          for (var name of data.ChronicData[i].EventName[j]) {
            if (!eventNames.includes(name)) {
              eventNames.push(name);
            }
          }
        }
      }
      setEventList(eventNames);

      populateCircadianRhythmSelector(data.ChronicData);
      populateEventLockedPowerSelector(data.ChronicData);
      populateEventPSDSelector(data.EventPSDs)
    }
  }, [data]);

  const exportCurrentStream = () => {
    var csvData = "Time,Power,Therapy,Amplitude,Device,Hemisphere";
    csvData += "\n";

    for (let i = 0; i < data.ChronicData.length; i++) {
      for (let j = 0; j < data.ChronicData[i].Power.length; j++) {
        for (let k = 0; k < data.ChronicData[i].Power[j].length; k++) {
          csvData += data.ChronicData[i].Timestamp[j][k] + ",";
          csvData += data.ChronicData[i].Power[j][k] + ",";
          csvData += data.ChronicData[i].Therapy[j].TherapyOverview + ",";
          csvData += data.ChronicData[i].Amplitude[j][k] + ",";
          csvData += data.ChronicData[i].Device + ",";
          csvData += data.ChronicData[i].Hemisphere + "\n";
        }
      }
    }

    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'ChronicBrainSense.csv';
    downloader.click();
  };

  return (
    <>
      {alert}
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    {data ? (
                      <>
                        <Grid item xs={12}>
                          <MDBox p={2}>
                            <Autocomplete
                              value={availableDevice.current}
                              options={availableDevice.list}
                              onChange={(event, value) => setAvailableDevices({...availableDevice, current: value})}
                              renderInput={(params) => (
                                <FormField
                                  {...params}
                                  label={dictionary.ChronicBrainSense.Select.Device[language]}
                                  InputLabelProps={{ shrink: true }}
                                />
                              )}
                            />
                          </MDBox>
                        </Grid>
                        <Grid item xs={12}>
                          <MDBox p={2}>
                            <MDTypography variant={"h6"} fontSize={24}>
                              {dictionary.ChronicBrainSense.Figure.FigureTitle[language]}
                            </MDTypography>
                            <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportCurrentStream()}>
                              {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
                            </MDButton>
                          </MDBox>
                        </Grid>
                        <Grid item xs={12} lg={12}>
                          <ChronicPowerTrend dataToRender={data} height={800} selectedDevice={availableDevice.current} events={eventList} figureTitle={"ChronicPowerTrend"}/>
                        </Grid>
                      </>
                    ) : (
                      <Grid item xs={12}>
                        <MDBox p={2}>
                          <MDTypography variant="h6" fontSize={24}>
                            {dictionary.WarningMessage.NoData[language]}
                          </MDTypography>
                        </MDBox>
                      </Grid>
                    )}
                  </Grid>
                </Card>
              </Grid>
              {circadianData.currentValue ? (
                <Grid item xs={12} lg={6}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={2} lineHeight={1}>
                          <Autocomplete
                            options={circadianData.selector}
                            value={circadianData.currentValue}
                            onChange={(event, value) => setCircadianData({...circadianData, currentValue: value})}
                            getOptionLabel={(option) => {
                              return option.label || "";
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={dictionary.ChronicBrainSense.Select.Therapy[language]}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <CircadianRhythm dataToRender={data.ChronicData} selector={circadianData.currentValue} height={600} figureTitle={"CircadianRhythm"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {eventLockedPowerData.currentValue ? (
                <Grid item xs={12} lg={6}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={2} lineHeight={1}>
                          <Autocomplete
                            options={eventLockedPowerData.selector}
                            value={eventLockedPowerData.currentValue}
                            onChange={(event, value) => setEventLockedPowerData({...eventLockedPowerData, currentValue: value})}
                            getOptionLabel={(option) => {
                              return option.label || "";
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={dictionary.ChronicBrainSense.Select.Therapy[language]}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <EventLockedPower dataToRender={data.ChronicData} selector={eventLockedPowerData.currentValue} events={eventList} height={600} figureTitle={"EventLockedPower"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
              {eventPSDData.currentValue ? (
                <Grid item xs={12} lg={6}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={2} lineHeight={1}>
                          <Autocomplete
                            options={eventPSDData.selector}
                            value={eventPSDData.currentValue}
                            onChange={(event, value) => setEventPSDData({...eventPSDData, currentValue: value})}
                            getOptionLabel={(option) => {
                              return option.label || "";
                            }}
                            renderInput={(params) => (
                              <FormField
                                {...params}
                                label={dictionary.ChronicBrainSense.Select.Therapy[language]}
                                InputLabelProps={{ shrink: true }}
                              />
                            )}
                          />
                        </MDBox>
                      </Grid>
                      <Grid item xs={12}>
                        <EventPowerSpectrum dataToRender={data.EventPSDs} selector={eventPSDData.currentValue} events={eventList} height={600} figureTitle={"EventPSD"}/>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              ) : null}
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default ChronicBrainSense;
