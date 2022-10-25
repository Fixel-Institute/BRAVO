import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";

// @mui material components
import { ThemeProvider } from "@mui/material/styles";
import {
  CssBaseline,
  Icon,
} from "@mui/material";

// Material Dashboard 2 PRO React components
import MDBox from "components/MDBox";
import Sidenav from "components/Sidenav";

// Material Dashboard 2 PRO React themes
import theme from "assets/theme";
import themeDark from "assets/theme-dark";

// Platform Components
import HomePage from "views/HomePage.js";
import SignIn from "views/Authentication/SignIn";
import Register from "views/Authentication/Register";
import SurveyEditor from "views/Survey/Editor";

import { usePlatformContext, setContextState } from "context.js";
import routes from "routes";

export default function App() {
  const [controller, dispatch] = usePlatformContext();
  const {
    hideSidenav,
    miniSidenav,
    showSidenav,
    layout,
    sidenavColor,
    transparentSidenav,
    whiteSidenav,
    darkMode,
  } = controller;
  const [onMouseEnter, setOnMouseEnter] = useState(false);
  const { pathname } = useLocation();

  // Open sidenav when mouse enter on mini sidenav
  const handleOnMouseEnter = () => {
    if (miniSidenav && !onMouseEnter) {
      setContextState(dispatch, "showSidenav", true);
      setOnMouseEnter(true);
    }
  };

  // Close sidenav when mouse leave mini sidenav
  const handleOnMouseLeave = () => {
    if (window.innerWidth >= 1200) {
      if (miniSidenav && onMouseEnter) {
        setContextState(dispatch, "showSidenav", false);
        setOnMouseEnter(false);
      }
    }
  };

  // Setting page scroll to 0 when changing the route
  useEffect(() => {
    document.documentElement.scrollTop = 0;
    document.scrollingElement.scrollTop = 0;
  }, [pathname]);

  const getRoutes = (allRoutes) => {
    return allRoutes.map((route) => {
      if (route.collapse) {
        return getRoutes(route.collapse);
      }

      if (route.route) {
        return <Route exact path={route.route} element={route.component} key={route.key} />;
      }

      return null;
    });
  }

  return (
    <ThemeProvider theme={darkMode ? themeDark : theme}>
      <CssBaseline />
      {layout === "dashboard" && (
        <>
          <Sidenav
            color={sidenavColor}
            brand={"/images/logo.png"}
            brandName="UF BRAVO Platform"
            routes={routes}
            onMouseEnter={handleOnMouseEnter}
            onMouseLeave={handleOnMouseLeave}
          />
        </>
      )}
      <Routes>
        <Route path="/index" element={<HomePage />} />
        <Route path="/login" element={<SignIn />} />
        <Route path="/register" element={<Register />} />
        {getRoutes(routes)}
        <Route path="/reports/*" element={<Navigate to="/patient-overview" />} />
        <Route path="/experimental/*" element={<Navigate to="/patient-overview" />} />
        <Route exact path="/survey/:surveyId/edit" element={<SurveyEditor />} />
        <Route path="*" element={<Navigate to="/index" />} />
      </Routes>
    </ThemeProvider>
  );
}
