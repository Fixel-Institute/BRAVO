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
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import { Autocomplete, Dialog, DialogContent, TextField, DialogActions, Grid, Menu, MenuItem } from "@mui/material";
import { createFilterOptions } from "@mui/material/Autocomplete";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

const filter = createFilterOptions();

function TimeDomainFigure({dataToRender, height, handleAddEvent, handleDeleteEvent, annotations, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const [contextMenu, setContextMenu] = React.useState(null);
  const [eventInfo, setEventInfo] = React.useState({
    name: "",
    time: 0,
    duration: 0,
    show: false
  });

  const handleGraphing = (data, channelInfos) => {
    fig.clearData();
    let xlim = [0,0];

    if (fig.fresh) {
      var axLength = 0;
      var channelInfo = null;
      for (var i in data) {
        if (data[i].Channels.length > axLength) {
          axLength = data[i].Channels.length;
          channelInfo = channelInfos[i];
        }
      }

      var ax = fig.subplots(axLength, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      for (var i in ax) {
        fig.setYlim([-100,100],ax[i]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[i]);

        const [side, target] = channelInfo[i].Hemisphere.split(" ");
        const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfo[i].Contacts[0]}-E${channelInfo[i].Contacts[1]}`;
        fig.setSubtitle(`${titleText}`,ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);

    }

    for (var i in data) {
      for (var j in data[i].Channels) {
        var timeArray = Array(data[i]["Stream"][j].length).fill(0).map((value, index) => new Date(data[i].Timestamp*1000 + 4*index));
        if (xlim[0] == 0 || xlim[0] > data[i].Timestamp) {
          xlim[0] = data[i].Timestamp;
        }
        if (xlim[1] == 0 || xlim[1] < data[i].Timestamp+0.004*data[i]["Stream"][j].length) {
          xlim[1] = data[i].Timestamp+0.004*data[i]["Stream"][j].length;
        }
        
        for (var k in ax) {
          
          if (!ax[k].title) {
            ax[k].title = data[i].Channels[j];
            fig.plot(timeArray, data[i]["Stream"][j], {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
            }, ax[k]);

            for (let l = 0; l < data[i].Annotations.length; l++) {
              fig.scatter([new Date(data[i].Annotations[l].Time*1000)], [0], {
                color: "#AA0000",
                size: 10,
                name: data[i].Annotations[l].Name,
                showlegend: false,
                legendgroup: data[i].Annotations[l].Name,
                hovertemplate: "  %{x} <br>  " + data[i].Annotations[l].Name + "<extra></extra>"
              }, ax[k]);
                
              if (data[i].Annotations[l].Duration > 0) {
                fig.addShadedArea([new Date(data[i].Annotations[l].Time*1000), new Date((data[i].Annotations[l].Time+data[i].Annotations[l].Duration)*1000)], null, {
                  color: "#AA0000",
                  name: data[i].Annotations[l].Name,
                  legendgroup: data[i].Annotations[l].Name,
                  showlegend: false,
                });
              }
            }
            break;
          } else if (ax[k].title == data[i].Channels[j]) {
            fig.plot(timeArray, data[i]["Stream"][j], {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
            }, ax[k]);
            
            for (let l = 0; l < data[i].Annotations.length; l++) {
              fig.scatter([new Date(data[i].Annotations[l].Time*1000)], [0], {
                color: "#AA0000",
                size: 10,
                name: data[i].Annotations[l].Name,
                showlegend: false,
                legendgroup: data[i].Annotations[l].Name,
                hovertemplate: "  %{x} <br>  " + data[i].Annotations[l].Name + "<extra></extra>"
              }, ax[k]);
                
              if (data[i].Annotations[l].Duration > 0) {
                fig.addShadedArea([new Date(data[i].Annotations[l].Time*1000), new Date((data[i].Annotations[l].Time+data[i].Annotations[l].Duration)*1000)], null, {
                  color: "#AA0000",
                  name: data[i].Annotations[l].Name,
                  legendgroup: data[i].Annotations[l].Name,
                  showlegend: false,
                });
              }
            }
            break;
          }
        }
      }
    }

    if (!data) {
      fig.purge();
      setShow(false);
    } else {
      fig.setXlim([new Date(xlim[0]*1000), new Date(xlim[1]*1000)])
      fig.render();
      setShow(true);
    }
  }

  // Refresh Left Figure if Data Changed
  React.useEffect(() => {
    if (dataToRender) handleGraphing(dataToRender.data, dataToRender.ChannelInfos);
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
        setEventInfo((eventInfo) => {
          eventInfo.time = new Date(data.points[0].x).getTime();
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
    }} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}>
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
    </MDBox>
  );
}

export default TimeDomainFigure;