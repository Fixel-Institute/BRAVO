/**
=========================================================
* Material Dashboard 2 PRO React - v2.1.0
=========================================================

* Product Page: https://www.creative-tim.com/product/material-dashboard-pro-react
* Copyright 2022 Creative Tim (https://www.creative-tim.com)

Coded by www.creative-tim.com

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

/** 
  All of the routes for the Material Dashboard 2 PRO React are added here,
  You can add a new route, customize the routes and delete the routes here.

  Once you add a new route on this file it will be visible automatically on
  the Sidenav.

  For adding a new route you can follow the existing routes in the routes array.
  1. The `type` key with the `collapse` value is used for a route.
  2. The `type` key with the `title` value is used for a title inside the Sidenav. 
  3. The `type` key with the `divider` value is used for a divider between Sidenav items.
  4. The `name` key is used for the name of the route on the Sidenav.
  5. The `key` key is used for the key of the route (It will help you with the key prop inside a loop).
  6. The `icon` key is used for the icon of the route on the Sidenav, you have to add a node.
  7. The `collapse` key is used for making a collapsible item on the Sidenav that contains other routes
  inside (nested routes), you need to pass the nested routes inside an array as a value for the `collapse` key.
  8. The `route` key is used to store the route location which is used for the react router.
  9. The `href` key is used to store the external links location.
  10. The `title` key is only for the item with the type of `title` and its used for the title text on the Sidenav.
  10. The `component` key is used to store the component of its route.
*/

// BRAVO Platform Layouts
import DashboardOverview from "views/Dashboard/Overview";
import PatientOverview from "views/Dashboard/PatientOverview";
import TherapyHistory from "views/Reports/TherapyHistory";
import BrainSenseSurvey from "views/Reports/BrainSenseSurvey";
import BrainSenseStreaming from "views/Reports/BrainSenseStreaming";
import IndefiniteStreaming from "views/Reports/IndefiniteStreaming";
import ChronicBrainSense from "views/Reports/ChronicBrainSense";

import TherapeuticPrediction from "views/Experimental/TherapeuticPrediction";
import PatientEvents from "views/Experimental/PatientEvents";
import AdaptiveStimulation from "views/Experimental/AdaptiveStimulation";
import ImageVisualization from "views/Experimental/ImageVisualization";
import WearableStream from "views/Experimental/WearableStream";

// Material Dashboard 2 PRO React components
import MDAvatar from "components/MDAvatar";

// @mui icons
import Icon from "@mui/material/Icon";

// Images
import DashboardIcon from '@mui/icons-material/Dashboard';
import DescriptionIcon from '@mui/icons-material/Description';
import BoltIcon from '@mui/icons-material/Bolt';
import PollIcon from '@mui/icons-material/Poll';
import SensorsIcon from '@mui/icons-material/Sensors';
import TimelineIcon from '@mui/icons-material/Timeline';
import PersonIcon from '@mui/icons-material/Person';
import BiotechIcon from '@mui/icons-material/Biotech';
import BatchPredictionIcon from '@mui/icons-material/BatchPrediction';
import FlashAutoIcon from '@mui/icons-material/FlashAuto';
import PhotoIcon from '@mui/icons-material/Photo';
import WatchIcon from '@mui/icons-material/Watch';

const routes = [
  {
    type: "collapse",
    name: "Dashboard",
    key: "dashboard",
    component: <DashboardOverview />,
    route: "/dashboard",
    icon: <DashboardIcon/>,
    noCollapse: true,
  },
  { type: "divider", key: "divider-1" },
  {
    type: "collapse",
    name: "PatientOverview",
    key: "patient-overview",
    component: <PatientOverview />,
    route: "/patient-overview",
    icon: <PersonIcon/>,
    noCollapse: true,
  },
  { type: "title", name: "Reports", key: "title-pages" },
  {
    type: "collapse",
    name: "Reports",
    key: "reports",
    icon: <DescriptionIcon/>,
    collapse: [
      {
        name: "TherapyHistory",
        key: "therapy-history",
        icon: <BoltIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/therapy-history",
        component: <TherapyHistory />
      },
      {
        name: "BrainSenseSurvey",
        key: "survey",
        icon: <PollIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/survey",
        component: <BrainSenseSurvey />
      },
      {
        name: "BrainSenseStreaming",
        key: "stream",
        icon: <SensorsIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/stream",
        component: <BrainSenseStreaming />
      },
      {
        name: "IndefiniteStreaming",
        key: "multistream",
        icon: <SensorsIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/multistream",
        component: <IndefiniteStreaming />
      },
      {
        name: "ChronicRecordings",
        key: "chronic-recordings",
        icon: <TimelineIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/chronic-recordings",
        component: <ChronicBrainSense />
      },
    ]
  },
  {
    type: "collapse",
    name: "Experimental",
    key: "experimental",
    icon: <BiotechIcon/>,
    collapse: [
      {
        name: "TherapeuticPrediction",
        key: "therapeutic-prediction",
        icon: <BatchPredictionIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/experimental/therapeutic-prediction",
        component: <TherapeuticPrediction />
      },
      {
        name: "PatientEvents",
        key: "patient-events",
        icon: <TimelineIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/experimental/patient-events",
        component: <PatientEvents />
      },
      {
        name: "AdaptiveStimulation",
        key: "adaptive",
        icon: <FlashAutoIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/experimental/adaptive",
        component: <AdaptiveStimulation />
      },
      {
        name: "ImageVisualization",
        key: "visualize",
        icon: <PhotoIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/experimental/visualize",
        component: <ImageVisualization />
      },
      {
        name: "WearableStream",
        key: "wearable",
        icon: <WatchIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/experimental/wearable",
        component: <WearableStream />
      },
    ]
  }
];

export default routes;
