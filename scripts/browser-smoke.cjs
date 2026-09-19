/* End-to-end test starts a disposable local service; no production data/token used. */
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawn} = require('node:child_process');
const playwright = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'playwright')) : require('playwright');
const root = path.resolve(__dirname, '..');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'portal-e2e-'));
const port = Number(process.env.PORTAL_TEST_PORT || 18761);
const python = process.env.PORTAL_TEST_PYTHON || 'python3';
const child = spawn(python, ['-m','portal_tsinder','--data-dir',tmp,'serve','--port',String(port)],
  {cwd:root, env:process.env, stdio:['ignore','pipe','pipe']});
let browser;
async function run() {
  let ready=false;
  for(let i=0;i<100;i++) {
    try { const r=await fetch(`http://127.0.0.1:${port}/health`); if(r.ok){ready=true;break;} }catch(_){}
    await new Promise(r=>setTimeout(r,100));
  }
  if(!ready)throw Error('server did not start');
  browser=await playwright.chromium.launch({headless:true,
    executablePath:process.env.PORTAL_CHROMIUM_EXECUTABLE || undefined,
    args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.fill('#token',fs.readFileSync(path.join(tmp,'operator.token'),'utf8').trim());
  await page.click('#login-form button');
  await page.waitForFunction(()=>!document.getElementById('login').open);
  await page.click('#baseline');
  await page.waitForFunction(()=>document.getElementById('geometry-status').textContent==='FORMAL PASS');
  await fs.promises.mkdir(path.join(root,'test-results'),{recursive:true});
  await page.screenshot({path:path.join(root,'test-results','overview.png'),fullPage:true});
  await page.click('[data-view="geometry"]');
  await page.waitForSelector('#gates table');
  if(await page.locator('#gates tr').count()<14)throw Error('gate table incomplete');
  await page.click('[data-view="experiments"]');
  await page.selectOption('#experiment-kind','quantum');
  await page.click('#experiment-run');
  await page.waitForFunction(()=>document.getElementById('experiment-result').textContent.includes('mean_fidelity'));
  await page.click('[data-view="control"]');
  for(const action of ['initialize','arm','start','estop']){
    await page.click(`[data-command="${action}"]`);
    await page.waitForFunction(a=>!document.querySelector(`[data-command="${a}"]`).disabled,action);
  }
  await page.waitForFunction(()=>document.getElementById('control-state').textContent==='LOCKOUT');
  await page.click('[data-view="registry"]');
  await page.waitForFunction(()=>document.querySelectorAll('#models-table tbody tr').length===24);
  await page.click('[data-view="audit"]');
  await page.waitForFunction(()=>document.getElementById('audit-status').textContent.includes('PASS'));
  const downloadPromise=page.waitForEvent('download');
  await page.locator('#runs-table button').first().click();
  const download=await downloadPromise;
  if(!(await download.suggestedFilename()).endsWith('.zip'))throw Error('export not downloaded');
  await page.setViewportSize({width:390,height:844});
  await page.click('[data-view="overview"]');
  await page.screenshot({path:path.join(root,'test-results','mobile.png'),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  if(overflow)throw Error('mobile horizontal overflow');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Browser smoke PASS: auth, baseline, geometry, quantum, controller lockout, registry, audit, ZIP export, mobile.');
}
run().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();
  child.kill('SIGTERM');
  await new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);});
  fs.rmSync(tmp,{recursive:true,force:true});
});
