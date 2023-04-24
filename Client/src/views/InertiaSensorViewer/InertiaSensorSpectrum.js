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
      fig.setSubtitle("Apple Movement Disorder - Dyskinesia Probability", ax[2]);

      fig.setYlim([0,180], ax[3]);
      fig.setYlabel("Heart Rate (Beat/Min)", {fontSize: 15}, ax[3]);
      fig.setSubtitle("HealthKit - Heart Rate", ax[3]);

      fig.setYlim([0,180], ax[4]);
      fig.setYlabel("Interval (ms)", {fontSize: 15}, ax[4]);
      fig.setSubtitle("HealthKit - Heart Rate Variability", ax[4]);

      fig.setYlim([0,10], ax[5]);
      fig.setYlabel("Sleep State", {fontSize: 15}, ax[5]);
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

    if (data.accelerometer.time.length > 3600000*3) {
      let downsampler = (value, index) => index % 12000 == 0;
      let accTime = data.accelerometer.time.filter(downsampler);
  
      let rmsPower = data.accelerometer.filtX.map((value, index) => {
        return Math.sqrt(Math.pow(data.accelerometer.filtX[index],2) + Math.pow(data.accelerometer.filtY[index],2) + Math.pow(data.accelerometer.filtZ[index],2));
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
    }

    fig.scatter(data.tremorSeverity.time, data.tremorSeverity.value, {
      marker: {
        size: 5,
      },
      color: "#000000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[1]);
    
    fig.scatter(data.dyskinesiaProbability.time, data.dyskinesiaProbability.value, {
      marker: {
        size: 5,
      },
      color: "#000000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[2]);
    
    fig.scatter(data.heartRate.time, data.heartRate.value, {
      linewidth: 1,
      color: "#FF0000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[3]);
    
    fig.scatter(data.heartRateVariability.time, data.heartRateVariability.value, {
      linewidth: 5,
      color: "#FF0000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[4]);

    fig.plot(data.sleepState.time, data.sleepState.value, {
      linewidth: 5,
      color: "#000000",
      showlegend: false,
      hovertemplate: " %{y:.2f} <extra></extra>"
    }, ax[5]);

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
    if (dataToRender.length > 0) {
      dataToRender.sort((a,b) => {
        return a.accelerometer.time[0] > b.accelerometer.time[0];
      });

      let data = dataToRender[0];
      for (let i = 1; i < dataToRender.length; i++) {

        for (let j = 0; j < dataToRender[i].accelerometer.x.length; j += 100000) {
          if (j + 100000 >= dataToRender[i].accelerometer.x.length) {
            data.accelerometer.x.push(...dataToRender[i].accelerometer.x.slice(j));
            data.accelerometer.y.push(...dataToRender[i].accelerometer.y.slice(j));
            data.accelerometer.z.push(...dataToRender[i].accelerometer.z.slice(j));
            data.accelerometer.time.push(...dataToRender[i].accelerometer.time.slice(j));
          } else {
            data.accelerometer.x.push(...dataToRender[i].accelerometer.x.slice(j, j+100000));
            data.accelerometer.y.push(...dataToRender[i].accelerometer.y.slice(j, j+100000));
            data.accelerometer.z.push(...dataToRender[i].accelerometer.z.slice(j, j+100000));
            data.accelerometer.time.push(...dataToRender[i].accelerometer.time.slice(j, j+100000));
          }
        }

        data.tremorSeverity.time.push(...dataToRender[i].tremorSeverity.time);
        data.tremorSeverity.value.push(...dataToRender[i].tremorSeverity.value);

        data.dyskinesiaProbability.time.push(...dataToRender[i].dyskinesiaProbability.time);
        data.dyskinesiaProbability.value.push(...dataToRender[i].dyskinesiaProbability.value);

        data.heartRate.time.push(...dataToRender[i].heartRate.time);
        data.heartRate.value.push(...dataToRender[i].heartRate.value);

        data.heartRateVariability.time.push(...dataToRender[i].heartRateVariability.time);
        data.heartRateVariability.value.push(...dataToRender[i].heartRateVariability.value);

        data.sleepState.time.push(...dataToRender[i].sleepState.time);
        data.sleepState.value.push(...dataToRender[i].sleepState.value);
      }

      data.accelerometer.filtX = new Array(data.accelerometer.x.length).fill(0);
      data.accelerometer.filtY = new Array(data.accelerometer.x.length).fill(0);
      data.accelerometer.filtZ = new Array(data.accelerometer.x.length).fill(0);

      let weight = 0;
      data.accelerometer.x.slice(1).map((value, index) => {
        data.accelerometer.filtX[index+1] = value - weight;
        weight += 0.2 * data.accelerometer.filtX[index+1];
      });

      weight = 0;
      data.accelerometer.y.slice(1).map((value, index) => {
        data.accelerometer.filtY[index+1] = value - weight;
        weight += 0.2 * data.accelerometer.filtY[index+1];
      });
      
      weight = 0;
      data.accelerometer.z.slice(1).map((value, index) => {
        data.accelerometer.filtZ[index+1] = value - weight;
        weight += 0.2 * data.accelerometer.filtZ[index+1];
      });

      setComboData(data);
    };
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
    if (ref.current.on) {
      ref.current.on("plotly_relayout", (eventdata) => {
        if (eventdata["xaxis.range[0]"] || eventdata["xaxis.autorange"]) {
          let ax = fig.getAxes();
          let startTime = new Date(eventdata["xaxis.range[0]"]).getTime();
          let endTime = new Date(eventdata["xaxis.range[1]"]).getTime();
          let timeWindow = endTime - startTime;

          if (eventdata["xaxis.autorange"]) {
            if (lastXRange != [0,0]) {
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
/*


          let ax = fig.getAxes();
          fig.clearAxes(ax[0]);



    if (timeWindow < 3600000 && timeWindow > 0) {
      const selectiveTime = (value, index) => {
        return data.accelerometer.time[index] < endTime && data.accelerometer.time[index] > startTime;
      };

      let downsampler = (value, index) => index % Math.floor(timeWindow/10/10000) == 0;
      let accTime = data.accelerometer.time.filter(selectiveTime).filter(downsampler);
      fig.plot(accTime, data.accelerometer.filtX.filter(selectiveTime).filter(downsampler), {
        linewidth: 1,
        color: "#f44336",
        name: "Accelerometer X-axis",
        showlegend: true,
        hovertemplate: " x: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, data.accelerometer.y.filter(selectiveTime).filter(downsampler), {
        linewidth: 1,
        color: "#8bc34a",
        name: "Accelerometer Y-axis",
        showlegend: true,
        hovertemplate: " y: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, data.accelerometer.z.filter(selectiveTime).filter(downsampler), {
        linewidth: 1,
        color: "#03a9f4",
        name: "Accelerometer Z-axis",
        showlegend: true,
        hovertemplate: " z: %{y:.2f} <extra></extra>"
      }, ax[0]);
    } else if (data.accelerometer.time.length < 3600*3*100) {
      let downsampler = (value, index) => index % 2 == 0;
      let accTime = data.accelerometer.time.filter(downsampler);
      fig.plot(accTime, data.accelerometer.filtX.filter(downsampler), {
        linewidth: 1,
        color: "#f44336",
        name: "Accelerometer X-axis",
        showlegend: true,
        hovertemplate: " x: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, data.accelerometer.y.filter(downsampler), {
        linewidth: 1,
        color: "#8bc34a",
        name: "Accelerometer Y-axis",
        showlegend: true,
        hovertemplate: " y: %{y:.2f} <extra></extra>"
      }, ax[0]);
      fig.plot(accTime, data.accelerometer.z.filter(downsampler), {
        linewidth: 1,
        color: "#03a9f4",
        name: "Accelerometer Z-axis",
        showlegend: true,
        hovertemplate: " z: %{y:.2f} <extra></extra>"
      }, ax[0]);
    } else {

          fig.render();
          //handleGraphing(comboData, startTime, endTime);
        }
        */
    }
  }, [ref.current, comboData]);

  return (
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default InertiaSensorSpectrum;