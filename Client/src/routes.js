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

import { MdOutlineEventAvailable, MdFitbit, MdBuildCircle, MdStorage, MdSdStorage } from "react-icons/md";
import { BsCollectionFill } from "react-icons/bs"
import { IoWatch } from "react-icons/io5";
import { FaBrain, FaFileWaveform, FaClipboardList, FaRing, FaMicrophone, FaTimeline, FaFilter } from "react-icons/fa6";
import { PiWavesBold } from "react-icons/pi";
import { FcSurvey } from "react-icons/fc";

// Images
import DevicesOtherIcon from '@mui/icons-material/DevicesOther';
import DashboardIcon from '@mui/icons-material/Dashboard';
import DescriptionIcon from '@mui/icons-material/Description';
import BoltIcon from '@mui/icons-material/Bolt';
import PollIcon from '@mui/icons-material/Poll';
import SensorsIcon from '@mui/icons-material/Sensors';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TimelineIcon from '@mui/icons-material/Timeline';
import PersonIcon from '@mui/icons-material/Person';
import BiotechIcon from '@mui/icons-material/Biotech';
import { AccessAlarm, People, Article, IosShare } from "@mui/icons-material";

import { experimentalRoutes } from "views/Experimental/plugins";

// BRAVO Platform Layouts
const DashboardOverview = lazy(() => import('views/Dashboard/Overview'));
const AsyncJobSchedule = lazy(() => import('views/AsyncJobSchedule'));
const StudyManagement = lazy(() => import('views/Dashboard/StudyManagement'));
const UploadDataView = lazy(() => import('views/Dashboard/UploadDataView'));
const ResearchAccessView = lazy(() => import('views/Dashboard/ShareResearchAccess'));
const ParticipantOverview = lazy(() => import('views/Dashboard/ParticipantOverview'));
const ImageVisualization = lazy(() => import('views/ImageVisualization'));
const FormList = lazy(() => import('views/Survey/FormList'));
const FormEditor = lazy(() => import('views/Survey/Editor'));
const FormViewer = lazy(() => import('views/Survey/Viewer'));
const ParticipantSurveyRecords = lazy(() => import('views/Reports/ParticipantRecords'));
const EmpaticaDataExplorer = lazy(() => import('views/ExternalSensors/Empatica'));
const FitbitDashboard = lazy(() => import('views/ExternalSensors/Fitbit'));
const OuraRingDashboard = lazy(() => import('views/ExternalSensors/OuraRing'));
const CustomizedAnalysis = lazy(() => import('views/CustomizedAnalysis'));
const AIHealthcare = lazy(() => import('views/Experimental/AIHealthcare'));
const InClinicMedicationCycle = lazy(() => import('views/Experimental/InClinicMedicationCycle'));
const PredictTherapyParameters = lazy(() => import('views/Experimental/PredictTherapyParameters'));

const FilterData = lazy(() => import('views/Dashboard/FilterData'));
const TherapyHistory = lazy(() => import('views/Reports/TherapyHistory'));
const NeuralActivitySnapshot = lazy(() => import('views/Reports/NeuralActivitySnapshot'));
const ParticipantEvents = lazy(() => import('views/Reports/ParticipantEvents'));
const TherapeuticEffects = lazy(() => import('views/Reports/TherapeuticEffects'));
const TimeSeriesAnalysis = lazy(() => import('views/Reports/TimeSeriesAnalysis'));
const ChronicNeuralActivity = lazy(() => import('views/Reports/ChronicNeuralActivity'));
const ChronicTimeline = lazy(() => import('views/Reports/ChronicTimeline'));
const SourceFiles = lazy(() => import('views/Reports/SourceFiles'));

// Group Analysis
const SurveyPeakIdentifier = lazy(() => import('views/GroupAnalysis/AnnotationTrainer/SurveyPeakIdentifier'));
const ElectrodeIdentifierExamination = lazy(() => import('views/GroupAnalysis/ElectrodeIdentifierExamination'));
const SpectralAnalysisExaminationStreaming = lazy(() => import('views/GroupAnalysis/SpectralAnalysisExaminationStreaming'));
const SpectralAnalysisExaminationSurvey = lazy(() => import('views/GroupAnalysis/SpectralAnalysisExaminationSurvey'));

const routes = {
  "Main": {
    children: [
      {
        type: "collapse",
        name: "Database",
        key: "dashboard",
        component: <DashboardOverview />,
        route: "/database",
        icon: <DashboardIcon/>,
        noCollapse: true,
      },
      {
        type: "collapse",
        name: "Filter Data",
        key: "filter-data",
        component: <FilterData />,
        route: "/filter-data",
        icon: <FaFilter />,
        noCollapse: true,
      },
      {
        type: "collapse",
        name: "StudyManagement",
        key: "study-management",
        component: <StudyManagement />,
        route: "/study-management",
        icon: <BsCollectionFill/>,
        noCollapse: true,
      },
      {
        type: "collapse",
        name: "Survey and Questionnaire",
        key: "SurveyList",
        component: <FormList />,
        route: "/form-manager",
        icon: <FaClipboardList />,
        noCollapse: true,
      },
      {
        type: "collapse",
        name: "Forms Editor",
        key: "SurveyEditor",
        component: <FormEditor />,
        route: "/form-manager/:form_link",
        icon: <FaClipboardList />,
        noCollapse: true,
        hide: true,
      },
      {
        type: "collapse",
        name: "Forms Viewer",
        key: "SurveyViewer",
        component: <FormViewer />,
        route: "/survey/:form_link",
        icon: <FaClipboardList />,
        noCollapse: true,
        hide: true,
      },
    ]
  },
  "SurveyTabs": {
    children: [
      {
        type: "collapse",
        name: "Survey and Questionnaire",
        key: "SurveyList",
        component: <FormList />,
        route: "/form-manager",
        icon: <FaClipboardList />,
        noCollapse: true,
      },
      {
        type: "collapse",
        name: "Forms Editor",
        key: "SurveyEditor",
        component: <FormEditor />,
        route: "/form-manager/:form_link",
        icon: <FaClipboardList />,
        noCollapse: true,
        hide: true,
      },
      {
        type: "collapse",
        name: "Forms Viewer",
        key: "SurveyViewer",
        component: <FormViewer />,
        route: "/survey/:form_link",
        icon: <FaClipboardList />,
        noCollapse: true,
        hide: true,
      }
    ]
  },
  "StudyGroupAnalysis": {
    icon: <AssessmentIcon />,
    name: "Group Analysis",
    children: [
      {
        key: "GroupAnalysis",
        name: "Group Analysis",
        title: true,
        hide: true
      },
      {
        key: "SpectralAnalysisExaminationStreaming",
        name: "Effects of Changes in Stimulation",
        icon: <BiotechIcon />,
        route: "/group-analysis/stimulation-induced-changes",
        component: <SpectralAnalysisExaminationStreaming />,
      },
      {
        key: "SpectralAnalysisExaminationSurvey",
        name: "DBS Snapshot Analysis",
        icon: <BiotechIcon />,
        route: "/group-analysis/dbs-snapshot-analysis",
        component: <SpectralAnalysisExaminationSurvey />,
      }
    ]
  },
  "GeneralReports": {
    icon: <AssessmentIcon />,
    name: "Brain Data",
    children: [
      {
        key: "GeneralReports",
        name: "General Reports",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: false,
        hide: true
      },
      {
        key: "therapyHistory",
        name: "Therapy History",
        icon: <BoltIcon />,
        route: "/reports/therapy-history/:participant_uid",
        component: <TherapyHistory />,
      },
      {
        key: "nerual-activity-snapshot",
        name: "Neural Activity Snapshot",
        icon: <PiWavesBold />,
        route: "/reports/nerual-activity-snapshot/:participant_uid",
        component: <NeuralActivitySnapshot />,
      },
      {
        key: "time-series-analysis",
        name: "Time-Series Analysis",
        icon: <FaFileWaveform />,
        route: "/reports/time-series-analysis/:participant_uid",
        component: <TimeSeriesAnalysis />,
      },
      {
        key: "chronic-neural-activity",
        name: "Chronic Neural Activity",
        icon: <TimelineIcon />,
        route: "/reports/chronic-neural-activity/:participant_uid",
        component: <ChronicNeuralActivity />,
      },
      {
        key: "multimodal-timeline-report",
        name: "Multi-Modality Timeline Report",
        icon: <DevicesOtherIcon />,
        route: "/reports/multimodal-timeline-report/:participant_uid",
        component: <ChronicTimeline />,
      },
      {
        key: "events",
        name: "Chronic Events",
        icon: <MdOutlineEventAvailable />,
        route: "/reports/events/:participant_uid",
        component: <ParticipantEvents />,
      }
    ]
  },
  "SurveyReports": {
    icon: <FcSurvey />,
    name: "Surveys and Questionnaires",
    children: [
      {
        key: "SurveysandQuestionnaires",
        name: "Surveys and Questionnaires",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: true,
        hide: true
      },
      {
        key: "FormRecords",
        name: "Form Records",
        icon: <FaClipboardList />,
        route: "/form-records/:participant_uid",
        component: <ParticipantSurveyRecords />,
      }
    ]
  },
  "ExternalSensorReports": {
    icon: <IoWatch />,
    name: "External Sensors",
    children: [
      {
        key: "ExternalSensor",
        name: "External Sensors",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: true,
        hide: true
      },
      {
        key: "FitbitDashboard",
        name: "Fitbit Dashboard",
        icon: <MdFitbit />,
        route: "/fitbit/dashboard/:participant_uid",
        component: <FitbitDashboard />,
      },
      {
        key: "OuraRingDashboard",
        name: "Oura Ring Dashboard",
        icon: <FaRing />,
        route: "/oura-ring/dashboard/:participant_uid",
        component: <OuraRingDashboard />,
      },
      {
        key: "EmpaticaDataExplorer",
        name: "Empatica Data Explorer",
        icon: <img src={"https://www.empatica.com/website/assets/images/embraceplus/embraceplus_closed_side_hero-sm-xhdpi.png"} width={"30pt"} alt="Empatica" />,
        route: "/empatica/data-explorer/:participant_uid",
        component: <EmpaticaDataExplorer />,
      }
    ]
  },
  "ImagingReports": {
    icon: <FaBrain />,
    name: "Imaging Reports",
    children: [
      {
        key: "ImagingReports",
        name: "Imaging Reports",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: true,
        hide: true
      },
      {
        key: "3dImageViewer",
        name: "3D Image Viewer",
        icon: <FaBrain />,
        route: "/image-visualization/:participant_uid",
        component: <ImageVisualization />,
      }
    ]
  },
  "CustomizedAnalysis": {
    icon: <MdBuildCircle />,
    name: "Customized Analysis",
    children: [
      {
        key: "CustomizedAnalysis",
        name: "Customized Analysis",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: true,
        hide: true
      },
      {
        key: "AnalysisBuilder",
        name: "Analysis Builder",
        icon: <MdBuildCircle />,
        route: "/analysis-builder/:participant_uid",
        component: <CustomizedAnalysis />,
      },
      {
        key: "AIHealthcare",
        name: "AI Healthcare",
        icon: <MdBuildCircle />,
        route: "/ai-healthcare/:participant_uid",
        component: <AIHealthcare />,
      },
      {
        key: "InClinicMedicationCycle",
        name: "In-clinic Medication Cycle",
        icon: <MdBuildCircle />,
        route: "/medication-cycle/:participant_uid",
        component: <InClinicMedicationCycle />,
      },
      {
        key: "PredictTherapyParameters",
        name: "Predict Therapy Parameters",
        icon: <MdBuildCircle />,
        route: "/predict-therapy-parameters/:participant_uid",
        component: <PredictTherapyParameters />,
      }
    ]
  },
  "DataManager": {
    icon: <MdStorage />,
    name: "Data Manager",
    children: [
      {
        key: "DataManager",
        name: "Data Manager",
        title: true,
        hide: true
      },
      {
        type: "collapse",
        name: "ParticipantOverview",
        key: "participant-overview",
        component: <ParticipantOverview />,
        route: "/participant-overview/:participant_uid",
        icon: <PersonIcon/>,
        noCollapse: true,
        hide: true
      },
      {
        key: "ExistingSourceFiles",
        name: "Existing Source Files",
        icon: <MdSdStorage  />,
        route: "/source-files/:participant_uid",
        component: <SourceFiles />,
      }
    ]
  },
}

export default routes;
