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

function ImpedanceHeatmap({dataToRender, onContactSelect, logType, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      let ax = fig.subplots(1, 2, {sharey: false, sharex: false, colSpacing: 0.05});
    }

    let ax = fig.getAxes();
    if (data.log.Left) {
      if (logType == "Bipolar") {
        let contactArrayY = Array(data.log.Left[logType].length).fill(0).map((value, index) => index);
        let contactArrayX = Array(data.log.Left[logType][0].length).fill(0).map((value, index) => index);
        fig.surf(contactArrayX, contactArrayY, data.log.Left[logType], {
          hovertemplate: `  %{z:d} Impedance <extra></extra>`,
          zsmooth: false,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 0.5, len: 1},
            clim: [0,6000*contactArrayY.length/4],
            showscale: false
          }),
        }, ax[0]);
        
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
      } else {
        let contactArrayY = Array(data.log.Left[logType].length).fill(0).map((value, index) => index);
        let contactArrayX = Array(data.log.Left[logType][0].length).fill(0).map((value, index) => index);
        fig.surf(contactArrayX, contactArrayY, data.log.Left[logType].map((value) => [value]), {
          hovertemplate: `  %{z:d} Impedance <extra></extra>`,
          zsmooth: false,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 0.5, len: 1},
            clim: [0,4000*contactArrayY.length/4],
            showscale: false
          }),
        }, ax[0]);
        
        fig.setAxisProps({
          ticks: "",
          showticklabels: false
        }, "x", ax[0]);
        fig.setAxisProps({
          ticksmode: "array",
          tickvals: contactArrayY,
          ticktext: contactArrayY.length == 4 ? contactArrayY : ["0","1A","1B","1C","2A","2B","2C","3"],
          showticklabels: true
        }, "y", ax[0]);
      }
    }

    if (data.log.Right) {
      if (logType == "Bipolar") {
        let contactArrayY = Array(data.log.Right[logType].length).fill(0).map((value, index) => index);
        let contactArrayX = Array(data.log.Right[logType][0].length).fill(0).map((value, index) => index);
        fig.surf(contactArrayX, contactArrayY, data.log.Right[logType], {
          hovertemplate: `  %{z:d} Impedance <extra></extra>`,
          zsmooth: false,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 0.5, len: 1},
            clim: [0,6000*contactArrayY.length/4],
            showscale: false
          }),
        }, ax[1]);
        
        fig.setAxisProps({
          ticksmode: "array",
          tickvals: contactArrayX,
          ticktext: contactArrayX.length == 4 ? contactArrayX : ["0","1A","1B","1C","2A","2B","2C","3"],
          showticklabels: true
        }, "x", ax[1]);
        fig.setAxisProps({
          ticksmode: "array",
          tickvals: contactArrayY,
          ticktext: contactArrayY.length == 4 ? contactArrayY : ["0","1A","1B","1C","2A","2B","2C","3"],
          showticklabels: true
        }, "y", ax[1]);
      } else {
        let contactArrayY = Array(data.log.Right[logType].length).fill(0).map((value, index) => index);
        let contactArrayX = Array(data.log.Right[logType][0].length).fill(0).map((value, index) => index);
        fig.surf(contactArrayX, contactArrayY, data.log.Right[logType].map((value) => [value]), {
          hovertemplate: `  %{z:d} Impedance <extra></extra>`,
          zsmooth: false,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 0.5, len: 1},
            clim: [0,4000*contactArrayY.length/4],
            showscale: false
          }),
        }, ax[1]);

        fig.setAxisProps({
          ticks: "",
          showticklabels: false
        }, "x", ax[1]);
        fig.setAxisProps({
          ticksmode: "array",
          tickvals: contactArrayY,
          ticktext: contactArrayY.length == 4 ? contactArrayY : ["0","1A","1B","1C","2A","2B","2C","3"],
          showticklabels: true
        }, "y", ax[1]);
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
    if (dataToRender.length > 0) handleGraphing(dataToRender[dataToRender.length-1]);
    else {
      fig.purge();
      setShow(false);
    }
  }, [dataToRender, logType, language]);

  const onResize = useCallback(() => {
    fig.refresh();
  }, []);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });
  
  var updateTimeout = null;
  var plotly_singleclicked = false;
  const plotly_onClick = (data) => {
    if (plotly_singleclicked) {
      plotly_singleclicked = false;
      clearTimeout(updateTimeout);
    } else {
      plotly_singleclicked = true;
      updateTimeout = setTimeout(function() {
        onContactSelect(data["points"][0]);
        plotly_singleclicked = false
      }, 300);
    }
  };

  React.useEffect(() => {
    if (ref.current.on) {
      ref.current.on("plotly_click", plotly_onClick);
    }
  }, [ref.current, dataToRender]);

  return (
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default ImpedanceHeatmap;