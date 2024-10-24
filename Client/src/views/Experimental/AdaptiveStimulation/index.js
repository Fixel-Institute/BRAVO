/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Grid,
} from "@mui/material"

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import AdaptivePowerTrend from "./AdaptivePowerTrend";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";

function AdaptiveStimulation() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);

  const [eventList, setEventList] = useState([]);
  const [availableDevice, setAvailableDevices] = useState({current: null, list: []});

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryAdaptiveStimulation", {
        id: patientID, 
        requestData: true, 
        timezoneOffset: new Date().getTimezoneOffset()*60
      }).then((response) => {
        if (response.data.ChronicData.length > 0) {
          setData(response.data.ChronicData);
          setAvailableDevices({
            current: response.data.ChronicData[0].Device,
            list: response.data.ChronicData.map((channel) => channel.Device).filter((value, index, array) => array.indexOf(value) === index)
          });
        };
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);


  useEffect(() => {
    
  }, [data]);

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
                          {dictionary.AdaptiveStimulation.Figure.ChronicAdaptive[language]}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <Autocomplete
                          value={availableDevice.current}
                          options={availableDevice.list}
                          onChange={(event, value) => setAvailableDevices({...availableDevice, current: value})}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={dictionary.AdaptiveStimulation.Table.SelectDevice[language]}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                        />
                      </MDBox>
                    </Grid>
                    <Grid item xs={12} lg={12}>
                      {data ? <AdaptivePowerTrend dataToRender={data} selectedDevice={availableDevice.current} height={800} events={eventList} figureTitle={"AdaptivePowerTrend"}/> : null}
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

export default AdaptiveStimulation;
