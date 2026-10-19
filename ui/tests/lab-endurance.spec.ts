import {test,expect,type Page} from '@playwright/test';
import {installMeter,startMeter,stopMeter,commandMetrics,summarize,cadenceAcceptance} from './measurement';

// Opt-in mixed browser endurance for manual lab refresh v4. Every cycle runs
// through the actual UI: create a manual run, stream with manual drive and the
// acceptance helper's preview pattern, pause, step, snapshot, close, branch from
// the snapshot (goal edit on odd cycles), alternate action/policy replay of the
// source, recorded playback, and a page reload every fifth cycle. Each cycle
// ends idle with a forced-GC renderer sample. This spec records raw evidence;
// scripts/manual_lab_refresh_v4.py judges cadence and listener growth.
const seconds=Number(process.env.PALIMPSEST_ENDURANCE_SECONDS??'0');
const cycleSeconds=Number(process.env.PALIMPSEST_ENDURANCE_CYCLE_SECONDS??'120');
const streamSeconds=Number(process.env.PALIMPSEST_ENDURANCE_STREAM_SECONDS??'4');

async function renderer(cdp:any,gc:boolean){
  if(gc){await cdp.send('HeapProfiler.collectGarbage');await cdp.send('HeapProfiler.collectGarbage');}
  const metrics=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((m:any)=>[m.name,m.value]));
  return {listeners:metrics.JSEventListeners,nodes:metrics.Nodes,js_heap_used:metrics.JSHeapUsedSize,documents:metrics.Documents};
}
async function api(page:Page,path:string){return page.evaluate(async path=>{const token=(await(await fetch('/api/v1/session')).json()).token;const response=await fetch('/api/v1'+path,{headers:{'X-Palimpsest-Session':token}});const value=await response.json();if(!response.ok)throw Error(`${response.status}: ${JSON.stringify(value)}`);return value;},path);}
// Same request shape as validPlacement(): fresh session, state read, preview POSTs.
async function previews(page:Page,id:string){return page.evaluate(async id=>{const token=(await(await fetch('/api/v1/session')).json()).token;const headers={'X-Palimpsest-Session':token,'Content-Type':'application/json'};const state=(await(await fetch(`/api/v1/runs/${id}`,{headers})).json()).state;const out:any[]=[];let valid:number[]|null=null;
  for(const xy of [[-5,-5],[-5,0],[5,5],[0,3]]){const response=await fetch(`/api/v1/runs/${id}/previews`,{method:'POST',headers,body:JSON.stringify({payload:{kind:'move_goal',xy},expected_revision:state.revision})});out.push(response.status);if(response.ok&&!valid)valid=xy;}
  return {statuses:out,valid};},id);}

test('mixed browser endurance with forced-GC renderer samples',async({page},info)=>{
  test.skip(!(seconds>0),'Opt-in endurance; set PALIMPSEST_ENDURANCE_SECONDS and serialize actual simulation jobs.');
  test.setTimeout((seconds+600)*1000);
  const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Performance.enable');
  const networkFailures:any[]=[],pageErrors:string[]=[];const started=Date.now();
  cdp.on('Network.loadingFailed',(event:any)=>{if(!event.canceled)networkFailures.push({elapsed_s:(Date.now()-started)/1000,error:event.errorText,type:event.type});});
  page.on('pageerror',error=>pageErrors.push(error.message));
  await installMeter(page);await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  const cycles:any[]=[];const baseline={idle_gc:await renderer(cdp,true)};
  const report=()=>({schema_version:1,configuration:{seconds,cycle_seconds:cycleSeconds,stream_seconds:streamSeconds,cycles:Math.floor(seconds/cycleSeconds)},baseline,cycles,network_failures:networkFailures,page_errors:pageErrors,elapsed_seconds:(Date.now()-started)/1000});
  const save=async()=>{const {writeFile}=await import('node:fs/promises');await writeFile(info.outputPath('lab-endurance.json'),JSON.stringify(report(),null,1)+'\n');};
  try{
    const total=Math.floor(seconds/cycleSeconds);
    for(let ordinal=0;ordinal<total;ordinal++){
      const cycleStart=Date.now();const cycle:any={ordinal,started_s:(cycleStart-started)/1000};
      await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');await page.getByLabel('Controller',{exact:true}).selectOption('manual');
      await page.getByRole('button',{name:'Create run',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
      const source=(await page.locator('.identity').innerText()).replace('Run ','');cycle.source=source;
      // Streaming window: manual drive commands, the preview pattern and the meter.
      await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running');
      await page.evaluate(()=>{const meter=(window as any).__labMeter;meter.commands=[];meter.applied={};});await startMeter(page);
      const manual=page.getByRole('button',{name:/Focus manual drive/});await manual.focus();
      for(const key of ['ArrowUp','ArrowLeft','ArrowUp','ArrowRight']){await page.keyboard.down(key);await page.waitForTimeout(streamSeconds*1000/8);await page.keyboard.up(key);await page.waitForTimeout(streamSeconds*1000/8);}
      const stream=await stopMeter(page);const commands=await commandMetrics(page);const acks=summarize(commands.map((c:any)=>c.ack_ms));
      cycle.cadence={window_ms:stream.window_ms,started_ms:stream.started,ended_ms:stream.ended,display_commits_ms:stream.commits,sample_arrival_count:stream.ws.length,acknowledgement_ms:acks,acknowledgement_raw_ms:commands.map((c:any)=>c.ack_ms),
        acceptance:cadenceAcceptance(stream.commits,stream.started,stream.ended,acks.p95)};
      const preview=await previews(page,source);cycle.previews=preview.statuses;
      cycle.streaming_raw=await renderer(cdp,false);
      await page.getByLabel('Edit',{exact:true}).focus();
      await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');
      const before=await page.locator('.run-heading').innerText();await page.getByRole('button',{name:'Step',exact:true}).click();await expect.poll(()=>page.locator('.run-heading').innerText()).not.toBe(before);
      cycle.source_ticks=(await api(page,`/runs/${source}`)).state.total_tick;
      await page.getByRole('button',{name:'Capture snapshot',exact:true}).click();await expect(page.locator('.notice')).toHaveText('Snapshot captured.');
      const snapshot=await page.getByLabel('Snapshot',{exact:true}).inputValue();expect(snapshot).not.toBe('');
      await page.getByRole('button',{name:'Close run',exact:true}).click();await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
      // Branch from the snapshot; odd cycles carry a validated goal edit.
      const edit=ordinal%2===1&&preview.valid;
      if(edit){await page.getByLabel('Edit',{exact:true}).selectOption('move_goal');await page.getByLabel('X (m)',{exact:true}).fill(String(preview.valid![0]));await page.getByLabel('Y (m)',{exact:true}).fill(String(preview.valid![1]));await page.getByLabel('Include the current world edit',{exact:true}).check();}
      else await page.getByLabel('Include the current world edit',{exact:true}).uncheck();
      await page.getByLabel('Snapshot',{exact:true}).selectOption(snapshot);await page.getByRole('button',{name:'Start branch',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
      cycle.branch=(await page.locator('.identity').innerText()).replace('Run ','');cycle.branch_edit=edit?preview.valid:null;
      for(let tick=0;tick<2;tick++){const prior=await page.locator('.run-heading').innerText();await page.getByRole('button',{name:'Step',exact:true}).click();await expect.poll(()=>page.locator('.run-heading').innerText()).not.toBe(prior);}
      await page.getByRole('button',{name:'Close run',exact:true}).click();await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
      // Alternate action and policy replay of the source; require a passed report.
      const mode=ordinal%2===0?'Action replay':'Policy replay';
      await page.getByLabel('Recorded run',{exact:true}).selectOption(source);await page.getByRole('button',{name:mode,exact:true}).click();
      await expect(page.locator('.mode')).toHaveText(mode);await expect(page.locator('.run-heading strong')).toHaveText('completed',{timeout:120_000});
      const replayReport=page.locator('.inspector details').filter({has:page.getByText('Replay verification result',{exact:true})}).locator('pre');await expect(replayReport).toContainText('"status": "passed"');
      cycle.replay={mode,result:JSON.parse(await replayReport.innerText())};
      await page.getByRole('button',{name:'Recorded playback',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Recorded playback');
      await page.getByLabel('Recorded run',{exact:true}).selectOption('');
      if(await page.getByRole('button',{name:'Close run',exact:true}).isEnabled())await page.getByRole('button',{name:'Close run',exact:true}).click();
      // Interruption: reload every fifth cycle and require stream recovery.
      if(ordinal%5===4){await page.reload();await expect(page.locator('.connection')).toContainText('Local stream connected',{timeout:15_000});cycle.reloaded=true;}
      await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled({timeout:30_000});
      await expect(page.locator('.error')).toHaveCount(0);
      cycle.active_seconds=(Date.now()-cycleStart)/1000;
      const idle=cycleStart+cycleSeconds*1000-Date.now()-2000;if(idle>0)await page.waitForTimeout(idle);
      cycle.idle_gc=await renderer(cdp,true);cycle.ended_s=(Date.now()-started)/1000;
      cycles.push(cycle);await save();
      console.log('ENDURANCE_CYCLE '+JSON.stringify({ordinal,source_ticks:cycle.source_ticks,mean_hz:cycle.cadence.acceptance.mean_hz,p99_ms:cycle.cadence.acceptance.interarrival_p99_ms,listeners_idle_gc:cycle.idle_gc.listeners,listeners_streaming_raw:cycle.streaming_raw.listeners,active_seconds:cycle.active_seconds}));
    }
  }finally{await save();}
  expect(cycles.length).toBe(Math.floor(seconds/cycleSeconds));expect(networkFailures).toEqual([]);expect(pageErrors).toEqual([]);
});
