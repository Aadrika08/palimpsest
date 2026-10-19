import assert from 'node:assert/strict';
import {cadence,windowRate,cadenceAcceptance,CADENCE_ACCEPTANCE} from './measurement.ts';

const timestamps=[1000,1100,1200];
assert.equal(cadence(timestamps).hz,10);
assert.deepEqual(windowRate(timestamps,0,8000),{count:3,window_ms:8000,hz:0.375});
assert.equal(windowRate([],0,8000).hz,0);
assert.equal(windowRate([1000],0,8000).hz,0.125);
assert.equal(windowRate([1],1,1).hz,null);
assert.equal(windowRate([1],2,1).hz,null);
assert.equal(windowRate([1],NaN,2).hz,null);
// Decided v4 acceptance: 30 Hz emission, delivered mean >= 29 Hz, p99 gap <= 70 ms, ack p95 < 150 ms.
assert.deepEqual(CADENCE_ACCEPTANCE,{emission_hz:30,display_mean_hz_min:29,interarrival_p99_ms_max:70,acknowledgement_p95_ms_below:150});
const even=Array.from({length:240},(_,i)=>i*1000/30);
const ok=cadenceAcceptance(even,0,8000,20);assert.equal(ok.passed,true);assert.equal(ok.mean_hz,30);assert.ok(Math.abs(ok.interarrival_p99_ms!-33.333)<.01);
// One 66 ms coalesced gap in 240 is within tolerance; mean 29.875 Hz.
const coalesced=even.filter((_,i)=>i!==120);const tolerant=cadenceAcceptance(coalesced,0,8000,20);assert.equal(tolerant.passed,true);assert.equal(tolerant.mean_hz,29.875);
// Below 29 Hz mean fails even with regular gaps.
assert.equal(cadenceAcceptance(Array.from({length:225},(_,i)=>i*35.7),0,8041,20).passed,false);
// A 3% tail of 80 ms gaps fails the p99 gap bound while the mean still passes.
const gappy:number[]=[];let t=0;for(let i=0;i<240;i++){gappy.push(t);t+=i%30===0?80:32;}assert.ok(cadenceAcceptance(gappy,0,gappy.at(-1)!+1,20).mean_hz!>=29);assert.equal(cadenceAcceptance(gappy,0,gappy.at(-1)!+1,20).passed,false);
// Acknowledgement p95 must stay below 150 ms; missing data never passes.
assert.equal(cadenceAcceptance(even,0,8000,150).passed,false);assert.equal(cadenceAcceptance(even,0,8000,null).passed,false);assert.equal(cadenceAcceptance([],0,8000,20).passed,false);
console.log('15 measurement checks passed; full-window gaps remain in the rate.');
