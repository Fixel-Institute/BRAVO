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

function SpectralFeatures({dataToRender, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15})
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)}`, {fontSize: 15})
      fig.setYlim([0, 5]);
    }

    for (let i in data) {
      const AllFeatures = Object.keys(data[i]).filter((a) => a.endsWith("_Mean")).map((a) => a.replaceAll("_Mean",""));
      
      const colors = colormap({
        colormap: 'rainbow',
        nshades: data.length * AllFeatures.length > 9 ? data.length * AllFeatures.length : 9,
        format: 'hex',
        alpha: 1,
      });

      for (let k in AllFeatures) {
        fig.plot(data[i].Time.map((a) => new Date(a*1000)), data[i][AllFeatures[k] + "_Mean"], {
          linewidth: 2,
          name: data[i].Channel + "_" + AllFeatures[k] + "_Mean",
          showlegend: true,
          color: colors[k+i*AllFeatures.length],
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)}<extra></extra>`,
        })
      }
    }

    if (data.length == 0) {
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
      handleGraphing(dataToRender)
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
    const allKeys = [];
    let maxLength = 0;
    for (let i in dataToRender) {
      const AllFeatures = Object.keys(dataToRender[i]).filter((a) => !a.endsWith("Channel"));
      if (dataToRender[i].Time.length > maxLength) maxLength = dataToRender[i].Time.length;
      for (let k in AllFeatures) {
        allKeys.push(dataToRender[i].Channel + "_" + AllFeatures[k])
      }
    }
    var csvData = allKeys.join(",") + "\n";

    for (let j = 0; j < maxLength; j++) {
      for (let i in dataToRender) {
        const AllFeatures = Object.keys(dataToRender[i]).filter((a) => !a.endsWith("Channel"));
        for (let k in AllFeatures) {
          if (dataToRender[i].Time.length > j) {
            csvData += dataToRender[i][AllFeatures[k]][j] + ",";
          }
        }
      }
      csvData += "\n";
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

export default SpectralFeatures;