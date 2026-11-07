// Actual browser screenshots; never render command logs as screenshots.
const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:1040}});
  const page = await context.newPage();
  const url=process.argv[2];
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForTimeout(12000);
  if(process.argv[4]==='training') {
    await page.getByText('Model training',{exact:true}).first().click();
    await page.waitForTimeout(6000);
  }
  if(process.argv[3]) await page.screenshot({path:process.argv[3],fullPage:true});
  console.log('URL:',page.url());
  console.log((await page.locator('body').innerText()).slice(0,18000));
  console.log('LINKS',await page.locator('a').evaluateAll(as=>as.map(a=>[a.innerText,a.getAttribute('href')]).filter(x=>x[0]).slice(0,80)));
  await browser.close();
})().catch(error=>{console.error(error.message);process.exit(1)});
