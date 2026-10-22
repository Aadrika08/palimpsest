// Real generated derivative; no inference or network services.
const {chromium}=require('/home/utkarsh/Work/shraddha/palimpsest/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve('runs/afterimage-presentation-2026-10-22-v2'),dir=path.join(root,'encounter');
(async()=>{
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(),blocked=[],errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 const files=Object.fromEntries(fs.readdirSync(dir).map(n=>[n,fs.readFileSync(path.join(dir,n))]));
 await context.route('**/*',route=>{const u=new URL(route.request().url()),n=u.pathname.slice(1)||'index.html';
 if(u.origin==='http://localhost'&&files[n])return route.fulfill({body:files[n],contentType:n.endsWith('.png')?'image/png':n.endsWith('.wav')?'audio/wav':n.endsWith('.svg')?'image/svg+xml':n.endsWith('.json')?'application/json':'text/html'});
 blocked.push(u.href);return route.abort();});
 await page.goto('http://localhost');
 const portrait=page.locator('#afterimage'),play=portrait.getByRole('button',{name:'Play 60-second portrait'});
 assert((await portrait.textContent()).includes('600 frames / 59.9 source seconds / 12 model seconds'));
 assert((await portrait.textContent()).includes('scripted manual-controller'));
 const summary=portrait.getByText('Inspect recorded responses one at a time',{exact:true});
 await page.waitForFunction(()=>document.getElementById('source-frame').dataset.frame==='0');
 assert(await portrait.locator('details').evaluate(e=>e.open));
 assert.equal(await portrait.locator('tbody tr').count(),600);
 assert((await page.locator('#portrait-status').textContent()).includes('has not started'));
 const pixels=await page.evaluate(async()=>{
  const expected=JSON.parse(document.getElementById('source-index').textContent).frames;
  const checks=[];
  for(let i=0;i<600;i++){
   const canvas=document.getElementById('source-frame'),rgba=canvas.getContext('2d').getImageData(0,0,128,128).data;
   const rgb=new Uint8Array(128*128*3);for(let p=0,j=0;p<rgba.length;p+=4){rgb[j++]=rgba[p];rgb[j++]=rgba[p+1];rgb[j++]=rgba[p+2];}
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',rgb)),b=>b.toString(16).padStart(2,'0')).join('');
   if(hash!==expected[i].frame_sha256||canvas.dataset.frame!==String(i))throw Error('browser frame mismatch '+i);
   checks.push(hash);document.getElementById('next').click();
  }
  document.getElementById('stop-portrait').click();return checks.length;
 });
 assert.equal(pixels,600);
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
   const frameObserver=new MutationObserver(()=>{const frame=Number(frameStatus.textContent.match(/^Frame (\d+)/)[1]);if(document.getElementById('source-frame').dataset.frame!==String(frame-1))throw Error('unsynchronized source frame');if(seen.at(-1)?.frame!==frame)seen.push({frame,elapsed:(performance.now()-start)/1000});});
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
 const failed=await context.newPage();
 await failed.route('**/afterimage-frames.png',route=>route.fulfill({body:Buffer.from('invalid png'),contentType:'image/png'}));
 await failed.goto('http://localhost');
 await failed.waitForFunction(()=>document.getElementById('portrait-status').textContent.includes('could not load'));
 assert(await failed.locator('#play-portrait').isDisabled());
 await failed.locator('#stop-portrait').click();
 assert((await failed.locator('#portrait-status').textContent()).includes('could not load'));
 assert(await failed.locator('#next').isDisabled());await failed.close();
 const result={status:'passed',browser_rgb_frames_exact:pixels,source_response_synchronized:true,load_failure_keeps_explanation_and_disables_playback:true,played,viewport_widths:[1440,390],keyboard_play_stop_and_manual_step:true,collapse_stops:true,no_automatic_start_or_repeat:true,blocked,page_errors:errors,scope:'actual portrait 60-second browser presentation and mapping; no human artistic judgment'};
 fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({...result,played:{elapsed:played.elapsed,frames:played.seen.length,points:played.points}}));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
