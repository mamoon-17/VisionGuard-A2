const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const remote='https://dagshub.com/mamoon-17/VisionGuard-A2.mlflow/';
const shots=[
 ['local-toy-fast','http://127.0.0.1:5001/#/experiments/1/runs/2c4dcc84fa9740f5b9981c424b673e65?workflowType=machine_learning'],
 ['local-toy-slow','http://127.0.0.1:5001/#/experiments/1/runs/ee4a21dbff2642959e713f19fa68b8a3?workflowType=machine_learning'],
 ['dagshub-project','https://dagshub.com/mamoon-17/VisionGuard-A2'],
 ['remote-toy',remote+'#/experiments/0/runs/ec83a126b74c4a068cb5a90f305b44bc'],
 ['remote-manual',remote+'#/experiments/1/runs/2e7bb40dd99f47a3a6425350387f0501'],
 ['remote-autolog',remote+'#/experiments/1/runs/47cc78ea0bb847b3a61ee4c2d687283f'],
 ['remote-artifacts',remote+'#/experiments/1/runs/47cc78ea0bb847b3a61ee4c2d687283f/artifacts'],
];
for(const [name,url] of shots){
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:90000});await page.waitForTimeout(10000);
 const got=page.getByRole('button',{name:'Got it',exact:true});if(await got.count())await got.click();
 await page.screenshot({path:`evidence/${name}.png`,fullPage:false});
 console.log(name,page.url(),(await page.locator('body').innerText()).slice(0,5500));
}
await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
