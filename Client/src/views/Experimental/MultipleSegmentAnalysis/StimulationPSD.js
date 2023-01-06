import React, {useCallback} from "react";
import {useResizeDetector} from "react-resize-detector";
import colormap from "colormap";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function StimulationPSD({dataToRender, channelInfos, therapy, height, type, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;
  
  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharey: false, sharex: false});
      fig.setScaleType("log", "y");
      fig.setTickValue([0.001, 0.01, 0.1, 1, 10, 100, 1000], "y");
      fig.setYlim([-3, 2]);
      fig.setXlim([0, 100]);
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});
      fig.setLegend({
        xanchor: "left"
      })

      const [side, target] = channelInfos[0].Channel.Hemisphere.split(" ");
      const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[0].Channel.Contacts[0]}-E${channelInfos[0].Channel.Contacts[1]}`;
      fig.setTitle(`${titleText}`);
    }

    const levels = data.length;
    const colors = colormap({
      colormap: "jet",
      nshades: Math.max(levels,10),
      format: "hex",
      alpha: 1
    });

    const frequency = Array(data[0]["PSD"].length).fill(0).map((value, index) => index/2);

    for (var j in data) {
      fig.plot(frequency, data[j]["PSD"], {
        name: `${channelInfos[j]["Segment"]} ${data[j]["Therapy"]["Frequency"].toFixed(0)} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} ${data[j]["Therapy"]["Pulsewidth"].toFixed(0)} ${dictionaryLookup(dictionary.FigureStandardUnit, "uS", language)} ${data[j]["Therapy"]["Amplitude"].toFixed(1)} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)}`,
        legendgroup: `${channelInfos[j]["Segment"]}`,
        color: colors[j],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${channelInfos[j]["Segment"]} ${data[j]["Therapy"]["Frequency"].toFixed(0)} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)} ${data[j]["Therapy"]["Pulsewidth"].toFixed(0)} ${dictionaryLookup(dictionary.FigureStandardUnit, "uS", language)} ${data[j]["Therapy"]["Amplitude"].toFixed(1)} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)} %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)} <extra></extra>`,
      });
    }

    if (fig.traces.length == 0) {
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

export default StimulationPSD;