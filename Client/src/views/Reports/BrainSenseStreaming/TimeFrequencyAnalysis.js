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

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function TimeFrequencyAnalysis({dataToRender, channelInfos, handleAddEvent, handleDeleteEvent, annotations, height, figureTitle}) {
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

  const handleGraphing = (data) => {
    fig.clearData();

    let yLimCap = 5000;
    if (fig.fresh) {
      if (data.Channels.length == 2) {
        let ax = fig.subplots(7, 1, {sharey: false, sharex: true});

        for (var i in data.Channels) {
          fig.setYlim([-200, 200], ax[0+i*3]);
          fig.setYlim([0, 100], ax[1+i*3]);
          fig.setYlim([0, 5000], ax[2+i*3]);

          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[i*3]);
          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[i*3+1]);
          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*3+2]);
        }

        for (var i in data.Channels) {
          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          if (channelInfos[i].Hemisphere == channelInfos[i].CustomName) {
            const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
            fig.setSubtitle(`${titleText}`,ax[i*3]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
          } else {
            const titleText = `${channelInfos[i].CustomName} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
            fig.setSubtitle(`${titleText}`,ax[i*3]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
          }
        }
        fig.setSubtitle(`${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "Stimulation", language)}`,ax[6]);

        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[6]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[6]);
      } else {
        let ax = fig.subplots(4, 1, {sharey: false, sharex: true});
        
        for (var i in data.Channels) {
          fig.setYlim([-200, 200], ax[0+i*3]);
          fig.setYlim([0, 100], ax[1+i*3]);
          fig.setYlim([0, 5000], ax[2+i*3]);
          
          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          if (channelInfos[i].Hemisphere == channelInfos[i].CustomName) {
            const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
            fig.setSubtitle(`${titleText}`,ax[i*3]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
          } else {
            const titleText = `${channelInfos[i].CustomName} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
            fig.setSubtitle(`${titleText}`,ax[i*3]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
            fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
          }
        }
        fig.setSubtitle(`${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "Stimulation", language)}`,ax[3]);

        fig.setYlim([-200, 200], ax[0]);

        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[0]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[1]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[2]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[3]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[3]);
        
      }
    }

    if (data.Channels.length == 2) {
      let ax = fig.getAxes();
      for (var i in data.Channels) {
        var timeArray = Array(data.Stream[i].RawData.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + 4*index));
        fig.plot(timeArray, data.Stream[i].RawData, {
          linewidth: 0.5,
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
        }, ax[i*3 + 0]);
        fig.setXlim([timeArray[0],timeArray[timeArray.length-1]], ax[0]);

        for (let j = 0; j < data.Annotations.length; j++) {
          fig.scatter([new Date(data.Annotations[j].Time*1000)], [0], {
            color: "#AA0000",
            size: 10,
            name: data.Annotations[j].Name,
            showlegend: false,
            legendgroup: data.Annotations[j].Name,
            hovertemplate: "  %{x} <br>  " + data.Annotations[j].Name + "<extra></extra>"
          }, ax[i*3 + 0]);
            
          if (data.Annotations[j].Duration > 0) {
            fig.addShadedArea([new Date(data.Annotations[j].Time*1000), new Date((data.Annotations[j].Time+data.Annotations[j].Duration)*1000)], {
              color: "#AA0000",
              name: data.Annotations[j].Name,
              legendgroup: data.Annotations[j].Name,
              showlegend: false,
            });
          }
        }

        var timeArray = Array(data.Stream[i].Spectrogram.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + data.Stream[i].Spectrogram.Time[index]*1000));
        fig.surf(timeArray, data.Stream[i].Spectrogram.Frequency, data.Stream[i].Spectrogram.Power, {
          zlim: [-20, 20],
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 1-(1/14)-(i*3+1)*(1/7), len: (1/7)},
            clim: data.Stream[i].Spectrogram.ColorRange,
          }),
        }, ax[i*3 + 1]);

        for (var powerband of data.PowerBand) {
          if (powerband.Name == data.Channels[i]) {
            var timeArray = Array(powerband.Time.length).fill(0).map((value, index) => new Date(data.PowerTimestamp*1000 + powerband.Time[index]*1000));
            fig.plot(timeArray, powerband.Power, {
              linewidth: 2,
              hovertemplate: `  %{y:.2f}<extra></extra>`,
            }, ax[i*3 + 2]);

            if (powerband.Power.some((value) => value > yLimCap)) {
              yLimCap = Math.max(powerband.Power);
              yLimCap = Math.ceil(yLimCap / 5000) * 5000;
              fig.setYlim([0, yLimCap], ax[2]);
            }
  
            const [side, target] = channelInfos[i].Hemisphere.split(" ");
            if (data.Info.Therapy[side].AdaptiveTherapyStatus == "ADBSStatusDef.RUNNING" || data.Info.Therapy[side].AdaptiveTherapyStatus == "ADBSStatusDef.SUSPENDED") {
              fig.plot([timeArray[0],timeArray[timeArray.length-1]], [data.Info.Therapy[side].LowerLfpThreshold, data.Info.Therapy[side].LowerLfpThreshold], {
                linewidth: 2,
                color: "r",
                hovertemplate: `  %{y:.2f}<extra></extra>`,
              }, ax[i*3 + 2]);
            }
          }
        }
      }
    } else {
      let ax = fig.getAxes();

      var timeArray = Array(data.Stream[0].RawData.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + 4*index));
      fig.plot(timeArray, data.Stream[0].RawData, {
        linewidth: 0.5,
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
      }, ax[0]);
      fig.setXlim([timeArray[0],timeArray[timeArray.length-1]], ax[0]);

      for (let j = 0; j < data.Annotations.length; j++) {
        fig.scatter([new Date(data.Annotations[j].Time*1000)], [0], {
          color: "#AA0000",
          size: 10,
          name: data.Annotations[j].Name,
          showlegend: false,
          legendgroup: data.Annotations[j].Name,
          hovertemplate: "  %{x} <br>  " + data.Annotations[j].Name + "<extra></extra>"
        }, ax[0]);
          
        if (data.Annotations[j].Duration > 0) {
          fig.addShadedArea([new Date(data.Annotations[j].Time*1000), new Date((data.Annotations[j].Time+data.Annotations[j].Duration)*1000)], {
            color: "#AA0000",
            name: data.Annotations[j].Name,
            legendgroup: data.Annotations[j].Name,
            showlegend: false,
          });
        }
      }

      var timeArray = Array(data.Stream[0].Spectrogram.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + data.Stream[0].Spectrogram.Time[index]*1000));
      fig.surf(timeArray, data.Stream[0].Spectrogram.Frequency, data.Stream[0].Spectrogram.Power, {
        zlim: [-20, 20],
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
        coloraxis: fig.createColorAxis({
          colorscale: "Jet",
          colorbar: {y: 0.65, len: (1/4)},
          clim: data.Stream[0].Spectrogram.ColorRange,
        }),
      }, ax[1]);

      for (var powerband of data.PowerBand) {
        if (powerband.Name == data.Channels[0]) {
          var timeArray = Array(powerband.Time.length).fill(0).map((value, index) => new Date(data.PowerTimestamp*1000 + powerband.Time[index]*1000));
          fig.plot(timeArray, powerband.Power, {
            linewidth: 2,
            hovertemplate: `  %{y:.2f}<extra></extra>`,
          }, ax[2]);

          if (powerband.Power.some((value) => value > yLimCap)) {
            yLimCap = Math.max(powerband.Power);
            yLimCap = Math.ceil(yLimCap / 5000) * 5000;
            fig.setYlim([0, yLimCap], ax[2]);
          }

          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          if (data.Info.Therapy[side].AdaptiveTherapyStatus == "ADBSStatusDef.RUNNING" || data.Info.Therapy[side].AdaptiveTherapyStatus == "ADBSStatusDef.SUSPENDED") {
            fig.plot([timeArray[0],timeArray[timeArray.length-1]], [data.Info.Therapy[side].LowerLfpThreshold, data.Info.Therapy[side].LowerLfpThreshold], {
              linewidth: 2,
              color: "r",
              hovertemplate: `  %{y:.2f}<extra></extra>`,
            }, ax[2]);
          }
        }
      }
    }

    let ax = fig.getAxes();
    for (var stimulation of data.Stimulation) {
      var stimulationLineColor;
      if (stimulation.Name.endsWith("RIGHT")) {
        stimulationLineColor = "#FCA503";
      } else {
        stimulationLineColor = "#253EF7";
      }
      var timeArray = Array(stimulation.Time.length).fill(0).map((value, index) => new Date(data.PowerTimestamp*1000 + stimulation.Time[index]*1000));
      fig.plot(timeArray, stimulation.Amplitude, {
        linewidth: 3,
        color: stimulationLineColor,
        shape: "hv",
        hovertemplate: ` ${stimulation.Name} %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)}<br>  %{x} <extra></extra>`,
        name: stimulation.Name,
        showlegend: true
      }, ax[ax.length-1]);
    }

    fig.setLegend({
      xanchor: "right",
      y: 1/ax.length - (0.15/ax.length)
    });

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
    if (dataToRender) handleGraphing(dataToRender);
    else {
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

export default TimeFrequencyAnalysis;