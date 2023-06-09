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
import { formatSegmentString, matchArray } from "database/helper-function";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function TimeDomainFigure({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, options, recordingInfo) => {
    fig.clearData();

    if (fig.fresh) {
      var axLength = options.ChannelNames.length;

      var ax = fig.subplots(axLength, 1, {sharex: true, sharey: true});
      for (var i in ax) {
        fig.setSubtitle(options.ChannelNames[i], ax[i]);
        fig.setYlim(options.RecommendedYLimit[i], ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
    }

    for (var i in data) {
      for (var j in data[i].ChannelNames) {
        var timeArray = Array(data[i]["Data"].length).fill(0).map((value, index) => new Date(data[i].StartTime*1000 + index*1000/data[i].SamplingRate));
        for (var k in ax) {
          if (!ax[k].title) {
            ax[k].title = data[i].ChannelNames[j];
            fig.plot(timeArray, data[i]["Data"].map((value) => value[j]), {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} <extra></extra>`,
            }, ax[k]);
            break;
          } else if (ax[k].title == data[i].ChannelNames[j]) {
            fig.plot(timeArray, data[i]["Data"].map((value) => value[j]), {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} <extra></extra>`,
            }, ax[k]);
            break;
          }
        }
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
    console.log(dataToRender)
    if (dataToRender) handleGraphing(dataToRender.Data, dataToRender.GraphOptions, dataToRender.RecordingInfo);
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
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default TimeDomainFigure;