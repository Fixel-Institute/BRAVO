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

function EventPowerSpectrum({dataToRender, selector, events, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setScaleType("log", "y");
      fig.setTickValue([0.1, 1, 10], "y");
      fig.setYlim([-1, 1]);
      fig.setXlim([0, 100]);
      fig.setXlabel("Frequency (Hz)", {fontSize: 15});
      fig.setYlabel("Power (a.u.)", {fontSize: 15});
      fig.setLegend();

      fig.setTitle(selector.hemisphere + " " + selector.therapyName);
    }

    const colors = colormap({
      colormap: "rainbow-soft",
      nshades: 25,
      format: "hex",
      alpha: 1
    });
    const increment = Math.floor(25 / events.length);

    const getColor = (name) => {
      for (var i in events) {
        if (name.startsWith(events[i])) return colors[i * increment];
      }
      return colors[0];
    };

    for (var k = 0; k < data.length; k++) {
      if (data[k]["Device"] + " " + data[k]["Hemisphere"] == selector.hemisphere) {
        for (var j = 0; j < data[k].Render.length; j++) {
          if (data[k].Render[j].Therapy == selector.therapyName) {
            for (var i = 0; i < data[k].Render[j].Events.length; i++) {

              var frequencyArray = new Array(100);
              for (var t = 0; t < frequencyArray.length; t++)  {
                frequencyArray[t] = t*250/256;
              }
    
              fig.shadedErrorBar(frequencyArray, data[k].Render[j].Events[i].MeanPSD, data[k].Render[j].Events[i].StdPSD, {
                color: getColor(data[k].Render[j].Events[i].EventName),
                name: data[k].Render[j].Events[i].EventName,
                linewidth: 2,
                hovertemplate: " " + data[k].Render[j].Events[i].EventName + " %{y:.2f} <extra></extra>",
                legendgroup: data[k].Render[j].Events[i].EventName,
                showlegend: true
              }, {
                color: getColor(data[k].Render[j].Events[i].EventName),
                legendgroup: data[k].Render[j].Events[i].EventName,
              });
            }
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
    if (dataToRender) handleGraphing(dataToRender);
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

export default EventPowerSpectrum;