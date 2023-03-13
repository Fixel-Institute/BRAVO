import {
  AccessAlarm, 
} from "@mui/icons-material";

import CircadianThreshold from "./index";

const route = {
  name: "CircadianThreshold",
  key: "circadian",
  icon: <AccessAlarm style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/circadian",
  component: <CircadianThreshold />,
  identified: true,
  deidentified: true
};

export default route;