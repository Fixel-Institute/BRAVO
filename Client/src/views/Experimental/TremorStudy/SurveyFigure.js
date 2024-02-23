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
import colormap from "colormap";

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
      fig.setTickValue([0.00000001, 0.0000001, 0.000001, 0.00001, 0.0001, 0.001, 0.01], "y");
      fig.setYlim([-8, -2]);
      fig.setXlim([0, 20]);
      fig.setTitle(figureTitle);

      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (g<sup>2</sup>/Hz)`, {fontSize: 15});
    }

    const colors = colormap({
      colormap: "jet",
      nshades: Math.max(Object.keys(data).length-1,10),
      format: "hex",
      alpha: 1
    });

    let count = 0;

    for (var key of Object.keys(data)) {
      if (key == "Frequency") continue;

      count += 1;
      const legendGroupName = "Test";

      fig.shadedErrorBar(data["Frequency"], data[key]["MeanPower"], data[key]["StdPower"], {
        name: key,
        legendgroup: key,
        color: colors[count],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${key} %{y:.2g} g<sup>2</sup>/Hz <extra></extra>`,
      }, {
        color: colors[count],
        alpha: 0.3,
        legendgroup: key,
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