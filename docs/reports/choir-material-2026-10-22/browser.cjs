const {chromium}=require('/home/utkarsh/Work/shraddha/palimpsest/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve('runs/choir-material-2026-10-22-v1'),dir=path.join(root,'encounter');
(async()=>{
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(),blocked=[],errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 const files=Object.fromEntries(fs.readdirSync(dir).map(n=>[n,fs.readFileSync(path.join(dir,n))]));
 await context.route('**/*',route=>{const u=new URL(route.request().url()),n=u.pathname.slice(1)||'index.html';
 if(u.origin==='http://choir.invalid'&&files[n])return route.fulfill({body:files[n],contentType:n.endsWith('.wav')?'audio/wav':n.endsWith('.svg')?'image/svg+xml':n.endsWith('.json')?'application/json':'text/html'});
 blocked.push(u.href);return route.abort();});
 await page.goto('http://choir.invalid');const choir=page.locator('#choir');
 assert((await choir.textContent()).includes('Playback ends after 120 seconds'));
 assert((await choir.textContent()).includes('Final episode uses a recorded prefix'));
 await choir.getByText('Episode boundaries',{exact:true}).click();
 assert.equal(await choir.locator('tbody tr').count(),18);
 const ranges=await choir.locator('tbody tr').allTextContents();
 for(const width of [1440,390]){
 await page.setViewportSize({width,height:1050});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await choir.screenshot({path:path.join(root,`choir-${width}.png`)});
 }
 const audio=choir.locator('audio');await audio.scrollIntoViewIfNeeded();
 assert(await audio.evaluate(a=>a.paused&&a.currentTime===0&&!a.autoplay));
 await audio.focus();await page.keyboard.press('Space');
 await page.waitForFunction(()=>document.querySelector('audio').currentTime>0);
 await choir.getByRole('button',{name:'Stop audio and return to start'}).focus();await page.keyboard.press('Enter');
 assert(await audio.evaluate(a=>a.paused&&a.currentTime===0));
 const played=await audio.evaluate(async a=>{const start=performance.now();const end=new Promise(r=>a.addEventListener('ended',r,{once:true}));await a.play();await end;return {duration:a.duration,elapsed:(performance.now()-start)/1000};});
 assert.equal(played.duration,120);assert(Math.abs(played.elapsed-120)<2);
 assert.deepEqual(blocked,[]);assert.deepEqual(errors,[]);
 const result={status:'passed',played,episodes:18,ranges,viewport_widths:[1440,390],keyboard_play_stop:true,autoplay:false,blocked,page_errors:errors,scope:'real FLYNN-derived WAV browser transport/presentation; no human listening judgment'};
 fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
