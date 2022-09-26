import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';
import { mean, sqrt, std } from "mathjs";

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility";

import { usePlatformContext } from "context";

function EventPowerSpectrum({dataToRender, timerange, events, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    var ax;
    if (fig.fresh) {
      ax = fig.subplots(1, 2, {sharex: true, sharey: true});
      fig.setScaleType("log", "y");
      fig.setTickValue([0.1, 1, 10], "y");
      fig.setYlim([-1, 1]);
      fig.setXlim([0, 100], ax[0]);
      fig.setXlim([0, 100], ax[1]);
      fig.setXlabel("Frequency (Hz)", {fontSize: 15}, ax[0]);
      fig.setXlabel("Frequency (Hz)", {fontSize: 15}, ax[1]);
      fig.setYlabel("Power (a.u.)", {fontSize: 15});
      fig.setLegend({
        xanchor: "left"
      });

      fig.setSubtitle("Left Hemisphere", ax[0]);
      fig.setSubtitle("Right Hemisphere", ax[1]);
    }

    const timeLimits = timerange.map((momentDate) => momentDate.toDate().getTime() / 1000)
    var frequencyArray = new Array(100);
    for (var t = 0; t < frequencyArray.length; t++)  {
      frequencyArray[t] = t*250/256;
    }
    
    const hemispheres = ["HemisphereLocationDef.Left", "HemisphereLocationDef.Right"];
    for (var i in data) {
      for (var hemisphereId in hemispheres ) {
        for (var eventName of Object.keys(events)) {
          const powerSpectrums = data[i][hemispheres[hemisphereId]].filter((value, index) => {
            return data[i][hemispheres[hemisphereId]][index] && data[i].EventName[index] == eventName && data[i].EventTime[index] < timeLimits[1] && data[i].EventTime[index] >= timeLimits[0];
          });

          if (powerSpectrums.length > 0) {
            const meanData = frequencyArray.map((value, index) => {
              return mean(powerSpectrums.map((value) => value[index]));
            });
            const stdData = frequencyArray.map((value, index) => {
              return std(powerSpectrums.map((value) => value[index])) / sqrt(powerSpectrums.length)*2;
            });

            fig.shadedErrorBar(frequencyArray, meanData, stdData, {
              color: events[eventName].color,
              name: eventName,
              linewidth: 2,
              hovertemplate: " " + eventName + " %{y:.2f} <extra></extra>",
              legendgroup: eventName,
              showlegend: true
            }, {
              color: events[eventName].color,
              legendgroup: eventName,
            }, ax[hemisphereId]);
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
  React.useEffect(async () => {
    if (dataToRender && timerange[0] && timerange[1]) handleGraphing(dataToRender);
  }, [dataToRender, timerange, language]);

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