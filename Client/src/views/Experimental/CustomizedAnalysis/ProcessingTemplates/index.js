import ExtractPSDsFromAnnotationsTemplate from "./ExtractPSDsFromAnnotationsTemplate";
import ExtractNarrowBandSpectralTemplate from "./ExtractNarrowBandSpectralTemplate";
import { availableProcessings } from "../AnalysisSteps";

const availableTemplates = [{
  value: "extractPSDsFromEvents",
  label: "Extract PSDs from Annotations for Event Comparison",
}, {
  value: "extractNarrowBandSpectral",
  label: "Extract Narrow-band Gamma from Recording",
}];

const ProcessingTemplates = ({type, ...rest}) => {

  if (type === "extractPSDsFromEvents") {
    return <ExtractPSDsFromAnnotationsTemplate availableRecordings={rest.availableRecordings} setConfiguration={(options) => {
      if (!options) (rest.setConfiguration(false));

      let steps = [];
      let stepConfig = {};
      let startSignal = options.targetRecording;
      if (options.cardiacRemoved) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "cardiacFilter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_CardiacFiltered" });
        startSignal += "_CardiacFiltered"; 
      }
      if (options.filtered) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "filter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highpass: "1", lowpass: "100", output: startSignal + "_Filtered" });
        startSignal += "_Filtered"; 
      }
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractAnnotations")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_PSDs", psdMethod: "Short-time Fourier Transform", averaged: options.averageFeatures });
      startSignal += "_PSDs"; 
      if (options.normalized) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "normalize")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highEdge: "90", lowEdge: "70", normalizeMethod: "FOOOF", output: startSignal + "_Normalized" });
        startSignal += "_Normalized"; 
      }
      stepConfig = availableProcessings.filter((a) => a.type.value == "calculateSpectralFeatures")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_SpectralFeatures" });
      stepConfig = availableProcessings.filter((a) => a.type.value == "view")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_Viewed" });

      rest.setConfiguration(steps)
    }}/>
  } else if (type === "extractNarrowBandSpectral") {
    return <ExtractNarrowBandSpectralTemplate availableRecordings={rest.availableRecordings} setConfiguration={(options) => {
      if (!options) (rest.setConfiguration(false));

      let steps = [];
      let stepConfig = {};
      let startSignal = options.targetRecording;
      if (options.cardiacRemoved) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "cardiacFilter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_CardiacFiltered" });
        startSignal += "_CardiacFiltered"; 
      }
      if (options.filtered) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "filter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highpass: "1", lowpass: "100", output: startSignal + "_Filtered" });
        startSignal += "_Filtered"; 
      }
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractNarrowBandFeature")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_GammaFeatures", averageDuration: options.averageDuration, frequencyRangeStart: 50, frequencyRangeEnd: 100, threshold: options.threshold });
      startSignal += "_GammaFeatures"; 
      if (options.normalized) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "normalize")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highEdge: "90", lowEdge: "70", normalizeMethod: "FOOOF", output: startSignal + "_Normalized" });
        startSignal += "_Normalized"; 
      }

      rest.setConfiguration(steps)
    }}/>
  }
  return null;
}

export {
  availableTemplates,
  ProcessingTemplates
}