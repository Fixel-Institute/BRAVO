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

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext } from "context";

import { dictionary, dictionaryLookup } from "assets/translation";

function EventPSDs({dataToRender, selector, height, config, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data, selector) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1,1, {sharey: true, sharex: true});
      fig.setScaleType("linear", "y");
      fig.setTickValue([-30, -20, -10, 0, 10, 20, 30], "y");
      fig.setYlim([-30, 20]);
      fig.setXlim([0, 100]);
      fig.setTitle(selector.value.text + " Comparison");

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
    if (selector.type == "Events") {
      for (var i in data[selector.value.value]) {
        fig.plot(data[selector.value.value][i]["Frequency"], data[selector.value.value][i]["MeanPower"], {
          name: data[selector.value.value][i]["Channel"],
          color: colors[i*4],
          linewidth: 2,
          showlegend: true,
          hovertemplate: `${data[selector.value.value][i]["Channel"]} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
        });
      }
    } else {
      const steps = Math.floor(24/eventNames.length);
      for (var j in eventNames) {
        for (var i in data[eventNames[j]]) {
          if (selector.value.value == data[eventNames[j]][i]["Channel"]) {
            fig.plot(data[eventNames[j]][i]["Frequency"], data[eventNames[j]][i]["MeanPower"], {
              name: eventNames[j],
              color: colors[j*steps],
              linewidth: 2,
              showlegend: true,
              hovertemplate: `${eventNames[j]} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
            });
          }
        }
      }
    }
    /*
    for (var i in data) {
      var timestruct = new Date(data[i]["Timestamp"]*1000);
      const colorIndex = Math.floor((data[0]["Timestamp"] - data[i]["Timestamp"]) / Timespan * (colors.length-1));
      
      fig.plot(data[i]["Frequency"], data[i]["MeanPower"], {
        name: timestruct.toLocaleString(language),
        color: colors[colors.length-1-colorIndex],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${timestruct.toLocaleString(language)} %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
      });
    }
    */

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

export default EventPSDs;