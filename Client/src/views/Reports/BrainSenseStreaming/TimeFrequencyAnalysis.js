import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function TimeFrequencyAnalysis({dataToRender, channelInfos, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      if (data.Channels.length == 2) {
        let ax = fig.subplots(7, 1, {sharey: false, sharex: true});

        for (var i in data.Channels) {
          fig.setYlim([-200, 200], ax[0+i*3]);
          fig.setYlim([0, 100], ax[1+i*3]);
          fig.setYlim([0, 5000], ax[2+i*3]);

          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[i*3]);
          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[i*3+1]);
          fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[i*3+2]);
        }

        for (var i in data.Channels) {
          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
          fig.setSubtitle(`${titleText}`,ax[i*3]);
          fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
          fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
        }
        fig.setSubtitle(`${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "Stimulation", language)}`,ax[6]);

        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[6]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[6]);
      } else {
        let ax = fig.subplots(4, 1, {sharey: false, sharex: true});
        
        for (var i in data.Channels) {
          fig.setYlim([-200, 200], ax[0+i*3]);
          fig.setYlim([0, 100], ax[1+i*3]);
          fig.setYlim([0, 5000], ax[2+i*3]);
          
          const [side, target] = channelInfos[i].Hemisphere.split(" ");
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
          fig.setSubtitle(`${titleText}`,ax[i*3]);
          fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "TimeFrequencyAnalysis", language)}`,ax[i*3 + 1]);
          fig.setSubtitle(`${titleText} ${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "PowerChannel", language)} ${data.Info.Therapy[side].FrequencyInHertz} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} `,ax[i*3 + 2]);
        }
        fig.setSubtitle(`${dictionaryLookup(dictionary.BrainSenseStreaming.Figure, "Stimulation", language)}`,ax[3]);

        fig.setYlim([-200, 200], ax[0]);

        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[0]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[1]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "AU", language)})`, {fontSize: 15}, ax[2]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15}, ax[3]);
        fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[3]);
        
      }
    }

    if (data.Channels.length == 2) {
      let ax = fig.getAxes();
      for (var i in data.Channels) {
        var timeArray = Array(data[data.Channels[i]].RawData.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + 4*index));
        fig.plot(timeArray, data[data.Channels[i]].RawData, {
          linewidth: 0.5,
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
        }, ax[i*3 + 0]);

        var timeArray = Array(data[data.Channels[i]].Spectrogram.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + data[data.Channels[i]].Spectrogram.Time[index]*1000));
        fig.surf(timeArray, data[data.Channels[i]].Spectrogram.Frequency, data[data.Channels[i]].Spectrogram.Power, {
          zlim: [-20, 20],
          hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
          coloraxis: fig.createColorAxis({
            colorscale: "Jet",
            colorbar: {y: 1-(1/14)-(i*3+1)*(1/7), len: (1/7)},
            clim: data[data.Channels[i]].Spectrogram.ColorRange,
          }),
        }, ax[i*3 + 1]);

        for (var powerband of data.PowerBand) {
          if (powerband.Name == data.Channels[i]) {
            var timeArray = Array(powerband.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + powerband.Time[index]*1000));
            fig.plot(timeArray, powerband.Power, {
              linewidth: 2,
              hovertemplate: `  %{y:.2f}<extra></extra>`,
            }, ax[i*3 + 2]);
          }
        }
      }
    } else {
      let ax = fig.getAxes();

      var timeArray = Array(data[data.Channels[0]].RawData.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + 4*index));
      fig.plot(timeArray, data[data.Channels[0]].RawData, {
        linewidth: 0.5,
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
      }, ax[0]);

      var timeArray = Array(data[data.Channels[0]].Spectrogram.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + data[data.Channels[0]].Spectrogram.Time[index]*1000));
      fig.surf(timeArray, data[data.Channels[0]].Spectrogram.Frequency, data[data.Channels[0]].Spectrogram.Power, {
        zlim: [-20, 20],
        hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
        coloraxis: fig.createColorAxis({
          colorscale: "Jet",
          colorbar: {y: 0.65, len: (1/4)},
          clim: data[data.Channels[0]].Spectrogram.ColorRange,
        }),
      }, ax[1]);

      for (var powerband of data.PowerBand) {
        if (powerband.Name == data.Channels[0]) {
          var timeArray = Array(powerband.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + powerband.Time[index]*1000));
          fig.plot(timeArray, powerband.Power, {
            linewidth: 2,
            hovertemplate: `  %{y:.2f}<extra></extra>`,
          }, ax[2]);
        }
      }
    }

    let ax = fig.getAxes();
    for (var stimulation of data.Stimulation) {
      var stimulationLineColor;
      if (stimulation.Name.endsWith("RIGHT")) {
        stimulationLineColor = "#FCA503";
      } else {
        stimulationLineColor = "#253EF7";
      }
      var timeArray = Array(stimulation.Time.length).fill(0).map((value, index) => new Date(data.Timestamp*1000 + stimulation.Time[index]*1000));
      fig.plot(timeArray, stimulation.Amplitude, {
        linewidth: 3,
        color: stimulationLineColor,
        shape: "hv",
        hovertemplate: ` ${stimulation.Name} %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)}<br>  %{x} <extra></extra>`,
      }, ax[ax.length-1])
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
    else {
      fig.purge();
      setShow(false);
    }
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

export default TimeFrequencyAnalysis;