import {test,expect,type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

async function api(page:Page,path:string,body?:unknown){return page.evaluate(async({path,body})=>{const token=(await(await fetch('/api/v1/session')).json()).token;const response=await fetch('/api/v1'+path,{method:body===undefined?'GET':'POST',headers:{'X-Palimpsest-Session':token,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});const value=await response.json();if(!response.ok)throw Error(`${response.status}: ${JSON.stringify(value)}`);return value;},{path,body});}
async function validPlacement(page:Page,kind:'move_goal'|'move_obstacle',different?:number[]){const id=(await page.locator('.identity').innerText()).replace('Run ','');return page.evaluate(async({id,kind,different})=>{const token=(await(await fetch('/api/v1/session')).json()).token;const headers={'X-Palimpsest-Session':token,'Content-Type':'application/json'};const state=(await(await fetch(`/api/v1/runs/${id}`,{headers})).json()).state;for(const x of [-5,-3,0,3,5])for(const y of [-5,-3,0,3,5]){if(different&&x===different[0]&&y===different[1])continue;const payload=kind==='move_goal'?{kind,xy:[x,y]}:{kind,index:0,xy:[x,y]};const result=await fetch(`/api/v1/runs/${id}/previews`,{method:'POST',headers,body:JSON.stringify({payload,expected_revision:state.revision})});if(result.ok)return[x,y];}throw Error('No valid placement in actual scenario');},{id,kind,different});}
async function fillEdit(page:Page,kind:'move_goal'|'move_obstacle',xy:number[]){await page.getByLabel('Edit',{exact:true}).selectOption(kind);await page.getByLabel('X (m)',{exact:true}).fill(String(xy[0]));await page.getByLabel('Y (m)',{exact:true}).fill(String(xy[1]));}
async function runId(page:Page){return(await page.locator('.identity').innerText()).replace('Run ','');}
async function createManual(page:Page){await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');await page.getByLabel('Controller',{exact:true}).selectOption('manual');await page.getByRole('button',{name:'Create run',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});return runId(page);}

test.afterEach(async({page},info)=>{
  if(info.status==='skipped')return;
  const cleanup=await page.evaluate(async()=>{const id=document.querySelector('.identity')?.textContent?.replace('Run ','');if(!id||! /^[0-9a-f]{32}$/.test(id))return null;const token=(await(await fetch('/api/v1/session')).json()).token;const response=await fetch(`/api/v1/runs/${id}/close`,{method:'POST',headers:{'X-Palimpsest-Session':token,'Content-Type':'application/json'},body:'{}'});return {run_id:id,http_status:response.status,response:await response.json()};});
  const body=JSON.stringify(cleanup,null,2);await info.attach('owner-close.json',{body,contentType:'application/json'});const {writeFile}=await import('node:fs/promises');await writeFile(info.outputPath('owner-close.json'),body+'\n');
  if(info.status==='passed')expect(cleanup,'Every successful actual workflow must retain an owner close response').not.toBeNull();if(!cleanup)return;expect(cleanup.http_status).toBe(200);expect(cleanup.response.run_id).toBe(cleanup.run_id);
  // A successful workflow requires a clean close. Failed tests retain the
  // already failed owner's authoritative status instead of hiding teardown.
  if(info.status==='passed')expect(cleanup.response.status).toBe('closed');else expect(['closed','failed']).toContain(cleanup.response.status);
});

test('actual local manual workflow, snapshots, sequential branches, comparison and export',async({page})=>{
  const browserErrors:string[]=[];page.on('pageerror',error=>browserErrors.push(error.message));
  await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');
  await page.getByLabel('Controller',{exact:true}).selectOption('manual');
  await page.getByRole('button',{name:'Create run',exact:true}).click();
  await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
  await expect(page.getByRole('img',{name:'Actual left eye policy input'})).toBeVisible();
  for(const name of ['Export SVG','Export PNG','Export bundle'])await expect(page.getByRole('button',{name,exact:true})).toBeDisabled();
  await expect(page.getByText('Close the active run before exporting.',{exact:true})).toBeVisible();
  const source=await page.locator('.identity').innerText();
  await page.getByRole('button',{name:'Start',exact:true}).click();
  await expect(page.locator('.run-heading strong')).toHaveText('running');
  await expect(page.getByRole('button',{name:'Export bundle',exact:true})).toBeDisabled();
  const manual=page.getByRole('button',{name:/Focus manual drive/});await manual.focus();await page.keyboard.down('ArrowUp');await page.waitForTimeout(150);await page.keyboard.up('ArrowUp');await page.keyboard.down('ArrowLeft');
  await page.getByLabel('Edit',{exact:true}).focus();await page.keyboard.up('ArrowLeft');
  await expect.poll(async()=>{const result=await api(page,`/runs/${source.replace('Run ','')}`);return result.state.pending_commands;}).toBe(0);
  const liveXY=await validPlacement(page,'move_obstacle');await fillEdit(page,'move_obstacle',liveXY);
  await expect(page.getByRole('button',{name:'Capture snapshot',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Preview edit',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Preview edit',exact:true}).click();
  await expect(page.getByRole('button',{name:'Apply edit',exact:true})).toBeEnabled();
  const editResponse=page.waitForResponse(response=>response.url().endsWith('/commands')&&response.request().postDataJSON()?.kind==='intervene');
  await page.getByRole('button',{name:'Apply edit',exact:true}).click();const liveReceipt=await(await editResponse).json();
  await expect.poll(async()=>{const result=await api(page,`/runs/${source.replace('Run ','')}/events?after=0&limit=200`);return result.events.filter((event:any)=>event.kind==='command_applied'&&event.id===liveReceipt.id).length;}).toBe(1);
  expect((await api(page,`/runs/${source.replace('Run ','')}`)).state.phase).toBe('running');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await expect(page.locator('.run-heading strong')).toHaveText('paused');
  // Read-only preview requests choose a valid placement from this actual world.
  const xy=await validPlacement(page,'move_goal');await fillEdit(page,'move_goal',xy);
  await page.getByRole('button',{name:'Preview edit',exact:true}).click();await expect(page.getByRole('button',{name:'Apply edit',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Apply edit',exact:true}).click();await expect(page.locator('.notice')).toContainText('intervene');
  await page.getByLabel('left eye enabled',{exact:true}).uncheck();await page.getByRole('button',{name:'Apply eye mask',exact:true}).click();await page.getByRole('button',{name:'Step',exact:true}).click();await expect(page.locator('.sensors figcaption').first()).toContainText('masked');
  await expect.poll(async()=>page.getByRole('img',{name:'Actual left eye policy input'}).evaluate((image:HTMLImageElement)=>{if(!image.complete||!image.naturalWidth)return false;const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;const context=canvas.getContext('2d')!;context.drawImage(image,0,0);return context.getImageData(0,0,canvas.width,canvas.height).data.every((value,i)=>i%4===3||value===0);})).toBe(true);
  const branchXY=await validPlacement(page,'move_goal',xy);
  await page.getByRole('button',{name:'Capture snapshot',exact:true}).click();await expect(page.locator('.notice')).toHaveText('Snapshot captured.');
  const snapshot=await page.getByLabel('Snapshot',{exact:true}).inputValue();expect(snapshot).not.toBe('');
  // At a paused boundary blur must publish zero manual intent, even without a step.
  await manual.focus();await page.keyboard.down('ArrowUp');
  await expect.poll(async()=>page.evaluate(async()=>{const token=(await(await fetch('/api/v1/session')).json()).token;const id=document.querySelector('.identity')!.textContent!.replace('Run ','');const response=await fetch(`/api/v1/runs/${id}/events?after=0&limit=200`,{headers:{'X-Palimpsest-Session':token}});const events=(await response.json()).events;const latest=events.filter((x:any)=>x.kind==='command_received'&&x.command.kind==='set_action').at(-1);return events.some((x:any)=>x.kind==='command_applied'&&x.id===latest?.command.id)?latest.command.payload.action:null;})).toEqual([1,0]);
  await page.getByRole('button',{name:'Capture snapshot',exact:true}).focus();await page.keyboard.up('ArrowUp');
  await expect.poll(async()=>page.evaluate(async()=>{const token=(await(await fetch('/api/v1/session')).json()).token;const id=document.querySelector('.identity')!.textContent!.replace('Run ','');const response=await fetch(`/api/v1/runs/${id}/events?after=0&limit=200`,{headers:{'X-Palimpsest-Session':token}});const events=(await response.json()).events;const commands=events.filter((x:any)=>x.kind==='command_received'&&x.command.kind==='set_action');const latest=commands.at(-1);return events.some((x:any)=>x.kind==='command_applied'&&x.id===latest?.command.id)?latest.command.payload.action:null;})).toEqual([0,0]);
  await page.reload();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});await expect(page.locator('.identity')).toHaveText(source);
  await page.getByRole('button',{name:'Close run',exact:true}).click();
  const branches:string[]=[];
  for(let i=0;i<2;i++){
    if(i===1){await fillEdit(page,'move_goal',branchXY);await page.getByLabel('Include the current world edit',{exact:true}).check();}
    await page.getByLabel('Snapshot',{exact:true}).selectOption(snapshot);await page.getByRole('button',{name:'Start branch',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
    branches.push((await page.locator('.identity').innerText()).replace('Run ',''));
    for(let tick=0;tick<3;tick++){const before=await page.locator('.run-heading').innerText();await page.getByRole('button',{name:'Step',exact:true}).click();await expect.poll(()=>page.locator('.run-heading').innerText()).not.toBe(before);}
    await page.getByRole('button',{name:'Close run',exact:true}).click();
  }
  expect(branches[0]).not.toBe(branches[1]);expect(source).not.toContain(branches[0]);
  await page.getByLabel('Left run',{exact:true}).selectOption(branches[0]);await page.getByLabel('Right run',{exact:true}).selectOption(branches[1]);await page.getByRole('button',{name:'Compare runs',exact:true}).click();await expect(page.getByText('Provenance differences — inspect before overlays',{exact:true})).toBeVisible();await expect(page.locator('.comparison svg')).toBeVisible();
  const compared=await api(page,`/compare?left=${branches[0]}&right=${branches[1]}`);expect(compared.left.worlds[0].world.goal.slice(0,2)).toEqual(xy);expect(compared.right.worlds[0].world.goal.slice(0,2)).toEqual(branchXY);expect(compared.left.events.some((event:any)=>event.kind==='intervention')).toBe(false);expect(compared.right.events.some((event:any)=>event.kind==='intervention')).toBe(true);
  await page.getByLabel('Recorded run',{exact:true}).selectOption(branches[0]);await page.getByRole('button',{name:'Recorded playback',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Recorded playback');await expect(page.getByRole('button',{name:'Step',exact:true})).toBeDisabled();
  const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Export SVG',exact:true}).click();const artifact=await downloading;expect(artifact.suggestedFilename()).toMatch(/\.svg$/);expect(await artifact.failure()).toBeNull();
  await page.screenshot({path:'test-results/actual-lab-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});await expect(page.getByRole('button',{name:'Recorded playback',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'test-results/actual-lab-mobile.png',fullPage:true});
  expect(browserErrors).toEqual([]);
});

test('actual replay jobs recover without samples and expose controls, reports and authenticated bundle',async({page,context})=>{
  const browserErrors:string[]=[];page.on('pageerror',error=>browserErrors.push(error.message));
  const source=await createManual(page);await page.getByRole('button',{name:'Start',exact:true}).click();
  await expect.poll(async()=>Number((await api(page,`/runs/${source}`)).state.total_tick),{timeout:90_000}).toBeGreaterThanOrEqual(220);
  await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');
  const sourceTicks=(await api(page,`/runs/${source}`)).state.total_tick;
  await page.getByRole('button',{name:'Close run',exact:true}).click();await page.getByLabel('Recorded run',{exact:true}).selectOption(source);
  await page.getByRole('button',{name:'Action replay',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Action replay');
  await expect(page.locator('.run-heading strong')).toHaveText('running',{timeout:90_000});const actions=await runId(page);expect(actions).not.toBe(source);
  await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');
  for(const name of ['Step','Reset','Preview edit','Apply edit','Capture snapshot','Apply eye mask','Export SVG','Export PNG','Export bundle'])await expect(page.getByRole('button',{name,exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:/Focus manual drive/})).toBeDisabled();await expect(page.getByRole('img',{name:'Actual left eye policy input'})).toHaveCount(0);
  const token=(await api(page,'/session')).token;
  await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running');await page.goto('about:blank');
  const outsideStatus=async()=>{const response=await context.request.get(`/api/v1/runs/${actions}`,{headers:{'X-Palimpsest-Session':token}});expect(response.ok()).toBe(true);return response.json();};
  await expect.poll(async()=>(await outsideStatus()).jobstate).toBe('paused');const pausedTick=(await outsideStatus()).state.total_tick;
  await page.goto('/');await expect(page.locator('.connection')).toContainText('Local stream connected',{timeout:15_000});await expect(page.locator('.run-heading strong')).toHaveText('paused');
  await page.reload();await expect(page.locator('.identity')).toHaveText(`Run ${actions}`,{timeout:15_000});await expect(page.locator('.mode')).toHaveText('Action replay');await expect(page.locator('.run-heading strong')).toHaveText('paused');await expect(page.locator('.profile-line')).toContainText('sparse-navigation');
  await page.waitForTimeout(350);expect((await api(page,`/runs/${actions}`)).state.total_tick).toBe(pausedTick);
  await expect(page.getByRole('button',{name:'Preview edit',exact:true})).toBeDisabled();
  await page.screenshot({path:'test-results/actual-replay-paused.png',fullPage:true});
  await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('completed',{timeout:90_000});
  const actionReport=page.locator('.inspector details').filter({has:page.getByText('Replay verification result',{exact:true})}).locator('pre');await expect(actionReport).toContainText('"status": "passed"');
  const actionResult=JSON.parse(await actionReport.innerText());expect(actionResult.mode).toBe('actions');expect(actionResult.compared_ticks).toBe(sourceTicks);expect(actionResult.controller_reexecuted).toBe(false);
  await page.getByLabel('Recorded run',{exact:true}).selectOption('');
  const artifactRequests:string[]=[];page.on('request',request=>{if(request.url().includes('/artifacts/')){expect(request.url()).not.toMatch(/token|session=/);expect(request.headers()['x-palimpsest-session']).toBeTruthy();artifactRequests.push(request.url());}});
  await expect(page.getByRole('button',{name:'Export bundle',exact:true})).toBeEnabled();
  let released=false;page.on('response',response=>{if(response.url().endsWith(`/runs/${actions}/close`)&&response.status()===200)released=true;});page.on('request',request=>{if(request.url().endsWith(`/runs/${actions}/exports`))expect(released).toBe(true);});
  const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Export bundle',exact:true}).click();const artifact=await downloading;expect(await artifact.failure()).toBeNull();expect(artifact.suggestedFilename()).toContain(actions);const downloadPath=await artifact.path();expect(downloadPath).toBeTruthy();
  const bundle=JSON.parse(execFileSync('python',['-c',"import hashlib,json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); m=json.loads(z.read('bundle-manifest.json')); assert all(hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256'] for f in m['files']); print(json.dumps({'names':z.namelist(),'report':json.loads(z.read('replay-report.json'))}))",downloadPath!],{encoding:'utf8'}));expect(bundle.names).toContain('job-events.jsonl');expect(bundle.report.status).toBe('passed');expect(artifactRequests.length).toBeGreaterThan(0);
  await page.getByLabel('Recorded run',{exact:true}).selectOption(source);await page.getByRole('button',{name:'Policy replay',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Policy replay');await expect(page.locator('.run-heading strong')).toHaveText('completed',{timeout:90_000});
  const policyResult=JSON.parse(await actionReport.innerText());expect(policyResult.mode).toBe('policy');expect(policyResult.status).toBe('passed');expect(policyResult.controller_reexecuted).toBe(true);expect(policyResult.compared_ticks).toBe(sourceTicks);await expect(page.locator('.profile-line')).toContainText('sparse-navigation');
  await expect(page.locator('.error')).toHaveCount(0);await page.screenshot({path:'test-results/actual-replay-completed.png',fullPage:true});
  await page.getByRole('button',{name:'Action replay',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running',{timeout:90_000});await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');
  await page.getByRole('button',{name:'Stop',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('canceled',{timeout:90_000});await expect(actionReport).toContainText('"status": "cancelled"');
  expect(browserErrors).toEqual([]);expect(await page.locator('.error').count()).toBe(0);
});

test('actual trajectory overlay isolation and keyboard error recovery',async({page})=>{
  const id=await createManual(page);await expect(page.locator('.notice')).not.toContainText('Loading run');
  await page.getByRole('button',{name:'Step',exact:true}).focus();await page.keyboard.press('Enter');
  await expect.poll(async()=>(await api(page,`/runs/${id}`)).state.total_tick).toBe(1);
  const before=await api(page,`/runs/${id}`);const eventsBefore=await api(page,`/runs/${id}/events?after=0&limit=200`);
  const mutations:string[]=[];page.on('request',request=>{if(request.url().includes('/api/')&&!['GET','HEAD'].includes(request.method()))mutations.push(request.method()+' '+new URL(request.url()).pathname);});
  const toggle=page.getByLabel('Show trajectory overlays',{exact:true});await toggle.focus();await page.keyboard.press('Space');await expect(toggle).not.toBeChecked();await expect(page.locator('[data-overlay="trajectory"]')).toHaveCount(0);await page.keyboard.press('Space');await expect(toggle).toBeChecked();await expect(page.locator('[data-overlay="trajectory"]')).toHaveCount(1);
  expect(await toggle.evaluate(element=>getComputedStyle(element).outlineWidth)).toBe('3px');
  const after=await api(page,`/runs/${id}`);expect(after.sample.inputs).toEqual(before.sample.inputs);expect(after.sample.transition).toEqual(before.sample.transition);expect(after.state).toEqual(before.state);expect(await api(page,`/runs/${id}/events?after=0&limit=200`)).toEqual(eventsBefore);expect(mutations).toEqual([]);
  await page.getByLabel('X (m)',{exact:true}).fill('100');await page.getByRole('button',{name:'Preview edit',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('alert')).toBeFocused();await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'Dismiss error',exact:true})).toBeFocused();await page.keyboard.press('Enter');await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByRole('button',{name:'Preview edit',exact:true})).toBeFocused();expect((await api(page,`/runs/${id}`)).state).toEqual(before.state);
  await page.getByRole('link',{name:'Skip to run controls',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByRole('navigation',{name:'Run controls',exact:true})).toBeFocused();
});

test('actual memory inspector, U-only branch and evidence-linked route annotations',async({page})=>{
  const browserErrors:string[]=[];page.on('pageerror',error=>browserErrors.push(error.message));
  await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  await page.getByLabel('Controller',{exact:true}).selectOption('teacher');
  await page.getByLabel('Scenario',{exact:true}).selectOption('memory-passages');
  await expect(page.getByLabel('Controller',{exact:true})).toHaveValue('manual');
  await expect(page.getByLabel('Controller',{exact:true}).locator('option[value="teacher"]')).toHaveJSProperty('disabled',true);
  await page.getByRole('button',{name:'Create run',exact:true}).click();
  await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
  const source=await runId(page);await expect(page.getByRole('region',{name:'Artificial memory'})).toBeVisible();
  await expect(page.locator('.input-stage')).toContainText('bearing will be selected');
  for(let tick=0;tick<8;tick++){
    await page.getByRole('button',{name:'Step',exact:true}).click();
    await expect.poll(async()=>(await api(page,`/runs/${source}`)).state.total_tick).toBe(tick+1);
  }
  await page.getByRole('button',{name:'Capture snapshot',exact:true}).click();
  await expect(page.locator('.notice')).toHaveText('Snapshot captured.');
  await page.getByRole('button',{name:'Use displayed U',exact:true}).click();
  await expect(page.getByRole('button',{name:'Start U-only branch',exact:true})).toBeDisabled();
  const before=await api(page,`/runs/${source}`), u=structuredClone(before.sample.memory.u);
  u.payload={rules:[{relation:'local_cue',trigger:'cue_changed'}],version:1,vocabulary:'passage-relations-v1'};
  u.provenance.method='hand-authored-v1';u.payload_sha256=createHash('sha256').update(JSON.stringify(u.payload)).digest('hex');
  await page.getByRole('button',{name:'Close run',exact:true}).click();
  await page.getByLabel('U artifact JSON',{exact:true}).setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{}')});
  await expect(page.getByText('invalid.json',{exact:true})).toBeVisible();
  const count=(await api(page,'/runs')).runs.length;
  await page.getByRole('button',{name:'Start U-only branch',exact:true}).click();
  await expect(page.getByRole('alert')).toBeVisible();
  expect((await api(page,'/runs')).runs.length).toBe(count);
  await page.getByRole('button',{name:'Dismiss error',exact:true}).click();
  await page.getByLabel('U artifact JSON',{exact:true}).setInputFiles({name:'authored-local.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(u))});
  await expect(page.getByText('authored-local.json',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Start U-only branch',exact:true}).click();
  await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
  const branch=await runId(page);expect(branch).not.toBe(source);
  await expect.poll(async()=>(await api(page,`/runs/${branch}`)).sample?.memory?.tick).toBe(7);
  const initial=await api(page,`/runs/${branch}`);
  expect(initial.state.total_tick).toBe(8);
  expect(initial.sample.memory.hashes.m).toBe(before.sample.memory.hashes.m);
  expect(initial.sample.memory.hashes.e).toBe(before.sample.memory.hashes.e);
  expect(initial.sample.memory.u).toEqual(u);
  for(let tick=8;tick<12;tick++){
    await page.getByRole('button',{name:'Step',exact:true}).click();
    await expect.poll(async()=>(await api(page,`/runs/${branch}`)).state.total_tick).toBe(tick+1);
  }
  await expect(page.locator('.memory-facts')).toContainText('uncertain');
  const marker=page.locator('a[href^="#event-"]').first();await expect(marker).toBeVisible();
  const href=await marker.getAttribute('href');expect(href).toMatch(new RegExp(`^#event-${branch}-[0-9]+$`));
  await marker.focus();await page.keyboard.press('Enter');
  await expect(page.locator(href!)).toBeVisible();await expect(page.locator(href!).locator('summary')).toContainText('memory_decision');
  const paused=await api(page,`/runs/${branch}`);
  const toggle=page.getByLabel('Show trajectory overlays',{exact:true});await toggle.uncheck();
  await expect(page.locator('[data-overlay="memory"]')).toHaveCount(0);await toggle.check();
  const after=await api(page,`/runs/${branch}`);expect(after.sample.inputs).toEqual(paused.sample.inputs);
  expect(after.sample.memory).toEqual(paused.sample.memory);expect(after.state).toEqual(paused.state);
  await page.getByRole('button',{name:'Close run',exact:true}).click();
  await page.getByLabel('Recorded run',{exact:true}).selectOption(branch);
  await page.getByLabel('Transition tick',{exact:true}).fill('10');
  await page.getByRole('button',{name:'Recorded playback',exact:true}).click();
  await expect(page.locator('.mode')).toHaveText('Recorded playback');
  await expect(page.locator('.memory-facts')).toContainText('uncertain');
  await expect(page.locator('a[href^="#event-"]').first()).toBeVisible();
  const recorded=await api(page,`/runs/${branch}/playback?episode=0&tick=10`);
  expect(recorded.memory.active.fact_id).toBe('fact-passage-a');
  await page.screenshot({path:'test-results/actual-memory-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/actual-memory-mobile.png',fullPage:true});
  expect(browserErrors).toEqual([]);await expect(page.getByRole('alert')).toHaveCount(0);
});

test('measured browser responsiveness and actual display cadence',async({page},info)=>{
  test.skip(process.env.PALIMPSEST_MEASURE_UI!=='1','Opt-in measurement; serialize actual simulation jobs.');
  const {installMeter,startMeter,stopMeter,commandMetrics,cadence,windowRate,summarize,cadenceAcceptance,CADENCE_ACCEPTANCE}=await import('./measurement');await installMeter(page);
  const id=await createManual(page);await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running');
  await expect(page.getByLabel('Active real-time factor',{exact:true})).not.toContainText('unavailable');
  const first=await api(page,`/runs/${id}`);expect(first.sample.performance.active_wall_seconds).toBeGreaterThan(0);expect(first.sample.performance.rtf).toBeCloseTo(first.sample.performance.advanced_simulation_seconds/first.sample.performance.active_wall_seconds,8);
  await startMeter(page);await page.waitForTimeout(8000);const stream=await stopMeter(page);
  for(let cycle=0;cycle<5;cycle++){await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running');}
  await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');await page.waitForTimeout(150);
  const paused=await api(page,`/runs/${id}`);await page.waitForTimeout(400);const stillPaused=await api(page,`/runs/${id}`);expect(stillPaused.sample.performance).toEqual(paused.sample.performance);
  const commands=await commandMetrics(page);const acknowledgements=summarize(commands.map((command:any)=>command.ack_ms));const applications=summarize(commands.filter((command:any)=>command.applied_ms!==null).map((command:any)=>command.applied_ms));const samples=windowRate(stream.ws,stream.started,stream.ended),commits=windowRate(stream.commits,stream.started,stream.ended),paints=windowRate(stream.paint,stream.started,stream.ended),raf=windowRate(stream.raf,stream.started,stream.ended);const acceptance=cadenceAcceptance(stream.commits,stream.started,stream.ended,acknowledgements.p95);
  const report={schema_version:2,rate_method:'event count / entire declared window seconds',percentile_method:'nearest rank ceil(p*n)',run_id:id,profile:{scenario:'sparse-navigation',controller:'manual',device:'cpu'},window_ms:stream.window_ms,started_ms:stream.started,ended_ms:stream.ended,timestamp_clock:'DOMHighResTimeStamp relative to browser performance time origin',raw_timestamps_ms:{sample_arrival:stream.ws,dom_sample_commit:stream.commits,after_commit_animation_frame:stream.paint,animation_frame_opportunities:stream.raf},interarrival_cadence:{sample_arrival:cadence(stream.ws),dom_sample_commit:cadence(stream.commits),after_commit_animation_frame:cadence(stream.paint),animation_frame_opportunities:cadence(stream.raf)},sample_arrival:samples,dom_sample_commit:commits,after_commit_animation_frame:paints,animation_frame_opportunities:raf,acknowledgement_ms:acknowledgements,observed_application_ms:applications,commands,performance:paused.sample.performance,targets:CADENCE_ACCEPTANCE,cadence_acceptance:{scope:'delivered DOM display updates over the full declared window',...acceptance},meets_targets:{cadence_acceptance:acceptance.passed,emission_30hz_sample_arrival:samples.hz!==null&&samples.hz>=30,acknowledgement_p95:acknowledgements.p95!==null&&acknowledgements.p95<150},limitations:['full-window rates include leading, trailing and internal gaps; interarrival cadence is separate','timestamp arrays are capped at 2000 events per channel','animation frames are callback opportunities, not physical scanout or invented samples','ack timing starts at browser fetch dispatch and includes response body parsing; loading excluded','application timing is first authoritative applied/rejected receipt observed over WebSocket, including delivery delay','manual CPU profile only; not a full-model/GPU performance claim']};
  await info.attach('ui-performance.json',{body:JSON.stringify(report,null,2),contentType:'application/json'});const {writeFile}=await import('node:fs/promises');await writeFile(info.outputPath('ui-performance.json'),JSON.stringify(report,null,2)+'\n');console.log('UI_PERFORMANCE '+JSON.stringify(report));
  expect(samples.count).toBeGreaterThan(2);expect(commits.count).toBeGreaterThan(2);expect(commands.every((command:any)=>command.http_status===200)).toBe(true);expect(acknowledgements.count).toBeGreaterThanOrEqual(10);expect(applications.count).toBe(acknowledgements.count);await expect(page.locator('.error')).toHaveCount(0);
  if(process.env.PALIMPSEST_REQUIRE_UI_TARGETS==='1'){expect(report.cadence_acceptance,'mean >= 29 Hz, p99 gap <= 70 ms, ack p95 < 150 ms').toMatchObject({passed:true});}
});

for(const scenario of ['exploration-landmarks','encoder-homing']){
  test(`actual declared task inspection and snapshot continuation: ${scenario}`,async({page})=>{
    await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
    await page.getByLabel('Controller',{exact:true}).selectOption('teacher');
    await page.getByLabel('Scenario',{exact:true}).selectOption(scenario);
    await expect(page.getByLabel('Controller',{exact:true})).toHaveValue('manual');
    await expect(page.getByLabel('Controller',{exact:true}).locator('option[value="teacher"]')).toHaveJSProperty('disabled',true);
    await page.getByRole('button',{name:'Create run',exact:true}).click();
    await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
    const source=await runId(page);await expect(page.getByRole('region',{name:'Declared task',exact:true})).toContainText(scenario);
    await expect(page.locator('.input-stage')).toContainText('bearing will be selected');
    await page.getByRole('button',{name:'Step',exact:true}).click();
    await expect.poll(async()=>(await api(page,`/runs/${source}`)).state.total_tick).toBe(1);
    const before=await api(page,`/runs/${source}`);
    await page.getByRole('button',{name:'Capture snapshot',exact:true}).click();
    await expect(page.locator('.notice')).toHaveText('Snapshot captured.');
    await page.getByRole('button',{name:'Close run',exact:true}).click();
    await page.getByRole('button',{name:'Start branch',exact:true}).click();
    await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
    const branch=await runId(page);expect(branch).not.toBe(source);
    await expect.poll(async()=>(await api(page,`/runs/${branch}`)).sample?.task).toEqual(before.sample.task);
    await page.getByRole('button',{name:'Step',exact:true}).click();
    await expect.poll(async()=>(await api(page,`/runs/${branch}`)).state.total_tick).toBe(2);
    const after=await api(page,`/runs/${branch}`);expect(after.sample.task.last_tick).toBe(1);
    await page.getByRole('button',{name:'Close run',exact:true}).click();
    await page.getByLabel('Recorded run',{exact:true}).selectOption(branch);
    await page.getByLabel('Transition tick',{exact:true}).fill('1');
    await page.getByRole('button',{name:'Recorded playback',exact:true}).click();
    await expect(page.locator('.mode')).toHaveText('Recorded playback');
    await expect(page.getByRole('region',{name:'Declared task',exact:true})).toContainText(scenario);
    const recorded=await api(page,`/runs/${branch}/playback?episode=0&tick=1`);expect(recorded.task).toEqual(after.sample.task);
    await expect(page.getByRole('alert')).toHaveCount(0);
  });
}
