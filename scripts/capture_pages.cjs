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
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  const close=page.getByRole('button',{name:/^(close|dismiss|not now)$/i});
  if(await close.count()) await close.first().click();
  if(process.argv[4]==='training') {
    const got = page.getByRole('button',{name:'Got it',exact:true});
    if(await got.count()) await got.click();
    await page.getByText('Model training',{exact:true}).first().click();
    await page.waitForTimeout(6000);
  }
  if(process.argv[4]==='metrics') {
    await page.getByText('Model metrics',{exact:true}).click();
    await page.waitForTimeout(9000);
  }
  if(process.argv[4]==='curves') {
    const run=page.url().match(/\/runs\/([^/?#]+)/)[1];
    const origin=page.url().split('#')[0];
    const params=new URLSearchParams({runs:JSON.stringify([run]),experiments:'["1"]',metric:'"val_loss"',
      plot_metric_keys:JSON.stringify(['loss','val_loss','accuracy','val_accuracy']),plot_layout:'{}',
      x_axis:'step',y_axis_scale:'linear',line_smoothness:'1',show_point:'true',deselected_curves:'[]'});
    await page.goto(origin+'#/metric?'+params.toString());await page.waitForTimeout(10000);
  }
  if(process.argv[4]==='artifacts') {
    for(const name of ['evidence','model','splits']){
      await page.getByText(name,{exact:true}).first().click();
      await page.waitForTimeout(500);
    }
  }
  if(process.argv[4]==='compare') {
    const confirm = page.getByRole('button',{name:'Confirm',exact:true});
    if(await confirm.count()) await confirm.click();
    const got=page.getByRole('button',{name:'Got it',exact:true});if(await got.count()) await got.click();
    console.log('CHECKBOXES',await page.getByRole('checkbox').count());
    console.log('BOXDETAILS',await page.getByRole('checkbox').evaluateAll(bs=>bs.map(b=>({html:b.outerHTML,rect:b.getBoundingClientRect().toJSON()}))));
    const boxes=page.locator('input[type=checkbox]:visible');
    await boxes.first().check();
    console.log('BUTTONS',await page.getByRole('button').allTextContents());
    const compare=page.getByRole('button',{name:/Compare/}).first();
    await compare.click();await page.waitForTimeout(9000);
  }
  if(process.argv[3]) await page.screenshot({path:process.argv[3],fullPage:true});
  console.log('URL:',page.url());
  console.log((await page.locator('body').innerText()).slice(0,18000));
  console.log('LINKS',await page.locator('a').evaluateAll(as=>as.map(a=>[a.innerText,a.getAttribute('href')]).filter(x=>x[0]).slice(0,80)));
  await browser.close();
})().catch(error=>{console.error(error.message);process.exit(1)});
