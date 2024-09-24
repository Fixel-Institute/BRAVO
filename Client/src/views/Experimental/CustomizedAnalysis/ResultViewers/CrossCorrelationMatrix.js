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
import * as math from "mathjs";

import colormap from "colormap";

import { Autocomplete } from "@mui/material";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext } from "context";

import { dictionary, dictionaryLookup } from "assets/translation";

function CrossCorrelationMatrix({dataToRender, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const [selector, setSelector] = React.useState({value: "", options: []});
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();
    if (fig.fresh) {
      
    }

    let contactArrayY = new Array(data.PrimaryFeatures.length).fill(0).map((a,i) => i);
    let contactArrayX = new Array(data.SecondaryFeatures.length).fill(0).map((a,i) => i);

    fig.surf(data.SecondaryFeatures, data.PrimaryFeatures, data.Matrix, {
      hovertemplate: `  X=%{x}<br>  Y=%{y}<br>  %{z:.2f} CorrelationMatrix <extra></extra>`,
      zsmooth: false,
      coloraxis: fig.createColorAxis({
        colorscale: "redblue",
        colorbar: {y: 0.5, len: 1},
        clim: [-1,1],
        showscale: true
      }),
    });
    
    /*
    fig.setAxisProps({
      ticksmode: "array",
      tickvals: contactArrayX,
      ticktext: data.SecondaryFeatures,
      showticklabels: true
    }, "x");

    fig.setAxisProps({
      ticksmode: "array",
      tickvals: contactArrayY,
      ticktext: data.PrimaryFeatures,
      showticklabels: true
    }, "y");
    */

    /*
    fig.setSubtitle(`Left Hemisphere ${logType} Impedance Map`, ax[0]);
    
    fig.setAxisProps({
      ticksmode: "array",
      tickvals: contactArrayX,
      ticktext: contactArrayX.length == 4 ? contactArrayX : ["0","1A","1B","1C","2A","2B","2C","3"],
      showticklabels: true
    }, "x", ax[0]);
    fig.setAxisProps({
      ticksmode: "array",
      tickvals: contactArrayY,
      ticktext: contactArrayY.length == 4 ? contactArrayY : ["0","1A","1B","1C","2A","2B","2C","3"],
      showticklabels: true
    }, "y", ax[0]);

    const cAxis = fig.createColorAxis({
      colorscale: "Jet",
      colorbar: {y: 0.75, len: 0.4},
      clim: colorRange,
    });

    const colors = colormap({
      colormap: 'rainbow',
      nshades: 9,
      format: 'hex',
      alpha: 1,
    });

    let meanPSD = data[0].Spectrogram[0].Frequency.map((a) => []);
    for (let recordingId in data) {
      if (data[recordingId].ChannelNames.includes(selector.value)) {
        const channelIndex = data[recordingId].ChannelNames.indexOf(selector.value);
        var timeArray = data[recordingId].Spectrogram[channelIndex].Time.map((value, index) => new Date(value*1000));
        fig.surf(timeArray, data[recordingId].Spectrogram[channelIndex].Frequency, data[recordingId].Spectrogram[channelIndex].logPower, {
          zlim: colorRange,
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
          coloraxis: cAxis,
        }, ax[0]);
        
        for (let i in data[recordingId].Spectrogram[channelIndex].Frequency) {
          meanPSD[i].push(...data[recordingId].Spectrogram[channelIndex].logPower[i]);
        }
      }
    }
    
    fig.shadedErrorBar(data[0].Spectrogram[0].Frequency, meanPSD.map((a) => math.mean(a)), meanPSD.map((a) => math.std(a)), {
      color: colors[1],
      linewidth: 2,
      hovertemplate: ` %{y:.2f} dB <extra></extra>`,
    }, {
      color: colors[1],
      alpha: 0.3,
    }, ax[1])

*/
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
      console.log(dataToRender)
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

  return (
    <MDBox lineHeight={1} p={2}>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 0, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default CrossCorrelationMatrix;