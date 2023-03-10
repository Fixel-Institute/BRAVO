import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import DashboardLayout from "../DatabaseLayout/DashboardLayout";
import PageLayout from "../OnePage/PageLayout";
import DashboardNavbar from "components/Navbars/DashboardNavbar";
import Footer from "components/Footers/DashboardFooter";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SurveyLayout({viewOnly, children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, sessionState } = controller;
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!viewOnly) {
      SessionController.handShake().then((state) => {
        if (!state) {
          SessionController.nullifyUser();
          setContextState(dispatch, "user", {});
          setContextState(dispatch, "patientID", null);

          const handleTimeout = () => {
            navigate("/", {replace: false});
          };

          setAlert(
            <MuiAlertDialog title={"ERROR"} message={dictionaryLookup(dictionary.ErrorMessage, "CONNECTION_TIMEDOUT", language)}
              handleClose={handleTimeout} 
              handleConfirm={handleTimeout}/>)
        }
      });
    }
  }, [pathname, sessionState]);

  return viewOnly ? <>
    <PageLayout sx={{padding: 5}}>
      {alert}
      {children}
    </PageLayout>
  </> : <>
    <DashboardLayout>
      {alert}
      {children}
    </DashboardLayout>
    <Footer />
  </>;
};
 
