import axios from "axios";
import cookie from "react-cookies";

import { ERRORCODE } from "./api-codes";
import { dictionary } from "assets/translation.js";
import MuiAlertDialog from "components/MuiAlertDialog"

//import { Manager } from "socket.io-client"

export const SessionController = (function () {
  let server = "https://bravo-server.jcagle.solutions";

  let synced = false;
  let session = {language: "en"};
  let user = {};
  let authToken = "";

  const setAuthToken = (token) => {
    authToken = token;
  };

  const query = async (url, form, config) => {
    return axios.post(server + url, form, {
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
    try {
      const response = await query("/api/querySessions", {});
      session = response.data.session;
      user = response.data.user;
      synced = true;
      return synced;
    } catch (error) {
      console.log(error);
    }
    return synced;
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