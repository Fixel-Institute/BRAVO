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

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function SurveyFigure({dataToRender, height, figureTitle}) {
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
      fig.setYlim([-3, 2]);
      fig.setXlim([0, 100]);
      if (data[0]) {
        const [side, target] = data[0].Hemisphere.split(" ");
        const titleText = `${data[0].DeviceName} ${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
        fig.setTitle(titleText);
      } else {
        fig.setTitle(figureTitle);
      }

      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
    }

    // Beta Band
    fig.addShadedArea([12,30], {
      color: "#03f4fc", 
      alpha: 0.3, 
      showlegend: true, 
      name: dictionaryLookup(dictionary.BrainSenseSurvey.Figure, "BetaBand", language)
    });

    for (var i in data) {
      var colorText = "#000000"
      var legendGroupName = `E${data[i]["Channel"][0]}-E${data[i]["Channel"][1]}`
      if (matchArray(data[i]["Channel"],[0,1])) colorText = "#9c27b0"
      else if (matchArray(data[i]["Channel"],[0,2])) colorText = "#f44336"
      else if (matchArray(data[i]["Channel"],[0,3])) colorText = "#ffeb3b"
      else if (matchArray(data[i]["Channel"],[1,2])) colorText = "#3f51b5"
      else if (matchArray(data[i]["Channel"],[1,3])) colorText = "#03a9f4"
      else if (matchArray(data[i]["Channel"],[2,3])) colorText = "#4caf50"

      else if (matchArray(data[i]["Channel"],[1.1,2.1])) {
        colorText = "#dd0000";
        legendGroupName = "Segmented Side 01";
      } else if (matchArray(data[i]["Channel"],[1.2,2.2])) {
        colorText = "#00dd00";
        legendGroupName = "Segmented Side 01";
      } else if (matchArray(data[i]["Channel"],[1.3,2.3])) {
        colorText = "#0000dd";
        legendGroupName = "Segmented Side 01";
      }

      else if (matchArray(data[i]["Channel"],[1.1,1.2])) {
        colorText = "#a31545";
        legendGroupName = "Segmented Ring 01";
      } else if (matchArray(data[i]["Channel"],[1.1,1.3])) {
        colorText = "#00a152";
        legendGroupName = "Segmented Ring 01";
      } else if (matchArray(data[i]["Channel"],[1.2,1.3])) {
        colorText = "#007bb2";
        legendGroupName = "Segmented Ring 01";
      }

      else if (matchArray(data[i]["Channel"],[2.1,2.2])) {
        colorText = "#ed4b82";
        legendGroupName = "Segmented Ring 02";
      } else if (matchArray(data[i]["Channel"],[2.1,2.3])) {
        colorText = "#33eb91";
        legendGroupName = "Segmented Ring 02";
      } else if (matchArray(data[i]["Channel"],[2.2,2.3])) {
        colorText = "#33bfff";
        legendGroupName = "Segmented Ring 02";
      }

      fig.shadedErrorBar(data[i]["Frequency"], data[i]["MeanPower"], data[i]["StdPower"], {
        name: formatSegmentString(data[i]["Channel"]),
        legendgroup: legendGroupName,
        color: colorText,
        linewidth: 2,
        showlegend: true,
        hovertemplate: `E${data[i]["Channel"][0]}-E${data[i]["Channel"][1]} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
      }, {
        color: colorText,
        alpha: 0.3,
        legendgroup: legendGroupName,
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


export default SurveyFigure;