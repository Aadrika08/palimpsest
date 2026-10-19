import assert from 'node:assert/strict';
import {busyTracker} from '../src/busy.ts';

// Overlapping UI operations (e.g. Close run, then a Recorded run selection) must
// keep controls busy until the last one settles; v5 rehearsal 2 clicked Action
// replay while Close run was still in flight and got HTTP 409.
const states:boolean[]=[];const tracker=busyTracker(value=>states.push(value));
let finishClose!:()=>void;const close=tracker.run(()=>new Promise<void>(resolve=>{finishClose=resolve;}));
const select=tracker.run(async()=>{});
await select;
assert.equal(states.at(-1),true,'a fast second operation must not clear busy while the first is pending');
finishClose();await close;
assert.equal(states.at(-1),false);
await assert.rejects(tracker.run(async()=>{throw new Error('boom');}),/boom/);
assert.equal(states.at(-1),false,'a failed operation still releases busy');
console.log('Busy checks passed: overlapping operations keep controls busy until all settle.');
