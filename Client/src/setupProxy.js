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

  app.use(createProxyMiddleware("/socket", {
    target: "http://localhost:3001",
    changeOrigin: true,
    ws: true
  }));
};