const {chromium}=require('/home/utkarsh/Work/shraddha/palimpsest/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve('runs/route-obstacle-material-2026-10-22-v1'),dir=path.join(root,'handoff');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1050}}),page=await context.newPage();
  const files=Object.fromEntries(fs.readdirSync(dir).map(n=>[n,fs.readFileSync(path.join(dir,n))]));
  const blocked=[],errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await context.route('**/*',route=>{const u=new URL(route.request().url()),n=u.pathname.slice(1)||'index.html';
   if(u.origin==='http://routes.invalid'&&files[n])return route.fulfill({body:files[n],contentType:n.endsWith('.wav')?'audio/wav':n.endsWith('.svg')?'image/svg+xml':n.endsWith('.json')?'application/json':'text/html'});
   blocked.push(u.href);return route.abort();});
  assert(files['human-review.md'].toString().includes('`index.html`'));
  assert(!files['human-review.md'].toString().includes('runs/static-artwork'));
  await page.goto('http://routes.invalid');
  assert.equal(await page.locator('main>section').count(),6);
  assert((await page.locator('#borrowed-body').textContent()).includes('375 intervals, 376 points, 7.5 simulation seconds'));
  const one=page.locator('#one-map');
  assert((await one.textContent()).includes('279 intervals / 5.58 simulation seconds'));
  assert((await one.textContent()).includes('branch at tick 100'));
  assert((await one.textContent()).includes('0.00184106827, -0.00171107054'));
  assert((await one.textContent()).includes('Obstacle 0 moved to [0.75, -0.75]; goal unchanged'));
  assert((await one.textContent()).includes('tick boundaries 100–375 (5.5 simulation seconds)'));
  assert(!(await page.textContent('body')).includes('two route sources have no parent relationship'));
  await one.scrollIntoViewIfNeeded();
  const frame=page.frameLocator('#one-map iframe');
  await frame.locator('#comparison-metadata').waitFor({state:'attached'});
  assert.equal(await frame.locator('svg').count(),3);
  assert.deepEqual(await frame.locator('figure.overlay polyline').evaluateAll(lines=>lines.map(p=>p.getAttribute('points').split(' ').length)),[376,280]);
  assert(await frame.locator('body').evaluate(e=>e.textContent.indexOf('Route overlay') < e.textContent.indexOf('Source conditions')));
  await frame.locator('figure.overlay').screenshot({path:path.join(root,'handoff-overlay.png')});
  const metadata=await frame.locator('#comparison-metadata').textContent();
  const parsed=JSON.parse(metadata),source=JSON.parse(files['routes-source.json']);
  assert.equal(parsed.comparison.left.run_id,source.parent_run_id);
  assert.equal(parsed.comparison.right.provenance.parent_run_id,source.parent_run_id);
  assert.equal(parsed.comparison.right.provenance.source_snapshot_id,source.snapshot_id);
  const summary=frame.getByText('Comparison summary and source provenance',{exact:true});
  await summary.focus();await page.keyboard.press('Enter');
  assert(await frame.locator('#comparison-metadata').isVisible());
  await page.keyboard.press('Enter');
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   assert(await frame.locator('html').evaluate(e=>e.scrollWidth<=e.clientWidth));
   await page.locator('#borrowed-body').screenshot({path:path.join(root,`handoff-borrowed-body-${width}.png`)});
   await one.screenshot({path:path.join(root,`handoff-one-map-${width}.png`)});
  }
  assert(await page.locator('audio').evaluate(a=>a.paused&&a.currentTime===0));
  assert((await page.locator('#portrait-status').textContent()).includes('has not started'));
  assert.deepEqual(blocked,[]);assert.deepEqual(errors,[]);
  const result={status:'passed',viewport_widths:[1440,390],overlay_points:[376,280],source_and_snapshot_ids_verified:true,keyboard_provenance_disclosure:true,all_six_modes_present:true,media_not_started:true,blocked,page_errors:errors,ten_minute_viewing_sessions:false};
  fs.writeFileSync(path.join(root,'handoff-browser.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
