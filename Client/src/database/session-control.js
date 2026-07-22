/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import axios from "axios";

import { ERRORCODE } from "./api-codes";
import { dictionary } from "assets/translation.js";
import MuiAlertDialog from "components/MuiAlertDialog"

//import { Manager } from "socket.io-client"

const timezoneNameDict = {
  "UTC-12:00": "Etc/GMT+12",
  "UTC-11:00": "Etc/GMT+11",
  "UTC-10:00": "Etc/GMT+10",
  "UTC-09:30": "Pacific/Marquesas",
  "UTC-09:00": "Etc/GMT+9",
  "UTC-08:00": "Etc/GMT+8",
  "UTC-07:00": "Etc/GMT+7",
  "UTC-06:00": "Etc/GMT+6",
  "UTC-05:00": "Etc/GMT+5",
  "UTC-04:00": "Etc/GMT+4",
  "UTC-03:30": "America/St_Johns",
  "UTC-03:00": "Etc/GMT+3",
  "UTC-02:00": "Etc/GMT+2",
  "UTC-01:00": "Etc/GMT+1",
  "UTC+00:00": "Etc/GMT",
  "UTC+01:00": "Etc/GMT-1",
  "UTC+02:00": "Etc/GMT-2",
  "UTC+03:00": "Etc/GMT-3",
  "UTC+03:30": "Iran",
  "UTC+04:00": "Etc/GMT-4",
  "UTC+04:30": "Asia/Kabul",
  "UTC+05:00": "Etc/GMT-5",
  "UTC+05:30": "Asia/Colombo",
  "UTC+05:45": "Asia/Kathmandu",
  "UTC+06:00": "Etc/GMT-6",
  "UTC+06:30": "Asia/Yangon",
  "UTC+07:00": "Etc/GMT-7",
  "UTC+08:00": "Etc/GMT-8",
  "UTC+09:00": "Etc/GMT-9",
  "UTC+09:30": "Australia/Darwin",
  "UTC+10:00": "Etc/GMT-10",
  "UTC+10:30": "Australia/LHI",
  "UTC+11:00": "Etc/GMT-11",
  "UTC+12:00": "Etc/GMT-12",
  "UTC+13:00": "Etc/GMT-13",
  "UTC+14:00": "Etc/GMT-14"
};

const timezoneOffsetDict={
  "UTC-12:00": -12*3600000,
  "UTC-11:00": -11*3600000,
  "UTC-10:00": -10*3600000,
  "UTC-09:30": -9*3600000-30*60000,
  "UTC-09:00": -9*3600000,
  "UTC-08:00": -8*3600000,
  "UTC-07:00": -7*3600000,
  "UTC-06:00": -6*3600000,
  "UTC-05:00": -5*3600000,
  "UTC-04:00": -4*3600000,
  "UTC-03:30": -3*3600000-30*60000,
  "UTC-03:00": -3*3600000,
  "UTC-02:00": -2*3600000,
  "UTC-01:00": -1*3600000,
  "UTC+00:00": 0,
  "UTC+01:00": 1*3600000,
  "UTC+02:00": 2*3600000,
  "UTC+03:00": 3*3600000,
  "UTC+03:30": 3*3600000+30*60000,
  "UTC+04:00": 4*3600000,
  "UTC+04:30": 4*3600000+30*60000,
  "UTC+05:00": 5*3600000,
  "UTC+05:30": 5*3600000+30*60000,
  "UTC+05:45": 5*3600000+45*60000,
  "UTC+06:00": 6*3600000,
  "UTC+06:30": 6*3600000+30*60000,
  "UTC+07:00": 7*3600000,
  "UTC+08:00": 8*3600000,
  "UTC+09:00": 9*3600000,
  "UTC+09:30": 9*3600000+30*60000,
  "UTC+10:00": 10*3600000,
  "UTC+10:30": 10*3600000+30*60000,
  "UTC+11:00": 11*3600000,
  "UTC+12:00": 12*3600000,
  "UTC+13:00": 13*3600000,
  "UTC+14:00": 14*3600000
};

export const SessionController = (function () {
  let server = "";
  let connectionStatus = false;

  let synced = false;
  let session = {language: "en"};
  let user = {};
  let serverVersion = "";
  let decryptionPassword = null;
  let decryptionShift = 0;

  const setServer = (address) => {
    server = address;
    localStorage.setItem("serverAddress", server);
  };

  const getServer = () => {
    return server;
  };

  const setDecryptionPassword = (password, shift) => {
    if (password == "") {
      decryptionPassword = null;
      decryptionShift = 0;
      return;
    };

    /* eslint no-undef: */
    decryptionPassword = new fernet.Secret(password);
    decryptionShift = shift;
  };

  const decodeMessage = (text) => {
    if (!decryptionPassword) return text;

    /* eslint no-undef: */
    var token = new fernet.Token({
      secret: decryptionPassword,
      token: text,
      ttl: 0
    });
    try {
      token.decode();
      return token.message;
    } catch {
      return text;
    }
  };

  const decodeTimestamp = (time) => {
    return Math.round(time + decryptionShift);
  }

  const getConnectionStatus = () => {
    return {
      version: serverVersion,
      status: connectionStatus
    };
  };

  const getDownloadLink = (url, form) => {
    let href = url;
    href += "?";
    for (let key in form) {
      href += key + "=";
      href += form[key] + "&"
    }
    
    return href.slice(0,-1);
  };

  const retrieveData = (url) => {
    let csrftoken = ""
    if (document.querySelector('[name=csrfmiddlewaretoken]')) {
      csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    return axios.get(server + url, {
      headers: {
        "X-CSRFToken": csrftoken
      },
      responseType: "arraybuffer"
    });
  };

  const get = (url) => {
    let csrftoken = ""
    if (document.querySelector('[name=csrfmiddlewaretoken]')) {
      csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    return axios.get(server + url, {
      headers: {
        "X-CSRFToken": csrftoken
      }
    });
  };

  const query = (url, form, config, timeout, responseType) => {
    let csrftoken = ""
    if (document.querySelector('[name=csrfmiddlewaretoken]')) {
      csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    return axios.post(server + url, form, {
      timeout: timeout,
      responseType: responseType,
      headers: {
        ...config,
        "X-CSRFToken": csrftoken
      }
    });
  };

  const displayError = (error, setAlert, redirect) => {
    if (typeof(error) === "string" && setAlert) {
      setAlert(
        <MuiAlertDialog title={"ERROR"} message={error}
          handleClose={() => setAlert()} 
          handleConfirm={() => redirect ? redirect() : setAlert()}/>
      );
      return;
    }

    if (setAlert && error.response) {
      var errorMessage = dictionary.ErrorMessage.UNKNOWN_ERROR[session.language];
      if (error.response.status === 500) {
        errorMessage = dictionary.ErrorMessage.INTERNAL_SERVER_ERROR[session.language];
      } else if (error.response.status === 405) {
        errorMessage = dictionary.ErrorMessage.ENDPOINT_NOT_EXIST[session.language];
      } else if (error.response.status === 404) {
        errorMessage = dictionary.ErrorMessage.ENDPOINT_NOT_EXIST[session.language];
      } else if (error.response.status === 403) {
        errorMessage = dictionary.ErrorMessage.PERMISSION_DENIED[session.language];
      } else if (error.response.status === 400) {
        for (var key of Object.keys(ERRORCODE)) {
          if (ERRORCODE[key] == error.response.data.code) {
            errorMessage = dictionary.ErrorMessage[key][session.language];
            break;
          }
        }
        if (error.response.data.message) {
          errorMessage = error.response.data.message;
        } else if (errorMessage == dictionary.ErrorMessage.UNKNOWN_ERROR[session.language]) {
          console.log(error.response.data);
        }
      } else if (error.response.status == 401) {
        errorMessage = dictionary.ErrorMessage["CONNECTION_TIMEDOUT"][session.language]
      } else {
        console.log(error);
      }
      setAlert(
        <MuiAlertDialog title={"ERROR"} message={errorMessage}
          handleClose={() => setAlert()} 
          handleConfirm={() => redirect ? redirect() : setAlert()}/>
      );
    } else {
      console.log(error);
      setAlert(
        <MuiAlertDialog title={"ERROR"} message={"Client Javascript Error"}
          handleClose={() => setAlert()} 
          handleConfirm={() => redirect ? redirect() : setAlert()}/>
      );
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
    localStorage.setItem("sessionContext", JSON.stringify(session));

    session["TimeSeriesAnalysisLayout"] = {};

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

  const setSession = (type, value, update) => {
    if (update) query("/api/updateSessions", {[type]: value}).catch((error) => console.log(error));
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

  const getTimezoneName = (UTCTime) => {
    return timezoneNameDict[UTCTime] ? {timeZone: timezoneNameDict[UTCTime]} : {};
  }

  const getTimezoneOffset = (startTime, UTCTime) => {
    const localOffset = new Date(startTime).getTimezoneOffset() * -60000
    return timezoneOffsetDict[UTCTime] === undefined ? 0 : (localOffset - timezoneOffsetDict[UTCTime]);
  }

  const authenticate = (username, password, rememberMe) => {
    return query("/api/login", {Email: username, Password: password, Persistent: rememberMe ? true : false});
  };

  const register = (username, email, password, institute) => {
  };

  const logout = () => {
    return query("/api/logout");
  };

  const nullifyUser = () => {
    user = {};
    session = {};
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

  const setParticipantUID = (id) => {
    session.participant_uid = id;
    return true;
  };

  const setPageIndex = (type, index) => {
    setSession(type+"PageIndex", index, false);
  };

  return {
    setServer: setServer,
    getServer: getServer,
    setDecryptionPassword: setDecryptionPassword,
    decodeTimestamp: decodeTimestamp,
    decodeMessage: decodeMessage,
    getConnectionStatus: getConnectionStatus,

    getDownloadLink: getDownloadLink,
    query: query,
    retrieveData: retrieveData,
    get: get,
    displayError: displayError,
    syncSession: syncSession,
    getSession: getSession,
    setSession: setSession,

    getDateTimeOptions: getDateTimeOptions,
    getTimezoneName: getTimezoneName,
    getTimezoneOffset: getTimezoneOffset,

    isSynced: isSynced,

    authenticate: authenticate,
    register: register,
    nullifyUser: nullifyUser,
    logout: logout,
    getUser: getUser,
    setUser: setUser,

    setParticipantUID: setParticipantUID,
    setPageIndex: setPageIndex
  }

})();