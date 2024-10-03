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
  const [selector, setSelector] = React.useState({value: "", options: []});
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15})
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)}`, {fontSize: 15})
      fig.setYlim([0, 5]);
      
      fig.setLegend({
        tracegroupgap: 5,
        xanchor: "left",
        yanchor: "top"
      });
    }

    for (let i in data) {
      const AllFeatures = Object.keys(data[i]).filter((a) => a.endsWith("_Mean")).map((a) => a.replaceAll("_Mean",""));
      
      const colors = colormap({
        colormap: 'rainbow',
        nshades: AllFeatures.length > 9 ? AllFeatures.length : 9,
        format: 'hex',
        alpha: 1,
      });

      for (let k in AllFeatures) {
        fig.plot(data[i].Time.map((a) => new Date(a*1000)), data[i][AllFeatures[k] + "_Mean"], {
          linewidth: 2,
          name: AllFeatures[k] + "_Mean",
          legendgroup: AllFeatures[k],
          showlegend: true,
          color: colors[k],
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
    if (selector.value == "") {
      let channelNames = [];
      for (let i in dataToRender) {
        if (!channelNames.includes(dataToRender[i].Channel)) {
          channelNames.push(dataToRender[i].Channel);
        }
      }
      setSelector({options: channelNames, value: channelNames[0]})
    }
    if (dataToRender && selector.value) {
      handleGraphing(dataToRender.filter((a) => a.Channel == selector.value))
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

  const exportCurrentStream = () => {
    let featureTable = {};
    for (let i in dataToRender) {
      for (let key in dataToRender[i]) {
        if (key == "Channel") {
          featureTable["Annotations"] = [];
          featureTable["Channel"] = [];
        } else {
          featureTable[key] = [];
        }
      }
    }
    
    for (let i in dataToRender) {
      const FeatureNames = dataToRender[i].Channel.split(" | ");

      for (let j in dataToRender[i].Time) {
        featureTable["Annotations"].push(FeatureNames[0]);
        featureTable["Channel"].push(FeatureNames[1]);
        featureTable["Time"].push(dataToRender[i].Time[j]);

        for (let key in dataToRender[i]) {
          if (key == "Channel" || key == "Time") continue;
          featureTable[key].push(dataToRender[i][key][j]);
        }
      }
    }
    
    const allKeys = Object.keys(featureTable);
    var csvData = Object.keys(featureTable).join(",") + "\n";
    for (let j in featureTable.Time) {
      for (let key of allKeys) {
        csvData += featureTable[key][j] + ",";
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
      <MDButton size="large" variant="contained" color="primary" style={{marginBottom: 3, marginTop: 3, width: "100%"}} onClick={() => exportCurrentStream()}>
        {dictionaryLookup(dictionary.FigureStandardText, "Export", language)}
      </MDButton>
      <MDBox ref={ref} id={figureTitle} style={{marginTop: 0, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
    </MDBox>
  );
}

export default SpectralFeatures;