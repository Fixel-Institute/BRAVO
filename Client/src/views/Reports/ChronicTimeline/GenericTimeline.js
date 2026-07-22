/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useCallback, useEffect, useState, useMemo } from "react";
import { useResizeDetector } from 'react-resize-detector';
import * as Math from "mathjs";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

import moment from "moment";
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { TimePicker } from "@mui/x-date-pickers";

import colormap from "colormap";
import { TwitterPicker, BlockPicker } from "react-color";

import { Card, Menu, MenuItem, Dialog, DialogContent, Grid, IconButton, Popover, TextField, DialogActions } from "@mui/material";
import { createFilterOptions } from "@mui/material/Autocomplete";

import { dictionary, dictionaryLookup } from "assets/translation";
import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { usePlatformContext } from "context";

const filter = createFilterOptions();

export default function GenericTimeline({data, availableChannels, annotations, handleAddEvent, handleDeleteEvent, updateColor, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [contextMenu, setContextMenu] = useState(null);
  const [eventInfo, setEventInfo] = useState({ name: "", time: 0, enddate: null, endtime: null, show: false });
  const [popup, setPopupState] = useState({item: ""});

  const [fig, setFig] = useState(null);
  const [renderData, setRenderData] = useState(null);
  const [annotationState, setAnnotationState] = useState({});

  useEffect(() => {
    const fig = new PlotlyRenderManager(figureTitle, language);
    setFig(fig);
  }, [figureTitle]);

  useEffect(() => {
    if (!fig) return;
    
    if (!fig.fresh) {
      fig.clearData();
    }

    const ax = fig.subplots(availableChannels.active.length, 1, {sharex: true, sharey: true});
    let subplotIds = [];
    for (let i in availableChannels.active) {
      subplotIds.push(`${availableChannels.active[i]}`);
      fig.setYlabel(``, {fontSize: 15}, ax[i]);
      fig.setSubtitle(`${availableChannels.active[i]}`,ax[i]);
    }
    fig.setSubplotId(subplotIds);
    
    fig.setLegend({ tracegroupgap: 5, xanchor: "left", y: 0.5, });
    fig.setLayoutProps({ barmode: "group", hovermode: "x", hoverdistance: 1 });

    if (!fig.fresh) {
      setRenderData([...renderData]);
    }

  }, [fig, availableChannels]);

  useEffect(() => {
    if (!fig) return;

    let lineSeries = [];
    let barSeries = [];
    
    for (let i in data) {
      if (data[i].AnalysisType === "CustomizedTimelineData") {
        let xData = [];
        for (let t in data[i].Time) {
          xData.push(new Date(data[i].Time[t]*1000));
          if (typeof data[i].Duration === "number") {
            xData.push(new Date(data[i].Time[t]*1000 + data[i].Duration*1000));
          } else {
            xData.push(new Date(data[i].Time[t]*1000 + data[i].Duration[t]*1000));
          }
        }

        for (let j in data[i].ChannelNames) {
          if (data[i].ChannelUnits[j] === "Category") {
            const yData = [];
            for (let t in data[i].Time) {
              yData.push(data[i]["Data"][j][t]);
            }

            barSeries.push({
              type: "bar",
              x: data[i]["Duration"].map((a,t) => new Date(a)*1000), y: data[i]["Data"][j], base: data[i].Time.map((a) => new Date(a*1000)),
              options: {
                id: data[i].ChannelNames[j],
                linewidth: 2,
                line: {shape: "hvh"},
                color: "#000000",
                showlegend: false,
                orientation: "h",
                hovertemplate: "%{y}<extra></extra>"
              }, 
              axName: data[i].ChannelNames[j]
            });
          } else {
            const yData = [];
            for (let t in data[i].Time) {
              yData.push(data[i]["Data"][j][t]);
              yData.push(data[i]["Data"][j][t]);
            }
            if ( yData.filter((a,i) => yData[i]).length === 0 ) continue;

            lineSeries.push({
              type: "lineseries",
              x: xData.filter((a,i) => yData[i]), y: yData.filter((a,i) => yData[i]),
              options: {
                id: data[i].ChannelNames[j],
                linewidth: 2,
                color: "#000000",
                hovertemplate: "%{y}<extra></extra>"
              }, 
              axName: data[i].ChannelNames[j]
            });
          }
        }
      } else if (data[i].AnalysisType === "CustomizedSurveyData") {
        let xData = [];
        for (let t in data[i].Time) {
          xData.push(new Date(data[i].Time[t]*1000));
        }

        for (let j in data[i].ChannelNames) {
          const yData = [];
          for (let t in data[i].Time) {
            yData.push(data[i]["Data"][j][t]);
          }
          if ( yData.filter((a,i) => yData[i]).length === 0 ) continue;

          lineSeries.push({
            type: "scatter",
            x: xData.filter((a,i) => yData[i]), y: yData.filter((a,i) => yData[i]),
            options: {
              id: data[i].ChannelNames[j],
              color: "#000000",
              hovertemplate: "%{y}<extra></extra>"
            }, 
            axName: data[i].ChannelNames[j]
          });
        }

      } else if (data[i].AnalysisType === "ChronicSpectrum") {
        for (let j in data[i].ChannelNames) {
          lineSeries.push({
            type: "surf",
            x: data[i].Time[j].map((a) => new Date(a*1000)), y: data[i].Frequency[j], z: data[i].Data[j],
            options: {
              zlim: data[i].CLim[j],
              hovertemplate: `  %{y:.2f} ${"Hz"}<br>  %{x} <br>  %{z:.2f} ${"dB"} <extra></extra>`,
            }, 
            axName: data[i].ChannelNames[j]
          });
        }
      }
    }

    if (barSeries.length > 0) {
      let allAx = barSeries.map((a) => a.axName);
      allAx = [...new Set(allAx)];

      for (let n in allAx) {
        let xaxis = [];
        let yaxis = [];
        let base = [];
        let options = {};
        for (let i in barSeries) {
          if (barSeries[i].axName !== allAx[n]) continue;
          
          options = barSeries[i].options;
          xaxis.push(...barSeries[i].x);
          yaxis.push(...barSeries[i].y);
          base.push(...barSeries[i].base);
        }

        lineSeries.push({
          type: "bar",
          x: xaxis, y: yaxis, base: base,
          options: options, 
          axName: allAx[n]
        });
      }
    }

    for (let i in annotations) {
      if (!annotations[i].Duration) {
        lineSeries.push({
          type: "annotations",
          x: [new Date(annotations[i].Date*1000), new Date(annotations[i].Date*1000)], y: [-50000, 50000],
          options: {
            id: annotations[i].Id,
            name: annotations[i].Name,
            linewidth: 2,
            color: annotationState[annotations[i].Name] ? annotationState[annotations[i].Name].color : "#00FF00",
            hovertemplate: "  %{x} <br>  " + annotations[i].Name + " <extra></extra>"
          }, 
          axName: "all"
        });
      } else {
        lineSeries.push({
          type: "shading",
          x: [new Date(annotations[i].Date*1000), new Date(annotations[i].Date*1000 + annotations[i].Duration*1000)],
          xDot: [new Date(annotations[i].Date*1000)],
          y: [-50000, 50000],
          yDot: [0],
          options: {
            id: annotations[i].Id,
            name: annotations[i].Name,
            size: 10,
            color: annotationState[annotations[i].Name] ? annotationState[annotations[i].Name].color : "#00FF00",
            alpha: 0.3, 
            hovertemplate: "  %{x} <br>  " + annotations[i].Name + " <extra></extra>"
          }, 
          axName: "all"
        })
      }
    }

    setRenderData(lineSeries);
    
  }, [fig, data, annotations]);

  useEffect(() => {
    setAnnotationState((annotationState) => {
      const colors = colormap({
        colormap: 'hsv',
        nshades: 12,
        format: 'hex',
        alpha: 1,
      });

      for (let i in annotations) {
        if (!annotationState[annotations[i].Name]) {
          annotationState[annotations[i].Name] = {show: true, color: colors[10-Object.keys(annotationState).length > 0 ? 10-Object.keys(annotationState).length : 0]}
        }
      }
      return {...annotationState}
    })
  }, [annotations]);

  useEffect(() => {
    if (!fig) return;

    setRenderData((renderData) => {
      for (let i in renderData) {
        if (renderData[i].type === "shading") {
          renderData[i].options.color = annotationState[renderData[i].options.name] ? annotationState[renderData[i].options.name].color : "#00FF00";
          renderData[i].options.hidden = annotationState[renderData[i].options.name] ? !annotationState[renderData[i].options.name].show : false;
        }
      }
      return [...renderData];
    })
  }, [fig, annotationState]);

  useEffect(() => {
    updateColor(annotationState);
  }, [annotationState]);

  useEffect(() => {
    if (!fig || !renderData) return;

    fig.traces = [];
    let yLim = {};
    let clim = {};

    for (let i in renderData) {
      const ax = fig.getAxes(renderData[i].axName);
      if (renderData[i].type === "surf" && ax) {
        if (!clim[renderData[i].axName]) {
          clim[renderData[i].axName] = {
            caxis: fig.createColorAxis({
              colorscale: "Jet",
              colorbar: {y: (ax.ydomain[0]+ax.ydomain[1])/2, len: ax.ydomain[1]-ax.ydomain[0]},
              clim: renderData[i].options.zlim,
            }),
            limits: [0,0]
          }
        }
      }

      if (renderData[i].type == "lineseries") {
        if (!yLim[renderData[i].axName]) yLim[renderData[i].axName] = [0,1];
        if (!renderData[i].options.hidden && ax) {
          const currentMax = Math.max(renderData[i].y.filter((a) => a !== null));
          if (currentMax > yLim[renderData[i].axName][1]) {
            yLim[renderData[i].axName][1] = currentMax*1.1;
          };
          const currentMin = Math.min(renderData[i].y.filter((a) => a !== null));
          if (currentMin < yLim[renderData[i].axName][0]) {
            yLim[renderData[i].axName][0] = currentMin*1.1;
          };
          fig.setYlim(yLim[renderData[i].axName], ax);
          fig.setScaleType("linear", "y", ax);
          fig.plot(renderData[i].x, renderData[i].y, renderData[i].options, ax);
        }
      } else if (renderData[i].type === "scatter") {
        if (!yLim[renderData[i].axName]) yLim[renderData[i].axName] = [0,1];
        if (!renderData[i].options.hidden && ax) {
          const currentMax = Math.max(renderData[i].y.filter((a) => a !== null));
          if (currentMax > yLim[renderData[i].axName][1]) {
            yLim[renderData[i].axName][1] = currentMax*1.1;
          };
          const currentMin = Math.min(renderData[i].y.filter((a) => a !== null));
          if (currentMin < yLim[renderData[i].axName][0]) {
            yLim[renderData[i].axName][0] = currentMin*1.1;
          };
          fig.setYlim(yLim[renderData[i].axName], ax);
          fig.setScaleType("linear", "y", ax);
          fig.scatter(renderData[i].x, renderData[i].y, renderData[i].options, ax);
        }
        
      } else if (renderData[i].type === "surf") {
        if (!renderData[i].options.hidden && ax) {
          fig.setScaleType("linear", "y", ax);
          if (renderData[i].options.zlim[0] < clim[renderData[i].axName].limits[0] || clim[renderData[i].axName].limits[0] == 0) clim[renderData[i].axName].limits[0] = renderData[i].options.zlim[0];
          if (renderData[i].options.zlim[1] > clim[renderData[i].axName].limits[1] || clim[renderData[i].axName].limits[1] == 0) clim[renderData[i].axName].limits[1] = renderData[i].options.zlim[1];
          fig.surf(renderData[i].x, renderData[i].y, renderData[i].z, {...renderData[i].options,
            coloraxis: clim[renderData[i].axName].caxis
          }, ax);
        }
      } else if (renderData[i].type == "bar") {
        if (!renderData[i].options.hidden && ax) {
          fig.setScaleType("category", "y", ax);
          fig.setScaleType("date", "x", ax);
          fig.setAxisProps({
            categoryorder: "array",
            categoryarray: ["deep", "light", "rem", "wake", "awake", "asleep"] 
          }, "y", ax);
          fig.bar(renderData[i].x, renderData[i].y, renderData[i].base, renderData[i].options, ax);
        }
      }
    }

    for (let i in renderData) {
      if (renderData[i].axName == "all") { 
        if (renderData[i].type === "shading" && !renderData[i].options.hidden) {
          const ax = fig.getAxes();
          for (let j in ax) {
            fig.addShadedArea(renderData[i].x, yLim[ax[j].id], {...renderData[i].options, hovertemplate: "<extra></extra>"}, ax[j]);
            fig.scatter(renderData[i].xDot, renderData[i].yDot, renderData[i].options, ax[j]);
          }
        }
      }
    }

    for (let key in clim) {
      fig.setCLim(clim[key].limits, clim[key].caxis);
    }
    fig.render();

    const ref = document.getElementById(figureTitle);
    if (ref) {
      ref.addEventListener("contextmenu", fig.onClick);
      document.addEventListener("PlotlyClick", plotly_onClick);
      document.addEventListener("PlotlyRelayout", plotly_onZoom);
      return () => {
        ref.removeEventListener("contextmenu", fig.onClick);
        document.removeEventListener("PlotlyClick", plotly_onClick);
        document.removeEventListener("PlotlyRelayout", plotly_onZoom);
      }
    };
  }, [fig, renderData]);

  const plotly_onClick = (evt) => {
    setEventInfo((eventInfo) => {
      eventInfo.channel_name = evt.detail.ax.id;
      eventInfo.time = new Date(evt.detail.x).getTime();
      eventInfo.enddate = new moment(new Date(evt.detail.x));
      eventInfo.endtime = new moment(new Date(evt.detail.x));
      return eventInfo;
    });
  }

  const plotly_onZoom = (evt) => {
    
  }

  const onResize = useCallback(() => {
    if (!fig) return;

    fig.refresh();
  }, [fig]);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });

  const onContextMenu = (event) => {
    event.preventDefault();
    setContextMenu( contextMenu === null ? { mouseX: event.clientX + 2, mouseY: event.clientY - 6, } : null );
  }

  return (
    <Grid container spacing={2} sx={{marginTop: 1}}>
      <Grid item xs={12}>
        <MDBox ref={ref} onContextMenu={onContextMenu} id={figureTitle} style={{marginBottom: 10, height: 200*availableChannels.active.length+100, width: "100%", display: availableChannels.active.length == 0 ? "none" : ""}}>
          <Menu
            open={contextMenu !== null}
            onClose={() => setContextMenu(null)}
            anchorReference="anchorPosition"
            anchorPosition={ contextMenu !== null ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined }
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
            <MDBox px={2} pt={2} sx={{minWidth: 500}}>
              <MDTypography variant="h5">
                {"New Custom Event"} 
              </MDTypography>
              <MDTypography variant="h6">
                {"Time: "}{new Date(eventInfo.time).toLocaleString("en-US", {
                  year: "numeric", 
                  month: "long",
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  timeZoneName: "longGeneric"
                })} 
              </MDTypography>
            </MDBox>
            <DialogContent>
              <Grid container spacing={2}>
                <Grid item xs={12} style={{display: "flex", flexDirection: "column"}}>
                  <TextField
                    variant="standard"
                    margin="dense"
                    id={"event-annotation"}
                    type={"text"}
                    label="Annotation Name"
                    placeholder={"Annotation Name"}
                    value={eventInfo.name}
                    onChange={(event) => setEventInfo({...eventInfo, name: event.target.value})}
                  />
                </Grid>
                <Grid item xs={12} style={{display: "flex", flexDirection: "column"}}>
                  <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"} justifyContent={"space-between"}>
                    <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
                      <DatePicker
                        label="Date"
                        value={eventInfo.enddate}
                        onChange={(newDate) => {
                          setEventInfo({...eventInfo, enddate: newDate});
                        }}
                        renderInput={(params) => <TextField {...params} />}
                      />
                    </LocalizationProvider>
                    <LocalizationProvider dateAdapter={AdapterMoment}>
                      <TimePicker
                        label="Time"
                        value={eventInfo.endtime}
                        onChange={(newDate) => {
                          setEventInfo({...eventInfo, endtime: newDate});
                        }}
                        renderInput={(params) => <TextField {...params} />}
                      />
                    </LocalizationProvider>
                  </MDBox>
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
      </Grid>
    </Grid>
  );
}
