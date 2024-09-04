/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, {useCallback} from "react";
import {useResizeDetector} from "react-resize-detector";

import colormap from "colormap";

import { Autocomplete } from "@mui/material";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext } from "context";

import { dictionary, dictionaryLookup } from "assets/translation";

function NarrowBandFeatures({dataToRender, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlim([config.frequencyRangeStart, config.frequencyRangeEnd]);

      fig.setLegend({
        tracegroupgap: 5,
        xanchor: "left",
        y: 0.5,
      });

      fig.setLayoutProps({
        hovermode: "xy"
      });
    }

    for (let i in data.Channel) {
      fig.scatter(data.Time[i].map((a) => new Date(a*1000)), data.NarrowBandFrequency[i], {
        size: data.NarrowBandPower[i].map((a) => a*5),
        customdata: data.NarrowBandPower[i].map((a) => a*5),
        color: "r",
        name: data.Channel[i],
        showlegend: true,
        hovertemplate: "  %{y}Hz <br>  %{customdata:.1f} <extra></extra>"
      });
    }

    if (data.Channel == 0) {
      fig.purge();
      setShow(false);
    } else {
      fig.render();
      setShow(true);
    }
  }

  // Refresh Left Figure if Data Changed
  React.useEffect(() => {
    if (dataToRender) {
      handleGraphing(dataToRender);
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

  const exportCurrentStream = () => {
    console.log(dataToRender)

    var csvData = "Time,Channel,PeakFrequency,PeakPower\n";
    for (let i in dataToRender["Channel"]) {
      for (let j in dataToRender["Time"][i]) {
        csvData += dataToRender["Time"][i][j] + "," + dataToRender["Channel"][i] + "," + dataToRender["NarrowBandFrequency"][i][j] + "," + dataToRender["NarrowBandPower"][i][j];
        csvData += "\n";
      }
    }

    var downloader = document.createElement('a');
    downloader.href = 'data:text/csv;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = figureTitle + '_Export.csv';
    downloader.click();
  };

  return (
    <MDBox lineHeight={1} p={2}>
      <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3, marginTop: 3, width: "100%"}} onClick={() => exportCurrentStream()}>
        {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
      </MDButton>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 0, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default NarrowBandFeatures;