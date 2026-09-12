const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'./tests/ui',
  timeout:180000,
  expect:{timeout:10000},
  workers:1,
  retries:process.env.CI?1:0,
  reporter:process.env.CI?'github':'list',
  use:{baseURL:'http://127.0.0.1:8767',browserName:'chromium',trace:'retain-on-failure'},
  webServer:{command:'python -m http.server 8767 --directory web',url:'http://127.0.0.1:8767',reuseExistingServer:!process.env.CI}
});
