import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  TextField,
  Autocomplete,
  Card,
  Grid,
  Dialog,
  DialogTitle,
  DialogActions,
  DialogContent,
  IconButton,
  Tooltip,
  Modal,
  ListItemButton,
  ListItemText,
  ListItemIcon
} from "@mui/material";

import { ViewInAr, Timeline } from "@mui/icons-material";

import React from "react";
import * as THREE from "three";
import { Canvas, useThree } from '@react-three/fiber';

import colormap from "colormap";

import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import RadioButtonGroup from "components/RadioButtonGroup";
import MDBadge from "components/MDBadge";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function WearableStream() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ChartTooltip, Legend);
  const chartCanvas = React.createRef();

  const [alert, setAlert] = useState(null);

  const [pairingState, setPairingState] = useState({
    state: false,
    pairingId: ""
  });

  const [pairedDevices, setPairedDevices] = useState([]);

  const [streamingDevice, setStreamingDevice] = useState({
    state: false,
    deviceId: ""
  });

  const [chartData, setChartData] = useState({
    datasets: []
  });

  const resetChart = () => {
    setChartData({
      datasets: [
        {
          label: "X",
          data: [],
          fill: false,
          radius: 0,
          lineTension: 0,
          borderWidth: 0.5,
          borderColor: 'rgb(255, 50, 50)',
          backgroundColor: 'rgb(255, 50, 50)',
          batchIndex: 0
        },
        {
          label: "Y",
          data: [],
          fill: false,
          radius: 0,
          lineTension: 0,
          borderWidth: 0.5,
          borderColor: 'rgb(50, 255, 50)',
          backgroundColor: 'rgb(50, 255, 50)',
          batchIndex: 1
        },
        {
          label: "Z",
          data: [],
          fill: false,
          radius: 0,
          lineTension: 0,
          borderWidth: 0.5,
          borderColor: 'rgb(50, 50, 255)',
          backgroundColor: 'rgb(50, 50, 255)',
          batchIndex: 2
        }
      ]
    });
  };

  useEffect(() => {
    resetChart();
  }, []);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: true});
    } else {
      SessionController.query("/mobile/wearable/queryPairedDevice", {
        PatientID: patientID,
      }).then((response) => {
        setPairedDevices(response.data)
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID])

  function wearableSocket(deviceId, onData) {
    this.ws = new WebSocket(window.location.origin.replace("http://","ws://").replace("https://","wss://") + "/socket/wearableStream");

    this.timestamp = 0;
    this.interval = 0;

    this.ws.onopen = () => {
      this.ws.send(JSON.stringify({
        joinStream: deviceId
      }));
    };

    this.ws.onmessage = (message) => {
      if (message.data instanceof Blob) {
        message.data.arrayBuffer().then((array) => {
          const data = new Int16Array(array);
  
          var array = [
            data.filter((value, index) => index % 3 == 0),
            data.filter((value, index) => index % 3 == 1),
            data.filter((value, index) => index % 3 == 2),
          ];
  
          onData(array, this.timestamp, this.interval);
          this.timestamp += (array[0].length) * this.interval;
  
        });
      } else {
        this.timestamp = 0;
        const config = JSON.parse(message.data);
        this.interval = 1 / config.SamplingRate;
        resetChart();
      }
    };

    this.ws.onerror = (error) => {
      console.log(error);
      this.ws.close(200);
    };

    this.ws.onclose = (code) => {
      if (code == 200) {
        setAlert(
          <MuiAlertDialog title={"ERROR"} message={"Websocket Closed Unexpectedly"}
            handleClose={() => setAlert()} 
            handleConfirm={() => setAlert()}/>
        );
      }
    };
  }

  useEffect(() => {
    if (chartCanvas.current && streamingDevice.state) {
      const socketHandler = new wearableSocket(streamingDevice.deviceId, (data, startIndex, interval) => {
        chartCanvas.current.data.datasets.forEach((dataset) => {
          for (let i = 0; i < data[dataset.batchIndex].length; i++) {
            dataset.data.push({
              x: startIndex + i*interval,
              y: data[dataset.batchIndex][i]/100
            });
          }
          if (dataset.data.length > (5/interval)) dataset.data = dataset.data.slice(-5/interval);
        });

        if (startIndex > 5) {
          chartCanvas.current.options.scales.x.max = data[0].length * interval + startIndex;
          chartCanvas.current.options.scales.x.min = chartCanvas.current.options.scales.x.max - 5;
        }
        
        chartCanvas.current.update();
      });

      return () => {
        console.log("close")
        socketHandler.ws.close();
      }
    }
  }, [streamingDevice]);

  const handlePairing = () => {
    SessionController.query("/mobile/wearable/verifyDevicePairing", {
      PatientID: patientID,
      PairingCode: pairingState.pairingId
    }).then((response) => {
      setPairingState({...pairingState, state: false, pairingId: ""});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
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
                      <MDBox display={"flex"} justifyContent={"space-between"} p={2}>
                        <MDTypography variant="h4">
                          {dictionaryLookup(dictionary.Wearable, "Title", language)}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox display={"flex"} justifyContent={"space-between"} p={2}>
                        {pairedDevices.map((device, index) => {
                          return (
                            <MDBox key={index} display={"flex"} flexDirection={"row"} justifyContent={"space-between"} p={2} style={{
                              borderBottom: "1px solid black",
                              width: "100%"
                            }}>
                              <MDTypography variant="h5">
                                {new Date(device.PairingDate*1000).toLocaleDateString(language)}
                              </MDTypography>
                              <MDTypography variant="h5">
                                {device.DeviceName}
                              </MDTypography>
                              <MDTypography variant="h5">
                                {device.DeviceMac}
                              </MDTypography>
                              <MDBox display={"flex"} flexDirection={"row"} justifyContent={"space-between"} >
                                <Tooltip title="View Stream" placement="top" style={{marginRight: 15}}>
                                  <IconButton variant="contained" color="info" onClick={() => {
                                    if (device.DeviceMac == streamingDevice.deviceId) {
                                      setStreamingDevice({state: false, deviceId: ""})
                                    } else {
                                      setStreamingDevice({state: true, deviceId: device.DeviceMac});
                                    }
                                  }}>
                                    <i className="fa-solid fa-eye" style={{fontSize: 25}}></i>
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Remove Pairing" placement="top">
                                  <IconButton variant="contained" color="error" onClick={() => {}}>
                                    <i className="fa-solid fa-xmark" style={{fontSize: 25}}></i>
                                  </IconButton>
                                </Tooltip>
                              </MDBox>
                            </MDBox>
                          )
                        })}
                      </MDBox>
                      <MDBox display={"flex"} justifyContent={"space-between"} p={2}>
                        <MDButton variant="contained" color={"info"} onClick={() => setPairingState({...pairingState, state: true})}> 
                          <MDTypography variant="p" color={"white"}>
                            {dictionaryLookup(dictionary.Wearable, "NewPair", language)}
                          </MDTypography>
                        </MDButton>
                      </MDBox>
                      <Dialog open={pairingState.state} onClose={() => {
                        setPairingState({...pairingState, state: false, pairingId: ""});
                      }}>
                        <DialogTitle>Subscribe</DialogTitle>
                        <DialogContent>
                          <TextField
                            autoFocus
                            label="Pairing Code"
                            value={pairingState.pairingId}
                            onChange={(event) => setPairingState({...pairingState, pairingId: event.target.value})}
                            type="text"
                            fullWidth
                            variant="standard"
                          />
                        </DialogContent>
                        <DialogActions>
                          <MDButton onClick={() => setPairingState({...pairingState, state: false, pairingId: ""})}>Cancel</MDButton>
                          <MDButton onClick={() => handlePairing()}>Subscribe</MDButton>
                        </DialogActions>
                      </Dialog>
                    </Grid>
                    {streamingDevice.state ? (
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <Line ref={chartCanvas} options={{
                          responsive: true,
                          animation: false,
                          scales: {
                            y: {
                              type: "linear",
                              beginAtZero: true,
                              min: -8,
                              max: 8
                            },
                            x: {
                              type: "linear",
                            }
                          },
                        }} data={chartData} />
                      </MDBox>
                    </Grid>
                    ) : null}
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

export default WearableStream;
