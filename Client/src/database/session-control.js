import axios from "axios";
import cookie from "react-cookies";

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

  const setAuthToken = (token) => {
    authToken = token;
    localStorage.setItem("accessToken", authToken);
  };

  const getAuthToken = () => {
    return authToken;
  };

  const setServer = (address) => {
    server = address;
    localStorage.setItem("serverAddress", server);
  };

  const getServer = () => {
    return server;
  };

  const getConnectionStatus = () => {
    return connectionStatus;
  };

  const query = (url, form, config, timeout) => {
    return axios.post(server + url, form, {
      timeout: timeout,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": authToken === "" ? null : "Token " + authToken,
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
  }

  const syncSession = async () => {
    if (localStorage.getItem("accessToken")) {
      authToken = localStorage.getItem("accessToken");
    }
    
    if (localStorage.getItem("serverAddress")) {
      server = localStorage.getItem("serverAddress");
      try {
        await query("/api/handshake", {}, {}, 2000);
        connectionStatus = true;
      } catch (error) {
        console.log(error);
      }
    } else {
      for (let address of [window.location.protocol + "//" + window.location.hostname + ":3001", "https://bravo-server.jcagle.solutions"]) {
        try {
          server = address;
          await query("/api/handshake", {}, {}, 2000);
          connectionStatus = true;
          break;
        } catch (error) {
          console.log(error);
        }
      }
    }

    if (!connectionStatus) return true;

    try {
      if (localStorage.getItem("sessionContext")) {
        session = JSON.parse(localStorage.getItem("sessionContext"));
      }
      const response = await query("/api/querySessions", {
        session: session,
      });
      session = response.data.session;
      localStorage.setItem("sessionContext", JSON.stringify(session));
      user = response.data.user;
      synced = true;

    } catch (error) {
      if (error.response.status == 401) {
        setAuthToken("");
        const response = await query("/api/querySessions", {});
        session = response.data.session;
        localStorage.setItem("sessionContext", JSON.stringify(session));
        user = response.data.user;
        synced = true;
      }
    }
    return true;
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
    query("/api/updateSession", {[type]: value});
    session[type] = value;
    localStorage.setItem("sessionContext", JSON.stringify(session));
  };

  const getDateTimeOptions = (type) => {
    if (type == "DateFull") {
      return {dateStyle: "full"};
    } else if (type == "DateLong") {
      return {dateStyle: "long"};
    } else if (type == "DateNumeric") {
      return {year: 'numeric', month: 'numeric', day: 'numeric'};
    }  else {
      return {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'}
    }
  };

  const handShake = async () => {
    if (Object.keys(user).length === 0) {
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

  const authenticate = (username, password) => {
    return query("/api/authenticate", {Email: username, Password: password});
  };

  const register = (username, email, password, institute) => {
    return query("/api/registration", {UserName: username, Email: email, Institute: institute, Password: password});
  };

  const logout = () => {
    return query("/api/logout");
  };

  const nullifyUser = () => {
    user = {};
    session = {};
    authToken = "";
    if (localStorage.getItem("accessToken")) {
      localStorage.setItem("accessToken", authToken);
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

  return {
    setAuthToken: setAuthToken,
    getAuthToken: getAuthToken,
    setServer: setServer,
    getServer: getServer,
    getConnectionStatus: getConnectionStatus,

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
  }

})();