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

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function AnalysisBuilderOverview({dataToRender, configuration, onStreamClicked, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, configuration) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      fig.setAxisProps({
        zeroline: false
      }, "y");
      fig.setTitle("Analysis Builder - Data Inclusion and Label");

      fig.setLegend({
        bgcolor: "transparent",
      });
      fig.setLayoutProps({
        hovermode: "xy"
      })
    }

    let uniqueDataType = {};
    let ydata = [];
    let xdata = []; 
    let texts = [];
    let xlim = [0,0];
    data.map((recording, index) => {
      let config = configuration[recording.RecordingId] || {TimeShift: 0, Type: "Signal", Label: ""};
      let dataTypeKeys = Object.keys(uniqueDataType);
      if (!dataTypeKeys.includes(config.Type)) uniqueDataType[config.Type] = dataTypeKeys.length;

      ydata.push(uniqueDataType[config.Type]);
      xdata.push(new Date(recording.Time*1000 + recording.Duration*500 + config.TimeShift))
      if (config.Label === "") texts.push("[" + recording.RecordingLabel + "]<br>" + recording.RecordingType);
      else texts.push(config.Label);

      if (recording.Time*1000 + config.TimeShift < xlim[0] || xlim[0] == 0) {
        xlim[0] = recording.Time*1000 + config.TimeShift;
      }
      if (recording.Time*1000 + recording.Duration*1000 + config.TimeShift > xlim[1] || xlim[1] == 0) {
        xlim[1] = recording.Time*1000 + recording.Duration*1000 + config.TimeShift;
      }
    });

    fig.setLayoutProps({
      shapes: data.map((recording, index) => {
        let config = configuration[recording.RecordingId] || {TimeShift: 0, Type: "Signal"};
        return {
          type: "rect",
          xref: 'x',
          x0: new Date(recording.Time*1000 + config.TimeShift),
          x1: new Date(recording.Time*1000 + recording.Duration*1000 + config.TimeShift),
          y0: uniqueDataType[config.Type] - 0.3,
          y1: uniqueDataType[config.Type] + 0.3,
          line: { color: "#33c9dc", width: 2 },
          fillcolor: "#00bcd4",
          opacity: 0.4
        };
      })
    });

    fig.addText(xdata, ydata, texts);
    fig.setXlim([new Date(xlim[0] - 0.1*(xlim[1]-xlim[0])), new Date(xlim[1] + 0.1*(xlim[1]-xlim[0]))]);

    const dataTypeKeys = Object.keys(uniqueDataType);
    fig.setYlim([-0.5, Math.max(dataTypeKeys.length, 3) - 0.5]);
    fig.setTickValue(dataTypeKeys.map((key) => uniqueDataType[key]), "y");
    fig.setTickLabel(dataTypeKeys.map((key) => key), "y");

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
    if (dataToRender.Recordings.length > 0) handleGraphing(dataToRender.Recordings, dataToRender.Configuration.Descriptor);
    else { 
      fig.purge();
      setShow(false);
    }
  }, [dataToRender, configuration, language]);

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
        onStreamClicked(data);
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

export default AnalysisBuilderOverview;