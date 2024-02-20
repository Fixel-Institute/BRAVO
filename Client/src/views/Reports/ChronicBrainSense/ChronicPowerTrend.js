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

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import { Menu, MenuItem, Dialog, DialogContent, Grid, Autocomplete, TextField, DialogActions } from "@mui/material";
import { createFilterOptions } from "@mui/material/Autocomplete";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

const filter = createFilterOptions();

function ChronicPowerTrend({dataToRender, events, selectedDevice, handleAddEvent, handleDeleteEvent, annotations, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [contextMenu, setContextMenu] = React.useState(null);
  const [annotationTypes, setAnnotationTypes] = React.useState([]);
  const [eventInfo, setEventInfo] = React.useState({
    name: "",
    time: 0,
    duration: 0,
    lastClick: 0,
    show: false
  });

  const [figureHeight, setFigureHeight] = React.useState(height);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    var axisTitles = []
    for (let k = 0; k < data.length; k++)
    {
      const [side, target] = data[k].Hemisphere.split(" ");
      const title = data[k]["Device"] + ` (${dictionaryLookup(dictionary.FigureStandardText, side, language)}) ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
      if (!axisTitles.includes(title)) axisTitles.push(title)
    }
    
    if (fig.fresh) {
      var ax = fig.subplots(data.length*2, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
       for (let i in data) {
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*2]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[i*2+1]);
        
        fig.setYlim([0, 5], ax[i*2+1]);

        if (data[i].Hemisphere === data[i].CustomName) {
          const [side, target] = data[i].Hemisphere.split(" ");
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
          fig.setSubtitle(`${titleText}`,ax[i*2]);
        } else {
          fig.setSubtitle(`${data[i].CustomName}`,ax[i*2]);
        }
        
        fig.setSubtitle(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)}`,ax[i*2+1]);
      }

      fig.setAxisProps({
        rangeselector: {buttons: [
          { count: 1, label: '1 Day', step: 'day', stepmode: 'todate' },
          { count: 7, label: '1 Week', step: 'day', stepmode: 'todate' },
          { count: 1, label: '1 Month', step: 'month', stepmode: 'todate' },
          {step: 'all'}
        ]},
      }, "x");

      fig.setLegend({
        tracegroupgap: 5,
        xanchor: "left",
        y: 0.5,
      });

      fig.setLayoutProps({
        hovermode: "xy"
      });
    }

    for (let i = 0; i < data.length; i++) {
      const eventData = {};
      const annotationData = {};
      for (let j = 0; j < events.length; j++) {
        eventData[events[j]] = {xdata: [], ydata: []};
      }
      for (let j = 0; j < annotationTypes.length; j++) {
        annotationData[annotationTypes[j]] = {xdata: [], ydata: []};
      }
      
      for (let j = 0; j < data[i].Timestamp.length; j++) {
        var therapyString = ""
        if (data[i]["Therapy"][j].hasOwnProperty("TherapyOverview")) therapyString = data[i]["Therapy"][j]["TherapyOverview"]
        
        var timeArray = Array(data[i]["Timestamp"][j].length).fill(0).map((value, index) => new Date(data[i]["Timestamp"][j][index]*1000));
        if (data[i]["Power"][j].length > 0) {
          fig.plot(timeArray, data[i]["Power"][j], {
            linewidth: 2,
            color: "#000000",
            hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f} <extra></extra>"
          }, ax[i*2]);
        } else {
          fig.plot([], [], {}, ax[i*2]);
        }


        if (data[i]["Amplitude"][j].length > 0) {
          if (data[i]["AdaptiveTimestamp"]) {
            timeArray = Array(data[i]["AdaptiveTimestamp"][j].length).fill(0).map((value, index) => new Date(data[i]["AdaptiveTimestamp"][j][index]*1000));
          }
          
          fig.plot(timeArray, data[i]["Amplitude"][j], {
            line: {shape: 'hv'},
            linewidth: 0.5,
            color: "#AA0000",
            hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f} <extra></extra>"
          }, ax[i*2+1]);
        } else {
          fig.plot([], [], {}, ax[i*2+1]);
        }

        for (let k = 0; k < data[i].EventName[j].length; k++) {
          if (Object.keys(eventData).includes(data[i].EventName[j][k])) {
            eventData[data[i].EventName[j][k]].xdata.push(data[i].EventTime[j][k]*1000);
            eventData[data[i].EventName[j][k]].ydata.push(data[i].EventPower[j][k]);
          }
        }
        
        for (let k in annotations) {
          if (Object.keys(eventData).includes(annotations[k].Name)) {
            annotationData[annotations[k].Name].xdata.push(annotations[k].Time*1000);
            annotationData[annotations[k].Name].ydata.push(0);
          }
        }
      }

      const colors = colormap({
        colormap: "rainbow-soft",
        nshades: 25,
        format: "hex",
        alpha: 1
      });
      const increment = Math.floor(25 / (events.length + annotationTypes.length));
  
      const getColor = (name) => {
        for (let k = 0; k < events.length; k++) {
          if (name.startsWith(events[k])) return colors[k * increment];
        }
        for (let k = 0; k < annotationTypes.length; k++) {
          if (name.startsWith(annotationTypes[k])) return colors[k * increment + events.length];
        }
        return colors[0];
      }

      for (let j = 0; j < events.length; j++) {
        fig.scatter(eventData[events[j]].xdata, eventData[events[j]].ydata, {
          color: getColor(events[j]),
          size: 5,
          name: events[j],
          showlegend: true,
          legendgroup: events[j],
          hovertemplate: "  %{x} <br>  " + events[j] + "<extra></extra>"
        }, ax[i*2])
      }
      
      for (let j = 0; j < annotationTypes.length; j++) {
        fig.scatter(annotationData[annotationTypes[j]].xdata, annotationData[annotationTypes[j]].ydata, {
          color: getColor(annotationTypes[j]),
          size: 5,
          name: "Clinician Events: " + annotationTypes[j],
          showlegend: true,
          legendgroup: "Clinician Events: " + annotationTypes[j],
          hovertemplate: "  %{x} <br>  Clinician Events: " + annotationTypes[j] + "<extra></extra>"
        }, ax[i*2])
      }
    }

    if (!data) {
      fig.purge();
      setShow(false);
    } else {
      fig.render();
      setShow(true);
    }
  }

  // Refresh Left Figure if Data Changed
  React.useEffect(() => {
    for (let i in annotations) {
      if (!annotationTypes.includes(annotations[i].Name)) {
        annotationTypes.push(annotations[i].Name)
      }
    }
    setAnnotationTypes([...annotationTypes]);

    if (dataToRender) {
      const channelData = dataToRender.ChronicData.filter((channel) => channel.Device == selectedDevice);
      if (channelData.length > 0) {
        setFigureHeight(channelData.length*height);
        handleGraphing(channelData)
      };
    };
  }, [dataToRender, events, selectedDevice, annotations, language]);

  const onResize = useCallback(() => {
    fig.refresh();
  }, []);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });

  React.useEffect(() => {
    if (ref.current.on) {
      ref.current.on("plotly_click", (data) => {
        setEventInfo((eventInfo) => {
          eventInfo.lastClick = new Date().getTime();
          eventInfo.time = new Date(data.points[0].x).getTime();
          return {...eventInfo};
        });
      });
    }
  }, [ref.current, dataToRender]);

  return (
    <MDBox ref={ref} onContextMenu={(event) => {
      event.preventDefault();
      setContextMenu(
        contextMenu === null ? {
          mouseX: event.clientX + 2,
          mouseY: event.clientY - 6,
        } : null
      );
    }} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: figureHeight, width: "100%", display: show ? "" : "none"}}>
      <Menu
        open={contextMenu !== null}
        onClose={() => setContextMenu(null)}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
        disableScrollLock={true}
      >
        <MenuItem onClick={() => {
          setContextMenu(null);
          if (new Date().getTime() - eventInfo.lastClick> 1000) return;
          setEventInfo({...eventInfo, name: "", show: true});
        }}>{"Add New Event"}</MenuItem>
        <MenuItem onClick={() => {
          setContextMenu(null);
          handleDeleteEvent(eventInfo);
          }}>{"Delete Event"}</MenuItem>
      </Menu>
      <Dialog open={eventInfo.show} onClose={() => setEventInfo({...eventInfo, show: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"New Custom Event"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid item xs={12} style={{display: "flex", flexDirection: "column"}}>
              <Autocomplete 
                selectOnFocus clearOnBlur
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="standard"
                    placeholder={dictionary.PatientOverview.TagNames[language]}
                  />
                )}
                filterOptions={(options, params) => {
                  const filtered = filter(options, params);
                  const { inputValue } = params;

                  // Suggest the creation of a new value
                  const isExisting = options.some((option) => inputValue === option.title);
                  if (inputValue !== '' && !isExisting) {
                    filtered.push({
                      value: inputValue,
                      title: `Add "${inputValue}"`,
                    });
                  }
                  return filtered;
                }}
                getOptionLabel={(option) => {
                  if (typeof option === 'string') {
                    return option;
                  }
                  if (option.inputValue) {
                    return option.inputValue;
                  }
                  return option.title;
                }}
                isOptionEqualToValue={(option, value) => {
                  return option.value === value.value;
                }}
                renderOption={(props, option) => <li {...props}>{option.title}</li>}

                value={{
                  title: eventInfo.name,
                  value: eventInfo.name
                }}
                options={annotationTypes.map((value) => ({
                  title: value,
                  value: value
                }))}
                onChange={(event, newValue) => setEventInfo({...eventInfo, name: newValue ? newValue.value : ""})}
              />
            </Grid>
            <Grid item xs={12} style={{display: "flex", flexDirection: "column"}}>
              <TextField
                variant="standard"
                margin="dense"
                type={"number"}
                label="Event Duration"
                placeholder={"0 for Instant Event"}
                value={eventInfo.duration}
                onChange={(event) => setEventInfo({...eventInfo, duration: event.target.value})}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setEventInfo({...eventInfo, show: false})}>Cancel</MDButton>
          <MDButton color="info" onClick={() => {
            handleAddEvent(eventInfo);
            setEventInfo({...eventInfo, show: false});
          }}>Add</MDButton>
        </DialogActions>
      </Dialog>
      
    </MDBox>
  );
}

export default ChronicPowerTrend;