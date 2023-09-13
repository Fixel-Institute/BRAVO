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

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function CircadianRhythm({dataToRender, selector, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, selector) => {
    fig.clearData();

    if (fig.fresh) {
      const currentTimestamp = new Date();
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15});
      fig.setXlim([new Date(currentTimestamp.getTimezoneOffset()*60*1000), new Date(24*60*60*1000 + currentTimestamp.getTimezoneOffset()*60*1000)])
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15});
      fig.setAxisProps({
        tickformat: "%H:%M %p"
      }, "x");

      fig.setLayoutProps({
        hovermode: "xy"
      });

      const [device, hemisphere, therapy] = selector.value.split("//");
      const titleText = `${device} ${hemisphere} ${selector.therapyName}`;
      fig.setTitle(`${titleText}`);
    }

    for (var k = 0; k < data.length; k++) {
      if (data[k]["Device"] + " " + data[k]["Hemisphere"] == selector.hemisphere) {
        for (var j = 0; j < data[k].CircadianPowers.length; j++) {
          if (data[k].CircadianPowers[j].Therapy == selector.therapyName) {
            var timeArray = Array(data[k].CircadianPowers[j]["AverageTimestamp"].length).fill(0).map((value, index) => new Date(data[k].CircadianPowers[j]["AverageTimestamp"][index]*1000));
            fig.shadedErrorBar(timeArray, data[k].CircadianPowers[j]["AveragePower"], data[k].CircadianPowers[j]["StdErrPower"], {
              color: "#AA0000",
              linewidth: 2,
              hovertemplate: "  %{x} <br>  " + selector.therapyName + "<br>  %{y:.2f} <extra></extra>",
            }, {
              color: "#AA0000",
            });
          }
        }
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
    if (dataToRender) handleGraphing(dataToRender, selector);
  }, [dataToRender, selector, language]);

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

export default CircadianRhythm;