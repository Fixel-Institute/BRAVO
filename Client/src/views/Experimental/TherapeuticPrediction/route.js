import {
  BatchPrediction, 
} from "@mui/icons-material";

import TherapeuticPrediction from "./index";

const route = {
  name: "TherapeuticPrediction",
  key: "therapeutic-prediction",
  icon: <BatchPrediction style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/therapeutic-prediction",
  component: <TherapeuticPrediction />,
  identified: true,
  deidentified: true
};

export default route;