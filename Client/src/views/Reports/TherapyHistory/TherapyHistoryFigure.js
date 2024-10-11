/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import { Card, Grid } from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";
import { SessionController } from "database/session-control";

function TherapyHistoryFigure({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [showDevice, setShowDevice] = React.useState([]);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const colors = colormap({
    colormap: 'rainbow-soft',
    nshades: 11,
    format: 'hex',
    alpha: 1,
  });
  const step = Math.floor(11 / Object.keys(dataToRender.TherapyDevices).length);

  const handleGraphing = (data) => {
    fig.clearData();
    
    let uniqueGroups = [];
    for (let i in data) {
      for (let j in data[i].therapyBlocks) { 
        if (!uniqueGroups.includes(data[i].therapyBlocks[j].label)) uniqueGroups.push(data[i].therapyBlocks[j].label)
      }
    }
    uniqueGroups = uniqueGroups.sort();
    
    if (fig.fresh) {
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      fig.setTickValue(uniqueGroups.map((value, index) => index), "y");
      fig.setTickLabel(uniqueGroups.map((value, index) => value), "y");
      fig.setAxisProps({
        zeroline: false
      }, "y");
      fig.setTitle(dictionaryLookup(dictionary.TherapyHistory.Figure, "TherapyChangeLog", language));

      fig.setLegend({
        bgcolor: "transparent",
        xanchor: "left"
      })
      fig.setLayoutProps({
        hovermode: "x"
      })
    }
    /*
    for (let i in data) {
      let xdata = [];
      let ydata = [];
      for (let j in data[i]["new_group"]) {
        let date = new Date(SessionController.decodeTimestamp(data[i]["date_of_change"][j]*1000));
        if (j == 0 || data[i]["old_group"][j] == "GroupIdDef.GROUP_UNKNOWN") {
          xdata.push(date, date);
          ydata.push(uniqueGroups.indexOf(data[i]["new_group"][j]), uniqueGroups.indexOf(data[i]["new_group"][j]));
        } else if (j > 0 && data[i]["old_group"][j] != data[i]["new_group"][j-1]) {
          xdata.push(date, date);
          ydata.push(null, uniqueGroups.indexOf(data[i]["new_group"][j]));
        } else {
          xdata.push(date)
          ydata.push(uniqueGroups.indexOf(data[i]["new_group"][j]));
        }
      }

      let deviceName = SessionController.decodeMessage(data[i]["device"]);
      if (deviceName.length > 30) deviceName = deviceName.slice(0,30) + "...";

      fig.plot(xdata, ydata, {
        type: 'scatter',
        mode: 'lines',
        line: {shape: 'hv'},
        hovertemplate: "  %{x} <br>  %{y} <extra></extra>",
        name: deviceName,
        legendgroup: data[i].device_inheritance,
        showlegend: true
      });
    }

    /*
    for (var i = 0; i < data.length; i++) {
      var xdata = []
      var ydata = []
      for (var j = 0; j < data[i]["new_group"].length; j++) {
        if (j == 0 || data[i]["previous_group"][j] == "GroupIdDef.GROUP_UNKNOWN") {
          var date = new Date(data[i]["date_of_change"][j]/1000000)
          xdata.push(date,date)
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0,0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1,1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2,2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3,3)
        } else if (j > 0 && data[i]["previous_group"][j] != data[i]["new_group"][j-1]) {
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          ydata.push(null)
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3)
        } else {
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3)
        }
      }
      
      fig.plot(xdata, ydata, {
        type: 'scatter',
        mode: 'lines',
        line: {shape: 'hv'},
        hovertemplate: "  %{x} <br>  %{y} <extra></extra>",
        name: data[i]["device_name"],
        showlegend: true
      });
*/

    let therapyBlocks = [];
    let xLim = [0,0]
    for (let i in data) {
      if (showDevice.includes(data[i].device)) {
        for (let j in data[i].therapyBlocks) {
          if (data[i].therapyBlocks[j].solid) {
            therapyBlocks.push({
              type: "rect",
              xref: 'x',
              x0: new Date(data[i].therapyBlocks[j].start*1000),
              x1: new Date(data[i].therapyBlocks[j].end*1000),
              y0: uniqueGroups.indexOf(data[i].therapyBlocks[j].label) - 0.3,
              y1: uniqueGroups.indexOf(data[i].therapyBlocks[j].label) + 0.3,
              line: { color: "#000000", width: 2 },
              fillcolor: colors[i*step],
              opacity: 0.6
            });
          }
          if (xLim[0] == 0 || xLim[0] > data[i].therapyBlocks[j].start) xLim[0] = data[i].therapyBlocks[j].start;
          if (xLim[1] == 0 || xLim[1] < data[i].therapyBlocks[j].end) xLim[1] = data[i].therapyBlocks[j].end;
        }
      }
    }

    fig.setLayoutProps({
      shapes: therapyBlocks,
      xaxis: {type: "date"}
    });
    fig.setXlim([new Date(xLim[0]*1000), new Date(xLim[1]*1000)]);
    fig.setYlim([-0.5, uniqueGroups.length-0.5]);

    if (!data) {
      fig.purge();
      setShow(false);
    } else {
      fig.render();
      setShow(true);
    }
  }

  React.useEffect(() => {
    setShowDevice(Object.keys(dataToRender.TherapyDevices));
  }, []);

  // Refresh Left Figure if Data Changed
  React.useEffect(() => {
    if (dataToRender.TherapyModification.length > 0) {
      let graphingData = []
      for (let device in dataToRender.TherapyDevices) {
        let TherapyChangeHistory = dataToRender.TherapyModification.filter((a) => a.type == "TherapyChangeGroup" && a.device == device).sort((a,b) => a.date-b.date);
        let TherapyBlocks = [];
        for (let i in TherapyChangeHistory) {
          if (i > 0) {
            if (TherapyChangeHistory[i-1].new_group == TherapyChangeHistory[i].old_group) {
              TherapyBlocks.push({
                label: TherapyChangeHistory[i-1].new_group,
                start: TherapyChangeHistory[i-1].date,
                end: TherapyChangeHistory[i].date,
                solid: true
              });
            } else {
              TherapyBlocks.push({
                label: TherapyChangeHistory[i-1].new_group,
                start: TherapyChangeHistory[i-1].date,
                end: TherapyChangeHistory[i-1].date + 24*3600 > TherapyChangeHistory[i].date ? (TherapyChangeHistory[i-1].date + 12*3600) : (TherapyChangeHistory[i-1].date + 24*3600),
                solid: false
              });
              TherapyBlocks.push({
                label: TherapyChangeHistory[i].old_group,
                start: TherapyChangeHistory[i].date - 24*3600 > TherapyChangeHistory[i-1].date ? (TherapyChangeHistory[i].date - 24*3600) : (TherapyChangeHistory[i].date - 12*3600),
                end: TherapyChangeHistory[i].date,
                solid: false
              });
            }
          }
        }
        graphingData.push({
          device: device,
          therapyBlocks: TherapyBlocks
        });
      }
      
      handleGraphing(graphingData);
    }
  }, [dataToRender, showDevice, language]);

  const onResize = useCallback(() => {
    fig.refresh();
  }, []);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });

  return (
    <MDBox>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
      {dataToRender ? (
        <Grid container spacing={2}>
          {Object.keys(dataToRender.TherapyDevices).map((device, index) => {
            return <Grid item xs={4} sm={3} key={device}>
              <Card style={{cursor: "pointer"}} onClick={() => {
                setShowDevice((showDevice) => {
                  if (showDevice.includes(device)) showDevice = showDevice.filter((a) => a != device)
                  else showDevice.push(device);
                  return [...showDevice];
                })
              }}>
                <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} padding={1}>
                  <MDBox style={{backgroundColor: colors[index*step], height: "10px", width: "10px", marginRight: 5}} />
                  <MDTypography fontSize={12} style={{textDecoration: showDevice.includes(device) ? "" : "line-through"}}>
                    {dataToRender.TherapyDevices[device].name.length > 15 ? dataToRender.TherapyDevices[device].name.slice(0,15) : dataToRender.TherapyDevices[device].name}
                  </MDTypography>
                </MDBox>
              </Card>
            </Grid>
          })}
        </Grid>
      ) : null}
    </MDBox>
  );
}

export default TherapyHistoryFigure;