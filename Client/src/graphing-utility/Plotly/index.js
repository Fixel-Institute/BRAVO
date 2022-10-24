import Plotly from 'plotly.js-dist-min';
import { zhCN } from "assets/plotly-locales/zh-cn";

const defaultLineOptions = {
  type: "scatter",
  mode: "lines",
  line: {color: "rgb(0,0,0)", width: 2},
  showlegend: false,
  hovertemplate: "<extra></extra>",
}

const defaultScatterOptions = {
  type: "scatter",
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

    title: {text: "", font: {size: 15}},
  },
  xaxis: {
    showgrid: true,
    gridcolor: "#DDDDDD",
    showline: true,
    linecolor: "#000000",
    showticklabels: true,

    ticks: "outside",

    title: {text: "", font: {size: 15}},
  },
  hovermode: "x",
  autosize: true,
  annotations: [],
}

class PlotlyRenderManager {
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

  clearData() {
    this.traces = [];
  }

  subplots(row, col, options={sharex: false, sharey: false}) {
    this.ax = [];

    if (options.sharex) {
      var xAxesLabels = Array(col).fill(0).map((value, index) => (index+1 == 1) ? "x" : "x" + (index+1).toString());
    } else {
      var xAxesLabels = Array(col*row).fill(0).map((value, index) => (index+1 == 1) ? "x" : "x" + (index+1).toString());
    }

    if (options.sharey) {
      var yAxesLabels = Array(row).fill(0).map((value, index) => (index+1 == 1) ? "y" : "y" + (index+1).toString());
    } else {
      var yAxesLabels = Array(row*col).fill(0).map((value, index) => (index+1 == 1) ? "y" : "y" + (index+1).toString());
    }
    
    this.layout.grid.subplots = Array(row).fill(0).map(() => Array(col));
    
    const colFraction = 1/col;
    const rowFraction = 1/row;
    const colSpacing = colFraction*0.02;
    const rowSpacing = rowFraction*0.15;
    for (var i = 0; i < row; i++) {
      for (var k = 0; k < col; k++) {
        var xaxis = (options.sharex ? xAxesLabels[k] : xAxesLabels[i*col+k]);
        var yaxis = (options.sharey ? yAxesLabels[i] : yAxesLabels[i*col+k]);
        this.layout.grid.subplots[i][k] = xaxis + yaxis;
        this.ax.push({
          xaxis: xaxis,
          yaxis: yaxis,
          xlayout: xaxis.replace("x","xaxis"),
          ylayout: yaxis.replace("y","yaxis"),
          xdomain: col > 1 ? [colFraction*k+colSpacing, colFraction*(k+1)-colSpacing] : [0,1],
          ydomain: row > 1 ? [1-(rowFraction*(i+1)-rowSpacing), 1-(rowFraction*i+rowSpacing)] : [0,1]
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

  getAxes() {
    return this.ax;
  }

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

  bar(x, y, options={}, ax=null) {
    var trace = JSON.parse(JSON.stringify(defaultBarOptions));
    trace.x = x;
    trace.y = y;

    for (var key of Object.keys(options)) {
      if (key == "facecolor") {
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

  addShadedArea(x, options={}, ax=null) {
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
    if (this.layout[this.gca["ylayout"]].type == "log") {
      ylim = [Math.pow(10, this.layout[this.gca["ylayout"]].range[0]), Math.pow(10, this.layout[this.gca["ylayout"]].range[1])];
    } else {
      ylim = this.layout[this.gca["ylayout"]].range;
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

    return;
  }

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
  }

  setLegend(options) {
    this.layout.legend = {
      ...this.layout.legend,
      ...options
    };
  }

  setTitle(title) {
    this.layout.title.text = title;
  }

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

  setYlim(ylim, ax=null) {
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
    
    this.layout[ax["ylayout"]].range = ylim;
  }

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
    
    this.layout[ax[axis+"layout"]] = {...this.layout[ax[axis+"layout"]], ...props};
  }

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

  render() {
    if (this.fresh) {
      Plotly.newPlot(this.divName, this.traces, this.layout, {responsive: true, locale: this.locale});
      this.fresh = false;
    } else {
      Plotly.react(this.divName, this.traces, this.layout, {responsive: true, locale: this.locale});
    }
  }

  purge() {
    Plotly.purge(this.divName);
    this.fresh = true;
  }

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
};