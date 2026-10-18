import {defineConfig} from '@playwright/test';
// Keep Chromium's shared memory (fetch/WebSocket data pipes, compositor and decoded
// images) on the dedicated /dev/shm tmpfs. Playwright's default
// --disable-dev-shm-usage moves it into TMPDIR=/tmp, which campaigns and test
// suites fill; a near-full /tmp then fails requests with
// net::ERR_INSUFFICIENT_RESOURCES (docs/reports/lab-chromium-resources-v1.md).
export default defineConfig({testDir:'./tests',workers:1,timeout:180_000,use:{baseURL:process.env.PALIMPSEST_LAB_URL??'http://127.0.0.1:8765',headless:true,viewport:{width:1440,height:1050},launchOptions:{executablePath:process.env.PALIMPSEST_BROWSER??'/usr/bin/chromium',args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']},screenshot:'only-on-failure',trace:'retain-on-failure'},reporter:'list'});
