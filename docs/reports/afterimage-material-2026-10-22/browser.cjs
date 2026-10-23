// Real generated derivative; no inference or network services.
const {chromium}=require('/home/utkarsh/Work/shraddha/palimpsest/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve('runs/afterimage-material-2026-10-22-v1'),dir=path.join(root,'encounter');
(async()=>{
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(),blocked=[],errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 const files=Object.fromEntries(fs.readdirSync(dir).map(n=>[n,fs.readFileSync(path.join(dir,n))]));
 await context.route('**/*',route=>{const u=new URL(route.request().url()),n=u.pathname.slice(1)||'index.html';
 if(u.origin==='http://afterimage.invalid'&&files[n])return route.fulfill({body:files[n],contentType:n.endsWith('.wav')?'audio/wav':n.endsWith('.svg')?'image/svg+xml':n.endsWith('.json')?'application/json':'text/html'});
 blocked.push(u.href);return route.abort();});
 await page.goto('http://afterimage.invalid');
 const portrait=page.locator('#afterimage'),play=portrait.getByRole('button',{name:'Play 60-second portrait'});
 assert((await portrait.textContent()).includes('600 frames / 59.9 source seconds / 12 model seconds'));
 assert((await portrait.textContent()).includes('scripted manual-controller'));
 const summary=portrait.getByText('Inspect recorded responses one at a time',{exact:true});
 await summary.focus();await page.keyboard.press('Enter');
 assert.equal(await portrait.locator('tbody tr').count(),600);
 assert((await page.locator('#portrait-status').textContent()).includes('has not started'));
 await page.locator('#next').focus();await page.keyboard.press('Enter');
 assert((await page.locator('#frame-status').textContent()).startsWith('Frame 2 of 600'));
 await play.focus();await page.keyboard.press('Enter');
 await page.waitForFunction(()=>document.getElementById('prefix').getAttribute('points').split(' ').length>2);
 assert(await page.locator('#next').isDisabled());
 await page.locator('#stop-portrait').focus();await page.keyboard.press('Enter');
 assert((await page.locator('#frame-status').textContent()).startsWith('Frame 1 of 600'));
 assert((await page.locator('#portrait-status').textContent()).startsWith('Stopped'));
 await play.click();await summary.click();
 await page.waitForFunction(()=>document.getElementById('portrait-status').textContent.startsWith('Stopped'));
 await summary.click();
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1050});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 }
 await page.setViewportSize({width:1440,height:1050});
 await play.scrollIntoViewIfNeeded();
 const played=await page.evaluate(async()=>{
   const start=performance.now(),seen=[];
   const frameStatus=document.getElementById('frame-status');
   const frameObserver=new MutationObserver(()=>{const frame=Number(frameStatus.textContent.match(/^Frame (\d+)/)[1]);if(seen.at(-1)?.frame!==frame)seen.push({frame,elapsed:(performance.now()-start)/1000});});
   frameObserver.observe(frameStatus,{childList:true});
   const ended=new Promise(resolve=>{const observer=new MutationObserver(()=>{if(document.getElementById('portrait-status').textContent.startsWith('Completed')){observer.disconnect();resolve();}});observer.observe(document.getElementById('portrait-status'),{childList:true});});
   document.getElementById('play-portrait').click();await ended;frameObserver.disconnect();
   return {elapsed:(performance.now()-start)/1000,seen,points:document.getElementById('prefix').getAttribute('points').split(' ').length};
 });
 assert(Math.abs(played.elapsed-60)<1);assert.equal(played.points,600);
 assert.deepEqual(played.seen.map(x=>x.frame),Array.from({length:600},(_,i)=>i+1));
 for(const entry of played.seen)assert(Math.abs(entry.elapsed-(entry.frame-1)/10)<.1);
 for(const width of [1440,390]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.locator('#controls').screenshot({path:path.join(root,`afterimage-${width}.png`)});
 }
 assert((await page.locator('#portrait-status').textContent()).startsWith('Completed'));
 assert((await page.locator('#frame-status').textContent()).startsWith('Frame 600 of 600'));
 assert.deepEqual(blocked,[]);assert.deepEqual(errors,[]);
 const result={status:'passed',played,viewport_widths:[1440,390],keyboard_play_stop_and_manual_step:true,collapse_stops:true,no_automatic_start_or_repeat:true,blocked,page_errors:errors,scope:'actual portrait 60-second browser presentation and mapping; no human artistic judgment'};
 fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({...result,played:{elapsed:played.elapsed,frames:played.seen.length,points:played.points}}));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
