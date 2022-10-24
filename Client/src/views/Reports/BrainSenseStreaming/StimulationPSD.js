import React, {useCallback} from "react";
import {useResizeDetector} from "react-resize-detector";
import colormap from "colormap";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function StimulationPSD({dataToRender, channelInfos, height, type, onCenterFrequencyChange, figureTitle}) {
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

      for (var i in channelInfos) {
        const [side, target] = channelInfos[i].Hemisphere.split(" ");
        if (type === side) {
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} E${channelInfos[i].Contacts[0]}-E${channelInfos[i].Contacts[1]}`;
          fig.setTitle(`${titleText}`);
        }
      }
    }

    const levels = (data[data.length - 1]["Stimulation"] * 10) + 1;
    const colors = colormap({
      colormap: "jet",
      nshades: Math.max(levels,10),
      format: "hex",
      alpha: 1
    });

    for (var j in data) {
      fig.plot(data[j]["Frequency"], data[j]["PSD"], {
        name: `${data[j]["Stimulation"].toFixed(1)} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)}`,
        color: colors[Math.round(data[j]["Stimulation"]*10)],
        linewidth: 2,
        showlegend: true,
        hovertemplate: `${data[j]["Stimulation"].toFixed(1)} ${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)} %{y:.2f} ${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)} <extra></extra>`,
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

  var updateTimeout = null;
  var plotly_singleclicked = false;
  const plotly_onClick = (data) => {
    if (plotly_singleclicked) {
      plotly_singleclicked = false;
      clearTimeout(updateTimeout);
    } else {
      plotly_singleclicked = true;
      updateTimeout = setTimeout(function() {
        onCenterFrequencyChange(type, data["points"][0]["x"]);
        plotly_singleclicked = false
      }, 300);
    }
  };

  React.useEffect(() => {
    if (ref.current.on) {
      ref.current.on("plotly_click", plotly_onClick);
    }
  }, [ref.current, dataToRender]);

  return (
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default StimulationPSD;