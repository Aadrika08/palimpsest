import {test,expect,type Page,type BrowserContext} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdtempSync,readFileSync,readdirSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,extname,resolve} from 'node:path';

// Real-browser checks for the six-mode offline encounter. The pack is served from
// its ZIP through request interception at an unroutable origin; every other request
// is aborted and recorded, so the page runs with the network blocked.
// Default: the committed encounter v1 pack and its committed input manifest.
// PALIMPSEST_ARTWORK_PACK selects a rebuilt pack (artwork materials v1), which
// carries its own inputs-manifest.json and declaration.json (declared durations).
const REPO=resolve(process.cwd(),'..');  // Playwright runs from ui/
const PACK=process.env.PALIMPSEST_ARTWORK_PACK??join(REPO,'docs/reports/artwork-encounter-v1-evidence/palimpsest-offline-encounter-v1.zip');
let INPUTS:any;let DECLARED:any=null;
const ORIGIN='http://artwork.invalid';
const TYPES:Record<string,string>={'.html':'text/html; charset=utf-8','.svg':'image/svg+xml','.wav':'audio/wav','.json':'application/json','.md':'text/markdown; charset=utf-8','.png':'image/png'};
const PEAK_LIMIT=10**(-1/20); // -1 dBFS

let root='';const files:Record<string,Buffer>={};
const record=(name:string,value:unknown)=>{const body=JSON.stringify(value,null,1);writeFileSync(test.info().outputPath(name),body+'\n');return test.info().attach(name,{body,contentType:'application/json'});};
const sha=(data:Buffer|string)=>createHash('sha256').update(data).digest('hex');
const input=(path:string)=>{const row=INPUTS.files.find((f:any)=>f.path===path);if(!row)throw Error(`input manifest lacks ${path}`);return row.sha256;};

test.beforeAll(()=>{
  root=mkdtempSync(join(tmpdir(),'artwork-encounter-'));
  execFileSync('python3',['-I','-c','import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',PACK,root]);
  for(const name of readdirSync(root,{recursive:true}) as string[]){try{files[name]=readFileSync(join(root,name));}catch{/* directory */}}
  INPUTS=files['inputs-manifest.json']?JSON.parse(files['inputs-manifest.json'].toString()):JSON.parse(readFileSync(join(REPO,'docs/reports/artwork-review-development-evidence/input-manifest.json'),'utf8'));
  if(files['declaration.json'])DECLARED=JSON.parse(files['declaration.json'].toString());
  const checksums=JSON.parse(files['checksums.json'].toString()).files;
  for(const [name,row] of Object.entries<any>(checksums)){expect(sha(files[name]),name).toBe(row.sha256);expect(files[name].length).toBe(row.size_bytes);}
});
test.afterAll(()=>{if(root)rmSync(root,{recursive:true,force:true});});

async function serve(context:BrowserContext){
  const blocked:string[]=[];
  await context.route('**/*',async route=>{const url=new URL(route.request().url());
    const name=decodeURIComponent(url.pathname.replace(/^\//,''))||'index.html';
    if(url.origin===ORIGIN&&files[name])return route.fulfill({status:200,body:files[name],contentType:TYPES[extname(name)]??'application/octet-stream'});
    blocked.push(route.request().url());return route.abort('blockedbyclient');});
  return blocked;
}
function metadata(svg:string){const raw=/<metadata[^>]*>([\s\S]*?)<\/metadata>/.exec(svg)![1];
  return JSON.parse(raw.replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'));}
function plmp(wav:Buffer){let pos=12;while(pos<wav.length){const id=wav.toString('ascii',pos,pos+4),size=wav.readUInt32LE(pos+4);if(id==='plmp')return JSON.parse(wav.toString('utf8',pos+8,pos+8+size));pos+=8+size+(size&1);}throw Error('no plmp chunk');}
async function open(page:Page,path='index.html'){await page.goto(`${ORIGIN}/${path}`);}
// Declared Afterimage source duration: frames x their declared spacing (10 fps -> 0.1 s).
function after_seconds(meta:any){const times=meta.stimulus.manifest.source_times_seconds;return times.length*(times.length>1?(times[1]-times[0]):0);}
function choirSeconds(choir:any){return choir.timing.ticks?choir.timing.ticks.length*choir.timing.control_interval_seconds:(choir.timing.end_tick_inclusive-choir.timing.start_tick+1)*choir.timing.control_interval_seconds;}

test('artwork pack provenance matches the committed input manifest',()=>{
  const afterimage=metadata(files['afterimage.svg'].toString());
  for(const [path,hash] of Object.entries(afterimage.recording_files_sha256))expect(hash,path).toBe(input(`runs/${afterimage.source_run_id}/${path}`));
  const choir=plmp(files['counterfactual-choir.wav']);const choirRun=INPUTS.run_ids.choir??INPUTS.run_ids.left;
  for(const file of choir.source.files)expect(file.sha256,file.path).toBe(input(`runs/${choirRun}/${file.path}`));
  expect(sha(files['counterfactual-choir.wav'].subarray(44,44+files['counterfactual-choir.wav'].readUInt32LE(40)))).toBe(choir.pcm_sha256);
  const body=metadata(files['borrowed-body.svg'].toString());expect(Object.values(INPUTS.run_ids)).toContain(body.run_id);
  const atlas=metadata(files['atlas.svg'].toString());expect(atlas.source.graph_sha256).toBe(input('graph/source-graph.json'));expect(atlas.source.graph_manifest_sha256).toBe(input('graph/extraction.json'));
  const pair=metadata(files['space-between-two-flies.svg'].toString());expect(pair.manifest_sha256).toBe(input('specimens/pair.json'));
  for(const specimen of pair.manifest.specimens)expect(specimen.sha256,specimen.file).toBe(input(`specimens/${specimen.file}`));
  const map=files['one-map-many-lives.html'].toString();for(const id of [INPUTS.run_ids.left,INPUTS.run_ids.right])expect(map).toContain(id);
});

test('six modes render faithful counts with labels at 1440 and 390 px, offline',async({page,context})=>{
  const blocked=await serve(context);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:width===390?844:1000});await open(page);
    await expect(page.getByRole('navigation',{name:'Artwork modes'}).getByRole('link')).toHaveText(['Afterimage','Borrowed body','One map, many possible lives','Counterfactual choir','Atlas of what disappears','The space between two flies']);
    for(const id of ['afterimage','borrowed-body','one-map','choir','atlas','specimens']){const section=page.locator(`section#${id}`);await section.scrollIntoViewIfNeeded();await expect(section.getByRole('heading',{level:2})).toBeVisible();
      await expect(section.getByRole('link',{name:/original artifact|Open/}).first()).toBeVisible();}
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`no horizontal scroll at ${width}px`).toBe(true);
    await page.screenshot({path:test.info().outputPath(`encounter-${width}.png`),fullPage:true});
  }
  // Visual element counts against each artifact's own source metadata.
  const counts:Record<string,unknown>={};
  const afterimage=metadata(files['afterimage.svg'].toString());await open(page,'afterimage.svg');
  counts.afterimage=await page.evaluate(()=>document.querySelector('polyline')!.points.length);expect(counts.afterimage).toBe(afterimage.alignment.length);
  const body=metadata(files['borrowed-body.svg'].toString());await open(page,'borrowed-body.svg');
  counts.borrowed_body=await page.evaluate(()=>document.querySelector('polyline')!.points.length);expect(counts.borrowed_body).toBe(body.traces[0].points.length);
  const atlas=metadata(files['atlas.svg'].toString());await open(page,'atlas.svg');
  counts.atlas=await page.evaluate(()=>({dashed:document.querySelectorAll('path[stroke-dasharray]').length,paths:document.querySelectorAll('path').length}));
  expect((counts.atlas as any).dashed).toBe(atlas.removed_edges.length??atlas.removed_edges);expect((counts.atlas as any).paths).toBeGreaterThanOrEqual(atlas.edges_before+atlas.edges_after);
  const pair=metadata(files['space-between-two-flies.svg'].toString());await open(page,'space-between-two-flies.svg');
  counts.specimens=await page.evaluate(()=>[...document.querySelectorAll('path')].map(p=>(p.getAttribute('d')!.match(/M/g)??[]).length).filter(n=>n>1));
  expect(counts.specimens).toEqual(pair.structures.map((s:any)=>s.edges));
  for(const name of ['afterimage.svg','borrowed-body.svg','atlas.svg','space-between-two-flies.svg']){await open(page,name);
    expect(await page.evaluate(()=>!!document.querySelector('svg > title, svg title')&&!!document.querySelector('svg desc')),name).toBe(true);}
  await open(page,'one-map-many-lives.html');
  counts.one_map=await page.evaluate(()=>[...document.querySelectorAll('polyline')].map(p=>p.points.length));
  expect(new Set(counts.one_map as number[])).toEqual(new Set(DECLARED?DECLARED.one_map_route_points:[1268,1293]));
  if(DECLARED){expect(counts.afterimage).toBe(DECLARED.afterimage_frames);expect(after_seconds(afterimage)).toBeCloseTo(DECLARED.afterimage_source_seconds,6);
    expect(body.traces.map((t:any)=>t.points.length)).toEqual(DECLARED.borrowed_body_route_points);}
  await record('visual-counts.json',counts);
  expect(blocked).toEqual([]);expect(errors).toEqual([]);
});

test('keyboard reaches every control in order; Afterimage previous and next',async({page,context})=>{
  const blocked=await serve(context);await open(page);
  const order:string[]=[];
  for(let i=0;i<40;i++){await page.keyboard.press('Tab');const name=await page.evaluate(()=>{const e=document.activeElement as HTMLElement;return e?`${e.tagName.toLowerCase()}:${(e.getAttribute('aria-label')??e.textContent??'').trim().slice(0,40)}`:'';});order.push(name);if(name.startsWith('body'))break;}
  const modes=order.filter(n=>n.startsWith('a:')).slice(0,6);
  expect(modes).toEqual(['a:Afterimage','a:Borrowed body','a:One map, many possible lives','a:Counterfactual choir','a:Atlas of what disappears','a:The space between two flies']);
  expect(order.indexOf('summary:Inspect recorded responses one at a time')).toBeGreaterThan(order.indexOf('a:The space between two flies'));
  expect(order.some(n=>n.startsWith('audio'))).toBe(true);expect(order.some(n=>n.startsWith('button:Stop'))).toBe(true);
  await record('tab-order.json',order);
  const summary=page.getByText('Inspect recorded responses one at a time');await summary.focus();await page.keyboard.press('Enter');
  const total=metadata(files['afterimage.svg'].toString()).alignment.length;
  const status=page.locator('#frame-status');await expect(status).toContainText(`Frame 1 of ${total}`);
  const previous=page.getByRole('button',{name:'Previous frame'}),next=page.getByRole('button',{name:'Next frame'});
  await expect(previous).toBeDisabled();
  const eyes=async()=>page.evaluate(()=>['eye-left','eye-right'].map(id=>{const image=document.getElementById(id) as HTMLImageElement|null;return image?{complete:image.complete,width:image.naturalWidth,src:image.getAttribute('src')}:null;}));
  if(DECLARED){await expect.poll(async()=>(await eyes()).map(e=>e&&e.width)).toEqual([128,128]);}
  await next.focus();
  for(let frame=2;frame<=total;frame++){await page.keyboard.press('Enter');await expect(status).toContainText(`Frame ${frame} of ${total}`);}
  await expect(next).toBeDisabled();await previous.focus();await page.keyboard.press('Space');await expect(status).toContainText(`Frame ${total-1} of ${total}`);
  expect(await page.locator('#prefix').evaluate((p:SVGPolylineElement)=>p.points.length)).toBe(total-1);
  if(DECLARED){await expect.poll(async()=>(await eyes()).map(e=>e&&e.width)).toEqual([128,128]);
    expect((await eyes()).map(e=>e!.src)).toEqual([`afterimage-eyes/${String(total-1).padStart(4,'0')}-left.png`,`afterimage-eyes/${String(total-1).padStart(4,'0')}-right.png`]);}
  expect(blocked).toEqual([]);
});

test('choir: no autoplay, keyboard play and stop, decoded audio matches its declaration',async({page,context})=>{
  const blocked=await serve(context);await open(page);
  const choir=plmp(files['counterfactual-choir.wav']);
  const declared=choirSeconds(choir);if(DECLARED)expect(declared).toBeCloseTo(DECLARED.choir_seconds,6);
  test.setTimeout((declared+120)*1000);
  const audio=page.locator('section#choir audio');await audio.scrollIntoViewIfNeeded();await page.waitForTimeout(1000);
  expect(await audio.evaluate((a:HTMLAudioElement)=>({paused:a.paused,time:a.currentTime,autoplay:a.autoplay}))).toEqual({paused:true,time:0,autoplay:false});
  // Decode the stored bytes at 48 kHz in a blank page (the encounter's CSP forbids
  // fetch): duration, rate, energy and peak of exactly the shipped file.
  const probe=await context.newPage();await probe.goto('about:blank');
  const decoded=await probe.evaluate(async(base64:string)=>{const data=Uint8Array.from(atob(base64),c=>c.charCodeAt(0)).buffer;
    const buffer=await new OfflineAudioContext(1,48000,48000).decodeAudioData(data);const samples=buffer.getChannelData(0);
    let peak=0,sum=0;for(const value of samples){peak=Math.max(peak,Math.abs(value));sum+=value*value;}
    return {duration:buffer.duration,sampleRate:buffer.sampleRate,channels:buffer.numberOfChannels,peak,rms:Math.sqrt(sum/samples.length)};},files['counterfactual-choir.wav'].toString('base64'));
  await probe.close();
  expect(decoded.sampleRate).toBe(choir.mapping.sample_rate_hz);expect(decoded.channels).toBe(1);
  expect(Math.abs(decoded.duration-declared)).toBeLessThan(1/48000+1e-9);
  expect(decoded.rms).toBeGreaterThan(1e-3);expect(decoded.peak).toBeLessThanOrEqual(PEAK_LIMIT);
  // Keyboard play on the native control, then the explicit stop button.
  await audio.focus();await page.keyboard.press('Space');await expect.poll(()=>audio.evaluate((a:HTMLAudioElement)=>!a.paused&&a.currentTime>0)).toBe(true);
  const stop=page.getByRole('button',{name:/Stop/});await stop.focus();await page.keyboard.press('Enter');
  expect(await audio.evaluate((a:HTMLAudioElement)=>({paused:a.paused,time:a.currentTime}))).toEqual({paused:true,time:0});
  // A full play ends at the declared length.
  await audio.focus();const played=await audio.evaluate(async(a:HTMLAudioElement)=>{const start=performance.now();await a.play();
    return await new Promise<{elapsed:number;duration:number}>(resolve=>a.addEventListener('ended',()=>resolve({elapsed:(performance.now()-start)/1000,duration:a.duration}),{once:true}));});
  expect(Math.abs(played.duration-declared)).toBeLessThan(.01);expect(Math.abs(played.elapsed-declared)).toBeLessThan(1.5);
  await record('choir-audio.json',{declared_seconds:declared,decoded,played,peak_dbfs:20*Math.log10(decoded.peak)});
  expect(blocked).toEqual([]);
});
