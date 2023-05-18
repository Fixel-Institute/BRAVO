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

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function ImpedanceHistory({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      
      fig.setYlabel(dictionaryLookup(dictionary.TherapyHistory.Figure, "Impedance", language), {fontSize: 15});
      fig.setTitle(dictionaryLookup(dictionary.TherapyHistory.Figure, "ImpedanceHistory", language));
    }
    
    let impedanceHistoryValues = data.data.map((item) => item.value);
    fig.setYlim([0, Math.max(...impedanceHistoryValues)*1.1]); 

    let impedanceHistoryDates = data.data.map((item) => Math.floor(item.timestamps / 3600 / 15 / 24)*3600*24*15).map((item) => new Date(item*1000));
    
    fig.box(impedanceHistoryDates, impedanceHistoryValues, {
      hoveron: "points",
      pointpos: -1.5,
      boxpoints: "all",
      jitter: 0.3,
      marker: {
        color: "#FF0000",
        size: 5
      }
    });

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

export default ImpedanceHistory;