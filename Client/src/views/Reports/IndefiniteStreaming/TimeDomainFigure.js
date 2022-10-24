import React, { useCallback } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function TimeDomainFigure({dataToRender, height, figureTitle}) {
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
        fig.setYlim([-100,100],ax[i]);
        fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Amplitude", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)})`, {fontSize: 15}, ax[i]);

        const [side, target] = channelInfo[i].Hemisphere.split(" ");
        const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfo[i].Contacts[0]}-E${channelInfo[i].Contacts[1]}`;
        fig.setSubtitle(`${titleText}`,ax[i]);
      }
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15}, ax[ax.length-1]);

    }

    for (var i in data) {
      for (var j in data[i].Channels) {
        var timeArray = Array(data[i][data[i].Channels[j]].length).fill(0).map((value, index) => new Date(data[i].Timestamp*1000 + 4*index));
        for (var k in ax) {
          if (!ax[k].title) {
            ax[k].title = data[i].Channels[j];
            fig.plot(timeArray, data[i][data[i].Channels[j]], {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
            }, ax[k]);
            break;
          } else if (ax[k].title == data[i].Channels[j]) {
            fig.plot(timeArray, data[i][data[i].Channels[j]], {
              linewidth: 0.5,
              hovertemplate: `  %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "mV", language)}<extra></extra>`,
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

export default TimeDomainFigure;