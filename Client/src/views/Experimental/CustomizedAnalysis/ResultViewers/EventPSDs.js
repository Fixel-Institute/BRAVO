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

function EventPSDs({dataToRender, channelName, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [eventPSDSelector, setEventPSDSelector] = React.useState({
    type: "Channels",
    options: [],
    value: ""
  });

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data, channelName) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1,1, {sharey: true, sharex: true});
      fig.setScaleType("linear", "y");
      fig.setTickValue([-30, -20, -10, 0, 10, 20, 30], "y");
      fig.setYlim([-30, 20]);
      fig.setXlim([0, 100]);
      fig.setTitle(channelName + " Comparison");

      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
    }

    const colors = colormap({
      colormap: 'rainbow',
      nshades: 24,
      format: 'hex',
      alpha: 1,
    });

    const eventNames = Object.keys(data);
    const steps = Math.floor(24/eventNames.length);
    for (var j in eventNames) {
      fig.shadedErrorBar(data[eventNames[j]]["Frequency"], data[eventNames[j]]["MeanPower"], data[eventNames[j]]["StdPower"], {
        name: eventNames[j],
        color: colors[j*steps],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${eventNames[j]} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
      }, {
        color: colors[j*steps],
        alpha: 0.3,
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
    if (dataToRender) {
      let ChannelNames = [];
      for (let i in dataToRender.Data.Timeseries) {
        for (let j in dataToRender.Data.Timeseries[i].ChannelNames) {
          if (!ChannelNames.includes(dataToRender.Data.Timeseries[i].ChannelNames[j])) {
            ChannelNames.push(dataToRender.Data.Timeseries[i].ChannelNames[j]);
          }
        }
      }
      setEventPSDSelector({...eventPSDSelector, options: ChannelNames, value: ChannelNames[0]});
    }

  }, [dataToRender, language]);

  React.useEffect(() => {
    if (eventPSDSelector.value) {
      handleGraphing(dataToRender.Data.EventPSDs[eventPSDSelector.value], eventPSDSelector.value);
    }
  }, [eventPSDSelector]);

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
    var csvData = JSON.stringify(dataToRender.Data.EventPSDs);

    var downloader = document.createElement('a');
    downloader.href = 'data:text/json;charset=utf-8,' + encodeURI(csvData);
    downloader.target = '_blank';
    downloader.download = 'EventPSDExport.json';
    downloader.click();
  };

  return (
    <MDBox lineHeight={1} p={2}>
      <Autocomplete
        value={eventPSDSelector.value}
        options={eventPSDSelector.options}
        onChange={(event, value) => setEventPSDSelector({...eventPSDSelector, value: value})}
        getOptionLabel={(option) => {
          return option;
        }}
        renderInput={(params) => (
          <FormField
            {...params}
            label={"Comparison Selector"}
            InputLabelProps={{ shrink: true }}
          />
        )}
        disableClearable
      />
      <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3, marginTop: 3, width: "100%"}} onClick={() => exportCurrentStream()}>
        {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
      </MDButton>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 0, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default EventPSDs;