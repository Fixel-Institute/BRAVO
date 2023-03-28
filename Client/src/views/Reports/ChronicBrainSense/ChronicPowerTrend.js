import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function ChronicPowerTrend({dataToRender, events, selectedDevice, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    var axisTitles = []
    for (var k = 0; k < data.length; k++)
    {
      const [side, target] = data[k].Hemisphere.split(" ");
      const title = data[k]["Device"] + ` (${dictionaryLookup(dictionary.FigureStandardText, side, language)}) ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
      if (!axisTitles.includes(title)) axisTitles.push(title)
    }
    
    if (fig.fresh) {
      var ax = fig.subplots(data.length*2, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
       for (var i in data) {
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*2]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[i*2+1]);
        
        fig.setYlim([0, 5], ax[i*2+1]);

        if (data[i].Hemisphere === data[i].CustomName) {
          const [side, target] = data[i].Hemisphere.split(" ");
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
          fig.setSubtitle(`${titleText}`,ax[i*2]);
        } else {
          fig.setSubtitle(`${data[i].CustomName}`,ax[i*2]);
        }
        
        fig.setSubtitle(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)}`,ax[i*2+1]);
      }

      fig.setAxisProps({
        rangeselector: {buttons: [
          { count: 1, label: '1 Day', step: 'day', stepmode: 'todate' },
          { count: 7, label: '1 Week', step: 'day', stepmode: 'todate' },
          { count: 1, label: '1 Month', step: 'month', stepmode: 'todate' },
          {step: 'all'}
        ]},
      }, "x");

      fig.setLegend({
        tracegroupgap: 5,
        xanchor: "left",
        y: 0.5,
      });

      fig.setLayoutProps({
        hovermode: "xy"
      });
    }

    for (var i = 0; i < data.length; i++) {
      const eventData = {};
      for (var name of events) {
        eventData[name] = {xdata: [], ydata: []};
      }

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

        for (var k = 0; k < data[i].EventName[j].length; k++) {
          if (Object.keys(eventData).includes(data[i].EventName[j][k])) {
            eventData[data[i].EventName[j][k]].xdata.push(data[i].EventTime[j][k]*1000);
            eventData[data[i].EventName[j][k]].ydata.push(data[i].EventPower[j][k]);
          }
        }
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

      for (var j = 0; j < events.length; j++) {
        fig.scatter(eventData[events[j]].xdata, eventData[events[j]].ydata, {
          color: getColor(events[j]),
          size: 5,
          name: events[j],
          showlegend: true,
          legendgroup: events[j],
          hovertemplate: "  %{x} <br>  " + events[j] + "<extra></extra>"
        }, ax[i*2])
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
    if (dataToRender) {
      const channelData = dataToRender.ChronicData.filter((channel) => channel.Device == selectedDevice);
      if (channelData.length > 0) handleGraphing(channelData);
    };
  }, [dataToRender, events, selectedDevice, language]);

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

export default ChronicPowerTrend;