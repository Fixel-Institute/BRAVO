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
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function TherapyHistoryFigure({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(1, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      fig.setYlim([-0.5, 3.5]);
      fig.setYlabel(dictionaryLookup(dictionary.TherapyHistory.Figure, "TherapyGroup", language),{fontSize: 15});
      fig.setTickValue([0,1,2,3], "y");
      fig.setTickLabel(["Group A","Group B","Group C","Group D"], "y");
      fig.setAxisProps({
        zeroline: false
      }, "y");
      fig.setTitle(dictionaryLookup(dictionary.TherapyHistory.Figure, "TherapyChangeLog", language));
    }

    for (var i = 0; i < data.length; i++) {
      var xdata = []
      var ydata = []
      for (var j = 0; j < data[i]["new_group"].length; j++) {
        if (j == 0 || data[i]["previous_group"][j] == "GroupIdDef.GROUP_UNKNOWN") {
          var date = new Date(data[i]["date_of_change"][j]/1000000)
          xdata.push(date,date)
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0,0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1,1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2,2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3,3)
        } else if (j > 0 && data[i]["previous_group"][j] != data[i]["new_group"][j-1]) {
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          ydata.push(null)
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3)
        } else {
          xdata.push(new Date(data[i]["date_of_change"][j]/1000000))
          if (data[i]["new_group"][j] == "GroupIdDef.GROUP_A") ydata.push(0)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_B") ydata.push(1)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_C") ydata.push(2)
          else if (data[i]["new_group"][j] == "GroupIdDef.GROUP_D") ydata.push(3)
        }
      }
      
      fig.plot(xdata, ydata, {
        type: 'scatter',
        mode: 'lines',
        line: {shape: 'hv'},
        hovertemplate: "  %{x} <br>  %{y} <extra></extra>",
        name: data[i]["device_name"]
      });

      let therapyStatusDate = data[i]["date_of_status"].map((value) => new Date(value/1000000));
      let newTherapyStatus = data[i]["new_status"].map((value)=> value ? 3.5 : -0.5);

      if (newTherapyStatus[0] == 3.5) {
        /*
        fig.addShadedArea([xdata[0], therapyStatusDate[0]], {
          color: "#FF0000"
        });
        */
      }
      for (let j = 0; j < newTherapyStatus.length; j++) {
        if (newTherapyStatus[j] == -0.5) {
          if (j == newTherapyStatus.length-1) {
            /*
            fig.addShadedArea([therapyStatusDate[j], new Date(data[i]["date_of_change"][data[i]["date_of_change"].length-1]/1000000)], {
              color: "#FF0000"
            });
            */
          } else {
            fig.addShadedArea([therapyStatusDate[j], therapyStatusDate[j+1]], {
              color: "#FF0000"
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
    if (dataToRender) handleGraphing(dataToRender);
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

export default TherapyHistoryFigure;