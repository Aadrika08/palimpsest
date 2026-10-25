const {chromium}=require(process.cwd()+'/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),{pathToFileURL}=require('url');
const root=path.resolve('runs/guided-encounter-2026-10-23-v1'),dir=path.join(root,'encounter');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
 try{
  const context=await browser.newContext(),page=await context.newPage(),external=[],errors=[];
  page.on('request',r=>{if(!r.url().startsWith(pathToFileURL(dir).href+'/'))external.push(r.url());});
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(dir,'index.html')).href);
  await page.waitForFunction(()=>document.getElementById('source-frame').dataset.frame==='0');
  assert.equal(await page.locator('main>section').count(),6);
  const guide=page.locator('aside[aria-labelledby="encounter-guide-title"]');
  const expected=['one-map','borrowed-body','afterimage','choir','atlas','specimens'];
  assert.deepEqual(await guide.locator('a').evaluateAll(a=>a.map(x=>x.hash.slice(1))),expected);
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1050});
   for(const id of expected){
    const link=guide.locator(`a[href="#${id}"]`);await link.focus();await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(()=>location.hash),'#'+id);
    assert(await page.locator('#'+id+'-title').isVisible());
   }
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await guide.screenshot({path:path.join(root,`guide-${width}.png`)});
  }
  assert(await page.locator('audio').evaluate(a=>a.paused&&a.currentTime===0));
  assert((await page.locator('#portrait-status').textContent()).includes('has not started'));
  await page.locator('#next').focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('#source-frame').getAttribute('data-frame'),'1');
  await page.locator('#stop-portrait').click();
  assert.equal(await page.locator('#source-frame').getAttribute('data-frame'),'0');
  assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
  const result={status:'passed',local_file_open:true,guide_targets:expected,viewport_widths:[1440,390],
   keyboard_all_six_destinations:true,portrait_manual_step_and_stop:true,no_automatic_playback:true,
   page_errors:errors,external_requests:external,scope:'static introduction and local portable navigation; unchanged media duration receipts retained separately'};
  fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
