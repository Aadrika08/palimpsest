// Two independent real-time sessions; no accelerated timers or model execution.
const {chromium}=require(process.cwd()+'/ui/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert');
const {execFileSync}=require('child_process');
const repo=process.cwd();
const source=path.join(repo,'runs/route-obstacle-material-2026-10-22-v1');
const root=path.join(repo,'runs/route-obstacle-material-2026-10-22-v1/sessions');
const names=['borrowed-body.svg','one-map-many-lives.html'];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const write=(name,value)=>fs.writeFileSync(path.join(root,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const files=Object.fromEntries(fs.readdirSync(path.join(source,'encounter')).map(n=>[n,fs.readFileSync(path.join(source,'encounter',n))]));
const expected=JSON.parse(files['checksums.json']).files;
function verifyInputs(){
 const zip=fs.readFileSync(path.join(source,'palimpsest-route-encounter-2026-10-22.zip'));
 const receipt=JSON.parse(fs.readFileSync(path.join(source,'artifacts.json')));
 assert.equal(zip.length,receipt.size_bytes);assert.equal(sha(zip),receipt.sha256);
 for(const [n,pin] of Object.entries(expected)){
  const bytes=fs.readFileSync(path.join(source,'encounter',n));
  assert.equal(bytes.length,pin.size_bytes);assert.equal(sha(bytes),pin.sha256);assert.equal(sha(files[n]),pin.sha256);
 }
}
async function structure(page,name){
 return page.evaluate(name=>{
  if(name==='one-map-many-lives.html'){
   const m=JSON.parse(document.querySelector('#comparison-metadata').textContent);
   return {actual:[...document.querySelectorAll('figure.overlay polyline')].map(p=>p.points.length),
           expected:['left','right'].flatMap(k=>m.comparison[k].traces.map(t=>t.points.length))};
  }
  const m=JSON.parse(document.querySelector('metadata').textContent);
  if(name==='borrowed-body.svg')return {actual:[...document.querySelectorAll('polyline')].map(p=>p.points.length),expected:m.traces.map(t=>t.points.length)};
  if(name==='atlas.svg'){
   const paths=document.querySelectorAll('path').length;
   return {actual:[document.querySelectorAll('path[stroke-dasharray]').length,paths>=m.edges_before+m.edges_after],expected:[m.removed_edges.length??m.removed_edges,true],paths_total:paths};
  }
  return {actual:[...document.querySelectorAll('path')].map(p=>(p.getAttribute('d').match(/M/g)||[]).length).filter(n=>n>1),expected:m.structures.map(s=>s.edges)};
 },name);
}
async function session(name){
 const id=name.replace(/\.(svg|html)$/,''),events=[],probes=[],errors=[],blocked=[];
 let browser,timer,result={name,status:'failed',duration_seconds:0};
 try{
  browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox'],ignoreDefaultArgs:['--disable-dev-shm-usage']});
  const work=async()=>{
   const context=await browser.newContext({viewport:{width:1440,height:1400}}),page=await context.newPage();
   page.on('pageerror',e=>errors.push(String(e)));page.on('crash',()=>errors.push('page crashed'));
   await context.route('**/*',route=>{
    const u=new URL(route.request().url()),n=u.pathname.slice(1);
    if(u.origin==='http://static-artwork.invalid'&&files[n])return route.fulfill({body:files[n],contentType:n.endsWith('.svg')?'image/svg+xml':'text/html'});
    blocked.push(u.href);return route.abort();
   });
   await page.goto('http://static-artwork.invalid/'+name);await page.bringToFront();
   const selector=name.endsWith('.html')?'figure.overlay svg':'svg';
   const artwork=page.locator(selector);await artwork.scrollIntoViewIfNeeded();
   const before=await structure(page,name);assert.deepEqual(before.actual,before.expected);
   await artwork.screenshot({path:path.join(root,id+'-start.png')});
   await page.evaluate(selector=>{
    window.sessionEvidence={frames:0,maxFrameGap:0,lastFrame:performance.now(),visibility:[],mutations:0};
    function frame(now){const e=window.sessionEvidence;e.maxFrameGap=Math.max(e.maxFrameGap,now-e.lastFrame);e.lastFrame=now;e.frames++;requestAnimationFrame(frame);}requestAnimationFrame(frame);
    document.addEventListener('visibilitychange',()=>window.sessionEvidence.visibility.push({time:performance.now(),state:document.visibilityState}));
    new MutationObserver(changes=>{window.sessionEvidence.mutations+=changes.length;}).observe(document.querySelector(selector),{subtree:true,attributes:true,childList:true,characterData:true});
   },selector);
   const started=performance.now(),startedUTC=new Date().toISOString();let prior=started;
   while(true){
    await new Promise(resolve=>setTimeout(resolve,1000));
    const now=performance.now();
    const probe=await page.evaluate(selector=>{
     const r=document.querySelector(selector).getBoundingClientRect(),e=window.sessionEvidence;
     return {visibility:document.visibilityState,rect:{x:r.x,y:r.y,width:r.width,height:r.height},
       fully_in_view:r.width>0&&r.height>0&&r.x>=-1&&r.y>=-1&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1,
       frames:e.frames,max_frame_gap_ms:e.maxFrameGap,frame_age_ms:performance.now()-e.lastFrame,mutations:e.mutations,visibility_events:e.visibility};
    },selector);
    probes.push({elapsed_seconds:(now-started)/1000,probe_gap_seconds:(now-prior)/1000,...probe});prior=now;
    assert.equal(probe.visibility,'visible');assert(probe.fully_in_view);
    assert(probe.max_frame_gap_ms<=5000&&probe.frame_age_ms<=5000&&probes.at(-1).probe_gap_seconds<=5);
    assert.equal(probe.mutations,0);assert.deepEqual(probe.visibility_events,[]);assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
    if(probes.length%30===0)fs.writeFileSync(path.join(root,id+'-progress.json'),JSON.stringify({name,elapsed_seconds:(now-started)/1000,status:'running'}));
    if(now-started>=600000)break;
   }
   const duration=(performance.now()-started)/1000,endedUTC=new Date().toISOString();
   assert(duration>=600&&duration<640);
   const after=await structure(page,name);assert.deepEqual(after,before);
   await artwork.screenshot({path:path.join(root,id+'-end.png')});
   verifyInputs();
   result={name,status:'passed',started_utc:startedUTC,ended_utc:endedUTC,duration_seconds:duration,
     counts:after,probes,events,errors,blocked,source_sha256:sha(files[name]),viewport:{width:1440,height:1400},
     automated:true,concurrent_sessions:true,human_viewing_or_acceptance:false};
  };
  await Promise.race([work(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('640-second session watchdog')),640000);})]);
 }catch(e){result={...result,error:String(e),probes,events,errors,blocked};}
 finally{clearTimeout(timer);if(browser)await browser.close();result.browser_disconnected=!browser||!browser.isConnected();write(id+'.json',result);}
 return result;
}
(async()=>{
 assert(!fs.existsSync(root),'fresh allocation required');
 assert.equal(execFileSync('git',['status','--porcelain'],{cwd:repo,encoding:'utf8'}).trim(),'','committed clean checkout required');
 verifyInputs();fs.mkdirSync(root);
 write('registration.json',{head:execFileSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'}).trim(),
   script_sha256:sha(fs.readFileSync(__filename)),plan_sha256:sha(fs.readFileSync(path.join(repo,'docs/plans/route-obstacle-material-2026-10-22.md'))),
   source_archive_sha256:JSON.parse(fs.readFileSync(path.join(source,'artifacts.json'))).sha256,
   modes:names,required_seconds_each:600,watchdog_seconds_each:640,concurrent:true,headless:true,qualification_claims:[]});
 const results=await Promise.all(names.map(session));
 const passed=results.every(r=>r.status==='passed'&&r.browser_disconnected);
 write('result.json',{status:passed?'passed':'failed',sessions:results.map(({probes,...r})=>r),qualification_claims:[]});
 console.log(JSON.stringify({status:passed?'passed':'failed',sessions:results.map(r=>({name:r.name,status:r.status,duration_seconds:r.duration_seconds,error:r.error}))}));
 process.exitCode=passed?0:1;
})().catch(e=>{console.error(e);process.exitCode=1});
