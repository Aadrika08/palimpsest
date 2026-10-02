import {test,expect,type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';

async function api(page:Page,path:string,body?:unknown){return page.evaluate(async({path,body})=>{const token=(await(await fetch('/api/v1/session')).json()).token;const response=await fetch('/api/v1'+path,{method:body===undefined?'GET':'POST',headers:{'X-Palimpsest-Session':token,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});const value=await response.json();if(!response.ok)throw Error(`${response.status}: ${JSON.stringify(value)}`);return value;},{path,body});}
async function validPlacement(page:Page,kind:'move_goal'|'move_obstacle',different?:number[]){const id=(await page.locator('.identity').innerText()).replace('Run ','');return page.evaluate(async({id,kind,different})=>{const token=(await(await fetch('/api/v1/session')).json()).token;const headers={'X-Palimpsest-Session':token,'Content-Type':'application/json'};const state=(await(await fetch(`/api/v1/runs/${id}`,{headers})).json()).state;for(const x of [-5,-3,0,3,5])for(const y of [-5,-3,0,3,5]){if(different&&x===different[0]&&y===different[1])continue;const payload=kind==='move_goal'?{kind,xy:[x,y]}:{kind,index:0,xy:[x,y]};const result=await fetch(`/api/v1/runs/${id}/previews`,{method:'POST',headers,body:JSON.stringify({payload,expected_revision:state.revision})});if(result.ok)return[x,y];}throw Error('No valid placement in actual scenario');},{id,kind,different});}
async function fillEdit(page:Page,kind:'move_goal'|'move_obstacle',xy:number[]){await page.getByLabel('Edit',{exact:true}).selectOption(kind);await page.getByLabel('X (m)',{exact:true}).fill(String(xy[0]));await page.getByLabel('Y (m)',{exact:true}).fill(String(xy[1]));}
async function runId(page:Page){return(await page.locator('.identity').innerText()).replace('Run ','');}
async function createManual(page:Page){await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');await page.getByLabel('Controller',{exact:true}).selectOption('manual');await page.getByRole('button',{name:'Create run',exact:true}).click();await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});return runId(page);}

test.afterEach(async({page})=>{await page.evaluate(async()=>{const id=document.querySelector('.identity')?.textContent?.replace('Run ','');if(!id||! /^[0-9a-f]{32}$/.test(id))return;const token=(await(await fetch('/api/v1/session')).json()).token;await fetch(`/api/v1/runs/${id}/close`,{method:'POST',headers:{'X-Palimpsest-Session':token,'Content-Type':'application/json'},body:'{}'});}).catch(()=>{});});

test('actual local manual workflow, snapshots, sequential branches, comparison and export',async({page})=>{
  const browserErrors:string[]=[];page.on('pageerror',error=>browserErrors.push(error.message));
  await page.goto('/');await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  await page.getByLabel('Scenario',{exact:true}).selectOption('sparse-navigation');
  await page.getByLabel('Controller',{exact:true}).selectOption('manual');
  await page.getByRole('button',{name:'Create run',exact:true}).click();
  await expect(page.getByRole('button',{name:'Step',exact:true})).toBeEnabled({timeout:90_000});
  await expect(page.getByRole('img',{name:'Actual left eye policy input'})).toBeVisible();
  const source=await page.locator('.identity').innerText();
  await page.getByRole('button',{name:'Start',exact:true}).click();
  await expect(page.locator('.run-heading strong')).toHaveText('running');
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
  for(const name of ['Step','Reset','Preview edit','Apply edit','Capture snapshot','Apply eye mask'])await expect(page.getByRole('button',{name,exact:true})).toBeDisabled();
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
  const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Export bundle',exact:true}).click();const artifact=await downloading;expect(await artifact.failure()).toBeNull();expect(artifact.suggestedFilename()).toContain(actions);const downloadPath=await artifact.path();expect(downloadPath).toBeTruthy();
  const bundle=JSON.parse(execFileSync('python',['-c',"import hashlib,json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); m=json.loads(z.read('bundle-manifest.json')); assert all(hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256'] for f in m['files']); print(json.dumps({'names':z.namelist(),'report':json.loads(z.read('replay-report.json'))}))",downloadPath!],{encoding:'utf8'}));expect(bundle.names).toContain('job-events.jsonl');expect(bundle.report.status).toBe('passed');expect(artifactRequests.length).toBeGreaterThan(0);
  await page.getByLabel('Recorded run',{exact:true}).selectOption(source);await page.getByRole('button',{name:'Policy replay',exact:true}).click();await expect(page.locator('.mode')).toHaveText('Policy replay');await expect(page.locator('.run-heading strong')).toHaveText('completed',{timeout:90_000});
  const policyResult=JSON.parse(await actionReport.innerText());expect(policyResult.mode).toBe('policy');expect(policyResult.status).toBe('passed');expect(policyResult.controller_reexecuted).toBe(true);expect(policyResult.compared_ticks).toBe(sourceTicks);await expect(page.locator('.profile-line')).toContainText('sparse-navigation');
  await expect(page.locator('.error')).toHaveCount(0);await page.screenshot({path:'test-results/actual-replay-completed.png',fullPage:true});
  await page.getByRole('button',{name:'Action replay',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('running',{timeout:90_000});await page.getByRole('button',{name:'Pause',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('paused');
  await page.getByRole('button',{name:'Stop',exact:true}).click();await expect(page.locator('.run-heading strong')).toHaveText('canceled',{timeout:90_000});await expect(actionReport).toContainText('"status": "cancelled"');
  expect(browserErrors).toEqual([]);expect(await page.locator('.error').count()).toBe(0);
});
