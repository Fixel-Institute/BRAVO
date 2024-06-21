import ExtractPSDsFromAnnotationsTemplate from "./ExtractPSDsFromAnnotationsTemplate";
import { availableProcessings } from "../AnalysisSteps";

const availableTemplates = [{
  value: "extractPSDsFromEvents",
  label: "Extract PSDs from Annotations for Event Comparison",
}];

const ProcessingTemplates = ({type, ...rest}) => {

  if (type === "extractPSDsFromEvents") {
    return <ExtractPSDsFromAnnotationsTemplate availableRecordings={rest.availableRecordings} setConfiguration={(options) => {
      if (!options) (rest.setConfiguration(false));

      let steps = [];
      let stepConfig = {};
      let startSignal = options.targetRecording;
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
  }
  return null;
}

export {
  availableTemplates,
  ProcessingTemplates
}