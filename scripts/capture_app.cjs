const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1350,height:900}});
 const base=process.argv[2]||'http://127.0.0.1:5002';
 const prefix=process.argv[3]||'app';
 await page.goto(base);await page.screenshot({path:`evidence/${prefix}-upload.png`});
 const rows=fs.readFileSync('splits/validation.csv','utf8').trim().split(/\r?\n/).slice(1).map(x=>x.split(','));
 console.log('columns',fs.readFileSync('splits/validation.csv','utf8').split(/\r?\n/)[0]);
 const header=fs.readFileSync('splits/validation.csv','utf8').split(/\r?\n/)[0].split(',');
 const pi=header.indexOf('path'),li=header.indexOf('label');
 for(const label of ['0','1']){
   const row=rows.find(r=>r[li]===label && fs.statSync(path.resolve('cashbowman/ai-generated-images-vs-real-images/versions/1',r[pi])).size<4*1024*1024);
   await page.goto(base); await page.locator('input[type=file]').setInputFiles(path.resolve('cashbowman/ai-generated-images-vs-real-images/versions/1',row[pi]));
   await page.locator('button[type=submit]').click();await page.waitForURL('**/predict');
   await page.screenshot({path:`evidence/${prefix}-result-${label}.png`}); console.log(await page.locator('body').innerText());
 }
 for(const [name,buffer,mime,filename] of [
  ['type',Buffer.from('text'),'text/plain','wrong.txt'],
  ['decode',Buffer.from('not a real png'),'image/png','broken.png'],
  ['size',Buffer.alloc(6*1024*1024,120),'image/png','oversized.png']]){
  await page.goto(base); await page.locator('input[type=file]').setInputFiles({name:filename,mimeType:mime,buffer});
  await page.locator('button[type=submit]').click(); await page.waitForURL('**/predict');
  await page.screenshot({path:`evidence/${prefix}-error-${name}.png`}); console.log(name,await page.locator('body').innerText());
 }
 await page.goto(base+'/history');await page.screenshot({path:`evidence/${prefix}-history.png`,fullPage:true});
 await page.goto(base+'/health');await page.screenshot({path:`evidence/${prefix}-health.png`});
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
