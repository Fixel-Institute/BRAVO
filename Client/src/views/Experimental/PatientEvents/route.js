/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

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