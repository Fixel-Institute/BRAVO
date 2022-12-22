import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function CircadianRhythm({dataToRender, therapyInfo, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    const currentTimestamp = new Date();
    if (fig.fresh) {
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

      //const titleText = `${device} ${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
      //fig.setTitle(`${titleText}`);
    }

    let offset = currentTimestamp.getTimezoneOffset()*60*1000;
    var timeArray = data.Timestamp.map((timestamp) => new Date(((timestamp-offset/1000) % (24*3600))*1000+offset))
    fig.scatter(timeArray, data.Power, {
      color: "#AA0000",
      size: 3,
      hovertemplate: "  %{x} <br>  " + "<br>  %{y:.2f} <extra></extra>",
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
    if (Object.keys(dataToRender).length > 0) handleGraphing(dataToRender);
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
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}
      onClick={(event) => event.stopPropagation()}
    />
  );
}

export default CircadianRhythm;