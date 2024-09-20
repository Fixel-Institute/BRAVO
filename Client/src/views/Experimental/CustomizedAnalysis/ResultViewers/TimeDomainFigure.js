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

function TimeDomainFigure({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [realheight, setHeight] = React.useState(height);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, channelInfos) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(channelInfos.length, 1, {sharex: true, sharey: true});
      setHeight(channelInfos.length * height)

      for (var i in ax) {
        fig.setYlim([-50,50],ax[i]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV", language)})`, {fontSize: 15}, ax[i]);
        fig.setSubtitle(channelInfos[i],ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
    }

    for (let i in data) {
      for (let j in data[i].ChannelNames) {
        let axIndex = channelInfos.indexOf(data[i].ChannelNames[j]);
        var timeArray = Array(data[i].Data.length).fill(0).map((value, index) => new Date(data[i].StartTime*1000 + index*1000/data[i].SamplingRate));
        
        fig.plot(timeArray, data[i].Data.map((a) => a[j]), {
          color: "#000000",
          linewidth: 1,
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV", language)}<br>  %{x} <br><extra></extra>`,
        }, ax[axIndex]);
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
    if (dataToRender) {
      let ChannelNames = [];
      for (let i in dataToRender) {
        for (let j in dataToRender[i].ChannelNames) {
          if (!ChannelNames.includes(dataToRender[i].ChannelNames[j])) {
            ChannelNames.push(dataToRender[i].ChannelNames[j]);
          }
        }
      }
      handleGraphing(dataToRender, ChannelNames);
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

  return (
    <MDBox lineHeight={1} p={2}>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: realheight, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default TimeDomainFigure;