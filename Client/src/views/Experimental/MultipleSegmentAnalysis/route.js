import {
  BatchPrediction, 
} from "@mui/icons-material";

import MultipleSegmentAnalysis from "./index";

const route = {
  name: "MultipleSegmentAnalysis",
  key: "segment-analysis",
  icon: <BatchPrediction style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/segment-analysis",
  component: <MultipleSegmentAnalysis />,
  identified: true,
  deidentified: true
};

export default route;