/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import React, {useCallback} from "react";
import {useResizeDetector} from "react-resize-detector";
import * as MathJS from "mathjs"

import colormap from "colormap";

import MDBox from "components/MDBox";

import { PlotlyRenderManager } from "graphing-utility/Plotly";
import { formatSegmentString, matchArray } from "database/helper-function";
import { usePlatformContext } from "context";

import { dictionary, dictionaryLookup } from "assets/translation";

function EventOnsetSpectrogram({dataToRender, selector, height, config, normalize, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [show, setShow] = React.useState(true);
  const fig = new PlotlyRenderManager(figureTitle, language);

  const handleGraphing = (data, selector) => {
    fig.clearData();

    if (fig.fresh) {
      fig.subplots(1,1, {sharey: true, sharex: true});
      fig.setXlabel("Time (s)", {fontSize: 15});
      fig.setYlim([0,100]);
      fig.setYlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Frequency", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Hertz", language)})`, {fontSize: 15});
      fig.setXlabel(`${dictionaryLookup(dictionary.FigureStandardText, "Time", language)} (${dictionaryLookup(dictionary.FigureStandardUnit, "Local", language)})`, {fontSize: 15});

    }

    if (normalize) {
      let Spectrum = [];
      for (let i in data[selector.value].Spectrum) {
        let baseline = MathJS.mean(...data[selector.value].Spectrum[i].filter((i, index) => {
          return data[selector.value].Time[index] < 0
        }));
        Spectrum.push(data[selector.value].Spectrum[i].map((value) => value-baseline));
      }
      fig.surf(data[selector.value].Time, data[selector.value].Frequency, Spectrum, {
        zlim: [-40, 40],
        coloraxis: "coloraxis",
      });
      
      fig.createColorAxis({
        colorscale: "Jet",
        colorbar: {y: 0.5, len: (1/2)},
        clim: [-40, 40],
      });

    } else {
      fig.surf(data[selector.value].Time, data[selector.value].Frequency, data[selector.value].Spectrum, {
        zlim: [-20, 20],
        coloraxis: "coloraxis",
      });
      
      fig.createColorAxis({
        colorscale: "Jet",
        colorbar: {y: 0.5, len: (1/2)},
        clim: [-20, 20],
      });
      
    }

    console.log(data[selector.value].Spectrum)
    
    
    if (data.length == 0) {
      fig.purge();
      setShow(false);
    } else {
      fig.render();
      setShow(true);
    }
  }

  // Refresh Left Figure if Data Changed
  React.useEffect(() => {
    if (dataToRender && selector.value !== "") handleGraphing(dataToRender, selector);
  }, [dataToRender, selector, language]);

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

export default EventOnsetSpectrogram;