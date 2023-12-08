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

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext } from "context";

import { dictionary, dictionaryLookup } from "assets/translation";

function ChannelCompare({dataToRender, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1,1, {sharey: true, sharex: true});
      fig.setScaleType("log", "y");
      fig.setTickValue([0.001, 0.01, 0.1, 1, 10, 100, 1000], "y");
      if (config.PSDMethod.value === "Estimated Medtronic PSD") {
        fig.setYlim([-1, 1]);
      } else {
        fig.setYlim([-3, 2]);
      }
      fig.setXlim([0, 100]);
      fig.setTitle(figureTitle);
      if (data[0]) {
        const [side, target] = data[0].Hemisphere.split(" ");
        const titleText = `${data[0].DeviceName} ${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${data[0].Channel[0]}-E${data[0].Channel[1]}`;
        fig.setTitle(titleText);
      } else {
        fig.setTitle(figureTitle);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
      
      fig.setLegend({xanchor: "left"});
    }

    const colors = colormap({
      colormap: 'jet',
      nshades: Math.max(data.length,50),
      format: 'hex',
      alpha: 1,
    });

    const Timespan = data[0]["Timestamp"] - data[data.length-1]["Timestamp"];
    
    for (var i in data) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      const colorIndex = Math.floor((data[0]["Timestamp"] - data[i]["Timestamp"]) / Timespan * (colors.length-1));
      
      fig.plot(data[i]["Frequency"], data[i]["MeanPower"], {
        name: timestruct.toLocaleString(language),
        color: colors[colors.length-1-colorIndex],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${timestruct.toLocaleString(language)} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
      });
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
    if (dataToRender) handleGraphing(dataToRender);
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

export default ChannelCompare;