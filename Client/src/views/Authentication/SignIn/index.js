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

// react-router-dom components
import { Link, useNavigate } from "react-router-dom";

// @mui material components
import Card from "@mui/material/Card";
import Switch from "@mui/material/Switch";
import Grid from "@mui/material/Grid";
import MuiLink from "@mui/material/Link";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import MuiAlertDialog from "components/MuiAlertDialog";

// Layout
import OnePageLayout from "layouts/OnePage";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";

export default function SignIn() {
  const [context, dispatch] = usePlatformContext();
  const { user, language } = context;

  const navigate = useNavigate();

  const [authInfo, setAuthInfo] = useState({email: "", password: ""});
  const [rememberMe, setRememberMe] = useState(false);
  const [alert, setAlert] = useState(null);
  const handleSetRememberMe = () => setRememberMe(!rememberMe);

  const handleAuthentication = () => {
    SessionController.authenticate(authInfo.email, authInfo.password, rememberMe).then((response) => {
      SessionController.setUser({
        ...response.data.user,
      });
      SessionController.setAuthToken(response.data.access);
      SessionController.setRefreshToken(response.data.refresh);
      SessionController.syncSession();
      setAuthInfo({...authInfo, password: ""});
      setContextState(dispatch, "user", {
        ...response.data.user,
      });
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  useEffect(() => {
    if (Object.keys(user).length > 0) {
      navigate("/dashboard", {replace: false});
    }
  }, [user]);

  const handlePasswordKeyPress = (event) => {
    if (event.key == "Enter") {
      handleAuthentication();
    }
  }

  return (
    <OnePageLayout image={"https://j9q7m2a3.rocketcdn.me/wp-content/uploads/2022/01/UF-Health.jpg"}>
      {alert}
      <Card>
        <MDBox
          variant="gradient"
          bgColor="info"
          borderRadius="lg"
          coloredShadow="info"
          mx={2}
          mt={-3}
          p={2}
          mb={1}
          textAlign="center"
        >
          <MDTypography variant="h4" fontWeight="medium" color="white" mt={1}>
            {dictionary.Login.AccountLogin[language]}
          </MDTypography>
        </MDBox>
        <MDBox pt={4} pb={3} px={3}>
          <MDBox component="form" role="form">
            <MDBox mb={2}>
              <MDInput type="email" label={dictionary.Login.Email[language]} value={authInfo.email} onChange={(event) => setAuthInfo({...authInfo, email: event.currentTarget.value})} fullWidth/>
            </MDBox>
            <MDBox mb={2}>
              <MDInput type="password" label={dictionary.Login.Password[language]} onKeyPress={handlePasswordKeyPress} value={authInfo.password} onChange={(event) => setAuthInfo({...authInfo, password: event.currentTarget.value})} fullWidth/>
            </MDBox>
            <MDBox display="flex" alignItems="center" ml={-1}>
              <Switch checked={rememberMe} onChange={handleSetRememberMe} />
              <MDTypography
                variant="button"
                fontWeight="regular"
                color="text"
                onClick={handleSetRememberMe}
                sx={{ cursor: "pointer", userSelect: "none", ml: -1 }}
              >
                &nbsp;&nbsp;Remember me
              </MDTypography>
            </MDBox>
            <MDBox mt={4} mb={1}>
              <MDButton variant="gradient" color="info" onClick={handleAuthentication} fullWidth>
                {dictionary.Login.Login[language]}
              </MDButton>
            </MDBox>
            <MDBox mt={3} mb={1} textAlign="center">
              <MDTypography variant="button" color="text">
                {dictionary.Login.NoAccount[language]}{" "}
                <MDTypography
                  component={Link}
                  to="/register"
                  variant="button"
                  color="info"
                  fontWeight="medium"
                  textGradient
                >
                  {dictionary.Login.CreateAccount[language]}
                </MDTypography>
              </MDTypography>
            </MDBox>
          </MDBox>
        </MDBox>
      </Card>
    </OnePageLayout>
  );
};