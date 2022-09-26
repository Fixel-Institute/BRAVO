import React from "react";

import { SessionController } from "database/session-control";

const PlatformContext = React.createContext();
PlatformContext.displayName = "UF BRAVO Platform Context"

function reducer(state, action) {
  SessionController.setSession(action.name, action.value);
  return { ...state, [action.name]: action.value};
}

function PlatformContextProvider({initialStates, children}) {
  const [controller, dispatch] = React.useReducer(reducer, initialStates);
  const value = React.useMemo(() => [controller, dispatch], [controller, dispatch]);
  return <PlatformContext.Provider value={value}> {children} </PlatformContext.Provider>;
}

function usePlatformContext() {
  const context = React.useContext(PlatformContext);
  if (!context) {
    throw new Error();
  }
  return context;
}

function setContextState(dispatch, name, value) {
  dispatch({name: name, value: value});
}

export {
  PlatformContextProvider,
  usePlatformContext,
  setContextState,
}