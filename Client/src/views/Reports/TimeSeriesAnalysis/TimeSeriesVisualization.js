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
import { Autocomplete, Dialog, DialogContent, TextField, DialogActions, Grid, Menu, MenuItem } from "@mui/material";
import { createFilterOptions } from "@mui/material/Autocomplete";

import * as Math from "mathjs"
import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function TimeSeriesVisualization({dataToRender, channelInfos, handleAddEvent, handleDeleteEvent, handleAdjustAlignment, annotations, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [figureHeight, setFigureHeight] = React.useState(height);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const [contextMenu, setContextMenu] = React.useState(null);
  const [eventInfo, setEventInfo] = React.useState({
    name: "",
    time: 0,
    duration: 0,
    show: false
  });
  const [dataAlignment, setDataAlignment] = React.useState({
    show: false,
    alignment: 0
  });

  const handleGraphing = (data) => {
    fig.clearData();
    const dataTypes = Object.keys(data.Timeseries);
    
    if (fig.fresh) {
      let ax = fig.subplots(dataTypes.length, 1, {sharey: false, sharex: true});

      for (let i in dataTypes) {
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[i]);
      }
    }
    
    var ax = fig.getAxes();
    for (let i in dataTypes) {
      for (let j in data.Timeseries[dataTypes[i]]) {
        var timeArray = Array(data.Timeseries[dataTypes[i]][j].length).fill(0).map((value, index) => new Date(data.ChannelInfo[dataTypes[i]][j].StartTime*1000 + index*1000/data.ChannelInfo[dataTypes[i]][j].SamplingRate));
        fig.plot(timeArray, data.Timeseries[dataTypes[i]][j], {
          linewidth: 0.5,
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
          meta: data.ChannelInfo[dataTypes[i]][j].RecordingUID
        }, ax[i]);
      }

      for (let j = 0; j < data.Annotations[dataTypes[i]].length; j++) {
        for (let evi = 0; evi < data.Annotations[dataTypes[i]][j].length; evi++) {
          fig.scatter([new Date(data.Annotations[dataTypes[i]][j][evi].time*1000)], [0], {
            color: "#AA0000",
            size: 10,
            name: data.Annotations[dataTypes[i]][j][evi].name,
            showlegend: false,
            legendgroup: data.Annotations[dataTypes[i]][j][evi].name,
            hovertemplate: "  %{x} <br>  " + data.Annotations[dataTypes[i]][j][evi].name + "<extra></extra>"
          }, ax[i]);
        }
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
    console.log(dataToRender);
    if (dataToRender) {
      handleGraphing(dataToRender);
    } else {
      fig.purge();
      setShow(false);
    }
  }, [dataToRender, language]);

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
        console.log(data)
        setEventInfo((eventInfo) => {
          eventInfo.time = new Date(data.points[0].x).getTime();
          eventInfo.recording_uid = data.points[0].fullData.meta;
          return {...eventInfo};
        });
      });
    }
  }, [ref.current, dataToRender]);

  return (
    <MDBox ref={ref} id={figureTitle} onContextMenu={(event) => {
      event.preventDefault();
      setContextMenu(
        contextMenu === null ? {
          mouseX: event.clientX + 2,
          mouseY: event.clientY - 6,
        } : null
      );
    }} style={{marginTop: 5, marginBottom: 10, height: figureHeight, width: "100%", display: show ? "" : "none"}}>
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
          setEventInfo({...eventInfo, name: "", show: true});
        }}>{"Add New Event"}</MenuItem>
        <MenuItem onClick={() => {
          setContextMenu(null);
          handleDeleteEvent(eventInfo);
          }}>{"Delete Event"}</MenuItem>
        <MenuItem onClick={() => {
          setContextMenu(null);
          setDataAlignment({...dataAlignment, show: true});
          }}>{"Adjust Alignment"}</MenuItem>
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
                    placeholder={dictionary.ParticipantOverview.TagNames[language]}
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
                options={annotations.map((value) => ({
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
      
      <Dialog open={dataAlignment.show} onClose={() => setDataAlignment({show: false, alignment: 0})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {"Adjust Secondary Recording Alignment"} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <TextField
            variant="standard"
            margin="dense"
            type={"number"}
            label="Time Shift toward Right (ms)"
            placeholder={"Enter Time Shift to be applied to Power Channel"}
            value={dataAlignment.alignment}
            onChange={(event) => setDataAlignment({...dataAlignment, alignment: event.target.value})}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setDataAlignment({...dataAlignment, show: false})}>Cancel</MDButton>
          <MDButton color="info" onClick={() => handleAdjustAlignment(dataAlignment.alignment).then((response) => {
            if (response) {
              setDataAlignment({...dataAlignment, show: false})
            }
          })}>Add</MDButton>
        </DialogActions>
      </Dialog>
    </MDBox>
  );
}

export default React.memo(TimeSeriesVisualization);