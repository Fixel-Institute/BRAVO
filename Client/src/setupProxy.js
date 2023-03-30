/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  app.use("/api", createProxyMiddleware({
    target: "http://localhost:3001",
    changeOrigin: true,
  }));

  app.use("/documentation", createProxyMiddleware({
    target: "http://localhost:3001",
    changeOrigin: true,
  }));

  app.use("/mobile", createProxyMiddleware({
    target: "http://localhost:3001",
    changeOrigin: true,
  }));

  app.use(createProxyMiddleware("/socket", {
    target: "http://localhost:3001",
    changeOrigin: true,
    ws: true
  }));
};