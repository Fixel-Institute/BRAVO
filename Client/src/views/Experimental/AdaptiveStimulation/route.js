import {
  FlashAuto, 
} from "@mui/icons-material";

import AdaptiveStimulation from "./index";

const route = {
  name: "AdaptiveStimulation",
  key: "adaptive",
  icon: <FlashAuto style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/adaptive",
  component: <AdaptiveStimulation />,
  identified: true,
  deidentified: true
};

export default route;