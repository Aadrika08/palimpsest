import assert from 'node:assert/strict';
import {RUN_WINDOW,windowRuns,windowSnapshots} from '../src/run-window.ts';

// A bounded window keeps selects small while every run stays reachable by search.
const runs=Array.from({length:90},(_,i)=>({run_id:i.toString(16).padStart(32,'0'),controller:i%2?'teacher':'manual',scenario:'sparse-navigation'}));
const ids=(view:{runs:{run_id:string}[]})=>view.runs.map(r=>r.run_id);
assert.equal(RUN_WINDOW,20);
const plain=windowRuns(runs,{query:'',pinned:[],recent:[]});
assert.equal(plain.runs.length,20);assert.equal(plain.hidden,70);assert.equal(plain.total,90);
// Session-recent runs come first, newest first; selected values are always present.
const recent=[runs[89].run_id,runs[88].run_id];const pinned=[runs[3].run_id,'',runs[89].run_id];
const view=windowRuns(runs,{query:'',pinned,recent});
assert.deepEqual(ids(view).slice(0,3),[runs[3].run_id,runs[89].run_id,runs[88].run_id]);
assert.equal(view.runs.length,20);assert.equal(new Set(ids(view)).size,20);
// Search reaches any run by id fragment, controller or scenario; pins stay visible.
assert.deepEqual(ids(windowRuns(runs,{query:runs[45].run_id.slice(-4),pinned:[],recent:[]})),[runs[45].run_id]);
assert.deepEqual(ids(windowRuns(runs,{query:' '+runs[45].run_id.slice(-6).toUpperCase()+' ',pinned:[runs[3].run_id],recent:[]})),[runs[3].run_id,runs[45].run_id]);
assert.equal(windowRuns(runs,{query:'teacher',pinned:[],recent:[]}).runs.every(r=>r.controller==='teacher'),true);
assert.equal(windowRuns(runs,{query:'teacher',pinned:[],recent:[]}).total,45);
// Unknown recent/pinned ids (not yet listed by the server) are kept as bare entries.
assert.deepEqual(ids(windowRuns([],{query:'',pinned:['f'.repeat(32)],recent:['e'.repeat(32)]})),['f'.repeat(32),'e'.repeat(32)]);
// Every one of the 90 runs is reachable through search alone.
for(const run of runs)assert.ok(ids(windowRuns(runs,{query:run.run_id,pinned:[],recent:[]})).includes(run.run_id));
// Snapshots: newest last in state; the window keeps the chosen one and the newest, or search matches.
const snaps=Array.from({length:60},(_,i)=>({run_id:runs[i].run_id,snapshot_id:'s'+i,revision:i}));
const sv=windowSnapshots(snaps,{query:'',chosen:'s2'});
assert.equal(sv.snapshots.length,20);assert.equal(sv.snapshots[0].snapshot_id,'s2');assert.equal(sv.snapshots.at(-1)!.snapshot_id,'s59');assert.equal(sv.hidden,40);
assert.deepEqual(windowSnapshots(snaps,{query:runs[7].run_id,chosen:''}).snapshots.map(s=>s.snapshot_id),['s7']);
assert.deepEqual(windowSnapshots(snaps,{query:'s1',chosen:''}).snapshots.length,11);
console.log('Run window checks passed: bounded selects, pinned and recent runs, search reaches every run and snapshot.');
