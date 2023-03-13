import TherapeuticPrediction from "views/Experimental/TherapeuticPrediction";
import MultipleSegmentAnalysis from "views/Experimental/MultipleSegmentAnalysis";
import PatientEvents from "views/Experimental/PatientEvents";
import CircadianThreshold from "views/Experimental/CircadianThreshold";
import ImageVisualization from "views/Experimental/ImageVisualization";
import WearableStream from "views/Experimental/WearableStream";

import BatchPredictionIcon from '@mui/icons-material/BatchPrediction';
import FlashAutoIcon from '@mui/icons-material/FlashAuto';
import PhotoIcon from '@mui/icons-material/Photo';
import WatchIcon from '@mui/icons-material/Watch';

import { 
  AccessAlarm, 
  BatchPrediction,
  Timeline,
  Watch, 
  Photo, 
  FlashAuto, 
} from "@mui/icons-material";

const enabledPlugins = [
  "TherapeuticPrediction",
  "MultipleSegmentAnalysis",
  "AdaptiveStimulation",
  "CircadianThreshold",
  "PatientEvents",
  "ImageVisualization",
  "WearableStream"
];

export const experimentalRoutes = enabledPlugins.map((plugin) => {
  return require("views/Experimental/" + plugin + "/route.js").default;
});

/*
export const experimentalRoutes = [
  {
  },
  {
  },
  {
  },,
  {
  },
  {
  },
]
*/