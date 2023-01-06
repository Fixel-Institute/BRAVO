import { useState, useEffect } from "react";

// react-router-dom components
import { Link, useNavigate } from "react-router-dom";

// @mui material components
import {
  Card, 
  Checkbox
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

// Layout
import OnePageLayout from "layouts/OnePage";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";

export default function Register() {
  const [context, dispatch] = usePlatformContext();
  const { language, user } = context;

  const navigate = useNavigate();

  const [alert, setAlert] = useState(null);
  const [authInfo, setAuthInfo] = useState({email: "", password: ""});
  const [rememberMe, setRememberMe] = useState(false);

  const handleRegistration = () => {
    SessionController.register(authInfo.username, authInfo.email, authInfo.password, authInfo.email).then((response) => {
      SessionController.setUser(response.data.user);
      SessionController.setAuthToken(response.data.token);
      SessionController.syncSession();
      setAuthInfo({...authInfo, password: ""});
      setContextState(dispatch, "user", response.data.user);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  useEffect(() => {
    if (Object.keys(user).length > 0) {
      navigate("/dashboard", {replace: false});
    }
  }, [user]);

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
            {dictionary.Register.AccountRegister[language]}
          </MDTypography>
        </MDBox>
        <MDBox pt={4} pb={3} px={3}>
          <MDBox component="form" role="form">
            <MDBox mb={2}>
              <MDInput type="text" label={dictionary.Register.UserName[language]} value={authInfo.username} onChange={(event) => setAuthInfo({...authInfo, username: event.currentTarget.value})} fullWidth/>
            </MDBox>
            <MDBox mb={2}>
              <MDInput type="email" label={dictionary.Register.Email[language]} value={authInfo.email} onChange={(event) => setAuthInfo({...authInfo, email: event.currentTarget.value})} fullWidth/>
            </MDBox>
            <MDBox mb={2}>
              <MDInput type="password" label={dictionary.Register.Password[language]} value={authInfo.password} onChange={(event) => setAuthInfo({...authInfo, password: event.currentTarget.value})} fullWidth/>
            </MDBox>
            <MDBox display="flex" alignItems="center" ml={-1}>
              <Checkbox value={rememberMe} onClick={() => setRememberMe(!rememberMe)} />
              <MDTypography
                variant="button"
                fontWeight="regular"
                color="text"
                sx={{ cursor: "pointer", userSelect: "none", ml: -1 }}
              >
                {dictionary.Register.Agree[language]}
              </MDTypography>
              <MDTypography
                component="a"
                href="#"
                variant="button"
                fontWeight="bold"
                color="info"
                textGradient
              >
                {dictionary.Register.Disclaimer[language]}
              </MDTypography>
            </MDBox>
            <MDBox mt={4} mb={1}>
              <MDButton variant="gradient" color="info" onClick={handleRegistration} fullWidth>
                {dictionary.Register.Register[language]}
              </MDButton>
            </MDBox>
            <MDBox mt={3} mb={1} textAlign="center">
              <MDTypography variant="button" color="text">
                <MDTypography
                  component={Link}
                  to="/login"
                  variant="button"
                  color="info"
                  fontWeight="medium"
                  textGradient
                >
                  {dictionary.Register.LoginAccount[language]}
                </MDTypography>
              </MDTypography>
            </MDBox>
          </MDBox>
        </MDBox>
      </Card>
    </OnePageLayout>
  );
};