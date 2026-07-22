/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import Plotly from 'plotly.js-dist';
import { zhCN } from "assets/plotly-locales/zh-cn";

const defaultLineOptions = {
  type: "scattergl",
  mode: "lines",
  line: {color: "rgb(0,0,0)", width: 2},
  showlegend: false,
  hovertemplate: "<extra></extra>",
}

const defaultScatterOptions = {
  type: "scattergl",
  mode: "markers",
  marker: {color: "rgb(0,0,0)", size: 5},
  showlegend: false,
  hovertemplate: "<extra></extra>",
}

const defaultShadeOptions = {
  linewidth: 2,
  color: "rgb(0,0,0)",
  showlegend: false,
  hovertemplate: "<extra></extra>",
}

const defaultShadedAreaOptions = {
  fillcolor: "#33333344",
  line: {color: "transparent"},
  hoverinfo: "skip",
  type: "scatter",
  showlegend: false
}

const defaultHistogramOptions = {
  type: "histogram",
  marker: {},
  showlegend: true,
  hovertemplate: "<extra></extra>",
}

const defaultBarOptions = {
  type: "bar",
  marker: {},
  showlegend: true,
  hovertemplate: "<extra></extra>",
}

const defaultBoxOptions = {
  type: "box",
  marker: {color: "rgb(46,20,105)"},
  line: {color: "rgb(46,20,105)"},
  showlegend: false,
  hovertemplate: "<extra></extra>",
}

const defaultHeatmapOptions = {
  type: "heatmap",
  zsmooth: "best",
  colorscale: "jet",
  hovertemplate: "<extra></extra>",
}

const defaultLayoutOptions = {
  title: {
    text: ""
  },
  grid: {
    subplots: [["xy"]],
  },
  legend: {
    x: 1,
    y: 1,
    xanchor: 'right',
    tracegroupgap: 0
  },
  yaxis: {
    type: "linear",
    showgrid: true,
    gridcolor: "#DDDDDD",
    showline: true,
    linecolor: "#000000",
    showticklabels: true,

    ticks: "outside",
    fixedrange: false,

    title: {text: "", font: {size: 15}},
  },
  xaxis: {
    showgrid: true,
    gridcolor: "#DDDDDD",
    showline: true,
    linecolor: "#000000",
    showticklabels: true,

    ticks: "outside",
    fixedrange: false,

    title: {text: "", font: {size: 15}},
  },
  hovermode: "x",
  boxmode: "group",
  autosize: true,
  annotations: [],
}

const setDictionaryProps = (dict, key, value) => {
  if (dict[key]) {
    if (typeof dict[key] == "object" && typeof value == "object") {
      for (let subkey in value) {
        dict[key] = setDictionaryProps(dict[key], subkey, value[subkey]);
      }
    } else {
      dict[key] = value;
    }
  } else {
    dict[key] = value;
  }
  return dict;
}

function downsampleLTTB(x, y, threshold) {
    const dataLength = x.length;
    if (threshold >= dataLength || threshold === 0) {
        return { x, y };
    }
    const sampledX = [];
    const sampledY = [];

    const every = (dataLength - 2) / (threshold - 2);
    let a = 0;

    sampledX.push(x[a]);
    sampledY.push(y[a]);

    for (let i = 0; i < threshold - 2; i++) {
        const avgRangeStart = Math.floor((i + 1) * every) + 1;
        const avgRangeEnd = Math.floor((i + 2) * every) + 1;
        const avgRangeLength = avgRangeEnd - avgRangeStart;

        let avgX = 0, avgY = 0;
        for (let j = avgRangeStart; j < avgRangeEnd; j++) {
            avgX += x[j];
            avgY += y[j];
        }
        avgX /= avgRangeLength;
        avgY /= avgRangeLength;

        const rangeOffs = Math.floor(i * every) + 1;
        const rangeTo = Math.floor((i + 1) * every) + 1;

        let maxArea = -1;
        let nextA = rangeOffs;

        const ax = x[a];
        const ay = y[a];

        for (let j = rangeOffs; j < rangeTo; j++) {
            const area = Math.abs(
                (ax - avgX) * (y[j] - ay) -
                (ax - x[j]) * (avgY - ay)
            );

            if (area > maxArea) {
                maxArea = area;
                nextA = j;
            }
        }

        sampledX.push(x[nextA]);
        sampledY.push(y[nextA]);
        a = nextA;
    }

    sampledX.push(x[dataLength - 1]);
    sampledY.push(y[dataLength - 1]);

    return { x: sampledX, y: sampledY };
}


class PlotlyRenderManager {

  /**
   * Create a Plotly Manager object for specific div on HTML.
   *
   * @param {string} divName - String Name of the div 
   * @param {string} locale - String name of the locale (language) for Plotly (``en-US``, or
   *     ``zh-CN``)
   */
  constructor(divName, locale) {
    this.traces = [];
    this.ax = [{
      xaxis: "x",
      yaxis: "y",
      xlayout: "xaxis",
      ylayout: "yaxis"
    }];
    this.coloraxis = [];
    this.gca = this.ax[0];
    this.layout = JSON.parse(JSON.stringify(defaultLayoutOptions));
    this.onClick = async (evt) => {}
    
    // How we handle figure update
    this.fresh = true;
    this.divName = divName;

    switch(locale) {
      case "en": 
        this.locale = "en-US";
        break;
      case "zh":
        Plotly.register(zhCN);
        this.locale = "zh-CN";
        break;
      default:
        this.locale = "en-US";
    }
  }

  /**
   * Clear all traces
   */
  clearData() {
    for (let i in this.ax) {
      delete this.layout[this.ax[i].xlayout];
      delete this.layout[this.ax[i].ylayout];
    }
    this.layout["annotations"] = [];
    this.traces = [];
  }

  /**
   * Create subplots within figure field.
   *
   * @param {number} row - number of rows in subplot grid
   * @param {number} col - number of columns in subplot grid
   * @param {Object} [options] - Axes Configuration Options
   * @param {bool} [options.sharex=false] - Each column share the same x-axis (default false)
   * @param {bool} [options.sharey=false] - Each row share the same y-axis (default false)
   * @param {bool} [options.colSpacing=false] - Spacing between each subplots on the same row (default 0.02)
   * @param {bool} [options.rowSpacing=false] - Spacing between each subplots on the same column (default 0.15)
   * 
   * @return {string[]} Array of subplots created, C-ordered. 
   */
  subplots(row, col, options={sharex: false, sharey: false, colSpacing: 0.02, rowSpacing: 0.25}) {
    this.ax = [];

    if (options.sharex) {
      var xAxesLabels = Array(col).fill(0).map((value, index) => (index+1 == 1) ? "x" : "x" + (index+1).toString());
    } else {
      var xAxesLabels = Array(col*row).fill(0).map((value, index) => (index+1 == 1) ? "x" : "x" + (index+1).toString());
    }
    
    if (!options.colSpacing) options.colSpacing = 0.02;
    if (!options.rowSpacing) options.rowSpacing = 0.25;
    if (!options.scales) options.scales = new Array(row).fill(1);
    
    if (options.sharey) {
      var yAxesLabels = Array(row).fill(0).map((value, index) => (index+1 == 1) ? "y" : "y" + (index+1).toString());
    } else {
      var yAxesLabels = Array(row*col).fill(0).map((value, index) => (index+1 == 1) ? "y" : "y" + (index+1).toString());
    }
    
    this.layout.grid.subplots = Array(row).fill(0).map(() => Array(col));

    function calculateSegments(ratios, totalLength = 1, spacingPercent = 0.25) {
      const n = ratios.length;
      
      // Step 1: Compute total units (segments + spacing units)
      const sumRatios = ratios.reduce((a, b) => a + b, 0);
      const spacingUnits = ratios.slice(0, n - 1).reduce((a, b) => a + b * spacingPercent, 0);
      const totalUnits = sumRatios + spacingUnits;

      // Step 2: Scale factor
      const k = totalLength / totalUnits;

      // Step 3: Compute positions
      let positions = [];
      let currentPos = 0;

      for (let i = 0; i < n; i++) {
        const segmentLength = ratios[i] * k;
        const start = currentPos;
        const end = start + segmentLength;
        positions.push({ segment: i + 1, start, end });
        currentPos = end;
        if (i < n - 1) {
          const spacingLength = ratios[i] * spacingPercent * k;
          currentPos += spacingLength;
        }
      }
      return positions;
    }

    const segments = calculateSegments(options.scales, 1, options.rowSpacing);
    const colFraction = 1/col;
    const colSpacing = colFraction*options.colSpacing;

    for (var i = 0; i < row; i++) {
      for (var k = 0; k < col; k++) {
        var xaxis = (options.sharex ? xAxesLabels[k] : xAxesLabels[i*col+k]);
        var yaxis = (options.sharey ? yAxesLabels[i] : yAxesLabels[i*col+k]);
        this.layout.grid.subplots[i][k] = xaxis + yaxis;
        
        const ydomain = [1 - segments[i].end, 1 - segments[i].start];
        
        this.ax.push({
          xaxis: xaxis,
          yaxis: yaxis,
          xlayout: xaxis.replace("x","xaxis"),
          ylayout: yaxis.replace("y","yaxis"),
          xdomain: col > 1 ? [colFraction*k+colSpacing, colFraction*(k+1)-colSpacing] : [0,1],
          ydomain: row > 1 ? ydomain : [0,1]
        });
      }
    }

    for (var currentAxe of this.ax) {
      this.layout[currentAxe.xlayout] = JSON.parse(JSON.stringify(defaultLayoutOptions.xaxis));
      if (col > 1) this.layout[currentAxe.xlayout].domain = currentAxe.xdomain;
      this.layout[currentAxe.ylayout] = JSON.parse(JSON.stringify(defaultLayoutOptions.yaxis));
      if (row > 1) this.layout[currentAxe.ylayout].domain = currentAxe.ydomain;
    }
    this.gca = this.ax[0];
    return this.ax;
  }

  addDualYAxis(ax) {
    let nextY = 2;
    for (let i in this.ax) {
      if (parseInt(this.ax[i].ylayout.replace("yaxis","")) >= nextY) {
        nextY += 1;
      }
    }

    let axProp = {...ax};
    axProp["yaxis"] = "y" + nextY.toFixed(0);
    axProp["ylayout"] = "yaxis" + nextY.toFixed(0);
    this.ax.push(axProp);

    this.layout[axProp.ylayout] = JSON.parse(JSON.stringify(defaultLayoutOptions.yaxis));
    this.layout[axProp.ylayout].domain = axProp.ydomain;
    this.layout[axProp.ylayout].overlaying = ax.yaxis;
    this.layout[axProp.ylayout].side = "right";
    

    return axProp;
  }

  setSubplotId(ids) {
    for (let i in this.ax) {
      this.ax[i].id = ids[i]
    }
  }

  /**
   * Get the subplot array from Manager Cache.
   *
   * @return {string[]} Array of subplots created, C-ordered. 
   */
  getAxes(id=null) {
    if (!id) return this.ax;
    for (let i in this.ax) {
      if (this.ax[i].id == id) return this.ax[i];
    }
  }

  /**
   * Add line plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - y-data array
   * @param {Object} [options] - Line Graph Configuration Options (https://plotly.com/javascript/reference/scatter/)
   * @param {string} [ax] - Subplot to add line to. Default to last access axes.
   * 
   * @return {Object} The line plot object created.
   */
  plot(x, y, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultLineOptions));
    trace.x = x;
    trace.y = y;
    trace.type = "scatter";
    trace.mode = "lines";

    for (var key of Object.keys(options)) {
      if (key == "linewidth") {
        trace.line.width = options[key];
      } else if (key == "color") {
        trace.line.color = options[key];
      } else if (key == "linedash") {
        trace.line.dash = options[key];
      } else if (key == "shape") {
        trace.line.shape = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    //this.layout[ax.ylayout].range = [Math.min(Math.min(...y), this.layout[ax.ylayout].range[0]), Math.max(Math.max(...y), this.layout[ax.ylayout].range[1])];
    //this.layout[ax.xlayout].range = [Math.min(Math.min(...x), this.layout[ax.xlayout].range[0]), Math.max(Math.max(...x), this.layout[ax.xlayout].range[1])];
    this.traces.push(trace);
    return trace;
  }

  /**
   * Add scatter plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - y-data array
   * @param {Object} [options] - Scatter Graph Configuration Options (https://plotly.com/javascript/reference/scatter/)
   * @param {string} [ax] - Subplot to add scatter plot to. Default to last access axes.
   * 
   * @return {Object} The line plot object created.
   */
  scatter(x, y, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultScatterOptions));
    trace.x = x;
    trace.y = y;
    trace.type = "scatter";
    trace.mode = "markers";

    for (var key of Object.keys(options)) {
      if (key == "color") {
        trace.marker.color = options[key];
      } else if (key == "size") {
        trace.marker.size = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add shaded error plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - average y-data array
   * @param {number[]} errorY - shaded y-data array 
   * @param {Object} [options] - Scatter Graph Configuration Options (https://plotly.com/javascript/reference/scatter/)
   * @param {Object} [shadeOptions] - Shaded Area Configuration Options 
   * @param {string} [shadeOptions.color] - #RRGGBB syntax
   * @param {number} [shadeOptions.alpha] - fractional alpha value from 0 to 1.
   * @param {string} [ax] - Subplot to add line to. Default to last access axes.
   * 
   */
  shadedErrorBar(x, y, errorY, options={}, shadeOptions={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultLineOptions));
    trace.x = x;
    trace.y = y;
    trace.type = "scatter";
    trace.mode = "lines";

    for (var key of Object.keys(options)) {
      if (key == "linewidth") {
        trace.line.width = options[key];
      } else if (key == "color") {
        trace.line.color = options[key];
      } else if (key == "shape") {
        trace.line.shape = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    this.traces.push(trace);

    var topY = new Array(x.length);
    for (var t = 0; t < x.length; t++) {
      topY[t] = y[t] + errorY[t];
    }
    var bottomY = new Array(x.length);
    for (var t = 0; t < x.length; t++) {
      bottomY[t] = y[t] - errorY[t];
    }

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = bottomY;
    trace.fill = "none";
    this.traces.push(trace);

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = topY;
    for (var key of Object.keys(shadeOptions)) {
      if (key == "color") {
        trace.fillcolor = shadeOptions[key] + trace.fillcolor.slice(-2);
      } else if (key == "alpha") {
        trace.fillcolor = trace.fillcolor.slice(0,-2) + (Math.round(shadeOptions[key]*255)).toString(16);
      } else {
        trace[key] = shadeOptions[key];
      }
    }
    trace.fill = "tonexty";
    this.traces.push(trace);
  }

  /**
   * Add shaded error plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - top y-data array
   * @param {number[]} threshold - the bottom y-data
   * @param {Object} [options] - Shaded Area Configuration Options 
   * @param {string} [options.color] - #RRGGBB syntax
   * @param {number} [options.alpha] - fractional alpha value from 0 to 1.
   * @param {string} [ax] - Subplot to add line to. Default to last access axes.
   * 
   */
  addShading(x, y, threshold, options={}, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    var topY = new Array(x.length);
    for (var t = 0; t < x.length; t++) {
      topY[t] = y[t] > threshold ? y[t] : threshold;
    }
    var bottomY = new Array(x.length);
    for (var t = 0; t < x.length; t++) {
      bottomY[t] = threshold;
    }

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = bottomY;
    trace.fill = "none";
    this.traces.push(trace);

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = topY;
    for (var key of Object.keys(options)) {
      if (key == "color") {
        trace.fillcolor = options[key] + trace.fillcolor.slice(-2);
      } else if (key == "alpha") {
        trace.fillcolor = trace.fillcolor.slice(0,-2) + (Math.round(options[key]*255)).toString(16);
      } else {
        trace[key] = options[key];
      }
    }
    trace.fill = "tonexty";
    this.traces.push(trace);
  }

  /**
   * Add heatmap (image) plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - y-data array
   * @param {number[]} z - z-data array (size x,y)
   * @param {Object} [options] - Heatmap Graph Configuration Options (https://plotly.com/javascript/reference/heatmap)
   * @param {string} [ax] - Subplot to add heatmap to. Default to last access axes.
   * 
   * @return {Object} The shaded error plot object created.
   */
  surf(x, y, z, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultHeatmapOptions));
    trace.x = x;
    trace.y = y;
    trace.z = z;

    for (var key of Object.keys(options)) {
      if (key == "zlim") {
        trace.zmin = options[key][0];
        trace.zmax = options[key][1];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add bar plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - y-data array
   * @param {Object} [options] - Bar Graph Configuration Options (https://plotly.com/javascript/reference/bar)
   * @param {string} [ax] - Subplot to add bar to. Default to last access axes.
   * 
   * @return {Object} The shaded error plot object created.
   */
  bar(x, y, base=[], options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultBarOptions));
    trace.x = x;
    trace.y = y;
    if (base.length > 0) {
      trace.base = base;
    }

    for (var key of Object.keys(options)) {
      if (key == "facecolor") {
        trace.marker.color = options[key];
      } else if (key == "color") {
        trace.facecolor = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add histogram to figure
   *
   * @param {number[]} x - data array
   * @param {Object} [options] - Bar Graph Configuration Options (https://plotly.com/javascript/reference/bar)
   * @param {string} [ax] - Subplot to add bar to. Default to last access axes.
   * 
   * @return {Object} The shaded error plot object created.
   */
  hist(x, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultHistogramOptions));
    trace.x = x;

    for (var key of Object.keys(options)) {
      if (key == "facecolor") {
        trace.marker.color = options[key];
      } else if (key == "color") {
        trace.facecolor = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add box plot to figure
   *
   * @param {number[]} x - x-data array
   * @param {number[]} y - y-data array
   * @param {Object} [options] - Box Graph Configuration Options (https://plotly.com/javascript/reference/box)
   * @param {string} [ax] - Subplot to add box to. Default to last access axes.
   * 
   * @return {Object} The shaded error plot object created.
   */
  box(x, y, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultBoxOptions));
    trace.x = x;
    trace.y = y;

    for (var key of Object.keys(options)) {
      if (key == "linecolor") {
        trace.line.color = options[key];
      } else if (key == "markercolor") {
        trace.marker.color = options[key];
      } else {
        trace[key] = options[key];
      }
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add shaded area to figure
   *
   * @param {number[]} x - x-data array
   * @param {Object} [options] - Scatter Graph Configuration Options (https://plotly.com/javascript/reference/scatter)
   * @param {string} [ax] - Subplot to add shaded area to. Default to last access axes.
   * 
   * @return {Object} The shaded error plot object created.
   */
  addShadedArea(x, y, options={}, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    var ylim = [];
    if (!y) {
      if (this.layout[this.gca["ylayout"]].type == "log") {
        ylim = [Math.pow(10, this.layout[this.gca["ylayout"]].range[0]), Math.pow(10, this.layout[this.gca["ylayout"]].range[1])];
      } else {
        ylim = this.layout[this.gca["ylayout"]].range;
      }
    } else {
      ylim = y;
    }

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = new Array(x.length).fill(ylim[0]);
    trace.fill = "none";
    this.traces.push(trace);

    var trace = JSON.parse(JSON.stringify(defaultShadedAreaOptions));
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;
    trace.x = x;
    trace.y = new Array(x.length).fill(ylim[1]);
    for (var key of Object.keys(options)) {
      if (key == "color") {
        trace.fillcolor = options[key] + trace.fillcolor.slice(-2);
      } else if (key == "alpha") {
        trace.fillcolor = trace.fillcolor.slice(0,-2) + (Math.round(options[key]*255)).toString(16);
      } else {
        trace[key] = options[key];
      }
    }
    trace.fill = "tonexty";
    this.traces.push(trace);

    return trace;
  }

  /**
   * Add text
   *
   * @param {number[]} x - x positions
   * @param {number[]} y - y positions
   * @param {string[]} text - texts
   * @param {Object} [options] - Text Configuration Options (https://plotly.com/javascript/reference/text/)
   * @param {string} [ax] - Subplot to add scatter plot to. Default to last access axes.
   * 
   * @return {Object} The line plot object created.
   */
  addText(x, y, text, options={}, ax=null) {
    var trace = {
      x: x, 
      y: y,
      text: text,
      mode: "text"
    };

    for (var key of Object.keys(options)) {
      trace[key] = options[key];
    }

    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    trace.xaxis = this.gca.xaxis;
    trace.yaxis = this.gca.yaxis;

    this.traces.push(trace);
    return trace;
  }

  /**
   * Add colorbar to figure
   *
   * @param {Object} [options] - Color Axis Graph Configuration Options (https://plotly.com/javascript/reference/layout/coloraxis/#layout-coloraxis)
   * 
   * @return {string} The colorbar ID 
   */
  createColorAxis(options={}) {
    var colorAxisID = "";
    var id = this.coloraxis.length + 1;
    if (id == 1) {
      colorAxisID = "coloraxis";
    } else {
      colorAxisID = "coloraxis" + id.toString();
    }

    this.layout[colorAxisID] = {showscale: true};
    this.coloraxis.push(colorAxisID);

    for (var key of Object.keys(options)) {
      if (key == "clim") {
        this.layout[colorAxisID].cmin = options[key][0];
        this.layout[colorAxisID].cmax = options[key][1];
      } else {
        this.layout[colorAxisID][key] = options[key];
      }
    }

    return colorAxisID;
  };

  getColorAxis() {
    return this.coloraxis;
  };

  setColorAxis(options, colorAxisID) {
    if (!options) {
      delete this.layout[colorAxisID];
      this.coloraxis = this.coloraxis.filter((a) => a != colorAxisID);
      return;
    }

    for (var key of Object.keys(options)) {
      if (key == "clim") {
        this.layout[colorAxisID].cmin = options[key][0];
        this.layout[colorAxisID].cmax = options[key][1];
      } else {
        this.layout[colorAxisID][key] = options[key];
      }
    }

    return this.coloraxis;
  };

  setClim(limit, colorAxisID) {
    this.layout[colorAxisID].cmin = limit[0];
    this.layout[colorAxisID].cmax = limit[1];
  }

  /**
   * Add legend to figure. 
   * Unlike other language, Plotly legend configuration is to configure appearance. Actual text is added in each plot trace's option.
   *
   * @param {Object} [options] - Legend Configuration Options (https://plotly.com/javascript/reference/layout/#layout-legend)
   * 
   * @return {string} The colorbar ID 
   */
  setLegend(options) {
    this.layout.legend = {
      ...this.layout.legend,
      ...options
    };
  }

  /**
   * Add title to figure. 
   *
   * @param {string} title - Title text
   * 
   */
  setTitle(title) {
    this.layout.title.text = title;
  }

  /**
   * Add title to figure. 
   *
   * @param {string} subtitle - Title text
   * @param {string} [ax] - Subplot to add subtitle to. Default to last access axes.
   * 
   */
  setSubtitle(subtitle, ax=null) {
    if (!ax) {
      this.setTitle(subtitle);
    } else {
      const xLocation = (ax.xdomain[0] + ax.xdomain[1]) * 0.5;
      const yLocation = ax.ydomain[1];
      const annotation = {
        text: subtitle, 
        font: {size: 20}, 
        showarrow: false, 
        x: xLocation, 
        y: yLocation, 
        xref: "paper", 
        yref: "paper", 
        yanchor: "bottom",
        xanchor: "center",
      };

      var existingAnnotations = false;
      for (var i in this.layout["annotations"]) {
        if (this.layout["annotations"][i].x == xLocation && this.layout["annotations"][i].y == yLocation) {
          this.layout["annotations"][i] = annotation;
          existingAnnotations = true;
        }
      }
      if (!existingAnnotations) {
        this.layout["annotations"].push(annotation);
      }
    }
  }

  /**
   * Add X-axis Label to figure. 
   *
   * @param {string} title - Label text
   * @param {Object} [options] - axis configuration (TODO) (https://plotly.com/javascript/reference/layout/xaxis/)
   * @param {Object} [options.fontSize] - Text Font Size (default = 15)
   * @param {string} [ax] - Subplot to add label to. Default to last access axes.
   * 
   */
  setXlabel(title, options={fontSize: 15}, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    this.layout[ax["xlayout"]].title = {text: title, font: {size: options.fontSize}};
  }

  /**
   * Add Y-axis Label to figure. 
   *
   * @param {string} title - Label text
   * @param {Object} [options] - axis configuration (TODO) (https://plotly.com/javascript/reference/layout/yaxis/)
   * @param {Object} [options.fontSize] - Text Font Size (default = 15)
   * @param {string} [ax] - Subplot to add label to. Default to last access axes.
   * 
   */
  setYlabel(title, options={fontSize: 15}, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    this.layout[ax["ylayout"]].title = {text: title, font: {size: options.fontSize}};
  }

  /**
   * Change x-axis limits. 
   *
   * @param {number[]} xlim - [min max] of x-axis limits.
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setXlim(xlim, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    this.layout[ax["xlayout"]].range = xlim;
  }

  /**
   * Change y-axis limits. 
   *
   * @param {number[]} ylim - [min max] of y-axis limits.
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setYlim(ylim, ax=null, update=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    if (update && this.layout[ax["ylayout"]].range) {
      if (this.layout[ax["ylayout"]].range[0] > ylim[0]) {
        this.layout[ax["ylayout"]].range[0] = ylim[0];
      }
      if (this.layout[ax["ylayout"]].range[1] < ylim[1]) {
        this.layout[ax["ylayout"]].range[1] = ylim[1];
      }
    } else {
      this.layout[ax["ylayout"]].range = ylim;
    }
  }

  /**
   * Get x-axis limits. 
   *
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  getXlim(ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    return this.layout[ax["xlayout"]].range;
  }

  /**
   * Get y-axis limits. 
   *
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  getYlim(ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    return this.layout[ax["ylayout"]].range;
  }

  /**
   * Change axis ticks location. 
   *
   * @param {number[]} values - array of tick values
   * @param {string} axis - `x` or `y` axis to be configured. 
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setTickValue(values, axis, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    this.layout[ax[axis+"layout"]].tickmode = "array";
    this.layout[ax[axis+"layout"]].tickvals = values;
  }

  /**
   * Change axis ticks label. 
   *
   * @param {number[]} labels - custom labels of the ticks. Same size as tick values
   * @param {string} axis - `x` or `y` axis to be configured. 
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setTickLabel(labels, axis, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    this.layout[ax[axis+"layout"]].ticktext = labels;
  }

  /**
   * Generic wrapper for changing axis Options
   *
   * @param {Object} [props] - axis configuration (https://plotly.com/javascript/reference/layout/xaxis/)
   * @param {string} axis - `x` or `y` axis to be configured. 
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setAxisProps(props, axis, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }
    
    for (let key in props) {
      this.layout[ax[axis+"layout"]] = setDictionaryProps(this.layout[ax[axis+"layout"]], key, props[key]);
    }
  }

  /**
   * Generic wrapper for changing layout Options
   *
   * @param {Object} [props] - axis configuration (https://plotly.com/javascript/reference/layout)
   * 
   */
  setLayoutProps(props) {
    for (var key of Object.keys(props)) {
      if (props[key].constructor.name == "Object")  {
        this.layout[key] = {
          ...this.layout[key],
          ...props[key]
        };
      } else {
        this.layout[key] = props[key];
      }
    }
  }

  /**
   * Change axis scale. 
   *
   * @param {string} type - String name of the scale type for axis (``linear``, or
   *     ``log``)
   * @param {string} axis - `x` or `y` axis to be configured. 
   * @param {string} [ax] - Subplot to configure. Default to last access axes.
   * 
   */
  setScaleType(type, axis, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    if (this.layout[ax[axis+"layout"]].type == "linear" && type == "log" && this.layout[ax[axis+"layout"]].range) {
      this.layout[ax[axis+"layout"]].range[0] = Math.log10(this.layout[ax[axis+"layout"]].range[0]);
      this.layout[ax[axis+"layout"]].range[1] = Math.log10(this.layout[ax[axis+"layout"]].range[1]);
    }
    this.layout[ax[axis+"layout"]].type = type;
  }

  updateAxes(traceId, ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    for (let i in this.traces) {
      if (this.traces[i].id == traceId) {
        this.traces[i].xaxis = this.gca.xaxis;
        this.traces[i].yaxis = this.gca.yaxis;
      }
    }
  }

  
  /**
   * Call to update figure or initial render
   */
  render() {
    const config = {
      responsive: true, locale: this.locale,
      toImageButtonOptions: {
        format: 'png', // one of png, svg, jpeg, webp
        scale: 1
      },
      modeBarButtonsToAdd: [
        "select2d",
        {
          name: 'Download Vector File',
          icon: {
            width: 857.1,
            height: 1000,
            path: 'm214-7h429v214h-429v-214z m500 0h72v500q0 8-6 21t-11 20l-157 156q-5 6-19 12t-22 5v-232q0-22-15-38t-38-16h-322q-22 0-37 16t-16 38v232h-72v-714h72v232q0 22 16 38t37 16h465q22 0 38-16t15-38v-232z m-214 518v178q0 8-5 13t-13 5h-107q-7 0-13-5t-5-13v-178q0-8 5-13t13-5h107q7 0 13 5t5 13z m357-18v-518q0-22-15-38t-38-16h-750q-23 0-38 16t-16 38v750q0 22 16 38t38 16h517q23 0 50-12t42-26l156-157q16-15 27-42t11-49z',
            transform: 'matrix(1 0 0 -1 0 850)'
          },
          click: function(gd) {
            const elementStyle = window.getComputedStyle(gd);
            Plotly.toImage(gd, {
              format:'svg',
              width: elementStyle.width.replace("px",""),
              height: elementStyle.height.replace("px","")
            }).then((url) => {
              var downloader = document.createElement('a');
              downloader.href = url;
              downloader.target = '_blank';
              downloader.download = gd.id + '.svg';
              downloader.click();
            });
          }
        },
        {
          name: 'Download Raw Series',
          icon: {
            path: 'M12 3C12.5523 3 13 3.44772 13 4V17.5858L18.2929 12.2929C18.6834 11.9024 19.3166 11.9024 19.7071 12.2929C20.0976 12.6834 20.0976 13.3166 19.7071 13.7071L12.7071 20.7071C12.3166 21.0976 11.6834 21.0976 11.2929 20.7071L4.29289 13.7071C3.90237 13.3166 3.90237 12.6834 4.29289 12.2929C4.68342 11.9024 5.31658 11.9024 5.70711 12.2929L11 17.5858V4C11 3.44772 11.4477 3 12 3Z',
            transform: 'scale(0.7) translate(0, 0)'
          },click: function(gd) {
            var csvData = "x, y, name\n";
            for (let i in gd.data) {
              if (["scatter","box"].includes(gd.data[i].type)) {
                for (let j in gd.data[i].x) {
                  csvData += gd.data[i].x[j] + "," + gd.data[i].y[j] + "," + (gd.data[i].name || " ") + "\n";
                }
              }
            }
            
            var downloader = document.createElement('a');
            downloader.href = 'data:text/json;charset=utf-8,' + encodeURI(csvData);
            downloader.target = '_blank';
            downloader.download = gd.id + ".csv";
            downloader.click();
          }
        },
      ],
    }

    const ref = document.getElementById(this.divName);
    if (ref) {
      this.onClick = async (evt) => {
        const bb = evt.target.getBoundingClientRect();
        let gca = this.ax[0];

        if (ref._fullLayout.grid) {
          for (let axId in ref._fullLayout.grid.subplots) {
            if (ref._fullLayout.grid.subplots[axId][0] == evt.target.dataset.subplot) {
              gca = this.ax[axId];
            }
          }
        }
        
        const x = ref._fullLayout[gca.xlayout].p2d(evt.clientX - bb.left);
        const y = ref._fullLayout[gca.ylayout].p2d(evt.clientY - bb.top);
        const event = new CustomEvent("PlotlyClick", {detail: {
          divName: this.divName,
          x, y, ax: gca
        }});
        document.dispatchEvent(event);
      }

      if (this.fresh) {
        Plotly.newPlot(this.divName, this.traces, this.layout, config).then(() => {
          ref.on("plotly_relayout", (evt) => {
            const event = new CustomEvent("PlotlyRelayout", {detail: { 
              ...evt, 
              divName: this.divName
            }});
            document.dispatchEvent(event);
          })
        });
        this.fresh = false;
      } else {
        Plotly.react(this.divName, this.traces, this.layout, config);
      }
    }
  }

  /**
   * Call to clear axis trends
   */
  clearAxes(ax=null) {
    if (!ax) {
      ax = this.gca;
    } else {
      if (this.ax.includes(ax)) {
        this.gca = ax;
      } else {
        console.log("WARNING: Ax Not Found");
        ax = this.gca;
      }
    }

    this.traces = this.traces.filter((trace) => !(trace.xaxis == this.gca.xaxis && trace.yaxis == this.gca.yaxis));
  }

  /**
   * Call to clear figure
   */
  purge() {
    Plotly.purge(this.divName);
    this.fresh = true;
  }

  /**
   * Call to update figure
   */
  refresh() {
    try {
      Plotly.relayout(this.divName, {});
    } catch (error) {
      return;
    }
  }
}

export {
  PlotlyRenderManager,
  downsampleLTTB
};