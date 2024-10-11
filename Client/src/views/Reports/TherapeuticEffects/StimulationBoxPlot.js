/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, {useCallback, useRef} from "react";
import {useResizeDetector} from "react-resize-detector";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { usePlatformContext } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

function StimulationBoxPlot({dataToRender, channelInfos, height, type, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(false);
  const figRef = useRef();

  const handleGraphing = (data) => {
    const fig = figRef.current;
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1, 1, {sharey: false, sharex: false});

      fig.setXlim([-0.5, 5.5]);
      fig.setYlim([0, 2]);
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Stimulation", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "mA", language)})`, {fontSize: 15});
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Power", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "uV2Hz", language)})`, {fontSize: 15});

      const [side, target] = channelInfos.Hemisphere.split(" ");
      const contactText = (typeof channelInfos.Contacts) == "string" ? channelInfos.Contacts : `E${channelInfos.Contacts[0]}-E${channelInfos.Contacts[1]}`;
      const titleText = `${dictionaryLookup(dictionary.FigureStandardText, side, language)} ${dictionaryLookup(dictionary.BrainRegions, target, language)} ${contactText}  @ ${data[0].CenterFrequency} ${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)}`;
      fig.setTitle(`${titleText}`);
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
    if (figRef) {
      figRef.current = new PlotlyRenderManager(figureTitle, language);
      if (dataToRender.length > 0) {
        handleGraphing(dataToRender);
      } else {
        figRef.current.purge();
        setShow(false);
      }
    }
  }, [dataToRender, figRef, language]);

  const onResize = useCallback(() => {
    if (figRef.current) {
      figRef.current.refresh();
    }
  }, [figRef.current]);

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