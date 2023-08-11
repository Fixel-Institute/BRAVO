/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Grid,
} from "@mui/material"

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import IndefiniteStreamingTable from "components/Tables/StreamingTable/IndefiniteStreamingTable";
import TimeDomainFigure from "./TimeDomainFigure";
import TimeFrequencyFigure from "./TimeFrequencyFigure";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function IndefiniteStreaming() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = React.useState([]);
  const [annotations, setAnnotations] = React.useState([]);
  const [dataToRender, setDataToRender] = React.useState(false);
  const [alert, setAlert] = React.useState(null);

  const [figureHeight, setFigureHeight] = React.useState(0);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryIndefiniteStreaming", {
        id: patientID, 
        requestOverview: true
      }).then((response) => {
        if (response.data.length > 0) {
          setAnnotations(response.data[0].annotations);
        }
        setData(response.data)
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const requestDataForRender = (dataList) => {
    var devices = [];
    var timestamps = [];
    var channelInfos = [];
    for (var i in dataList) {
      if (dataList[i].state) {
        devices.push(dataList[i].DeviceID);
        timestamps.push(dataList[i].Timestamp);
        channelInfos.push(dataList[i].Channels);
      }
    }
    if (devices.length == 0) return;

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryIndefiniteStreaming", {
      id: patientID, 
      requestData: true, 
      devices: devices, 
      timestamps: timestamps
    }).then((response) => {
      var axLength = 0;
      for (var i in response.data) {
        if (response.data[i].Channels.length > axLength) {
          axLength = response.data[i].Channels.length;
        }
      }
      setFigureHeight(200*axLength);
      setDataToRender({data: response.data, ChannelInfos: channelInfos});
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const exportCurrentStream = () => {
    var csvData = "Time";
    for (var i = 0; i < dataToRender.data[0]["Channels"].length; i++) {
      csvData += "," + dataToRender.data[0]["Channels"][i] + " Raw";
    }
    csvData += "\n";
    
    for (var section in dataToRender.data) {
      for (var i = 0; i < dataToRender.data[section]["Stream"][0].length; i++) {
        csvData += (i*1/250 + dataToRender.data[section].Timestamp);
        for (var j = 0; j < dataToRender.data[section]["Channels"].length; j++) {
          csvData += "," + dataToRender.data[section]["Stream"][j][i];
        }
        csvData += "\n";
      }
    }

    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'IndefiniteStreamExport.csv';
    downloader.click();
  };

  const handleAddEvent = async (eventInfo) => {
    try {
      const response = await SessionController.query("/api/queryCustomAnnotations", {
        id: patientID,
        addEvent: true,
        name: eventInfo.name,
        time: eventInfo.time / 1000,
        duration: parseFloat(eventInfo.duration)
      });

      if (response.status == 200) {
        setDataToRender((dataToRender) => {
          dataToRender.data[0].Annotations = [...dataToRender.data[0].Annotations, {
            Time: eventInfo.time / 1000,
            Name: eventInfo.name,
            Duration: parseFloat(eventInfo.duration)
          }];
          return {...dataToRender};
        });

        setAnnotations((annotations) => {
          if (!annotations.includes(eventInfo.name)) {
            annotations.push(eventInfo.name);
          }
          return [...annotations];
        });
      }
    } catch (error) {
      SessionController.displayError(error, setAlert);
    }
  };

  const handleDeleteEvent = async (eventInfo) => {
    for (let i in dataToRender.data) {
      if (dataToRender.data[i].Annotations.length > 0) {
        eventInfo.targetInfo = eventInfo;
        eventInfo.targetInfo.timeDiff = 10;
      }
    }
      
    for (let j in dataToRender.data) {
      for (let i = 0; i < dataToRender.data[j].Annotations.length; i++) {
        let absoluteDiffTime = Math.abs(dataToRender.data[j].Annotations[i].Time - eventInfo.time/1000);
        if (absoluteDiffTime < eventInfo.targetInfo.timeDiff) {
          eventInfo.targetInfo = dataToRender.data[j].Annotations[i];
          eventInfo.targetInfo.timeDiff = absoluteDiffTime;
        }
      }
    }
    
    if (eventInfo.targetInfo.timeDiff < 10) {
      setAlert(<MuiAlertDialog 
        title={`Remove ${eventInfo.targetInfo.Name} Event`}
        message={`Are you sure you want to delete the entry [${eventInfo.targetInfo.Name}] @ ${new Date(eventInfo.targetInfo.Time*1000)} ?`}
        confirmText={"YES"}
        denyText={"NO"}
        denyButton
        handleClose={() => setAlert(null)}
        handleDeny={() => setAlert(null)}
        handleConfirm={() => {
          SessionController.query("/api/queryCustomAnnotations", {
            id: patientID,
            deleteEvent: true,
            name: eventInfo.targetInfo.Name,
            time: eventInfo.targetInfo.Time
          }).then(() => {
            setDataToRender((dataToRender) => {
              for (let j in dataToRender.data) {
                dataToRender.data[j].Annotations = dataToRender.data[j].Annotations.filter((a) => {
                  if (a.Name == eventInfo.targetInfo.Name && a.Time == eventInfo.targetInfo.Time && a.Duration == eventInfo.targetInfo.Duration) {
                    return false;
                  }
                  return true;
                })
              }
              return {...dataToRender};
            });
            setAlert(null);
          }).catch((error) => {
            SessionController.displayError(error, setAlert);
          });
        }}
      />)
    }
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
                      <MDBox p={2} lineHeight={1}>
                        {data.length > 0 ? (
                          <IndefiniteStreamingTable data={data} requestDataForRender={requestDataForRender}/>
                        ) : (
                          <MDTypography variant="h6" fontSize={24}>
                            {dictionary.WarningMessage.NoData[language]}
                          </MDTypography>
                        )}
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              {dataToRender ? (
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2} display={"flex"} flexDirection={"row"}>
                        <MDBox display={"flex"} flexDirection={"column"}>
                          <MDTypography variant="h5" fontWeight={"bold"} fontSize={24}>
                            {dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "RawData", language)}
                          </MDTypography>
                          <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3}} onClick={() => exportCurrentStream()}>
                            {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
                          </MDButton>
                        </MDBox>
                      </MDBox>
                      <TimeDomainFigure dataToRender={dataToRender} height={figureHeight} 
                        handleAddEvent={handleAddEvent} handleDeleteEvent={handleDeleteEvent} annotations={annotations}
                        figureTitle={"IndefiniteStreamTimeDomain"}/>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              ) : null}
              <Grid item xs={12}> 
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <TimeFrequencyFigure dataToRender={dataToRender} height={figureHeight} figureTitle={"IndefiniteStreamTimeFrequency"}/>
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

export default IndefiniteStreaming;
