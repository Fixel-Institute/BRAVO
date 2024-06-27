/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect, Suspense, lazy } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";

import MDBox from "components/MDBox";
import SideMenu from "components/SideMenu";
import LoadingProgress from "components/LoadingProgress";

// Platform Components
import HomePage from "views/HomePage.js";
import SignIn from "views/Authentication/SignIn";
import Register from "views/Authentication/Register";
import SurveyEditor from "views/Survey/Editor";
import SurveyViewer from "views/Survey/Viewer";
import InertiaSensorViewer from "views/InertiaSensorViewer";

import { usePlatformContext, setContextState } from "context.js";
import { SessionController } from "database/session-control";
import Logo from "assets/img/logo.png";

import routes from "routes";
import Profile from "views/Dashboard/Profile";
import LocalUpdaterView from "views/LocalUpdater";

export default function App() {
  const [controller, dispatch] = usePlatformContext();
  const {
    user,
    hideSidenav,
    miniSidenav,
    layout,
    sidenavColor,
    darkMode,
  } = controller;
  const [onMouseEnter, setOnMouseEnter] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
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

  return <>
    {layout === "dashboard" && (
      <>
        <SideMenu
          color={sidenavColor}
          brand={Logo}
          brandName="UF BRAVO Platform"
          routes={routes}
          onMouseEnter={handleOnMouseEnter}
          onMouseLeave={handleOnMouseLeave}
        />
      </>
    )}
    <Suspense fallback={<LoadingProgress/>}>
      <Routes>
        <Route path="/index" element={<HomePage />} />
        <Route path="/login" element={<SignIn />} />
        <Route path="/register" element={<Register />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/updater" element={<LocalUpdaterView />} />
        {getRoutes(routes)}
        <Route path="/inertiaSensorViewer" element={<InertiaSensorViewer />} />
        <Route path="/reports/*" element={<Navigate to="/patient-overview" />} />
        <Route path="/experimental/*" element={<Navigate to="/patient-overview" />} />
        <Route exact path="/survey/:surveyId/edit" element={<SurveyEditor />} />
        <Route exact path="/survey/:surveyId" element={<SurveyViewer />} />
        <Route path="*" element={<Navigate to="/index" />} />
      </Routes>
    </Suspense>
  </>
}
