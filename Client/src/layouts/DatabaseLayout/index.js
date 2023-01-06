import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import DashboardLayout from "./DashboardLayout";
import DashboardNavbar from "components/Navbars/DashboardNavbar";
import Footer from "components/Footers/DashboardFooter";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";

export default function DatabaseLayout({children}) {
  const [controller, dispatch] = usePlatformContext();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    SessionController.handShake().then((state) => {
      if (!state) {
        const redirectHomepage = () => {
          setContextState(dispatch, "user", {});
          setContextState(dispatch, "patientID", null);
          navigate("/index", {replace: false});
        };
        setAlert(
          <MuiAlertDialog title={"ERROR"} message={"Connection Timed-out"}
            handleClose={redirectHomepage} 
            handleConfirm={redirectHomepage}/>
        );
      }
    })
  }, [pathname]);

  return <>
    <DashboardLayout>
      {alert}
      <DashboardNavbar fixedNavbar />
      {children}
    </DashboardLayout>
    <Footer />
  </>;
};
 
