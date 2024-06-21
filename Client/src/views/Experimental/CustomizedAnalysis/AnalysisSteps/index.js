import CalculateSpectralFeaturesEditor from "./CalculateSpectralFeaturesEditor"
import ExportEditor from "./ExportEditor"
import ExtractAnnotationsEditor from "./ExtractAnnotationsEditor"
import FilterEditor from "./FilterEditor"
import NormalizeEditor from "./NormalizeEditor"
import ViewEditor from "./ViewEditor"

const availableProcessings = [{
  type: {
    value: "filter",
    label: "Apply Filter to TimeDomain Data",
  },
  highpass: "",
  lowpass: "",
}, {
  type: {
    value: "extractAnnotations",
    label: "Extract PSDs from Annotations",
  },
  psdMethod: "Short-time Fourier Transform",
  averaged: true,
}, {
  type: {
    value: "normalize",
    label: "Normalize PSD Data",
  },
  normalizeMethod: "FOOOF",
  highEdge: "",
  lowEdge: "",
}, {
  type: {
    value: "calculateSpectralFeatures",
    label: "Calculate Spectral Features from PSD Data"
  },
}, {
  type: {
    value: "export",
    label: "Export Data"
  },
}, {
  type: {
    value: "view",
    label: "View Data"
  },
}];

const AnalysisSteps = ({type, ...rest}) => {
  const defaultConfigs = availableProcessings.filter((a) => a.value == type);
  if (type === "filter") {
    return <FilterEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  } else if (type === "extractAnnotations") {
    return <ExtractAnnotationsEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  } else if (type === "normalize") {
    return <NormalizeEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  } else if (type === "calculateSpectralFeatures") {
    return <CalculateSpectralFeaturesEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  } else if (type === "export") {
    return <ExportEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  } else if (type === "view") {
    return <ViewEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs}
      updateConfiguration={rest.updateConfiguration}
    />
  }
  
  return null;
}

export {
  availableProcessings,
  AnalysisSteps
}