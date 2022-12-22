import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  TextField,
  Autocomplete,
  Card,
  Grid,
} from "@mui/material";

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import colormap from "colormap";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import RadioButtonGroup from "components/RadioButtonGroup";
import MDBadge from "components/MDBadge";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import PatientEventCount from "./PatientEventCount";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import EventPowerSpectrum from "./EventPowerSpectrum";

function PatientEvents() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [eventList, setEventList] = useState({});
  const [eventGroupingDuration, setEventGroupingDuration] = useState("Week");

  const [timerange, setTimerange] = useState({start: null, end: null});

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: true});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryPatientEvents", {
        id: patientID
      }).then((response) => {
        setData(response.data.EventPSDs);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  useEffect(() => {
    if (data) {
      const eventNames = {};
      for (var i = 0; i < data.length; i++) {
        for (var j = 0; j < data[i].EventName.length; j++) {
          if (!Object.keys(eventNames).includes(data[i].EventName[j])) {
            eventNames[data[i].EventName[j]] = {};
          }
        }
      }

      const colors = colormap({
        colormap: "rainbow-soft",
        nshades: Object.keys(eventNames).length > 11 ? Object.keys(eventNames).length : 11,
        format: "hex",
        alpha: 1
      });

      var counter = 0;
      var increment = colors.length / Object.keys(eventNames).length;
      for (var key of Object.keys(eventNames)) {
        eventNames[key].color = colors[Math.floor(counter)];
        counter += increment;
      }

      setEventList(eventNames);
    }
  }, [data]);

  const adapterLocales = {
    "zh": "zh-CN",
    "en": "en-US"
  }

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
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {dictionary.PatientEvents.Figure.EventFrequency[language]}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox pb={2} display={"flex"} flexDirection={"row"}>
                        {Object.keys(eventList).map((key) => {
                          return (
                          <MDBox key={key} mx={2} px={2}
                            style={{cursor: "pointer", background: eventList[key].color, borderRadius: 10}} 
                            onClick={() => console.log("test")}
                          >
                            <MDTypography fontWeight={"bold"} fontSize={15} color={"white"}>{key}</MDTypography>
                          </MDBox>
                          );
                        })}
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <MDBox px={2} pb={2} display={"flex"} flexDirection={"row"}>
                        <RadioButtonGroup row 
                          defaultValue={eventGroupingDuration}
                          value={eventGroupingDuration} 
                          options={[
                            {value: "Week", label: "By Week"},
                            {value: "Month", label: "By Month"},
                          ]}
                          onChange={(event) => setEventGroupingDuration(event.target.value)}
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      {Object.keys(eventList).length > 0 ? <PatientEventCount dataToRender={data} height={400} events={eventList} grouping={eventGroupingDuration} stack figureTitle={"EventCounts"}/> : null}
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {dictionary.PatientEvents.Figure.EventFrequencyTimeRange[language]}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2} display={"flex"} flexDirection={"row"}>
                        <MDTypography variant={"h6"} fontSize={24} pr={2}>
                          {"From"}
                        </MDTypography>
                        <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
                          <DatePicker
                            label="Start Date"
                            value={timerange.start}
                            onChange={(newDate) => {
                              setTimerange({...timerange, start: newDate});
                            }}
                            renderInput={(params) => <TextField {...params} />}
                          />
                        </LocalizationProvider>
                        <MDTypography variant={"h6"} fontSize={24} px={2}>
                          {"To"}
                        </MDTypography>
                        <LocalizationProvider dateAdapter={AdapterMoment}>
                          <DatePicker
                            label="End Date"
                            value={timerange.end}
                            onChange={(newDate) => {
                              setTimerange({...timerange, end: newDate});
                            }}
                            renderInput={(params) => <TextField {...params} />}
                          />
                        </LocalizationProvider>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <EventPowerSpectrum dataToRender={data} timerange={[timerange.start, timerange.end]} events={eventList} height={600} figureTitle={"EventPSDs"} />
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default PatientEvents;
