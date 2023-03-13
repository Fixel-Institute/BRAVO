import {
  Timeline, 
} from "@mui/icons-material";

import PatientEvents from "./index";

const route = {
  name: "PatientEvents",
  key: "patient-events",
  icon: <Timeline style={{color: "white", margin: 0, padding: 0}}/>,
  route: "/experimental/patient-events",
  component: <PatientEvents />,
  identified: true,
  deidentified: true
};

export default route;