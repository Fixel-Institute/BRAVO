/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

const enabledPlugins = [
  "TherapeuticPrediction",
  "MultipleSegmentAnalysis",
  "AdaptiveStimulation",
  "CircadianThreshold",
  "PatientEvents",
  "ImageVisualization",
  "CustomizedAnalysis",
  "MobileManager"
];

export const experimentalRoutes = enabledPlugins.map((plugin) => {
  return require("views/Experimental/" + plugin + "/route.js").default;
});
