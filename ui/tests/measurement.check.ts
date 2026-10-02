import assert from 'node:assert/strict';
import {cadence,windowRate} from './measurement.ts';

const timestamps=[1000,1100,1200];
assert.equal(cadence(timestamps).hz,10);
assert.deepEqual(windowRate(timestamps,0,8000),{count:3,window_ms:8000,hz:0.375});
assert.equal(windowRate([],0,8000).hz,0);
assert.equal(windowRate([1000],0,8000).hz,0.125);
assert.equal(windowRate([1],1,1).hz,null);
assert.equal(windowRate([1],2,1).hz,null);
assert.equal(windowRate([1],NaN,2).hz,null);
console.log('7 measurement checks passed; full-window gaps remain in the rate.');
