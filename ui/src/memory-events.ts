import type {Event, Sample} from './protocol';

export type MemoryAnnotation = {sequence:number;episode:number;tick:number;xy:[number,number];label:string;href:string};

export function memoryAnnotations(events:Event[], sample?:Pick<Sample,'run_id'|'inputs'>):MemoryAnnotation[] {
  if(!sample) return [];
  const result:MemoryAnnotation[]=[];
  for(const event of events) {
    if(event.kind!=='memory_decision'||event.run_id!==sample.run_id||event.episode!==sample.inputs.episode) continue;
    const tick=event.episode_step, sequence=event.sequence;
    if(typeof tick!=='number'||!Number.isInteger(tick)||tick<0||tick>sample.inputs.tick||typeof sequence!=='number'||!Number.isInteger(sequence)||sequence<0) continue;
    const detail=event.detail as {kind?:string}|undefined, anchor=event.route_anchor as {stage?:string;xy?:unknown[]}|undefined;
    if(!detail||!['memory_selection','memory_revision','memory_inspection'].includes(detail.kind??'')||anchor?.stage!=='pre-control'||!Array.isArray(anchor.xy)||anchor.xy.length!==2||!anchor.xy.every(v=>typeof v==='number'&&Number.isFinite(v))) continue;
    result.push({sequence,episode:event.episode,tick,xy:anchor.xy as [number,number],label:detail.kind!.replace('memory_',''),href:`#event-${sample.run_id}-${sequence}`});
  }
  return result.slice(-32);
}
