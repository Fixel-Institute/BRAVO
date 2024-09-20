import CalculateSpectralFeaturesEditor from "./CalculateSpectralFeaturesEditor"
import ExportEditor from "./ExportEditor"
import ExtractTimeFrequencyAnalysisEditor from "./ExtractTimeFrequencyAnalysisEditor"
import ExtractAnnotationsEditor from "./ExtractAnnotationsEditor"
import ExtractNarrowBandSpectralEditor from "./ExtractNarrowBandSpectral"
import CardiacFilterEditor from "./CardiacFilterEditor"
import FilterEditor from "./FilterEditor"
import NormalizeEditor from "./NormalizeEditor"
import ViewEditor from "./ViewEditor"
import WienerFilterrEditor from "./WienerFilterrEditor"


const availableProcessings = [{
  type: {
    value: "cardiacFilter",
    label: "Apply Cardiac Filter to TimeDomain Data",
  },
  cardiacFilterMethod: "Kurtosis-peak Detection Template Matching",
}, {
  type: {
    value: "wienerFilter",
    label: "Apply Wiener Filter to TimeDomain Data (Exploratory Artifact Removal Method)",
  },
}, {
  type: {
    value: "filter",
    label: "Apply Filter to TimeDomain Data",
  },
  highpass: "",
  lowpass: "",
}, {
  type: {
    value: "extractTimeFrequencyAnalysis",
    label: "Extract Time-Frequency Analysis from Time-series",
  },
  dropMissing: true,
  psdMethod: "Welch's Periodogram",
  window: 1000,
  overlap: 500,
  frequencyResolution: 0.5,
  modelOrder: 30
}, {
  type: {
    value: "extractAnnotations",
    label: "Extract PSDs from Annotations",
  },
  label: "annotation",
  averaged: true,
}, {
  type: {
    value: "extractNarrowBandFeature",
    label: "Extract Narrow Band Spectral Feature Peaks",
  },
  labelRecording: "",
  averageDuration: 10,
  frequencyRangeStart: 50,
  frequencyRangeEnd: 100,
  threshold: 5,
}, {
  type: {
    value: "normalize",
    label: "Normalize PSD Data",
  },
  normalizeMethod: "FOOOF",
  highEdge: "90",
  lowEdge: "70",
}, {
  type: {
    value: "calculateSpectralFeatures",
    label: "Calculate Spectral Features from PSD Data"
  },
  bands: []
}];

const AnalysisSteps = ({type, ...rest}) => {
  const defaultConfigs = availableProcessings.filter((a) => a.type.value == type);
  if (defaultConfigs.length > 0) {
    if (type === "filter") {
      return <FilterEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "cardiacFilter") {
      return <CardiacFilterEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "wienerFilter") {
      return <WienerFilterrEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "extractTimeFrequencyAnalysis") {
      return <ExtractTimeFrequencyAnalysisEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "extractAnnotations") {
      return <ExtractAnnotationsEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "normalize") {
      return <NormalizeEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "calculateSpectralFeatures") {
      return <CalculateSpectralFeaturesEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "extractNarrowBandFeature") {
      return <ExtractNarrowBandSpectralEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "export") {
      return <ExportEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    } else if (type === "view") {
      return <ViewEditor currentState={rest.currentState} availableRecordings={rest.availableRecordings} newProcess={rest.newProcess} defaultConfigs={defaultConfigs[0]}
        updateConfiguration={rest.updateConfiguration}
      />
    }
  }
  
  return null;
}

export {
  availableProcessings,
  AnalysisSteps
}