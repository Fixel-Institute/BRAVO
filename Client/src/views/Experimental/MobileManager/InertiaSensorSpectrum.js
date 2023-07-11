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

function InertiaSensorSpectrum({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const [comboData, setComboData] = React.useState(null);
  const [xrange, setXRange] = React.useState([]);

  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      let ax = fig.subplots(6, 1, {sharex: true, sharey: true});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);
      fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
      fig.setSubtitle("Accelerometer (100Hz)", ax[0]);

      fig.setYlim([1,5], ax[1]);
      fig.setYlabel("Severity (1-5)", {fontSize: 15}, ax[1]);
      fig.setSubtitle("Apple Movement Disorder - Tremor Severity (Weighted Severity)", ax[1]);

      fig.setYlim([0,1], ax[2]);
      fig.setYlabel("Probability (0-1)", {fontSize: 15}, ax[2]);
      fig.setSubtitle("Apple Movement Disorder - Dyskinetic Probability", ax[2]);

      fig.setYlim([0,180], ax[3]);
      fig.setYlabel("Heart Rate (Beat/Min)", {fontSize: 15}, ax[3]);
      fig.setSubtitle("HealthKit - Heart Rate", ax[3]);

      fig.setYlim([0,180], ax[4]);
      fig.setYlabel("Interval (ms)", {fontSize: 15}, ax[4]);
      fig.setSubtitle("HealthKit - Heart Rate Variability", ax[4]);

      fig.setYlim([-0.1,5.1], ax[5]);
      fig.setTickValue([0,1,2,3,4,5], "y", ax[5]);
      fig.setTickLabel(["In Bed", "Sleep", "Awake", "Core Sleep", "Deep Sleep", "REM Sleep"], "y", ax[5]);
      fig.setSubtitle("HealthKit - Sleep State", ax[5]);
      
      fig.setLegend({
        tracegroupgap: 5,
        xanchor: 'left',
      });

      fig.setLayoutProps({
        hovermode: "x"
      });
    }

    let ax = fig.getAxes();

    if (data.Accelerometer.Time.length > 3600000*3) {
      let downsampler = (value, index) => index % 12000 == 0;
      let accTime = data.Accelerometer.Time.filter(downsampler);
  
      let rmsPower = data.Accelerometer.Data.map((value, index) => {
        return Math.sqrt(Math.pow(data.Accelerometer.Data[index][0],2) + Math.pow(data.Accelerometer.Data[index][1],2) + Math.pow(data.Accelerometer.Data[index][2],2));
      });
      let downSampledPower = new Array(accTime.length).fill(0);
      rmsPower.map((value, index) => {
        downSampledPower[Math.floor(index/12000)] += value / 12000;
      });
      
      fig.scatter(accTime, downSampledPower, {
        marker: {
          size: 5,
        },
        color: "#000000",
        showlegend: false,
        hovertemplate: " %{y:.2f} <extra></extra>"
      }, ax[0]);
  
      fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
      fig.setSubtitle("Mean Force (2-minute)", ax[0]);
    } else {
      let downsampler = (value, index) => index % 2 == 0;
      let accTime = comboData.Accelerometer.Time.filter(downsampler).map((t) => new Date(t*1000));
      let accData = comboData.Accelerometer.Data.filter(downsampler);

      fig.plot(accTime, accData.map((sample) => sample[0]), {
        linewidth: 1,
        color: "#f44336",
        name: "Accelerometer X-axis",
        showlegend: true,
        hovertemplate: " x: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, accData.map((sample) => sample[1]), {
        linewidth: 1,
        color: "#8bc34a",
        name: "Accelerometer Y-axis",
        showlegend: true,
        hovertemplate: " y: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, accData.map((sample) => sample[2]), {
        linewidth: 1,
        color: "#03a9f4",
        name: "Accelerometer Z-axis",
        showlegend: true,
        hovertemplate: " z: %{y:.2f} <extra></extra>"
      }, ax[0]);

      fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
      fig.setSubtitle("Accelerometer (100Hz)", ax[0]);
    }

    fig.scatter(data.TremorSeverity.Time.map((t) => new Date(t*1000)), data.TremorSeverity.Data.map((sample) => {
      let tremorSeverity = 0;
      let totalScale = 0;
      sample.map((value, index) => {
        tremorSeverity += value * index;
        if (index > 0) totalScale += value
      });

      if (totalScale > 0) {
        return tremorSeverity / totalScale;
      }
      return null;
    }), {
      marker: {
        size: 5,
      },
      color: "#000000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[1]);
    
    fig.scatter(data.DyskineticProbability.Time.map((t) => new Date(t*1000)), data.DyskineticProbability.Data, {
      marker: {
        size: 5,
      },
      color: "#000000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[2]);
    
    fig.scatter(data.HeartRate.Time.map((t) => new Date(t*1000)), data.HeartRate.Data, {
      marker: {
        size: 5,
      },
      color: "#FF0000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[3]);
    
    fig.scatter(data.HeartRateVariability.Time.map((t) => new Date(t*1000)), data.HeartRateVariability.Data, {
      marker: {
        size: 5,
      },
      color: "#FF0000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[4]);

    let sleepColors = ["#000000","#d7e360","#f6685e","#03a9f4","#0276aa","#35baf6"];
    for (let i in data.SleepState.Time) {
      fig.plot([data.SleepState.Time[i]*1000, data.SleepState.Time[i]*1000+data.SleepState.TimeRange[i]*1000], [data.SleepState.Data[i], data.SleepState.Data[i]], {
        linewidth: 10,
        color: sleepColors[data.SleepState.Data[i]],
        showlegend: false,
        hovertemplate: " %{y:.2f} <extra></extra>"
      }, ax[5]);
    }

    if (data.SleepState.Time.length == 0) {
      fig.plot([data.Time*1000, data.Time*1000], [data.SleepState.Data[2], data.SleepState.Data[2]], {
        linewidth: 10,
        color: sleepColors[data.SleepState.Data[2]],
        showlegend: false,
        hovertemplate: " %{y:.2f} <extra></extra>"
      }, ax[5]);
    }

    if (!data) {
      fig.purge();
      setShow(false);
    } else {
      fig.render();
      setShow(true);
    }
  }

  React.useEffect(() => {
    setComboData(dataToRender);
  }, [dataToRender]);

  React.useEffect(() => {
    if (comboData) {
      handleGraphing(comboData);
      setXRange([0,0]);
    }
  }, [language, comboData])

  const onResize = useCallback(() => {
    fig.refresh();
  }, []);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });

  var updateTimeout = null;
  var plotly_singleclicked = false;
  const plotly_onClick = (data) => {
    if (plotly_singleclicked) {
      plotly_singleclicked = false;
      clearTimeout(updateTimeout);
    } else {
      plotly_singleclicked = true;
    }
  };

  var lastXRange = [0,0];
  var lastTimeWindow = 3600*1000*5;
  React.useEffect(() => {
    /*
    if (ref.current.on) {
      ref.current.on("plotly_relayout", (eventdata) => {
        if (eventdata["xaxis.range[0]"] || eventdata["xaxis.autorange"]) {
          let ax = fig.getAxes();
          let startTime = new Date(eventdata["xaxis.range[0]"]).getTime();
          let endTime = new Date(eventdata["xaxis.range[1]"]).getTime();
          let timeWindow = endTime - startTime;

          if (eventdata["xaxis.autorange"]) {
            if (comboData.accelerometer.time.length < 3600000*3) {
              fig.clearAxes(ax[0]);
              
              let downsampler = (value, index) => index % 2 == 0;
              let accTime = comboData.accelerometer.time.filter(downsampler);
              fig.plot(accTime, comboData.accelerometer.x.filter(downsampler), {
                linewidth: 1,
                color: "#f44336",
                name: "Accelerometer X-axis",
                showlegend: true,
                hovertemplate: " x: %{y:.2f} <extra></extra>"
              }, ax[0]);
              fig.plot(accTime, comboData.accelerometer.y.filter(downsampler), {
                linewidth: 1,
                color: "#8bc34a",
                name: "Accelerometer Y-axis",
                showlegend: true,
                hovertemplate: " y: %{y:.2f} <extra></extra>"
              }, ax[0]);
              fig.plot(accTime, comboData.accelerometer.z.filter(downsampler), {
                linewidth: 1,
                color: "#03a9f4",
                name: "Accelerometer Z-axis",
                showlegend: true,
                hovertemplate: " z: %{y:.2f} <extra></extra>"
              }, ax[0]);

              fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
              fig.setSubtitle("Accelerometer (100Hz)", ax[0]);
  
              fig.render();
              lastXRange = [0,0];
            } else if (lastXRange != [0,0]) {
              fig.clearAxes(ax[0]);

              let downsampler = (value, index) => index % 12000 == 0;
              let accTime = comboData.accelerometer.time.filter(downsampler);
  
              let rmsPower = comboData.accelerometer.filtX.map((value, index) => {
                return Math.sqrt(Math.pow(comboData.accelerometer.filtX[index],2) + Math.pow(comboData.accelerometer.filtY[index],2) + Math.pow(comboData.accelerometer.filtZ[index],2));
              });
              let downSampledPower = new Array(accTime.length).fill(0);
              rmsPower.map((value, index) => {
                downSampledPower[Math.floor(index/12000)] += value / 12000;
              });
              
              fig.scatter(accTime, downSampledPower, {
                marker: {
                  size: 5,
                },
                color: "#000000",
                showlegend: false,
                hovertemplate: " %{y:.2f} <extra></extra>"
              }, ax[0]);
  
              fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
              fig.setSubtitle("Mean Force (2-minute)", ax[0]);
  
              fig.render();
              lastXRange = [0,0];
            }
          } else {
            if (timeWindow < 3600000*3) {
              if (startTime < lastXRange[0] || endTime > lastXRange[1]) {
                fig.clearAxes(ax[0]);
                
                let downsampler = (value, index) => index % 2 == 0 && comboData.accelerometer.time[index].getTime() > startTime && comboData.accelerometer.time[index].getTime() < endTime;
                let accTime = comboData.accelerometer.time.filter(downsampler);
                fig.plot(accTime, comboData.accelerometer.x.filter(downsampler), {
                  linewidth: 1,
                  color: "#f44336",
                  name: "Accelerometer X-axis",
                  showlegend: true,
                  hovertemplate: " x: %{y:.2f} <extra></extra>"
                }, ax[0]);
                fig.plot(accTime, comboData.accelerometer.y.filter(downsampler), {
                  linewidth: 1,
                  color: "#8bc34a",
                  name: "Accelerometer Y-axis",
                  showlegend: true,
                  hovertemplate: " y: %{y:.2f} <extra></extra>"
                }, ax[0]);
                fig.plot(accTime, comboData.accelerometer.z.filter(downsampler), {
                  linewidth: 1,
                  color: "#03a9f4",
                  name: "Accelerometer Z-axis",
                  showlegend: true,
                  hovertemplate: " z: %{y:.2f} <extra></extra>"
                }, ax[0]);
  
                fig.setYlabel("Force (g)", {fontSize: 15}, ax[0]);
                fig.setSubtitle("Accelerometer (100Hz)", ax[0]);
    
                fig.render();
                lastXRange = [startTime, endTime];
              } else {
  
              }
            }
          }
        }
      });
    }
    */
  }, [ref.current, comboData]);

  return (
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default InertiaSensorSpectrum;