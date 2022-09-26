import { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { BrowserRouter } from "react-router-dom";
import App from "App";

// Material Dashboard 2 PRO React Context Provider
import { PlatformContextProvider } from "context.js";

// Session Sync
import { SessionController } from "database/session-control.js";

function Main() {
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    if (!synced) {
      SessionController.syncSession().then((result) => {
        setSynced(result);
      });
    }
  }, []);

  return synced ? (
    <PlatformContextProvider initialStates={SessionController.getSession()}>
      <App />
    </PlatformContextProvider>
  ) : null;
}

ReactDOM.render(
  <BrowserRouter>
    <Main />
  </BrowserRouter>,
  document.getElementById("root")
);
