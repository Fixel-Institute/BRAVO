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
  Backdrop,
  ClickAwayListener,
  Card,
  Grid,
} from "@mui/material"

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import CircadianRhythm from "./CircadianRhythm";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { formatStimulationChannel } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function CircadianThreshold() {
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
      SessionController.query("/api/queryChronicNeuralActivity", {
        id: patientID, 
        requestData: true, 
        timezoneOffset: new Date().getTimezoneOffset()*60
      }).then((response) => {
        if (response.data.ChronicData.length > 0) {
          populateCircadianRhythmSelector(response.data.ChronicData);
          setData(response.data.ChronicData);
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
          if (data[i]["CustomName"]) {
            options.push({
              label: data[i]["Device"] + " " + data[i]["CustomName"] + " " + data[i]["CircadianPowers"][j]["Therapy"],
              hemisphere: data[i]["Device"] + " " + data[i]["Hemisphere"],
              therapyName: data[i]["CircadianPowers"][j]["Therapy"],
              value: data[i]["Device"] + "//" + data[i]["CustomName"] + "//" + data[i]["CircadianPowers"][j]["Therapy"]
            });
          } else {
            options.push({
              label: data[i]["Device"] + " " + data[i]["Hemisphere"] + " " + data[i]["CircadianPowers"][j]["Therapy"],
              hemisphere: data[i]["Device"] + " " + data[i]["Hemisphere"],
              therapyName: data[i]["CircadianPowers"][j]["Therapy"],
              value: data[i]["Device"] + "//" + data[i]["Hemisphere"] + "//" + data[i]["CircadianPowers"][j]["Therapy"]
            });
          }
        }
      }
    }

    if (options.length > 0) {
      setCircadianData({...circadianData, selector: options, currentValue: options[0]});
    } else {
      setCircadianData({});
    }
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
                          <MDBox p={2} lineHeight={1}>
                            <Autocomplete
                              options={circadianData.selector}
                              value={circadianData.currentValue}
                              onChange={(event, value) => {
                                setCircadianData({...circadianData, currentValue: value})
                              }}
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
                        <Grid item xs={12} lg={12}>
                          <CircadianRhythm dataToRender={data} selector={circadianData.currentValue} height={700} figureTitle={"CircadianRhythmThreshold"} />
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
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default CircadianThreshold;
