export const config = {
  runner: "local",
  specs: ["./e2e/**/*.e2e.js"],
  maxInstances: 1,
  baseUrl: "http://127.0.0.1:4173",
  logLevel: "error",
  waitforTimeout: 10000,
  connectionRetryTimeout: 120000,
  connectionRetryCount: 1,
  framework: "mocha",
  reporters: ["spec"],
  mochaOpts: {
    ui: "bdd",
    timeout: 60000,
  },
  services: ["chromedriver"],
  capabilities: [
    {
      browserName: "chrome",
      "goog:chromeOptions": {
        args: ["--headless=new", "--disable-gpu", "--window-size=1400,1000"],
      },
    },
  ],
};
