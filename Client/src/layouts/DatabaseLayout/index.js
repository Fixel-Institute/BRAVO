/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import DashboardLayout from "./DashboardLayout";
import DashboardNavbar from "components/Navbars/DashboardNavbar";
import Footer from "components/Footers/DashboardFooter";
import MuiAlertDialog from "components/MuiAlertDialog";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function DatabaseLayout({children}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, authExpired } = controller;
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    SessionController.handShake().then((state) => {
      if (!state) {
        SessionController.nullifyUser();
        setContextState(dispatch, "user", {});
        setContextState(dispatch, "participant_uid", null);
        
        const handleTimeout = () => {
          navigate("/", {replace: false});
        }

        setAlert(
          <MuiAlertDialog title={"ERROR"} message={dictionaryLookup(dictionary.ErrorMessage, "CONNECTION_TIMEDOUT", language)}
            handleClose={handleTimeout} 
            handleConfirm={handleTimeout}/>)
      }
    });
  }, [pathname, authExpired]);

  return <>
    <DashboardLayout>
      {alert}
      <DashboardNavbar fixedNavbar />
      {children}
    </DashboardLayout>
    <Footer />
  </>;
};
 
