import assert from 'node:assert/strict';
import {memoryAnnotations} from '../src/memory-events.ts';

const event={kind:'memory_decision',run_id:'source',episode:2,episode_step:8,sequence:42,
  detail:{kind:'memory_revision'},route_anchor:{stage:'pre-control',xy:[1.25,-2]}};
const sample={run_id:'source',inputs:{episode:2,tick:8}};
const before=JSON.stringify(event);
// The view receives a full Sample; this fixture only exercises its two cursor fields.
const annotations=memoryAnnotations([event],sample as Parameters<typeof memoryAnnotations>[1]);
assert.deepEqual(annotations,[{sequence:42,episode:2,tick:8,xy:[1.25,-2],label:'revision',href:'#event-source-42'}]);
for(const changed of [{run_id:'different'},{episode:1},{episode_step:9},{sequence:-1},
  {detail:{kind:'memory_bridge'}},{route_anchor:{stage:'after-control',xy:[1,2]}},
  {route_anchor:{stage:'pre-control',xy:[NaN,2]}}]) {
  assert.deepEqual(memoryAnnotations([{...event,...changed}],sample as Parameters<typeof memoryAnnotations>[1]),[]);
}
assert.equal(JSON.stringify(event),before);
assert.equal(memoryAnnotations(Array.from({length:40},(_,sequence)=>({...event,sequence})),sample as Parameters<typeof memoryAnnotations>[1]).length,32);
console.log('Memory annotation checks passed: evidence pointer, exact coordinates, cursor isolation, bounds, immutability.');
