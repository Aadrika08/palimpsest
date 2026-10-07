import {test,expect} from '@playwright/test';
import {fileURLToPath} from 'node:url';

test('closed recorded runs recover snapshots and branch from the selected source',async({page})=>{
  test.setTimeout(20_000);
  const origin='http://palimpsest.test';
  const source='1'.repeat(32),other='2'.repeat(32),branch='3'.repeat(32);
  const initial='a'.repeat(32),captured='b'.repeat(32),otherSnapshot='c'.repeat(32);
  const reports={
    [source]:{run_id:source,status:'closed',state:null,snapshots:[
      {snapshot_id:initial,initial:true,revision:0,episode:0,tick:0},
      {snapshot_id:captured,revision:4,episode:0,tick:7},
    ]},
    [other]:{run_id:other,status:'closed',state:null,snapshots:[
      {snapshot_id:otherSnapshot,initial:true,revision:0,episode:0,tick:0},
    ]},
  };
  const profiles={scenarios:[{id:'reproduction',label:'Reproduction'}],controllers:[{id:'manual',label:'Manual'}],textures:[{id:'checker',label:'Checker'}]};
  const pageErrors:string[]=[],unexpected:string[]=[];
  const branchBodies:unknown[]=[];
  page.on('pageerror',error=>pageErrors.push(error.message));
  // Every HTTP request and WebSocket is intercepted; no lab service is started.
  await page.routeWebSocket(/.*/,socket=>{
    expect(socket.url()).toBe('ws://palimpsest.test/api/v1/stream');
    socket.onMessage(message=>expect(JSON.parse(String(message))).toEqual({token:'fixture-session'}));
  });
  await page.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),path=url.pathname;
    if(url.origin===origin&&request.method()==='GET'){
      if(path==='/'||/^\/assets\/[A-Za-z0-9_.-]+\.(js|css)$/.test(path)){
        await route.fulfill({path:fileURLToPath(new URL(`../dist/${path==='/'?'index.html':path.slice(1)}`,import.meta.url))});return;
      }
      if(path==='/api/v1/session'){await route.fulfill({json:{token:'fixture-session'}});return;}
      if(path==='/api/v1/profiles'){await route.fulfill({json:profiles});return;}
      if(path==='/api/v1/runs'){await route.fulfill({json:{runs:[source,other].map(run_id=>({run_id,status:'closed',controller:'manual',scenario:'reproduction'}))}});return;}
      const report=reports[path.slice('/api/v1/runs/'.length)];
      if(path.startsWith('/api/v1/runs/')&&report){await route.fulfill({json:report});return;}
      if(path===`/api/v1/runs/${branch}`){await route.fulfill({json:{run_id:branch,status:'loading',state:null}});return;}
    }
    if(url.origin===origin&&path==='/api/v1/branches'&&request.method()==='POST'){
      expect(request.headers()['x-palimpsest-session']).toBe('fixture-session');
      branchBodies.push(request.postDataJSON());
      await route.fulfill({status:202,json:{run_id:branch,status:'loading'}});return;
    }
    unexpected.push(`${request.method()} ${request.url()}`);await route.abort();
  });
  await page.goto(origin);
  await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled({timeout:2500});
  await expect(page.locator('.identity')).toHaveText('Run not created');
  const snapshots=page.getByLabel('Snapshot',{exact:true});
  await page.getByLabel('Recorded run',{exact:true}).selectOption(source);
  await expect(snapshots.locator('option')).toHaveCount(3,{timeout:2500});
  await expect(snapshots.locator(`option[value="${initial}"]`)).toHaveCount(1);
  await expect(snapshots.locator(`option[value="${captured}"]`)).toHaveCount(1);
  await page.getByLabel('Recorded run',{exact:true}).selectOption(other);
  await expect(snapshots.locator('option')).toHaveCount(4);
  await expect(snapshots.locator(`option[value="${captured}"]`)).toHaveCount(1);
  await expect(snapshots.locator(`option[value="${otherSnapshot}"]`)).toHaveCount(1);
  await page.getByLabel('Recorded run',{exact:true}).selectOption(source);
  await expect(page.getByRole('button',{name:'Create run',exact:true})).toBeEnabled();
  await expect(snapshots.locator('option')).toHaveCount(4);
  await snapshots.selectOption(captured);
  await page.getByRole('button',{name:'Start branch',exact:true}).click();
  await expect(page.locator('.identity')).toHaveText(`Run ${branch}`);
  expect(branchBodies).toEqual([{source_run_id:source,snapshot_id:captured}]);
  expect(unexpected).toEqual([]);
  expect(pageErrors).toEqual([]);
});
