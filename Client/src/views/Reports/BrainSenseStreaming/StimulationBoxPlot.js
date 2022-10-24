import React, {useCallback} from "react";
import {useResizeDetector} from "react-resize-detector";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function StimulationBoxPlot({dataToRender, channelInfos, height, type, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharey: false, sharex: false});

      fig.setXlim([-0.5, 5.5]);
      fig.setYlim([0, 2]);
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});

      for (var i in channelInfos) {
        const [side, target] = channelInfos[i].Hemisphere.split(" ");
        if (type === side) {
          const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} @ ${data[0].CenterFrequency} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}`;
          fig.setTitle(`${titleText}`);
        }
      }
    }

    var maxStimulation = 0;
    var maxSignal = 0;
    for (var j in data) {
      const xdata = Array(data[j].SpectralFeatures.length).fill(0).map((value, index) => data[j].Stimulation)
      fig.box(xdata, data[j]["SpectralFeatures"], {
        width: 0.2,
        hovertemplate: `${data[j]["Stimulation"].toFixed(1)} mA %{y:.2f} μV<sup>2</sup>/Hz <extra></extra>`,
      });
      if (xdata[0] > maxStimulation) maxStimulation = xdata[0];
      if (Math.max(...data[j]["SpectralFeatures"]) > maxSignal) maxSignal = Math.max(...data[j]["SpectralFeatures"]);
    }
    fig.setXlim([-0.5, Math.max(maxStimulation,5) + 0.5]);
    fig.setYlim([0, maxSignal * 1.05]);

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

  return (
    <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: height, width: "100%", display: show ? "" : "none"}}/>
  );
}

export default StimulationBoxPlot;