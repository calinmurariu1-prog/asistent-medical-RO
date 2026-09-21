import {defineConfig, devices} from "@playwright/test";
export default defineConfig({testDir:"./tests",testMatch:"**/*.spec.ts",workers:1,timeout:45000,
 use:{baseURL:process.env.E2E_URL||"http://localhost:3012",channel:process.env.CI?undefined:"msedge",trace:"retain-on-failure",screenshot:"only-on-failure"},
 projects:[{name:"desktop",use:{viewport:{width:1440,height:1000}}},
 {name:"iphone",use:{...devices["iPhone 13"],defaultBrowserType:"chromium"}},
 {name:"android",use:{...devices["Pixel 7"]}}]});
