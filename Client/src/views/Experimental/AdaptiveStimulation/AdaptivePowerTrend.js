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

function AdaptivePowerTrend({dataToRender, selectedDevice, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      var ax = fig.subplots(data.length*2, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
       for (var i in data) {
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*2]);
        //fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[i*2+1]);
        fig.setYlabel(`Percent On Time (%)`, {fontSize: 15}, ax[i*2+1]);
        
        fig.setYlim([0, 100], ax[i*2+1]);

        if (data[i].Hemisphere === data[i].CustomName) {
          const [side, target] = data[i].Hemisphere.split(" ");
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)}`;
          fig.setSubtitle(`${titleText}`,ax[i*2]);
        } else {
          fig.setSubtitle(`${data[i].CustomName}`,ax[i*2]);
        }
        
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
      let hemisphereName = "RightHemisphere";
      if (data[i].Hemisphere.startsWith("Left")) {
        hemisphereName = "LeftHemisphere";
      }
      
      for (var j = 0; j < data[i].Timestamp.length; j++) {
        var therapyString = ""
        let therapyInfo = data[i]["Therapy"][j][hemisphereName];

        if (data[i]["Therapy"][j].hasOwnProperty("TherapyOverview")) {
          therapyString = data[i]["Therapy"][j]["TherapyOverview"]
        } else {
          if (therapyInfo.AmplitudeThreshold) therapyString = `${therapyInfo.Channel} ${therapyInfo.Frequency}Hz ${therapyInfo.PulseWidth}µS ${therapyInfo.AmplitudeThreshold[0]}-${therapyInfo.AmplitudeThreshold[1]}mA`;
          else therapyString = `${therapyInfo.Channel} ${therapyInfo.Frequency}Hz ${therapyInfo.PulseWidth}µS ${therapyInfo.Amplitude}mA`;
        }

        var timeArray = Array(data[i]["Timestamp"][j].length).fill(0).map((value, index) => new Date(data[i]["Timestamp"][j][index]*1000));
        fig.plot(timeArray, data[i]["Power"][j], {
          linewidth: 1,
          color: "#000000",
          hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f} <extra></extra>"
        }, ax[i*2]);

        if (data[i]["DutyCycle"][j].length > 0) {
          fig.plot(timeArray, data[i]["DutyCycle"][j], {
            linewidth: 0.5,
            color: "#AA0000",
            hovertemplate: "  %{x} <br>  " + therapyString + "<br>  %{y:.2f}% <extra></extra>"
          }, ax[i*2+1]);  
        }

        if (therapyInfo.hasOwnProperty("LFPThresholds")) {
          if (!(therapyInfo.LFPThresholds[0] == 20 && therapyInfo.LFPThresholds[1] == 30 && therapyInfo.CaptureAmplitudes[0] == 0 && therapyInfo.CaptureAmplitudes[1] == 0)) {
            fig.plot([timeArray[0],timeArray[timeArray.length-1]], [therapyInfo.LFPThresholds[0],therapyInfo.LFPThresholds[0]], {
              linewidth: 2,
              color: "#f50057",
              hovertemplate: "<extra></extra>"
            }, ax[i*2]);

            if (therapyInfo.LFPThresholds[0] != therapyInfo.LFPThresholds[1]) {
              fig.plot([timeArray[0],timeArray[timeArray.length-1]], [therapyInfo.LFPThresholds[1],therapyInfo.LFPThresholds[1]], {
                linewidth: 2,
                color: "#1100AA",
                hovertemplate: "<extra></extra>"
              }, ax[i*2]);
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
    if (dataToRender) {
      handleGraphing(dataToRender.filter((channel) => channel.Device == selectedDevice));
    };
  }, [dataToRender, selectedDevice, language]);

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