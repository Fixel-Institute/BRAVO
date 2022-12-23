import { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "App";

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

const root = ReactDOM.createRoot(document.getElementById("root"))
root.render(
  <BrowserRouter>
    <Main />
  </BrowserRouter>,
);
