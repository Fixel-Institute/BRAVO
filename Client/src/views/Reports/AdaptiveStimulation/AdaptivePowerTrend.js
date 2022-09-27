import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function AdaptivePowerTrend({dataToRender, events, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    console.log(data)

    if (fig.fresh) {
      var ax = fig.subplots(data.length*2, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
       for (var i in data) {
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*2]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[i*2+1]);
        
        fig.setYlim([0, 5], ax[i*2+1]);

        const [side, target] = data[i].Hemisphere.split(" ");
        const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
        fig.setSubtitle(`${titleText}`,ax[i*2]);
        fig.setSubtitle(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)}`,ax[i*2+1]);
      }

      fig.setLegend({
        tracegroupgap: 5,
      });

      fig.setLayoutProps({
        hovermode: "xy"
      });
    }
    
    for (var i = 0; i < data.length; i++) {
      for (var j = 0; j < data[i].Timestamp.length; j++) {
        var therapyString = ""
        if (data[i]["Therapy"][j].hasOwnProperty("TherapyOverview")) therapyString = data[i]["Therapy"][j]["TherapyOverview"]

        var timeArray = Array(data[i]["Timestamp"][j].length).fill(0).map((value, index) => new Date(data[i]["Timestamp"][j][index]*1000));
        fig.plot(timeArray, data[i]["Power"][j], {
          linewidth: 2,
          color: "#000000",
          hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f} <extra></extra>"
        }, ax[i*2]);

        fig.plot(timeArray, data[i]["Amplitude"][j], {
          linewidth: 0.5,
          color: "#AA0000",
          hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f} <extra></extra>"
        }, ax[i*2+1]);

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
    if (dataToRender) handleGraphing(dataToRender.ChronicData);
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

export default AdaptivePowerTrend;