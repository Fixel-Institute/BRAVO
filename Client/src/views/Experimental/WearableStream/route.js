import {
  Watch, 
} from "@mui/icons-material";

import WearableStream from "./index";

const route = {
  name: "WearableStream",
  key: "wearable",
  icon: <Watch style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/wearable",
  component: <WearableStream />,
  identified: true,
  deidentified: true
};

export default route;