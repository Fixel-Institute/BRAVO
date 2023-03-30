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

function PatientEventCount({dataToRender, events, height, stack, grouping, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, timeRange) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharex: true, sharey: true});
      //fig.setXlim(timeRange.map((time) => new Date(time*1000)));
      //fig.setXlim(timeRange);
      fig.setYlabel("Frequency (Count)", {fontsize: 15});
      
      fig.setLegend({
        tracegroupgap: 5,
        xanchor: 'left',
      });

      fig.setLayoutProps({
        hovermode: "xy",
        barmode: stack ? "stack" : "group"
      });
      fig.setTitle("Patient Marked Event Logs");
    }

    var timeblock = Object.keys(data);
    timeblock = timeblock.sort((a,b) => a > b);

    const yearRange = timeRange.map((time) => {
      return new Date(time*1000).getFullYear();
    });
    const keyRange = timeRange.map((time) => {
      if (grouping == "Week") {
        const year = new Date(time*1000).getFullYear();
        var weekNumber = Math.floor((time % (3600*24*365)) / (3600*24) / 7);
        weekNumber = weekNumber > 51 ? 51 : weekNumber;
        const weekKey = `${year} Week ${weekNumber.toFixed(0).padStart(2, "0")}`;
        return weekKey;
      } else if (grouping == "Month") {
        const year = new Date(time*1000).getFullYear();
        const month = new Date(time*1000).getMonth();
        const monthKey = `${year} Month ${(month+1).toFixed(0).padStart(2, "0")}`;
        return monthKey;
      }
    });

    for (var key of Object.keys(events)) {
      var ydata = [];
      var xdata = [];
      var label = [];

      for (var year = yearRange[0]; year <= yearRange[1]; year++) {
        if (grouping == "Week") {
          const startTime = new Date(`${year}-01-01`);
          for (var weekNumber = 0; weekNumber < 52; weekNumber++) {
            const weekKey = `${year} Week ${weekNumber.toFixed(0).padStart(2, "0")}`;
            if (weekKey >= keyRange[0] && weekKey <= keyRange[1]) {
              xdata.push(new Date(startTime.getTime() + weekNumber *7*3600*24*1000 + startTime.getTimezoneOffset()*60000).toLocaleDateString(language));
              ydata.push(data[weekKey] ? data[weekKey].filter((value) => value == key).length : 0);
              label.push(ydata[ydata.length-1].toFixed(0).padStart(2,"0"));
            }
          }
        } else if (grouping == "Month") {
          for (var monthNumber = 0; monthNumber < 12; monthNumber++) {
            const startTime = new Date(`${year}-${(monthNumber+1).toFixed(0).padStart(2, "0")}-01`);
            const monthKey = `${year} Month ${(monthNumber+1).toFixed(0).padStart(2, "0")}`;
            if (monthKey >= keyRange[0] && monthKey <= keyRange[1]) {
              xdata.push(new Date(startTime.getTime() + startTime.getTimezoneOffset()*60000).toLocaleDateString(language));
              ydata.push(data[monthKey] ? data[monthKey].filter((value) => value == key).length : 0);
              label.push(ydata[ydata.length-1].toFixed(0).padStart(2,"0"));
            }
          }
        }
      }

      fig.bar(xdata, ydata, {
        facecolor: events[key].color,
        name: key,
        meta: key,
        text: label,
        hovertemplate: "  %{x} %{meta} <br>  Count: %{y} <extra></extra>",
      });
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

      var data = {};
      var timeRange = [-1,-1];
      for (var i in dataToRender) {
        for (var j in dataToRender[i].EventTime) {
          if (timeRange[0] < 0 || dataToRender[i].EventTime[j] < timeRange[0]) {
            timeRange[0] = dataToRender[i].EventTime[j];
          }
          if (timeRange[1] < 0 || dataToRender[i].EventTime[j] > timeRange[1]) {
            timeRange[1] = dataToRender[i].EventTime[j];
          }

          const dateTime = new Date(dataToRender[i].EventTime[j]*1000);
          const year = dateTime.getFullYear();
  
          if (grouping == "Week") {
            var weekNumber = Math.floor((dataToRender[i].EventTime[j] % (3600*24*365)) / (3600*24) / 7);
            weekNumber = weekNumber > 51 ? 51 : weekNumber;
            const weekKey = `${year} Week ${weekNumber.toFixed(0).padStart(2, "0")}`;
            if (!Object.keys(data).includes(weekKey)) {
              data[weekKey] = [];
            }
            data[weekKey].push(dataToRender[i].EventName[j]);

          } else if (grouping == "Month") {
            const month = dateTime.getMonth();
            const monthKey = `${year} Month ${(month+1).toFixed(0).padStart(2, "0")}`;
            if (!Object.keys(data).includes(monthKey)) {
              data[monthKey] = [];
            }
            data[monthKey].push(dataToRender[i].EventName[j]);
          }
        }
      }
  
      handleGraphing(data, timeRange);
    } 
  }, [dataToRender, language, grouping, stack]);

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

export default PatientEventCount;