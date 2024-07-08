/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, useNavigate } from "react-router-dom";
import App from "App";

import { ThemeProvider } from "@mui/material/styles";
import {
  CssBaseline,
} from "@mui/material";

import LoadingProgress from "components/LoadingProgress";

import theme from "assets/theme";
import themeDark from "assets/theme-dark";

import { PlatformContextProvider } from "context.js";
import "assets/fontawesome/css/all.min.css";

import { usePlatformContext, setContextState } from "context.js";
import { SessionController } from "database/session-control";

function Main() {
  const navigate = useNavigate();

  const [controller, dispatch] = usePlatformContext();
  const { user, layout } = controller;

  const [sessionReady, setSessionReady] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let server = window.location.protocol + "//" + window.location.hostname;
    SessionController.verifyServerAddress(server).then(async (connectionState) => {
      let sessionStates = {};
      if (connectionState) {
        sessionStates = await SessionController.syncSession();
      } else if (server === "") {
        // Regardless of condition, reset Auth Token if we cannot connect to the first serverAddress in cache.
        if (window.location.protocol == "http:") {
          if (await SessionController.verifyServerAddress(window.location.protocol + "//" + window.location.hostname + ":3001")) {
            sessionStates = await SessionController.syncSession();
          }
        }
      }

      for (let key of Object.keys(sessionStates)) {
        setContextState(dispatch, key, sessionStates[key]);
      }
      setSessionReady(true);
    });
  }, []);

  useEffect(() => {
    if (sessionReady) {
      if (Object.keys(user).length == 0) {
        setContextState(dispatch, "report", "");
        setContextState(dispatch, "participant_uid", null);
      }
      setInitialized(true);
      return;
    }

    const sessionTimeout = setTimeout(() => {
      setContextState(dispatch, "user", {});
      setContextState(dispatch, "report", "");
      setContextState(dispatch, "participant_uid", null);
      setInitialized(true);
    }, 5000);

    return () => clearTimeout(sessionTimeout);
  }, [sessionReady])

  const updateToken = () => {
    const usr = SessionController.getUser();
    if (Object.keys(usr).length == 0) return;
    SessionController.refreshAuthToken().then((response) => {
      if (response.status != 200) {
        SessionController.nullifyUser();
      }
    });
  };

  useEffect(() => {
    let authWatchdog = setInterval(updateToken, 10*60*1000);
    updateToken();
    
    return () => {
      clearInterval(authWatchdog);
    };
  }, [user])

  return initialized ? (
    <App />
  ) : (
    <LoadingProgress message={"Initializing"} />
  )
}

const root = createRoot(document.getElementById("root"))
root.render(
  <BrowserRouter>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PlatformContextProvider initialStates={{
        language: "en",
        user: {}
      }}>
        <Main />
      </PlatformContextProvider>
    </ThemeProvider>
  </BrowserRouter>,
);
