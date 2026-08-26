/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import {useCallback, useState, useEffect, useMemo} from "react";
import {useResizeDetector} from "react-resize-detector";
import colormap from "colormap";
import * as math from "mathjs";

import { Autocomplete, Grid, Switch, FormControlLabel } from "@mui/material";
import FormField from "components/MDInput/FormField";
import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";
import { SessionController } from "database/session-control";

function StimulationPSD({dataToRender, activeChannels, onRequestServerAnalysis, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;
  
  const [figGroup, setFigGroup] = useState({});
  const [fig, setFig] = useState(null);
  const [renderData, setRenderData] = useState(null);
  const [cacheData, setCacheData] = useState(null);
  const [therapyLabel, setTherapyLabel] = useState({});
  const [parameter, setParameter] = useState("Amplitude");

  const [refresh, setRefresh] = useState(0);
  const [centerFreq, setCenterFreq] = useState(22);

  useEffect(() => {
    let newGroup = {};
    for (let i in dataToRender.AllChannels) {
      if (!figGroup[dataToRender.AllChannels[i]]) {
        newGroup[dataToRender.AllChannels[i]] = new PlotlyRenderManager(figureTitle + "_" + dataToRender.AllChannels[i], language);
        newGroup[dataToRender.AllChannels[i] + "Boxplot"] = new PlotlyRenderManager(figureTitle + "Boxplot_" + dataToRender.AllChannels[i], language);
      } else {
        newGroup[dataToRender.AllChannels[i]] = figGroup[dataToRender.AllChannels[i]];
        newGroup[dataToRender.AllChannels[i] + "Boxplot"] = figGroup[dataToRender.AllChannels[i] + "Boxplot"];
      }
    }
    setFigGroup(newGroup);
    setTherapyLabel({})
  }, [figureTitle, activeChannels, dataToRender]);

  useEffect(() => {
    for (let key in figGroup) {
      const fig = figGroup[key];
      if (!fig.fresh) {
        fig.clearData();
      }
      
      if (key.endsWith("Boxplot")) {
        fig.subplots(1, 1, {sharey: false, sharex: false});
        fig.setYlim([0, 20]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
        fig.setLayoutProps({
          hovermode: "xy"
        });

      } else {
        fig.subplots(1, 1, {sharey: false, sharex: false});
        fig.setScaleType("log", "y");
        fig.setTickValue([0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000], "y");
        fig.setYlim([-3, 2]);
        fig.setXlim([0, 100]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
        fig.setSubtitle(key.split(": ")[1]);

      }
      if (!fig.fresh) {
        refreshRender(fig, key);
      }
    }
  }, [figGroup]);

  const getTherapyChanges = (key) => {
    let modifiedParameters = [];
    let previousState = {};
    let therapySeries = {};
    let parameters = ["Amplitude", "Frequency", "Pulsewidth"];
    for (let i in dataToRender.Therapy) {
      for (let j in dataToRender.Therapy[i].TherapySeries) {
        if (dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key]) {
          if (dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key].Type == "StandardIPGStimulation") {
            for (let parameter of parameters) {
              if (previousState[parameter] === undefined) {
                therapySeries[parameter] = [{time: dataToRender.Therapy[i].TherapySeries[j].Time, state: dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key][parameter]}]
              } else {
                if (dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key][parameter] != previousState[parameter]) {
                  modifiedParameters.push(parameter)
                  therapySeries[parameter].push({time: dataToRender.Therapy[i].TherapySeries[j].Time, state: dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key][parameter]})
                }
              }
              previousState[parameter] = dataToRender.Therapy[i].TherapySeries[j].TherapyOverview[key][parameter];
            }
          }
        }
      }
    }

    if (Object.keys(therapySeries).length == 0) {
      for (let parameter of parameters) {
        therapySeries[parameter] = [{time: 0, state: -1}]
      }
    }
    
    return therapySeries;
  }

  useEffect(() => {
    let duration = 0;
    for (let i in dataToRender.Signal) {
      duration += dataToRender.Signal[i].SignalSeries.Data.length
    };

    if (duration > 3000*250) {
      setCacheData({...dataToRender.TherapeuticEffects, type: "ServerSideRender"});
      return;
    }

    let cacheData = {};

    // Extract PSDs
    for (let i in dataToRender.Signal) {
      const therapySeries = getTherapyChanges(therapyLabel[dataToRender.Signal[i].SignalSeries.ChannelNames] ? therapyLabel[dataToRender.Signal[i].SignalSeries.ChannelNames] : dataToRender.Signal[i].SignalSeries.ChannelNames);
      cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames] = JSON.parse(JSON.stringify(therapySeries));
      if (therapySeries[parameter].length > 1) {
        for (let stage = 0; stage < therapySeries[parameter].length; stage++) {
          const selected_data = dataToRender.Signal[i].SignalSeries.Spectrum.Power.map((a) => {
            return a.filter((b,t) => {
              const currentTime = dataToRender.Signal[i].SignalSeries.Spectrum.Time[t] + dataToRender.Signal[i].SignalSeries.StartTime + dataToRender.Signal[i].Alignment;
              return (currentTime > therapySeries[parameter][stage].time+2) && (
                (stage+1 >= therapySeries[parameter].length) ? true : (currentTime < therapySeries[parameter][stage+1].time-2)
              );
            })
          });
          if (selected_data[0].length > 10) {
            cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][stage].freq = dataToRender.Signal[i].SignalSeries.Spectrum.Frequency;
            cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][stage].power = math.matrix(selected_data);
            cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][stage].state = therapySeries[parameter][stage].state;
          }
        }
      } else if (therapySeries[parameter].length == 1) {
        cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][0].freq = dataToRender.Signal[i].SignalSeries.Spectrum.Frequency;
        cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][0].power = math.matrix(dataToRender.Signal[i].SignalSeries.Spectrum.Power);
        cacheData[dataToRender.Signal[i].SignalSeries.ChannelNames][parameter][0].state = therapySeries[parameter][0].state;
      }
    }

    setCacheData(cacheData);
  }, [figGroup, parameter, therapyLabel, dataToRender]);

  useEffect(() => {
    if (!cacheData) return;

    const colors = colormap({
      colormap: 'jet',
      nshades: 101,
      format: 'hex',
      alpha: 1,
    });

    const getFrequencyIndex = (freq) => {
      for (let i = 0; i < freq.length; i++) {
        if (freq[i] >= centerFreq) return i;
      }
    }

    let graphSeries = [];
    if (cacheData.type === "ServerSideRender") {
      for (let label in cacheData) {
        for (let channel in cacheData[label]) {
          if ((channel == label && !therapyLabel[channel]) || (therapyLabel[channel] == label && therapyLabel[channel])) {
            const maxColor = math.max(cacheData[label][channel][parameter].map((a) => a.State*10));
            const colorMapper = (level) => colors[Math.floor(level/maxColor*100)];
            
            for (let stage in cacheData[label][channel][parameter]) {
              const stageColor = colorMapper(parseFloat(cacheData[label][channel][parameter][stage].State)*10);
              let ylim = math.quantileSeq(math.abs(math.matrix(cacheData[label][channel][parameter][stage].MeanPower)), [0.25, 1]);
              ylim[0] = Math.floor(Math.log10(ylim[0]));
              ylim[1] = Math.ceil(Math.log10(ylim[1]));
              graphSeries.push({
                type: "line",
                x: cacheData[label][channel][parameter][stage].Frequency, y: cacheData[label][channel][parameter][stage].MeanPower, error_y: cacheData[label][channel][parameter][stage].StdErrPower,
                ylim: ylim,
                line_options: {
                  id: parameter + ": " + cacheData[label][channel][parameter][stage].State,
                  name: parameter + ": " + cacheData[label][channel][parameter][stage].State,
                  legendgroup: parameter + ": " + cacheData[label][channel][parameter][stage].State,
                  color: stageColor,
                  linewidth: 2,
                  hovertemplate: `  ${parameter + ": " + cacheData[label][channel][parameter][stage].State}<br>  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)}<extra></extra>`,
                  showlegend: true
                }, 
                shade_options: {
                  color: stageColor,
                  alpha: 0.3,
                  legendgroup: parameter + ": " + cacheData[label][channel][parameter][stage].State,
                  showlegend: false
                }, 
                figName: channel
              });

              const index = getFrequencyIndex(cacheData[label][channel][parameter][stage].Frequency);
              graphSeries.push({
                type: "bar", x: [cacheData[label][channel][parameter][stage].State], y: [cacheData[label][channel][parameter][stage].MeanPower[index]], 
                options: {
                  error_y: {
                    type: "data",
                    array: [cacheData[label][channel][parameter][stage].StdErrPower[index]],
                    visible: true
                  },
                  width: 0.5,
                  facecolor: stageColor,
                  hovertemplate: `  %{y:.2f} <extra></extra>`,
                  showlegend: false,
                },
                figName: channel + "Boxplot"
              })
            }
          }
        }
      }

    } else {
      for (let key in cacheData) {
        const therapySeries = cacheData[key];

        // Calculate Average PSDs
        for (let parameter in therapySeries) {

          const maxColor = math.max(therapySeries[parameter].map((a) => a.state*10));
          const colorMapper = (level) => colors[Math.floor(level/maxColor*100)];

          let uniqueValues = [];
          for (let stage in therapySeries[parameter]) {
            if (!uniqueValues.includes(therapySeries[parameter][stage].state)) {
              uniqueValues.push(therapySeries[parameter][stage].state);
            }
          }

          for (let value of uniqueValues.sort((a,b) => a-b)) {
            let matrix = null
            let frequency = null;
            for (let stage in therapySeries[parameter]) {
              if (therapySeries[parameter][stage].state == value && therapySeries[parameter][stage].freq) {
                if (!matrix) {
                  matrix = therapySeries[parameter][stage].power;
                  frequency = therapySeries[parameter][stage].freq;
                } else {
                  matrix = math.concat(matrix, therapySeries[parameter][stage].power, 1);
                }
              }
            }

            if (matrix && frequency) {
              let ylim = math.quantileSeq(math.abs(matrix), [0.25, 1]);
              ylim[0] = Math.floor(Math.log10(ylim[0]));
              ylim[1] = Math.ceil(Math.log10(ylim[1]));
              graphSeries.push({
                type: "line",
                x: frequency, y: math.mean(matrix, 1)._data, error_y: math.std(matrix, 1)._data.map((a) => a/math.sqrt(math.size(matrix)._data[1])),
                ylim: ylim,
                line_options: {
                  id: parameter + ": " + value,
                  name: parameter + ": " + value,
                  legendgroup: parameter + ": " + value,
                  color: colorMapper(parseFloat(value)*10),
                  linewidth: 2,
                  hovertemplate: `  ${parameter + ": " + value}<br>  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)}<extra></extra>`,
                  showlegend: true
                }, 
                shade_options: {
                  color: colorMapper(parseFloat(value)*10),
                  alpha: 0.3,
                  legendgroup: parameter + ": " + value,
                  showlegend: false
                }, 
                figName: key
              });
            }
          }
        }
        
        for (let parameter in therapySeries) {
          let xData = [], yData = [];
          for (let stage in therapySeries[parameter]) {
            if (therapySeries[parameter][stage].freq) {
              const centerIndex = getFrequencyIndex(therapySeries[parameter][stage].freq);
              xData.push(...therapySeries[parameter][stage].power._data[centerIndex].map((a) => therapySeries[parameter][stage].state));
              yData.push(...therapySeries[parameter][stage].power._data[centerIndex]);
            }
          }
          
          if (yData.length > 0) {
            graphSeries.push({
              type: "box",
              x: xData, y: yData, 
              parameter: parameter,
              options: {
                width: 0.2,
                hovertemplate: `<extra></extra>`,
              },
              figName: key + "Boxplot"
            });
          }
        }
      }
    }

    setRenderData(graphSeries);
  }, [cacheData, therapyLabel, centerFreq]);

  const refreshRender = (fig, figName) => {
    let maxYlim = 0;
    let psdYlim = [0,0]
    for (let i in renderData) {
      if (renderData[i].figName == figName) {
        if (renderData[i].type === "line") {
          if (renderData[i].ylim[1] > psdYlim[1]) psdYlim[1] = renderData[i].ylim[1];
          if (renderData[i].ylim[0] < psdYlim[0]) psdYlim[0] = renderData[i].ylim[0];
          fig.setYlim(psdYlim);
          fig.shadedErrorBar(renderData[i].x, renderData[i].y, renderData[i].error_y, renderData[i].line_options, renderData[i].shade_options);
        } else if (renderData[i].type === "box") {
          fig.box(renderData[i].x, renderData[i].y, renderData[i].options);
          fig.setSubtitle("Spectral Features @ " + centerFreq.toFixed(1) + " Hz");
          fig.setXlabel(renderData[i].parameter, {fontSize: 15});
          fig.setYlim([0, math.max(renderData[i].y)*1.1]);
        } else if (renderData[i].type === "bar") {
          fig.bar(renderData[i].x, renderData[i].y, [], renderData[i].options);
          fig.setSubtitle("Spectral Features @ " + centerFreq.toFixed(1) + " Hz");
          fig.setXlabel(renderData[i].parameter, {fontSize: 15});
          if (math.max(renderData[i].y)*1.1 > maxYlim) {
            maxYlim = math.max(renderData[i].y)*1.1+renderData[i].options.error_y.array[0];
            fig.setYlim([0, maxYlim]);
          }
        }
      }
    }
    fig.render();
  }

  useEffect(() => {
    for (let key in figGroup) {
      const fig = figGroup[key];
      if (key.endsWith("Boxplot")) {
        fig.traces = [];
        refreshRender(fig, key);
      } else {
        fig.traces = [];
        refreshRender(fig, key);
      }
      
      const ref = document.getElementById(figureTitle + "_" + key);
      if (ref) {
        ref.on("plotly_click", plotly_onClick);
      };
      
      setRefresh((refresh) => {
        return refresh += 1;
      });
    }

    return () => {
      for (let key in figGroup) {
        const ref = document.getElementById(figureTitle + "_" + key);
        if (ref && ref.removeListener) {
          ref.removeListener("plotly_click", plotly_onClick);
        };
      }
    }
  }, [figGroup, renderData]);

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

  var updateTimeout = null;
  var plotly_singleclicked = false;
  const plotly_onClick = (data) => {
    if (plotly_singleclicked) {
      plotly_singleclicked = false;
      clearTimeout(updateTimeout);
    } else {
      plotly_singleclicked = true;
      updateTimeout = setTimeout(function() {
        setCenterFreq(data["points"][0]["x"]);
        plotly_singleclicked = false
      }, 300);
    }
  };

  return useMemo(() => (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <MDBox px={3} pt={3}>
          <Autocomplete
            value={parameter}
            options={["Amplitude", "Frequency", "Pulsewidth"]}
            onChange={(event, value) => setParameter(value)}
            renderInput={(params) => (
              <FormField
                {...params}
                label={"Therapy Label Selector"}
                InputLabelProps={{ shrink: true }}
              />
            )}
            disableClearable
          />
        </MDBox>
      </Grid>
      {dataToRender.AllChannels.map((a, thatIndex) => {
        let visibility = activeChannels.includes(a) && (figGroup[a] && figGroup[a].traces.length > 0);
        let otherIndex = thatIndex === 0 ? 1 : 0;
        return [
          <Grid key={figureTitle + "_SwitchControl"} item xs={12} >
            <MDBox px={3} style={{display: visibility ? "" : "none"}}>
              <FormControlLabel control={<Switch value={therapyLabel[a] != a} onChange={(event, value) => {
                if (dataToRender.AllChannels.length == 2) {
                  setTherapyLabel({...therapyLabel, [a]: therapyLabel[a] === dataToRender.AllChannels[otherIndex] ? dataToRender.AllChannels[thatIndex] : dataToRender.AllChannels[otherIndex]})
                }
              }} />} label="Use Other Electrode as Stimulation Reference" />
            </MDBox>
          </Grid>,
          <Grid key={figureTitle + "_" + a} item xs={12} sm={6}>
            <MDBox ref={ref} id={figureTitle + "_" + a} style={{height: 600, width: "100%", display: visibility ? "" : "none"}}/>
          </Grid>,
          <Grid key={figureTitle + "Boxplot_" + a} item xs={12} sm={6}>
            <MDBox id={figureTitle + "Boxplot_" + a} style={{height: 600, width: "100%", display: visibility ? "" : "none"}}/>
          </Grid>
        ]
      })}
    </Grid>
  ), [refresh]);
}

export default StimulationPSD;