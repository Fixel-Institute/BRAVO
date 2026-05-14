/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useCallback, useState, useEffect, useMemo } from "react";
import { useResizeDetector } from 'react-resize-detector';

import LoadingProgress from "components/LoadingProgress";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import FormField from "components/MDInput/FormField";
import MDButton from "components/MDButton";
import { Autocomplete, Dialog, DialogContent, TextField, DialogActions, Grid, Menu, MenuItem } from "@mui/material";
import { createFilterOptions } from "@mui/material/Autocomplete";

import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';

import * as math from "mathjs"
import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function MedtronicCircadianRhythm({dataToRender, annotations, timelineRange, circadianState, channelSelector, onSelection, activeChannel, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [fig, setFig] = useState(null);
  const [renderData, setRenderData] = useState(null);
  const [cacheData, setCacheData] = useState({});
  const [activeDevice, setActiveDevice] = useState("");
  const [timerange, setTimerange] = useState({device: "", start: null, end: null});

  useEffect(() => {
    const fig = new PlotlyRenderManager(figureTitle, language);
    setFig(fig);
  }, [figureTitle]);

  useEffect(() => {
    setTimerange({...timelineRange});
  }, [timelineRange])

  useEffect(() => {
    if (!fig) return;
    
    if (!fig.fresh) {
      fig.clearData();
    }

    let ax = fig.subplots(1, 1, {sharex: true, sharey: true});
    fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[0]);
    fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[0]);
    fig.setLayoutProps({
      bargap: 0.01,
      hovermode: "x",
      dragmode: onSelection ? "select" : "zoom",
    });

    fig.addDualYAxis(ax[0]);
    fig.setYlabel("Event Count", {fontSize: 15}, ax[1]);
    fig.setAxisProps({
      title: {
        font: {
          color: "#FF0000"
        }
      },
      tickcolor:  "#FF0000",
      tickfont: {
        color: "#FF0000"
      },
      showgrid: false
    }, "y", ax[1]);

    fig.setAxisProps({
      tickformat: "%H:%M"
    }, "x", ax[0]);

    if (!fig.fresh) {
      refreshRender();
    }

  }, [fig]);

  useEffect(() => {
    if (!fig) return;
    let graphSeries = [{
      type: "line", x: [], y: [], error_y: [],
      line_options: {
        linewidth: 2,
        color: "#000000",
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)}<extra></extra>`,
        showlegend: false
      }, 
      shade_options: {
        color: "#000000",
        alpha: 0.3,
        showlegend: false
      }, 
    }, {
      type: "line", x: [], y: [], error_y: [],
      line_options: {
        linewidth: 2,
        color: "#bb2b2b",
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, " mA", language)}<extra></extra>`,
        showlegend: false
      }, 
      shade_options: {
        color: "#bb2b2b",
        alpha: 0.3,
        showlegend: false
      }, 
    }, {
      type: "bar", x: [], y: [], options: {
        width: 600000,
        opacity: 0.3,
        facecolor: "#196ac7",
        showlegend: false,
      }
    }, {
      type: "histogram", x: [], options: {
        opacity: 1,
        xbins: {
          size: 5,
        },
        facecolor: "#000000",
        hovertemplate: `  %{x} ${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)}<extra></extra>`,
        showlegend: false,
      }
    }, {
      type: "threshold", x: [], y: [],
      options: {
        linewidth: 2,
        color: "#00942c",
        hovertemplate: `  25% Threshold: %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)}<extra></extra>`,
        showlegend: false
      }
    }, {
      type: "threshold", x: [], y: [],
      options: {
        linewidth: 2,
        color: "#00942c",
        hovertemplate: `  75% Threshold: %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)}<extra></extra>`,
        showlegend: false
      }
    }, {
      type: "threshold", x: [], y: [],
      options: {
        linewidth: 2,
        color: "#00942c",
        hovertemplate: `  50% Threshold: %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)}<extra></extra>`,
        showlegend: false
      }
    }];

    let timePeriods = [0,0];
    if (timerange.start) {
      timePeriods[0] = timerange.start.toDate().getTime() / 1000;
    }
    if (timerange.end) {
      timePeriods[1] = timerange.end.toDate().getTime() / 1000;
    }

    let xData = [], yData = [], events = [];
    let yStim = [];
    for (let i in dataToRender) {
      for (let j in dataToRender[i].ChannelNames) {
        if (dataToRender[i].Description[j].Bypass) continue;
        if (dataToRender[i].ChannelNames[j].endsWith(" LFP")) {
          const channelName = dataToRender[i].ChannelNames[j].replace(" LFP", "");
          const therapyName = channelName + " (" + dataToRender[i].Description[j].Stimulation + " Sense: " + dataToRender[i].Description[j].SensingFrequency + ")";
          if (activeChannel == therapyName) {
            for (let k in dataToRender[i].ChannelNames) {
              if (dataToRender[i].ChannelNames[k] == dataToRender[i].ChannelNames[j].replace(" LFP", " Amplitude")) {
                yStim.push(...dataToRender[i].Data[k]);
              }
            }
            xData.push(...dataToRender[i].Time);
            yData.push(...dataToRender[i].Data[j]);
            events.push(...annotations.filter((a) => a.Date > dataToRender[i].Time[0] && a.Date < dataToRender[i].Time[dataToRender[i].Time.length-1]).map((a) => a.Date))
          } else if (activeChannel.startsWith("Time-based Assessment") && channelName === timerange.device) {
            for (let k in dataToRender[i].ChannelNames) {
              if (dataToRender[i].ChannelNames[k] == dataToRender[i].ChannelNames[j].replace(" LFP", " Amplitude")) {
                yStim.push(...dataToRender[i].Data[k].filter((a,k) => dataToRender[i].Time[k] > timePeriods[0] && dataToRender[i].Time[k] < timePeriods[1]));
              }
            }
            xData.push(...dataToRender[i].Time.filter((a) => a > timePeriods[0] && a < timePeriods[1]));
            yData.push(...dataToRender[i].Data[j].filter((a,k) => dataToRender[i].Time[k] > timePeriods[0] && dataToRender[i].Time[k] < timePeriods[1]));
          }
        }
      }
    }

    xData = xData.filter((a,i) => yData[i]);
    yStim = yStim.filter((a,i) => yData[i]);
    yData = yData.filter((a,i) => yData[i]);

    const timezoneOffset = new Date().getTimezoneOffset();
    xData = xData.map((a) => math.round(((a-timezoneOffset*60) % 86400) / 600) * 600000);
    events = events.map((a) => math.round(((a-timezoneOffset*60) % 86400) / 600) * 600000);
    const inRange = (time, ref, window) => {
      if (math.abs(time - ref) < window) return true; 
      if (math.abs(time+86400 - ref) < window) return true; 
      if (math.abs(time-86400 - ref) < window) return true; 
      return false
    }

    // Thresholds
    let thresholdXData = [3600*10*1000, 3600*18*1000];
    let thresholdYData = yData.filter((a,t) => inRange(xData[t],3600*14*1000,3600*4*1000));
    if (thresholdYData.length > 5) {
      let thresholds = math.quantileSeq(thresholdYData, [0.25, 0.75, 0.5]);
      graphSeries[4].x = thresholdXData.map((a) => new Date(a+timezoneOffset*60000));
      graphSeries[4].y = [thresholds[0], thresholds[0]];
      graphSeries[5].x = thresholdXData.map((a) => new Date(a+timezoneOffset*60000));
      graphSeries[5].y = [thresholds[1], thresholds[1]];
      graphSeries[6].x = thresholdXData.map((a) => new Date(a+timezoneOffset*60000));
      graphSeries[6].y = [thresholds[2], thresholds[2]];
    }

    setCacheData({xData: xData.map((a) => a+timezoneOffset*60000), yData: yData, yStim: yStim});

    const window = 1200000;
    const defaultTimeArray = new Array(145).fill(0).map((a,i) => i*600000);
    for (let i = 0; i < defaultTimeArray.length; i++) {
      graphSeries[0].x.push(new Date(defaultTimeArray[i]+timezoneOffset*60000));
      graphSeries[1].x.push(new Date(defaultTimeArray[i]+timezoneOffset*60000));

      if (i == 0 || i == 144) {
        let windowedData = yData.filter((a,t) => inRange(xData[t],defaultTimeArray[0],window) || inRange(xData[t],defaultTimeArray[144],window));
        if (windowedData.length > 0) {
          graphSeries[0].y.push(math.mean(windowedData));
          graphSeries[0].error_y.push(math.std(windowedData)/math.sqrt(windowedData.length)*2);
        } else {
          graphSeries[0].y.push(0);
          graphSeries[0].error_y.push(0);
        }

        windowedData = yStim.filter((a,t) => inRange(xData[t],defaultTimeArray[0],window) || inRange(xData[t],defaultTimeArray[144],window));
        if (windowedData.length > 0) {
          graphSeries[1].y.push(math.mean(windowedData));
          graphSeries[1].error_y.push(math.std(windowedData)/math.sqrt(windowedData.length)*2);
        } else {
          graphSeries[1].y.push(0);
          graphSeries[1].error_y.push(0);
        }
      } else {
        let windowedData = yData.filter((a,t) => inRange(xData[t],defaultTimeArray[i],window));
        if (windowedData.length > 0) {
          graphSeries[0].y.push(math.mean(windowedData));
          graphSeries[0].error_y.push(math.std(windowedData)/math.sqrt(windowedData.length)*2);
        } else {
          graphSeries[0].y.push(0);
          graphSeries[0].error_y.push(0);
        }
        
        windowedData = yStim.filter((a,t) => inRange(xData[t],defaultTimeArray[i],window));
        if (windowedData.length > 0) {
          graphSeries[1].y.push(math.mean(windowedData));
          graphSeries[1].error_y.push(math.std(windowedData)/math.sqrt(windowedData.length)*2);
        } else {
          graphSeries[1].y.push(0);
          graphSeries[1].error_y.push(0);
        }
      }

      graphSeries[2].x.push(new Date(defaultTimeArray[i]+timezoneOffset*60000));
      graphSeries[2].y.push(events.filter((a) => a == defaultTimeArray[i]).length);
    }

    graphSeries[3].x = yData;
    if (graphSeries[3].x.length > 0) {
      graphSeries[3].options.xbins.size = (math.quantileSeq(yData,0.95) - math.quantileSeq(yData,0.05)) > 2000 ? 20 : 5
    }
    setRenderData(graphSeries);
  }, [fig, activeChannel, timerange, annotations, dataToRender, circadianState.amplitude]);

  const refreshRender = () => {
    const ax = fig.getAxes();
    for (let i in renderData) {
      if (renderData[i].type === "line" && !circadianState.histogram) {
        if (i == 0 || (i == 1 && !circadianState.eventCount)) {
          fig.shadedErrorBar(renderData[i].x, renderData[i].y, renderData[i].error_y, renderData[i].line_options, renderData[i].shade_options, ax[i]);
        }
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[0]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[0]);
        fig.setAxisProps({
          type: "date",
          tickformat: "%H:%M",
        }, "x", ax[0]);
        fig.setYlim([math.min(renderData[i].y) - 0.1, math.max(renderData[i].y) + 0.1], ax[1]);

        fig.setYlabel("Stimulation Amplitude (mA)", {fontSize: 15}, ax[1]);
      } else if (renderData[i].type === "threshold" && !circadianState.histogram && !circadianState.eventCount) {
        fig.plot(renderData[i].x, renderData[i].y, renderData[i].options, ax[0]);
      } else if (renderData[i].type === "bar" && circadianState.eventCount) {
        fig.bar(renderData[i].x, renderData[i].y, [], renderData[i].options, ax[1]);
        fig.setYlim([0, math.max(renderData[i].y) || 1], ax[1]);
        fig.setYlabel("Event Count (N)", {fontSize: 15}, ax[1]);
      } else if (renderData[i].type === "histogram" && circadianState.histogram) {
        fig.hist(renderData[i].x, renderData[i].options, ax[0]);
        fig.setXlabel(`Power`, {fontSize: 15}, ax[0]);
        fig.setYlabel(`Count`, {fontSize: 15}, ax[0]);
        fig.setAxisProps({
          type: "linear",
          tickformat: "",
        }, "x", ax[0]);
      }
    }
    
    fig.setAxisProps({
      title: {
        font: {
          color: "#FF0000"
        }
      },
      tickcolor:  "#FF0000",
      tickfont: {
        color: "#FF0000"
      },
      showgrid: false
    }, "y", ax[1]);
    fig.render();
  }

  const plotly_onSelect = (e) => {
    if (onSelection && e) {
      const dateRange = e.range.x.map((a) => new Date(a).getTime());
      const allData = cacheData.xData.map((a, i) => ({
        x: a,
        y: cacheData.yData[i]
      })).filter((a,i) => {
        return (a.x >= dateRange[0] && a.x <= dateRange[1]);
      }).map((a) => a.y);
      onSelection(allData);
    }
  }

  useEffect(() => {
    if (!fig || !renderData) return;
    
    fig.traces = [];
    try {
      refreshRender();
    } catch (error) {
      console.log(error);
    }
    
    const ref = document.getElementById(figureTitle);
    if (ref) {
      ref.on("plotly_selected", plotly_onSelect);
      return () => {
        ref.removeListener("plotly_selected", plotly_onSelect);
      }
    };
  }, [fig, renderData, circadianState]);

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

  return useMemo(() => (
    <MDBox display={"flex"} flexDirection={"column"}>
      {activeChannel === "Time-based Assessment" ? (
        <MDBox p={2}>
          <Autocomplete
            disableClearable
            value={timerange.device}
            options={channelSelector}
            onChange={(event, value) => setTimerange({...timerange, device: value})}
            renderInput={(params) => (
              <FormField
                {...params}
                label={"Channel Selector"}
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </MDBox>
      ) : null}
      {activeChannel === "Time-based Assessment" ? (
      <MDBox p={2} display={"flex"} flexDirection={"row"}>
        <MDTypography variant={"p"} fontSize={20} pr={2}>
          {"From"}
        </MDTypography>
        <LocalizationProvider dateAdapter={AdapterMoment} adapterLocale={"us"}>
          <DatePicker
            label="Start Date"
            value={timerange.start}
            onChange={(newDate) => {
              setTimerange({...timerange, start: newDate});
            }}
            renderInput={(params) => <TextField {...params} />}
          />
        </LocalizationProvider>
        <MDTypography variant={"p"} fontSize={20} px={2}>
          {"To"}
        </MDTypography>
        <LocalizationProvider dateAdapter={AdapterMoment}>
          <DatePicker
            label="End Date"
            value={timerange.end}
            onChange={(newDate) => {
              setTimerange({...timerange, end: newDate});
            }}
            renderInput={(params) => <TextField {...params} />}
          />
        </LocalizationProvider>
      </MDBox>
      ) : null}
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: 600, width: "100%", display: ""}}/>
    </MDBox>
  ), [renderData, timerange]);
}

export default MedtronicCircadianRhythm;