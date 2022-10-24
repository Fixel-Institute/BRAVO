import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function TimeFrequencyFigure({dataToRender, height, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);
  
  const handleGraphing = (data, channelInfos) => {
    fig.clearData();
    
    if (fig.fresh) {
      var axLength = 0;
      var channelInfo = null;
      for (var i in data) {
        if (data[i].Channels.length > axLength) {
          axLength = data[i].Channels.length;
          channelInfo = channelInfos[i];
        }
      }

      var ax = fig.subplots(axLength, 1, {sharex: true, sharey: true});
      fig.setXlabel("Time (local time)", {fontSize: 15}, ax[ax.length-1]);
      for (var i in ax) {
        fig.setYlim([0,100],ax[i]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15}, ax[i]);

        const [side, target] = channelInfo[i].Hemisphere.split(" ");
        const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfo[i].Contacts[0]}-E${channelInfo[i].Contacts[1]}`;
        fig.setSubtitle(`${titleText}`,ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);

      fig.createColorAxis({
        colorscale: "Jet",
        colorbar: {y: 0.5, len: (1/2)},
        clim: [-20, 20],
      });
    }

    for (var i in data) {
      for (var j in data[i].Channels) {
        var timeArray = Array(data[i].Spectrums[data[i].Channels[j]].Time.length).fill(0).map((value, index) => new Date(data[i].Timestamp*1000 + data[i].Spectrums[data[i].Channels[j]].Time[index]*1000));
        for (var k in ax) {
          if (!ax[k].title) {
            ax[k].title = data[i].Channels[j];
            fig.surf(timeArray, data[i].Spectrums[data[i].Channels[j]].Frequency, data[i].Spectrums[data[i].Channels[j]].logPower, {
              zlim: [-20, 20],
              coloraxis: "coloraxis",
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
            }, ax[k]);
            break;
          } else if (ax[k].title == data[i].Channels[j]) {
            fig.surf(timeArray, data[i].Spectrums[data[i].Channels[j]].Frequency, data[i].Spectrums[data[i].Channels[j]].logPower, {
              zlim: [-20, 20],
              coloraxis: "coloraxis",
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}<br>  %{x} <br>  %{z:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "dB", language)} <extra></extra>`,
            }, ax[k]);
            break;
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
    if (dataToRender) handleGraphing(dataToRender.data, dataToRender.ChannelInfos);
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

export default TimeFrequencyFigure ;