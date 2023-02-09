import { useState, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "App";

import { PlatformContextProvider } from "context.js";

function Main() {
  return <PlatformContextProvider initialStates={{
    language: "en",
    user: {}
  }}>
    <App />
  </PlatformContextProvider>
}

const root = ReactDOM.createRoot(document.getElementById("root"))
root.render(
  <BrowserRouter>
    <Main />
  </BrowserRouter>,
);
