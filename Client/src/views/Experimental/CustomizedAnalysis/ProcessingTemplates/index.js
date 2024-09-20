import ExtractPSDsFromAnnotationsTemplate from "./ExtractPSDsFromAnnotationsTemplate";
import ExtractNarrowBandSpectralTemplate from "./ExtractNarrowBandSpectralTemplate";
import ExtractBetaGammaAnalysisTemplate from "./ExtractBetaGammaAnalysisTemplate";
import { availableProcessings } from "../AnalysisSteps";

const availableTemplates = [{
  value: "extractPSDsFromEvents",
  label: "Extract PSDs from Annotations for Event Comparison",
}, {
  value: "extractNarrowBandSpectral",
  label: "Extract Narrow-band Gamma from Recording",
}, {
  value: "extractBetaGammaAnalysis",
  label: "Extract Beta/Gamma Power Trend During Streaming",
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
      if (options.wiener) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "wienerFilter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_WienerFiltered" });
        startSignal += "_WienerFiltered"; 
      }
      if (options.cardiacRemoved) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "cardiacFilter")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_CardiacFiltered" });
        startSignal += "_CardiacFiltered"; 
      }
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractTimeFrequencyAnalysis")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_Spectrogram", psdMethod: "Welch's Periodogram" });
      startSignal += "_Spectrogram"; 
      
      if (options.normalized) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "normalize")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highEdge: "90", lowEdge: "70", normalizeMethod: "FOOOF", output: startSignal + "_Normalized" });
        startSignal += "_Normalized"; 
      }
      
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractAnnotations")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_PSDs", averaged: options.averageFeatures });
      startSignal += "_PSDs"; 

      stepConfig = availableProcessings.filter((a) => a.type.value == "calculateSpectralFeatures")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_SpectralFeatures", bands: [
        ["Theta", 4, 8], 
        ["Alpha", 8, 12], 
        ["LowBeta", 12, 20], 
        ["HighBeta", 20,30], 
        ["LowGamma", 30, 60], 
        ["HighGamma", 60, 90]
      ] });

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
      
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractTimeFrequencyAnalysis")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_Spectrogram", psdMethod: options.psdMethod, window: options.averageDuration*1000, overlap: options.averageDuration*500 });
      startSignal += "_Spectrogram"; 
      
      if (options.normalized) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "normalize")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highEdge: "90", lowEdge: "70", normalizeMethod: "FOOOF", output: startSignal + "_Normalized" });
        startSignal += "_Normalized"; 
      }

      stepConfig = availableProcessings.filter((a) => a.type.value == "extractNarrowBandFeature")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_GammaFeatures", frequencyRangeStart: 50, frequencyRangeEnd: 100, threshold: options.threshold });
      startSignal += "_GammaFeatures"; 

      rest.setConfiguration(steps)
    }}/>
  } else if (type === "extractBetaGammaAnalysis") {
    return <ExtractBetaGammaAnalysisTemplate availableRecordings={rest.availableRecordings} setConfiguration={(options) => {
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
      
      stepConfig = availableProcessings.filter((a) => a.type.value == "extractTimeFrequencyAnalysis")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_Spectrogram", psdMethod: options.psdMethod, window: options.averageDuration*1000, overlap: options.averageDuration*500 });
      startSignal += "_Spectrogram"; 
      
      if (options.normalized) {
        stepConfig = availableProcessings.filter((a) => a.type.value == "normalize")[0];
        steps.push({ ...stepConfig, targetRecording: startSignal, highEdge: "90", lowEdge: "70", normalizeMethod: "FOOOF", output: startSignal + "_Normalized" });
        startSignal += "_Normalized"; 
      }

      stepConfig = availableProcessings.filter((a) => a.type.value == "calculateSpectralFeatures")[0];
      steps.push({ ...stepConfig, targetRecording: startSignal, output: startSignal + "_SpectralFeatures", bands: [
        ["LowBeta", 12, 20], 
        ["HighBeta", 20,30], 
        ["Beta", 12,30], 
        ["LowGamma", 30, 60],
        ["HighGamma", 60, 90]
      ] });

      rest.setConfiguration(steps)
    }}/>
  }
  return null;
}

export {
  availableTemplates,
  ProcessingTemplates
}