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

function SpectrogramView({dataToRender, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const [selector, setSelector] = React.useState({value: "", options: []});
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();
    if (fig.fresh) {
      let ax = fig.subplots(2, 1, {sharey: false, sharex: false});
      fig.setYlim([0, 100], ax[0]);
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[0]);

      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)})`, {fontSize: 15}, ax[1]);
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[1]);
      fig.setXlim([0, 100], ax[1]);

      fig.setTitle(figureTitle);
      fig.setSubtitle(selector.value + " Spectrogram", ax[0])
    }

    let ax = fig.getAxes();
    
    let colorRange = [999,-999];
    for (let recordingId in data) {
      if (data[recordingId].ChannelNames.includes(selector.value)) {
        const channelIndex = data[recordingId].ChannelNames.indexOf(selector.value);
        if (data[recordingId].Spectrogram[channelIndex].ColorRange[0] < colorRange[0]) {
          colorRange[0] = data[recordingId].Spectrogram[channelIndex].ColorRange[0];
        }
        if (data[recordingId].Spectrogram[channelIndex].ColorRange[1] > colorRange[1]) {
          colorRange[1] = data[recordingId].Spectrogram[channelIndex].ColorRange[1];
        }
      }
    }
    fig.setYlim(colorRange, ax[1]);

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
    let channelNames = [];
    for (let i in dataToRender.Data) {
      channelNames.push(...dataToRender.Data[i].ChannelNames.filter((a) => !channelNames.includes(a)));
    }
    setSelector({options: channelNames, value: channelNames[0]})
    if (dataToRender && selector.value) {
      handleGraphing(dataToRender.Data)
    }
  }, [dataToRender, selector.value, language]);

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
      <Autocomplete
        value={selector.value}
        options={selector.options}
        onChange={(event, value) => setSelector({...selector, value: value})}
        getOptionLabel={(option) => {
          return option;
        }}
        renderInput={(params) => (
          <FormField
            {...params}
            label={"Channel Selector"}
            InputLabelProps={{ shrink: true }}
          />
        )}
        disableClearable
      />
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 0, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default SpectrogramView;