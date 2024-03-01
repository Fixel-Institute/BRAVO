/** 
  All of the routes for the Material Dashboard 2 React are added here,
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

import {Suspense, lazy} from "react";

// Material Dashboard 2 React components
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
import { AccessAlarm, People, Article, IosShare } from "@mui/icons-material";

import { experimentalRoutes } from "views/Experimental/plugins";

// BRAVO Platform Layouts
const DashboardOverview = lazy(() => import('views/Dashboard/Overview'));
const PatientLookupTable = lazy(() => import('views/Dashboard/PatientLookupTable'));
const ResearchAccessView = lazy(() => import('views/Dashboard/ShareResearchAccess'));
const PatientOverview = lazy(() => import('views/Dashboard/PatientOverview'));
const SurveyList = lazy(() => import('views/Survey/Overview'));
const TherapyHistory = lazy(() => import('views/Reports/TherapyHistory'));
const BrainSenseSurvey = lazy(() => import('views/Reports/BrainSenseSurvey'));
const BrainSenseStreaming = lazy(() => import('views/Reports/BrainSenseStreaming'));
const IndefiniteStreaming = lazy(() => import('views/Reports/IndefiniteStreaming'));
const ChronicBrainSense = lazy(() => import('views/Reports/ChronicBrainSense'));
const SessionOverview = lazy(() => import('views/Reports/SessionsOverview'));

const routes = [
  {
    type: "collapse",
    name: "Dashboard",
    key: "dashboard",
    component: <DashboardOverview />,
    route: "/dashboard",
    icon: <DashboardIcon/>,
    noCollapse: true,
    identified: true,
    deidentified: true
  },
  {
    type: "collapse",
    name: "ShareResearchAccess",
    key: "access-permissions",
    component: <ResearchAccessView />,
    route: "/access-permissions",
    icon: <IosShare/>,
    noCollapse: true,
    identified: true,
    deidentified: true
  },
  {
    type: "collapse",
    name: "PatientLookupTable",
    key: "deidentification-table",
    component: <PatientLookupTable />,
    route: "/deidentification-table",
    icon: <People/>,
    noCollapse: true,
    identified: false,
    deidentified: true
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
    identified: true,
    deidentified: true
  },
  { type: "title", name: "Reports", key: "title-pages" },
  {
    type: "collapse",
    name: "Reports",
    key: "reports",
    identified: true,
    deidentified: true,
    icon: <DescriptionIcon/>,
    collapse: [
      {
        name: "TherapyHistory",
        key: "therapy-history",
        icon: <BoltIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/therapy-history",
        component: <TherapyHistory />,
        identified: true,
        deidentified: true
      },
      {
        name: "BrainSenseSurvey",
        key: "survey",
        icon: <PollIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/survey",
        component: <BrainSenseSurvey />,
        identified: true,
        deidentified: true
      },
      {
        name: "BrainSenseStreaming",
        key: "stream",
        icon: <SensorsIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/stream",
        component: <BrainSenseStreaming />,
        identified: true,
        deidentified: true
      },
      {
        name: "IndefiniteStreaming",
        key: "multistream",
        icon: <SensorsIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/multistream",
        component: <IndefiniteStreaming />,
        identified: true,
        deidentified: true
      },
      {
        name: "ChronicRecordings",
        key: "chronic-recordings",
        icon: <TimelineIcon style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/chronic-recordings",
        component: <ChronicBrainSense />,
        identified: true,
        deidentified: true
      },
      {
        name: "SessionOverview",
        key: "session-overview",
        icon: <Article style={{color: "white", margin: 0, padding: 0}}/>,
        route: "/reports/session-overview",
        component: <SessionOverview />,
        identified: true,
        deidentified: true
      },
    ]
  },
  {
    type: "collapse",
    name: "Experimental",
    key: "experimental",
    identified: true,
    deidentified: true,
    icon: <BiotechIcon/>,
    collapse: [
      ...experimentalRoutes
    ]
  },
  {
    type: "collapse",
    name: "Surveys",
    key: "surveys",
    component: <SurveyList />,
    route: "/surveys",
    icon: <DashboardIcon/>,
    noCollapse: true,
    identified: true,
    deidentified: true
  },
];

export default routes;
