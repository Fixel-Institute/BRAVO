import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function EventLockedPower({dataToRender, selector, events, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      const currentTimestamp = new Date();
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.Time, "Minutes", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15});
      fig.setLegend();

      fig.setLayoutProps({
        hovermode: "x"
      });

      const [device, side, target] = selector.hemisphere.split(" ");
      const titleText = `${device} ${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} ${selector.therapyName}`;
      fig.setTitle(`${titleText}`);
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
    }

    for (var k = 0; k < data.length; k++) {
      if (data[k]["Device"] + " " + data[k]["Hemisphere"] == selector.hemisphere) {
        for (var j = 0; j < data[k].EventLockedPower.length; j++) {
          if (data[k].EventLockedPower[j].Therapy == selector.therapyName) {
            for (var i = 0; i < data[k].EventLockedPower[j].PowerChart.length; i++) {
              fig.shadedErrorBar(data[k].EventLockedPower[j].TimeArray, data[k].EventLockedPower[j].PowerChart[i].Line, data[k].EventLockedPower[j].PowerChart[i].Shade, {
                color: getColor(data[k].EventLockedPower[j].PowerChart[i].EventName),
                name: data[k].EventLockedPower[j].PowerChart[i].EventName,
                meta: data[k].EventLockedPower[j].PowerChart[i].EventName,
                linewidth: 2,
                hovertemplate: " %{meta} : %{y:.2f} <extra></extra>",
                legendgroup: data[k].EventLockedPower[j].PowerChart[i].EventName,
                showlegend: true
              }, {
                color: getColor(data[k].EventLockedPower[j].PowerChart[i].EventName),
                legendgroup: data[k].EventLockedPower[j].PowerChart[i].EventName,
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

export default EventLockedPower;