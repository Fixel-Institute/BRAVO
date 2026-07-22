/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useCallback, useEffect } from "react";
import { useResizeDetector } from 'react-resize-detector';

import MDBox from "components/MDBox";

import colormap from "colormap";
import { TwitterPicker, BlockPicker } from "react-color";

import { Autocomplete, Card, Menu, MenuItem, Dialog, DialogContent, Grid, IconButton, Popover, TextField, DialogActions } from "@mui/material";
import MDTypography from "components/MDTypography";
import RadioButtonGroup from "components/RadioButtonGroup";
import FormField from "components/MDInput/FormField";

import { PlotlyRenderManager } from "graphing-utility/Plotly";

import { dictionary, dictionaryLookup } from "assets/translation";
import { usePlatformContext } from "context";

function FitbitScoreTimeline({dataToRender, type, figureTitle}) {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const [popup, setPopupState] = useState({item: ""});

  const [fig, setFig] = useState(null);
  const [renderData, setRenderData] = useState(null);
  const [activeScores, setActiveScores] = useState([]);
  const [availableScores, setAvailableScores] = useState([]);

  useEffect(() => {
    setFig(new PlotlyRenderManager(figureTitle, language));
  }, [figureTitle]);

  useEffect(() => {
    if (!fig) return;
    
    if (!fig.fresh) {
      fig.clearData();
    }

    fig.subplots(1, 1, {sharex: true, sharey: true});
    fig.setYlabel("Score", {fontsize: 15});
    fig.setLegend({
      x: 0, y: -0.2,
      xanchor: 'left', yanchor: "top",
      orientation: "h", 
    })
    
    if (!fig.fresh) {
      refreshRender();
    }
  }, [fig]);

  useEffect(() => {
    if (!dataToRender) return;

    let allKeys = [];
    for (let key in dataToRender) {
      for (let j in dataToRender[key]) {
        for (let i in dataToRender[key][j].ChannelNames) {
          if (!allKeys.includes(key + " | " + dataToRender[key][j].ChannelNames[i])) {
            allKeys.push(key + " | " + dataToRender[key][j].ChannelNames[i]);
          }
        }
      }
    }
    
    setAvailableScores(allKeys);
    setActiveScores([])
  }, [dataToRender]);

  useEffect(() => {
    if (!fig) return;

    let allSubscores = [];
    const colors = colormap({
      colormap: 'rainbow',
      nshades: activeScores.length < 10 ? 10 : activeScores.length,
      format: 'hex',
      alpha: 1,
    });

    let legendGroup = [];

    let graphSeries = [];
    for (let score of activeScores) {
      let key = score.split(" | ")[0];
      let channel = score.split(" | ")[1];
      
      if (!dataToRender[key]) continue;
      
      for (let day in dataToRender[key]) {
        
        let xData = dataToRender[key][day].Time.map((a) => new Date(a*1000)), yData = [];
        for (let j in dataToRender[key][day].Time) {
          xData.push(new Date(dataToRender[key][day].Time[j]*1000));
        }

        for (let i in dataToRender[key][day].ChannelNames) {
          if (dataToRender[key][day].ChannelNames[i] === channel) {
            yData = dataToRender[key][day].Data[i];
          }
        }

        graphSeries.push({
          type: "line", x: xData, y: yData, 
          options: {
            mode: "lines",
            line: {shape: "hv"},
            linewidth: 2,
            name: score,
            legendgroup: score,
            color: legendGroup.includes(score) ? colors[legendGroup.length-1] : colors[legendGroup.length],
            hovertemplate: `  ${score}:  %{y:.2f}<extra></extra>`,
            showlegend: legendGroup.includes(score) ? false : true,
          }
        })

        if (!legendGroup.includes(score)) {
          legendGroup.push(score);
        }
      }
    }
    
    setRenderData(graphSeries);

  }, [dataToRender, activeScores])

  const refreshRender = () => {
    for (let i in renderData) {
      if (renderData[i].type === "line") {
        fig.plot(renderData[i].x, renderData[i].y, renderData[i].options);
      }
    }
    fig.render();
  }

  // Refresh Left Figure if Data Changed
  useEffect(() => {
    if (!fig) return;
    
    fig.traces = [];
    refreshRender();
  }, [fig, renderData]);

  const onResize = useCallback(() => {
    if (!fig) return;

    fig.refresh();
  }, [fig]);

  const {ref} = useResizeDetector({
    onResize: onResize,
    refreshMode: "debounce",
    refreshRate: 50,
    skipOnMount: false
  });

  return (
    <Grid>
      <Grid item xs={12}>
        <MDBox px={2} pb={2}>
          <Autocomplete
            multiple disableClearable
            value={activeScores}
            options={availableScores}
            onChange={(event, value) => {
              setActiveScores(value)
            }}
            isOptionEqualToValue={(option, value) => {
              return option === value;
            }}
            renderOption={(props, option) => <li {...props}>{option}</li>}
            getOptionLabel={(option) => {
              if (typeof option === 'string') {
                return option;
              }
              if (option.inputValue) {
                return option.inputValue;
              }
              return option;
            }}
            renderInput={(params) => (
              <FormField
                {...params}
                label={"Choose Active Score to Display"}
                InputLabelProps={{ shrink: true }}
              />
            )}
            fullWidth
          />
        </MDBox>
      </Grid>
      <Grid>
        <MDBox ref={ref} id={figureTitle} style={{marginTop: 5, marginBottom: 10, height: 500, width: "100%", display: ""}}/>
      </Grid>
    </Grid>
  );
}

export default FitbitScoreTimeline;