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

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function PreciseTimeAlignmentView({dataToRender, configuration, onStreamClicked, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, configuration) => {
    fig.clearData();
    for (let i in data) {
      if (!data[i].data) return;
    }

    if (fig.fresh) {
      var axLength = data.length;

      var ax = fig.subplots(axLength, 1, {sharex: true, sharey: false});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      for (var i in ax) {
        fig.setSubtitle(`${configuration[data[i].RecordingId].Label || data[i].title}`,ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
      fig.setLegend({
        xanchor: "left",
        tracegroupgap: 10
      });
    }
    
    for (let i in data) {
      let config = configuration[data[i].RecordingId] || {TimeShift: 0, Type: "Signal", Label: ""};
      var timeArray = Array(data[i].data.Data[0].length).fill(0).map((value, index) => new Date(data[i].data.StartTime*1000 + index / data[i].data.SamplingRate * 1000 + config.TimeShift));
      let downScaleFactor = 1;
      if (data[i].data.Data[0].length > 300000) {
        downScaleFactor = Math.floor(data[i].data.Data[0].length / 300000);
      }
      for (let j in data[i].data.ChannelNames) {
        fig.plot(timeArray.filter((value, index) => index % downScaleFactor == 0), data[i].data.Data[j].filter((value, index) => index % downScaleFactor == 0), {
          linewidth: 0.5,
          hovertemplate: `  %{y:.2f} ${" (unit) "}<extra></extra>`,
          //name: configuration[data[i].RecordingId]["Channels"][data[i].data.ChannelNames[j]].name,
          showlegend: true,
        }, ax[i]);
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
    if (dataToRender.length > 0) handleGraphing(dataToRender, configuration.Configuration.Descriptor);
    else { 
      fig.purge();
      setShow(false);
    }
  }, [dataToRender, configuration, language]);

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
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: 300*dataToRender.length, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default PreciseTimeAlignmentView;