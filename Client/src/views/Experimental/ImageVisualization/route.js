import {
  Photo, 
} from "@mui/icons-material";

import ImageVisualization from "./index";

const route = {
  name: "ImageVisualization",
  key: "visualize",
  icon: <Photo style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/visualize",
  component: <ImageVisualization />,
  identified: true,
  deidentified: true
};

export default route;