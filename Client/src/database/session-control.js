/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import axios from "axios";

import { ERRORCODE } from "./api-codes";
import { dictionary } from "assets/translation.js";
import MuiAlertDialog from "components/MuiAlertDialog"

//import { Manager } from "socket.io-client"

export const SessionController = (function () {
  //let server = "https://bravo-server.jcagle.solutions";
  let server = "";
  let connectionStatus = false;

  let synced = false;
  let session = {language: "en"};
  let user = {};
  let authToken = "";
  let refreshToken = "";
  let serverVersion = "";

  const setAuthToken = (token) => {
    authToken = token;
  };

  const getAuthToken = () => {
    return authToken;
  };

  const setRefreshToken = (token) => {
    refreshToken = token;
    localStorage.setItem("refreshToken", refreshToken);
  };

  const getRefreshToken = () => {
    return refreshToken;
  };

  const setServer = (address) => {
    server = address;
    localStorage.setItem("serverAddress", server);
  };

  const getServer = () => {
    return server;
  };

  const getConnectionStatus = () => {
    return {
      version: serverVersion,
      status: connectionStatus
    };
  };

  const query = (url, form, config, timeout, responseType) => {
    return axios.post(server + url, form, {
      timeout: timeout,
      responseType: responseType,
      headers: {
        "Authorization": authToken === "" ? null : "Bearer " + authToken,
        ...config,
      }
    });
  };

  const displayError = (error, setAlert) => {
    if (setAlert && error.response) {
      var errorMessage = dictionary.ErrorMessage.UNKNOWN_ERROR[session.language];
      if (error.response.status === 500) {
        errorMessage = dictionary.ErrorMessage.INTERNAL_SERVER_ERROR[session.language];
      } else if (error.response.status === 404) {
        errorMessage = dictionary.ErrorMessage.ENDPOINT_NOT_EXIST[session.language];
      } else if (error.response.status === 403) {
        errorMessage = dictionary.ErrorMessage.PERMISSION_DENIED[session.language];
      } else if (error.response.status === 400) {
        for (var key of Object.keys(ERRORCODE)) {
          if (ERRORCODE[key] === error.response.data.code) {
            errorMessage = dictionary.ErrorMessage[key][session.language];
            break;
          }
        }
        if (errorMessage == dictionary.ErrorMessage.UNKNOWN_ERROR[session.language]) {
          console.log(ERRORCODE);
          console.log(error.response.data);
        }
      } else if (error.response.status == 401) {
        setAuthToken("");
        setRefreshToken("");
        errorMessage = dictionary.ErrorMessage["CONNECTION_TIMEDOUT"][session.language]
      } else {
        console.log(error);
      }
      setAlert(
        <MuiAlertDialog title={"ERROR"} message={errorMessage}
          handleClose={() => setAlert()} 
          handleConfirm={() => setAlert()}/>
      );
    } else {
      console.log(error);
    }
  };

  const verifyServerAddress = async (storedServer) => {
    // Reset Credentials in case of 401
    authToken = "";
    server = storedServer;

    connectionStatus = false;
    try {
      const response = await query("/api/handshake", {}, {}, 2000);
      if (response.status == 200) {
        if (response.data.Version) {
          serverVersion = response.data.Version;
        } else {
          serverVersion = "";
        }
        connectionStatus = true;
      }
    } catch (error) {
      serverVersion = "";
      console.log(error);
    }

    if (connectionStatus) setServer(server);
    return connectionStatus;
  };

  const refreshAuthToken = async () => {
    if (refreshToken === "") return {status: 500};

    try {
      const refreshResponse = await query("/api/authRefresh", {
        refresh: refreshToken
      });
      setAuthToken(refreshResponse.data.access);
      return refreshResponse;
    } catch(error) {
      setAuthToken("");
      setRefreshToken("");
      return error;
    }
  };

  const verifyToken = async (token) => {
    // Token can be empty, which is common if you are not logged in.
    if (token === "") return;

    refreshToken = token;
    const response = await refreshAuthToken();
    if (response.status !== 200) {
      setRefreshToken("");
    }
  };

  const syncSession = async () => {
    if (localStorage.getItem("sessionContext")) {
      session = JSON.parse(localStorage.getItem("sessionContext"));
    }
    const response = await query("/api/querySessions", {
      session: session,
    });
    session = {...session, ...response.data.session};

    if (!Object.keys(session).includes("IndefiniteStreamLayout")) {
      session.BrainSenseSurveyLayout = {};
      session.BrainSensestreamLayout = {};
      session.IndefiniteStreamLayout = {};
      session.ChronicBrainSenseLayout = {};
    }

    localStorage.setItem("sessionContext", JSON.stringify(session));
    user = response.data.user;
    return getSession();
  };

  const isSynced = () => {
    return synced;
  };

  const getSession = () => {
    return {
      ...session,
      user: user,
    }
  };

  const setSession = (type, value) => {
    query("/api/updateSession", {[type]: value}).catch((error) => console.log(error));
    session[type] = value;
    session["lastActive"] = new Date().getTime();
    localStorage.setItem("sessionContext", JSON.stringify(session));
  };

  const getDateTimeOptions = (type) => {
    if (type == "DateFull") {
      return {dateStyle: "full"};
    } else if (type == "DateLong") {
      return {dateStyle: "long"};
    } else if (type == "DateNumeric") {
      return {year: 'numeric', month: 'numeric', day: 'numeric'};
    } else {
      return {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'}
    }
  };

  const handShake = async () => {
    if (Object.keys(user).length === 0 || refreshToken === "") {
      return false;
    }
    
    try {
      await query("/api/handshake");
      return true;
    } catch (error) {
      nullifyUser();
      return false;
    }
  };

  const authenticate = (username, password, rememberMe) => {
    return query("/api/authenticate", {Email: username, Password: password, Persistent: rememberMe ? true : false});
  };

  const register = (username, email, password, institute) => {
    return query("/api/registration", {UserName: username, Email: email, Institute: institute, Password: password});
  };

  const logout = () => {
    return query("/api/logout", {
      refresh: refreshToken,
    });
  };

  const nullifyUser = () => {
    user = {};
    session = {};
    authToken = "";
    if (localStorage.getItem("accessToken")) {
      localStorage.setItem("accessToken", authToken);
    }
    if (localStorage.getItem("refreshToken")) {
      localStorage.setItem("refreshToken", refreshToken);
    }
    if (localStorage.getItem("sessionContext")) {
      localStorage.setItem("sessionContext", session);
    }
  };

  const setUser = (account) => {
    user = account;
  };

  const getUser = () => {
    return user;
  };

  const setPatientID = async (id) => {
    try {
      await query("/api/setPatientID", { id: id });  
      session.patientID = id;
      return true;
    } catch (error) {
      return false;
    }
  };

  const getPatientInfo = (patientID) => {
    return query("/api/queryPatientInfo", {
      id: patientID
    });
  };

  const setPageIndex = (type, index) => {
    setSession(type+"PageIndex", index);
  };

  return {
    setAuthToken: setAuthToken,
    getAuthToken: getAuthToken,
    setRefreshToken: setRefreshToken,
    getRefreshToken: getRefreshToken,
    refreshAuthToken: refreshAuthToken,
    setServer: setServer,
    getServer: getServer,
    getConnectionStatus: getConnectionStatus,

    verifyServerAddress: verifyServerAddress,
    verifyToken: verifyToken,

    query: query,
    displayError: displayError,
    syncSession: syncSession,
    getSession: getSession,
    setSession: setSession,

    getDateTimeOptions: getDateTimeOptions,

    isSynced: isSynced,
    handShake: handShake,

    authenticate: authenticate,
    register: register,
    nullifyUser: nullifyUser,
    logout: logout,
    getUser: getUser,
    setUser: setUser,

    setPatientID: setPatientID,
    getPatientInfo: getPatientInfo,
    setPageIndex: setPageIndex
  }

})();