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

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function CorrelationScatterPlot({dataToRender, correlationIndex, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharey: false, sharex: false, colSpacing: 0.05});
      fig.setXlabel("log Neural Power (dB)", {fontSize: 15});
      fig.setYlabel("log Motion Power (dB)", {fontSize: 15});
      fig.setTitle(`Neural ${correlationIndex.x.toFixed(1)} Hz vs. Accelerometer ${correlationIndex.y.toFixed(1)} Hz`)
    }

    if (data) {
      const xData = data.Power[data.DataFrequency.indexOf(correlationIndex.x)];
      const yData = data.SensorPower[data.SensorFrequency.indexOf(correlationIndex.y)]
      fig.scatter(xData, yData, {size: 3});
      fig.setXlim([Math.min(...xData), Math.max(...xData)]);
      fig.setYlim([Math.min(...yData), Math.max(...yData)]);
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
    if (dataToRender.CorrelationMatrix) handleGraphing(dataToRender);
    else {
      fig.purge();
      setShow(false);
    }
  }, [dataToRender, correlationIndex, language]);

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

export default CorrelationScatterPlot;