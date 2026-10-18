import {test,expect} from '@playwright/test';

// Opt-in bounded diagnostic for the v3 ERR_INSUFFICIENT_RESOURCES failure.
// It keeps one actual manual run streaming for PALIMPSEST_RESOURCE_SECONDS and
// repeats the acceptance helper's preview POST pattern (bodies left unread),
// recording renderer counters and every network failure. It asserts only that
// no preview fails in transport; it is not the manual acceptance workflow.
test('bounded Chromium resource diagnostic for streamed lab samples',async({page},info)=>{
  test.skip(process.env.PALIMPSEST_RESOURCE_DIAGNOSTIC!=='1','Opt-in diagnostic; serialize actual simulation jobs.');
  const seconds=Number(process.env.PALIMPSEST_RESOURCE_SECONDS??'60');test.setTimeout((seconds+120)*1000);
  const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Performance.enable');
  const inflight=new Set<string>();const failures:any[]=[];let requests=0,dataUrls=0;
  cdp.on('Network.requestWillBeSent',event=>{if(event.request.url.startsWith('data:')){dataUrls++;return;}requests++;inflight.add(event.requestId);});
  cdp.on('Network.loadingFinished',event=>inflight.delete(event.requestId));
  cdp.on('Network.loadingFailed',event=>{inflight.delete(event.requestId);failures.push({t:Date.now(),error:event.errorText,type:event.type});});
  let frames=0,frameBytes=0;cdp.on('Network.webSocketFrameReceived',event=>{frames++;frameBytes+=event.response.payloadData.length;});
  await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');await page.getByLabel('Controller',{exact:true}).selectOption('manual');
  await page.getByRole('button',{name:'Create run',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
  const id=(await page.locator('.identity').innerText()).replace('Run ','');
  await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running');
  const rows:any[]=[];const started=Date.now();
  // Same shape as validPlacement(): fresh session, state read, unconsumed preview bodies.
  const previewPair=()=>page.evaluate(async id=>{const out:any[]=[];try{const token=(await(await fetch('/api/v1/session')).json()).token;const headers={'X-Palimpsest-Session':token,'Content-Type':'application/json'};const state=(await(await fetch(`/api/v1/runs/${id}`,{headers})).json()).state;for(const xy of [[-5,-5],[-5,0]]){const response=await fetch(`/api/v1/runs/${id}/previews`,{method:'POST',headers,body:JSON.stringify({payload:{kind:'move_goal',xy},expected_revision:state.revision})});out.push(response.status);}}catch(error){out.push(String(error));}return out;},id);
  // Optional controlled exhaustion of Chromium's shared-memory directory (TMPDIR,
  // because Playwright passes --disable-dev-shm-usage). Only for private tmpfs runs.
  const leave=process.env.PALIMPSEST_RESOURCE_FILL_LEAVE;const fill:any[]=[];
  async function exhaust(){const {statfsSync,openSync,writeSync,closeSync,unlinkSync}=await import('node:fs');const {tmpdir}=await import('node:os');const {join}=await import('node:path');
    const dir=tmpdir();const free=()=>{const s=statfsSync(dir);return s.bavail*s.bsize;};const path=join(dir,'resource-filler.bin');const before=free();const fd=openSync(path,'w');const chunk=Buffer.alloc(1<<20);
    try{while(free()>Number(leave)+chunk.length)writeSync(fd,chunk);}finally{closeSync(fd);}
    const during=free();const exhausted=await previewPair();unlinkSync(path);await page.waitForTimeout(500);const recovered=await previewPair();
    fill.push({dir,free_before:before,free_during:during,exhausted,free_after:free(),recovered});console.log('RESOURCE_FILL '+JSON.stringify(fill.at(-1)));}
  // Optional: shared memory pinned by unread response bodies (held, then read).
  const pins:any={};
  if(process.env.PALIMPSEST_RESOURCE_PIN_PROBE==='1'){const {statfsSync}=await import('node:fs');const {tmpdir}=await import('node:os');const free=()=>{const s=statfsSync(tmpdir());return s.bavail*s.bsize;};
    const settle=async()=>{await cdp.send('HeapProfiler.collectGarbage');await page.waitForTimeout(500);return free();};
    pins.baseline=await settle();
    await page.evaluate(async id=>{const token=(await(await fetch('/api/v1/session')).json()).token;const headers={'X-Palimpsest-Session':token,'Content-Type':'application/json'};(window as any).__held=[];for(let i=0;i<20;i++)(window as any).__held.push(await fetch(`/api/v1/runs/${id}/previews`,{method:'POST',headers,body:JSON.stringify({payload:{kind:'move_goal',xy:[-5,-5]},expected_revision:-1})}));},id);
    pins.twenty_unread_held=await settle();
    await page.evaluate(async()=>{for(const response of (window as any).__held)await response.text();});pins.twenty_read=await settle();
    await page.evaluate(()=>{delete (window as any).__held;});pins.released=await settle();
    console.log('RESOURCE_PINS '+JSON.stringify(pins));}
  while(Date.now()-started<seconds*1000){
    await page.waitForTimeout(5000);
    if(leave&&!fill.length)await exhaust();
    const previews=await previewPair();
    const metrics=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
    const status=await page.evaluate(async id=>{const token=(await(await fetch('/api/v1/session')).json()).token;return(await(await fetch(`/api/v1/runs/${id}`,{headers:{'X-Palimpsest-Session':token}})).json()).state;},id);
    const imageSrcBytes=await page.evaluate(()=>[...document.images].reduce((total,image)=>total+image.src.length,0));
    rows.push({elapsed_s:(Date.now()-started)/1000,total_tick:status.total_tick,phase:status.phase,previews,requests,data_url_requests:dataUrls,inflight:inflight.size,failures:failures.length,ws_frames:frames,ws_payload_chars:frameBytes,image_src_chars:imageSrcBytes,
      js_heap_used:metrics.JSHeapUsedSize,dom_nodes:metrics.Nodes,documents:metrics.Documents,listeners:metrics.JSEventListeners,resources:metrics.Resources});
    console.log('RESOURCE_SAMPLE '+JSON.stringify(rows.at(-1)));
    if(status.phase!=='running')break;
  }
  if(rows.at(-1)?.phase==='running'){await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');}
  // Optional continuation through the rest of the v3 workflow after a long run:
  // paused snapshot, two branches (second with a goal edit), comparison,
  // recorded playback and SVG export, all through the UI.
  const workflow:any={};
  if(process.env.PALIMPSEST_RESOURCE_WORKFLOW==='1'){
    const fill=async(xy:number[])=>{await page.getByLabel('Edit',{exact:true}).selectOption('move_goal');await page.getByLabel('X (m)',{exact:true}).fill(String(xy[0]));await page.getByLabel('Y (m)',{exact:true}).fill(String(xy[1]));};
    workflow.source_ticks=(await page.evaluate(async id=>{const token=(await(await fetch('/api/v1/session')).json()).token;return(await(await fetch(`/api/v1/runs/${id}`,{headers:{'X-Palimpsest-Session':token}})).json()).state.total_tick;},id));
    await page.getByRole('button',{name:'Capture snapshot',exact:true}).click();await expect(page.locator('.notice')).toHaveText('Snapshot captured.');
    const snapshot=await page.getByLabel('Snapshot',{exact:true}).inputValue();expect(snapshot).not.toBe('');workflow.snapshot=snapshot;
    await page.getByRole('button',{name:'Close run',exact:true}).click();
    const branches:string[]=[];
    for(let i=0;i<2;i++){
      if(i===1){await fill([5,5]);await page.getByLabel('Include the current world edit',{exact:true}).check();}
      await page.getByLabel('Snapshot',{exact:true}).selectOption(snapshot);await page.getByRole('button',{name:'Start branch',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
      branches.push((await page.locator('.identity').innerText()).replace('Run ',''));
      for(let tick=0;tick<3;tick++){const before=await page.locator('.run-heading').innerText();await page.getByRole('button',{name:'Step',exact:true}).click();await expect.poll(()=>page.locator('.run-heading').innerText()).not.toBe(before);}
      await page.getByRole('button',{name:'Close run',exact:true}).click();
    }
    workflow.branches=branches;expect(branches[0]).not.toBe(branches[1]);
    await page.getByLabel('Left run',{exact:true}).selectOption(branches[0]);await page.getByLabel('Right run',{exact:true}).selectOption(branches[1]);await page.getByRole('button',{name:'Compare runs',exact:true}).click();await expect(page.locator('.comparison svg')).toBeVisible();workflow.compared=true;
    await page.getByLabel('Recorded run',{exact:true}).selectOption(branches[0]);await page.getByRole('button',{name:'Recorded playback',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Recorded playback');workflow.playback=true;
    const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Export SVG',exact:true}).click();const artifact=await downloading;expect(await artifact.failure()).toBeNull();workflow.export=artifact.suggestedFilename();
    await expect(page.locator('.error')).toHaveCount(0);console.log('RESOURCE_WORKFLOW '+JSON.stringify(workflow));
  }
  const report={schema_version:1,run_id:id,seconds,rows,fill,pins,workflow,failures};
  await info.attach('chromium-resources.json',{body:JSON.stringify(report,null,2),contentType:'application/json'});const {writeFile}=await import('node:fs/promises');await writeFile(info.outputPath('chromium-resources.json'),JSON.stringify(report,null,2)+'\n');
  if(!workflow.export)await page.evaluate(async id=>{const token=(await(await fetch('/api/v1/session')).json()).token;await fetch(`/api/v1/runs/${id}/close`,{method:'POST',headers:{'X-Palimpsest-Session':token,'Content-Type':'application/json'},body:'{}'});},id);
  if(leave)return;expect(failures).toEqual([]);expect(rows.flatMap(row=>row.previews).every((value:unknown)=>typeof value==='number')).toBe(true);
});
