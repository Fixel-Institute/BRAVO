import axios from "axios";
import cookie from "react-cookies";

import { ERRORCODE } from "./api-codes";
import { dictionary } from "assets/translation.js";
import MuiAlertDialog from "components/MuiAlertDialog"

//import { Manager } from "socket.io-client"

export const SessionController = (function () {
  var synced = false;

  var session = {language: "en"};
  var user = {};

  const getCSRFToken = () => {
    return cookie.load("csrftoken");
  };

  const query = async (url, form) => {
    axios.defaults.headers.post["X-CSRFToken"] = cookie.load("csrftoken");
    axios.defaults.headers.post["Content-Type"] = "application/json";
    axios.defaults.headers.post["Accept"] = "application/json";
    return axios.post(url, form);
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
    if (!synced) {
      try {
        const response = await query("/api/querySessions", {});
        session = response.data.session;
        user = response.data.user;
        synced = true;
        return synced;
      } catch (error) {
        console.log(error);
      }
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

  const getPatientInfo = async () => {
    return query("/api/queryPatientInfo", {id: session.patientID});
  };

  const getTherapyHistory = async () => {
    try {
      const response = await SessionController.query("/api/queryTherapyHistory", {id: session.patientID});
      return({state: true, data: response.data});

    } catch (error) {
      if (error.response.status === 400) {
        const errorCode = error.response.data.code;
        if (errorCode === ERRORCODE.IMPROPER_SUBMISSION) {
          return({state: false, error: "IMPROPER_SUBMISSION"});
        } else if (errorCode === ERRORCODE.MALFORMATED_REQUEST) {
          return({state: false, error: "MALFORMATED_REQUEST"});
        }
      } else if (error.response.status === 500) {
        return({state: false, error: "INTERNAL_SERVER_ERROR"});
      } else if (error.response.status === 403) {
        return({state: false, error: "PERMISSION DENIED"});
      } else {
        return({state: false, error: "UNKNOWN_ERROR"});
      }
    }
  };

  const getSurveyData = async (ssr) => {
    try {
      const response = await SessionController.query("/api/queryBrainSenseSurveys", {id: session.patientID});
      return({state: true, data: response.data});

    } catch (error) {
      if (error.response.status === 400) {
        const errorCode = error.response.data.code;
        if (errorCode === ERRORCODE.IMPROPER_SUBMISSION) {
          return({state: false, error: "IMPROPER_SUBMISSION"});
        } else if (errorCode === ERRORCODE.MALFORMATED_REQUEST) {
          return({state: false, error: "MALFORMATED_REQUEST"});
        }
      } else if (error.response.status === 500) {
        return({state: false, error: "INTERNAL_SERVER_ERROR"});
      } else if (error.response.status === 403) {
        return({state: false, error: "PERMISSION DENIED"});
      } else {
        return({state: false, error: "UNKNOWN_ERROR"});
      }
    }
  };

  const getStreamingOverview = (ssr) => {
    return SessionController.query("/api/queryBrainSenseStreaming", {id: session.patientID, requestOverview: true});
  };

  const getStreamingData = async (recordingId, ssr) => {
    try {
      const response = await SessionController.query("/api/queryBrainSenseStreaming", {id: session.patientID, recordingId: recordingId, requestData: true});
      return({state: true, data: response.data});

    } catch (error) {
      if (error.response.status === 400) {
        const errorCode = error.response.data.code;
        if (errorCode === ERRORCODE.IMPROPER_SUBMISSION) {
          return({state: false, error: "IMPROPER_SUBMISSION"});
        } else if (errorCode === ERRORCODE.MALFORMATED_REQUEST) {
          return({state: false, error: "MALFORMATED_REQUEST"});
        } else if (errorCode === ERRORCODE.DATA_NOT_FOUND) {
          return({state: false, error: "DATA_NOT_FOUND"});
        }
      } else if (error.response.status === 500) {
        return({state: false, error: "INTERNAL_SERVER_ERROR"});
      } else if (error.response.status === 403) {
        return({state: false, error: "PERMISSION DENIED"});
      } else {
        return({state: false, error: "UNKNOWN_ERROR"});
      }
    }
  };

  const getMontageOverview = async (ssr) => {
    try {
      const response = await SessionController.query("/api/queryIndefiniteStreaming", {id: session.patientID, requestOverview: true});
      return({state: true, data: response.data});

    } catch (error) {
      if (error.response.status === 400) {
        const errorCode = error.response.data.code;
        if (errorCode === ERRORCODE.IMPROPER_SUBMISSION) {
          return({state: false, error: "IMPROPER_SUBMISSION"});
        } else if (errorCode === ERRORCODE.MALFORMATED_REQUEST) {
          return({state: false, error: "MALFORMATED_REQUEST"});
        }
      } else if (error.response.status === 500) {
        return({state: false, error: "INTERNAL_SERVER_ERROR"});
      } else if (error.response.status === 403) {
        return({state: false, error: "PERMISSION DENIED"});
      } else {
        return({state: false, error: "UNKNOWN_ERROR"});
      }
    }
  };

  const getMontageData = async (devices, timestamps, ssr) => {
    try {
      const response = await SessionController.query("/api/queryIndefiniteStreaming", {id: session.patientID, requestData: true, devices: devices, timestamps: timestamps});
      return({state: true, data: response.data});

    } catch (error) {
      if (error.response.status === 400) {
        const errorCode = error.response.data.code;
        if (errorCode === ERRORCODE.IMPROPER_SUBMISSION) {
          return({state: false, error: "IMPROPER_SUBMISSION"});
        } else if (errorCode === ERRORCODE.MALFORMATED_REQUEST) {
          return({state: false, error: "MALFORMATED_REQUEST"});
        }
      } else if (error.response.status === 500) {
        return({state: false, error: "INTERNAL_SERVER_ERROR"});
      } else if (error.response.status === 403) {
        return({state: false, error: "PERMISSION DENIED"});
      } else {
        return({state: false, error: "UNKNOWN_ERROR"});
      }
    }
  };

  const getChronicData = (ssr) => {
    return SessionController.query("/api/queryChronicBrainSense", {id: session.patientID, requestData: true, timezoneOffset: new Date().getTimezoneOffset()*60});
  };

  return {
    getCSRFToken: getCSRFToken,
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
    getTherapyHistory: getTherapyHistory,
    getSurveyData: getSurveyData,
    getStreamingOverview: getStreamingOverview,
    getStreamingData: getStreamingData,
    getMontageOverview: getMontageOverview,
    getMontageData: getMontageData,
    getChronicData: getChronicData,
  }

})();