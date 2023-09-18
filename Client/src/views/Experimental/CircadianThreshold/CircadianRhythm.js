/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, { useRef, useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';
import * as Math from "mathjs";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function CircadianRhythm({dataToRender, selector, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [threshold, setThreshold] = React.useState(1000);
  const figRef = useRef();
  
  const handleGraphing = (data, selector, threshold) => {
    const fig = figRef.current;
    fig.clearData();

    if (fig.fresh) {
      const ax = fig.subplots(2, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[1]);
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[0]);
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[1]);
      fig.setYlim([0, 5], ax[1]);
      fig.setSubtitle(`${selector.therapyName}`,ax[0]);
      fig.setSubtitle(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)}`,ax[1]);

      fig.setLegend({
        tracegroupgap: 5,
        xanchor: "left",
        y: 0.5,
      });

      fig.setLayoutProps({
        hovermode: "xy"
      });
    }

    var estimatedCDBS = 0;
    var estimatedADBS = 0;
    const ax = fig.getAxes();
    for (var k = 0; k < data.length; k++) {
      var therapyKey = "LeftHemisphere";
      if (data[k]["Hemisphere"].startsWith("Right")) {
        therapyKey = "RightHemisphere";
      }

      if (data[k]["Device"] + " " + data[k]["Hemisphere"] == selector.hemisphere) {
        for (var j = 0; j < data[k].Power.length; j++) {
          if (data[k].Therapy[j].TherapyOverview == selector.therapyName) {
            if (data[k]["Power"][j].length > 0) {
              var timeArray = Array(data[k]["Timestamp"][j].length).fill(0).map((value, index) => new Date(data[k]["Timestamp"][j][index]*1000));

              fig.plot(timeArray, data[k]["Power"][j], {
                linewidth: 2,
                color: "#000000",
                hovertemplate: "  %{x} <br>  %{y:.2f} <extra></extra>"
              }, ax[0]);

              fig.plot([timeArray[0], timeArray[data[k]["Timestamp"][j].length-1]], [threshold, threshold], {
                linewidth: 2,
                color: "#FF0000",
                hovertemplate: "  %{x} <br>  %{y:.2f} <extra></extra>"
              }, ax[0]);

              
              var stimulationArray = Array(data[k]["Timestamp"][j].length).fill(data[k].Therapy[j][therapyKey].Amplitude).map((value, index) => data[k]["Power"][j][index] < threshold ? 0 : value);
              estimatedADBS += Math.sum(stimulationArray);
              estimatedCDBS += (data[k]["Timestamp"][j].length * data[k].Therapy[j][therapyKey].Amplitude);
              fig.scatter(timeArray, stimulationArray, {
                size: 3,
                color: "#AA0000",
                hovertemplate: "  %{x} <br>  %{y:.2f} mA <extra></extra>"
              }, ax[1]);
            }
          }
        }
      }
    }

    const PercentDutyCycle = estimatedADBS / estimatedCDBS;
    fig.setSubtitle(`Estimated ${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${(PercentDutyCycle*100).toFixed(2)}%)`,ax[1]);

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
    if (Object.keys(selector).length > 0) {
      if (dataToRender && figRef.current) handleGraphing(dataToRender, selector, threshold);
    }
  }, [dataToRender, selector, threshold, figRef.current, language]);

  const onResize = useCallback(() => {
    if (figRef) {
      figRef.current = new PlotlyRenderManager(figureTitle, language);
      figRef.current.refresh();
    }
  }, [figRef]);

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
        onThresholdChange(data["points"][0]["y"]);
        plotly_singleclicked = false
      }, 300);
    }
  };

  const onThresholdChange = (threshold) => {
    setThreshold(threshold);
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

export default CircadianRhythm;