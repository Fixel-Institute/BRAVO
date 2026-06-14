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

import { Grid } from "@mui/material";
import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { SessionController } from "database/session-control";
import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function SnapshotPSDs({dataToRender, figureTitle, monopolarEstimate}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;
  
  const [figGroup, setFigGroup] = useState({});
  const [fig, setFig] = useState(null);
  const [renderData, setRenderData] = useState(null);
  const [cacheData, setCacheData] = useState(null);

  const [refresh, setRefresh] = useState(0);
  const [centerFreq, setCenterFreq] = useState(22);

  useEffect(() => {
    setFigGroup(() => {
      return {
        [figureTitle]: new PlotlyRenderManager(figureTitle, language),
        [figureTitle + "_Boxplot"]: new PlotlyRenderManager(figureTitle + "_Boxplot", language)
      }
    });
  }, [figureTitle]);

  useEffect(() => {
    for (let key in figGroup) {
      const fig = figGroup[key];
      if (!fig.fresh) {
        fig.clearData();
      }
      
      if (key.endsWith("Boxplot")) {
        const ax = fig.subplots(1, 1, {sharey: false, sharex: false});
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, monopolarEstimate ? "dB" : "uV2Hz", language)})`, {fontSize: 15});

      } else {
        fig.subplots(1, 1, {sharey: false, sharex: false});
        fig.setScaleType("log", "y");
        fig.setTickValue([0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000], "y");
        fig.setYlim([-3, 2]);
        fig.setXlim([0, 100]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
        fig.setSubtitle(key);

      }
      if (!fig.fresh) {
        refreshRender(fig, key);
      }
    }
  }, [monopolarEstimate, figGroup]);

  useEffect(() => {
    
    const asyncFunc = async () => {
      const colors = ["#f44336", "#9c27b0", "#2196f3", "#4caf50", "#ffc107", "#b23c17",
                      "#f44336", "#9c27b0", "#2196f3", "#4caf50", "#ffc107", "#b23c17"]

      const getFrequencyIndex = (freq) => {
        for (let i = 0; i < freq.length; i++) {
          if (freq[i] >= centerFreq) return i;
        }
      }

      let uniqueHemisphere = {};

      let graphSeries = [];
      for (let i in dataToRender) {
        let ylim = math.quantileSeq(dataToRender[i].Power, [0.25, 1]);
        ylim[0] = Math.floor(Math.log10(ylim[0]));
        ylim[1] = Math.ceil(Math.log10(ylim[1]));
        graphSeries.push({
          type: "line", x: dataToRender[i].Frequency, y: dataToRender[i].Power, error_y: dataToRender[i].stdPower,
          ylim: ylim,
          line_options: {
            linewidth: 2,
            name: dataToRender[i].ChannelName.split(": ")[1],
            legendgroup: dataToRender[i].ChannelName.split(": ")[1],
            color: colors[i],
            hovertemplate: `  ${dataToRender[i].ChannelName.split(": ")[1]}<br>  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)}<extra></extra>`,
            showlegend: true
          }, 
          shade_options: {
            legendgroup: dataToRender[i].ChannelName.split(": ")[1],
            color: colors[i],
            alpha: 0.3,
            showlegend: false
          }, 
          figName: figureTitle
        });

        const index = getFrequencyIndex(dataToRender[i].Frequency);
        if (!monopolarEstimate) {
          graphSeries.push({
            type: "bar", x: [dataToRender[i].ChannelName.split(": ")[1]], y: [dataToRender[i].Power[index]], 
            options: {
              error_y: {
                type: "data",
                array: [dataToRender[i].stdPower[index]],
                visible: true
              },
              facecolor: colors[i],
              hovertemplate: `  %{y:.2f} <extra></extra>`,
              showlegend: false,
            },
            figName: figureTitle + "_Boxplot"
          })
        } else {
          const parts = dataToRender[i].ChannelName.split(": ")[1].split(" ");
          const hemisphere = parts.slice(0, -1).join(" ");
          if (!uniqueHemisphere[hemisphere]) {
            uniqueHemisphere[hemisphere] = {}
          }
          if (parts[parts.length - 1] === "E00-E03") {
            uniqueHemisphere[hemisphere]["C0-C3"] = dataToRender[i].Power[index];
          } else if (parts[parts.length - 1] === "E01-E02") {
            uniqueHemisphere[hemisphere]["C1-C2"] = dataToRender[i].Power[index];
          } else if (parts[parts.length - 1] === "E02-E03") {
            uniqueHemisphere[hemisphere]["C2-C3"] = dataToRender[i].Power[index];
          }
        }
      }
      
      if (monopolarEstimate) {
        let i = 0;
        for (let key in uniqueHemisphere) {
          try {
            const response = await SessionController.query("/api/requestAIPrediction", {
              RequestType: "Fleeting2026",
              AnalysisName: "MonopolarPowerEstimation",
              Data: uniqueHemisphere[key]
            })
            
            for (let chan in ["0", "1", "2", "3"]) {
              graphSeries.push({
                type: "bar", x: [key + " E0" + chan], y: response.data["C" + chan], 
                options: {
                  error_y: {
                    type: "data",
                    array: response.data["C" + chan + "_SE"],
                    visible: true
                  },
                  facecolor: colors[i],
                  hovertemplate: `  %{y:.2f} <extra></extra>`,
                  showlegend: false,
                },
                figName: figureTitle + "_Boxplot"
              });
              i++;
            }
          } catch (error) {
            console.error("Error fetching monopolar estimation:", error);
          }
        }
      }
      setRenderData(graphSeries);
    }

    asyncFunc();
  }, [figGroup, monopolarEstimate, dataToRender, centerFreq]);

  const refreshRender = (fig, figName) => {
    let psdYlim = [0,0];
    for (let i in renderData) {
      if (renderData[i].figName == figName) {
        if (renderData[i].type === "line") {
          if (renderData[i].ylim[1] > psdYlim[1]) psdYlim[1] = renderData[i].ylim[1];
          if (renderData[i].ylim[0] < psdYlim[0]) psdYlim[0] = renderData[i].ylim[0];
          fig.setYlim(psdYlim);
          fig.shadedErrorBar(renderData[i].x, renderData[i].y, renderData[i].error_y, renderData[i].line_options, renderData[i].shade_options);
        } else if (renderData[i].type === "bar") {
          fig.bar(renderData[i].x, renderData[i].y, [], renderData[i].options);
          fig.setSubtitle("Spectral Features @ " + centerFreq.toFixed(1) + " Hz");
          //fig.box(renderData[i].x, renderData[i].y, renderData[i].options);
          //fig.setSubtitle("Spectral Features @ " + centerFreq.toFixed(1) + " Hz");
          //fig.setXlabel(renderData[i].parameter, {fontSize: 15});
          //fig.setYlim([0, math.max(renderData[i].y)*1.1]);
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
    }

    const ref = document.getElementById(figureTitle);
    if (ref && ref.on) {
      ref.on("plotly_click", plotly_onClick);
    };
    setRefresh((refresh) => {
      return refresh += 1;
    });

    return () => {
      const ref = document.getElementById(figureTitle);
      if (ref && ref.removeListener) {
        ref.removeListener("plotly_click", plotly_onClick);
      };
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
    <Grid container spacing={0}>
      <Grid key={figureTitle} item xs={12} lg={6}>
        <MDBox ref={ref} id={figureTitle} style={{height: 600, width: "100%"}}/>
      </Grid>
      <Grid key={figureTitle + "_Boxplot"} item xs={12} lg={6}>
        <MDBox id={figureTitle + "_Boxplot"} style={{height: 600, width: "100%"}}/>
      </Grid>
    </Grid>
  ), [refresh]);
}

export default SnapshotPSDs;