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
  const [dataToRender, setDataToRender] = React.useState(false);
  const [alert, setAlert] = React.useState(null);

  const [figureHeight, setFigureHeight] = React.useState(0);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: true});
    } else {
      SessionController.query("/api/queryIndefiniteStreaming", {
        id: patientID, 
        requestOverview: true
      }).then((response) => {
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
      for (var i = 0; i < dataToRender.data[section]["Time"].length; i++) {
        csvData += dataToRender.data[section]["Time"][i] + dataToRender.data[section].Timestamp;
        for (var j = 0; j < dataToRender.data[section]["Channels"].length; j++) {
          csvData += "," + dataToRender.data[section][dataToRender.data[section]["Channels"][j]][i];
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
                      <TimeDomainFigure dataToRender={dataToRender} height={figureHeight} figureTitle={"IndefiniteStreamTimeDomain"}/>
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
