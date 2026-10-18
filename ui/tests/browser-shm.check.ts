import assert from 'node:assert/strict';
import {readFileSync,readdirSync,readlinkSync,statfsSync} from 'node:fs';
import {chromium} from '@playwright/test';
import config from '../playwright.config.ts';

// Chromium backs fetch/WebSocket data pipes, compositor and decoded-image memory
// with shared-memory files. Playwright passes --disable-dev-shm-usage by default,
// which moves them into TMPDIR (/tmp here): the tmpfs that campaigns and test
// suites fill. Near-full /tmp then fails lab requests with
// net::ERR_INSUFFICIENT_RESOURCES (manual lab refresh v3). The lab browser must
// keep them on /dev/shm instead.
function descendants(pid:number):number[]{
  const found:number[]=[];const stack=[pid];
  while(stack.length){const current=stack.pop()!;let tasks:string[]=[];try{tasks=readdirSync(`/proc/${current}/task`);}catch{continue;}
    for(const task of tasks){let children:string[]=[];try{children=readFileSync(`/proc/${current}/task/${task}/children`,'utf8').split(/\s+/).filter(Boolean);}catch{continue;}
      for(const child of children.map(Number))if(!found.includes(child)){found.push(child);stack.push(child);}}}
  return found;
}
function sharedMemoryPaths(){
  const paths=new Set<string>();
  for(const pid of descendants(process.pid)){
    try{for(const line of readFileSync(`/proc/${pid}/maps`,'utf8').split('\n')){const path=line.split(/\s+/).slice(5).join(' ');if(path.includes('.org.chromium.'))paths.add(path.replace(/ \(deleted\)$/,''));}}catch{}
    try{for(const fd of readdirSync(`/proc/${pid}/fd`)){try{const target=readlinkSync(`/proc/${pid}/fd/${fd}`);if(target.includes('.org.chromium.'))paths.add(target.replace(/ \(deleted\)$/,''));}catch{}}}catch{}
  }
  return [...paths];
}

const shm=statfsSync('/dev/shm');
const browser=await chromium.launch({...config.use?.launchOptions,headless:true});
try{
  const page=await browser.newPage();
  await page.setContent('<p>shared memory probe</p>');
  // Drive a few response-body data pipes through the network service.
  for(let i=0;i<3;i++)await page.evaluate(async()=>(await fetch('data:text/plain,'+'x'.repeat(4096))).text());
  const paths=sharedMemoryPaths();
  assert.ok(paths.length>0,'expected Chromium shared-memory files to be observable');
  const outside=paths.filter(path=>!path.startsWith('/dev/shm/'));
  assert.deepEqual(outside,[],`Chromium shared memory must stay on /dev/shm, not TMPDIR: ${outside.slice(0,3).join(', ')}`);
  console.log(`browser shared-memory check passed: ${paths.length} regions on /dev/shm (${Math.floor(shm.bavail*shm.bsize/2**20)} MiB free)`);
}finally{await browser.close();}
