import type {RunSummary, Snapshot} from './protocol';

// Run and snapshot selects render a bounded window instead of every recorded run,
// so the page's DOM stays bounded however many runs a session records. Selected
// values are always present, runs from this browser session come first, and a
// search over id, controller and scenario reaches any run.
export const RUN_WINDOW=10;

type RunView={runs:RunSummary[];total:number;hidden:number};

function matches(query:string, ...values:unknown[]){
  return values.some(value=>typeof value==='string'&&value.toLowerCase().includes(query));
}

export function windowRuns(runs:RunSummary[], {query,pinned,recent}:{query:string;pinned:string[];recent:string[]}, limit=RUN_WINDOW):RunView {
  const term=query.trim().toLowerCase();
  const byId=new Map(runs.map(run=>[run.run_id,run]));
  const pool=term?runs.filter(run=>matches(term,run.run_id,run.controller,run.scenario)):runs;
  const chosen:RunSummary[]=[];const seen=new Set<string>();
  const add=(run:RunSummary)=>{if(!seen.has(run.run_id)){seen.add(run.run_id);chosen.push(run);}};
  for(const id of pinned)if(id)add(byId.get(id)??{run_id:id});
  if(!term)for(const id of recent){if(chosen.length>=limit)break;add(byId.get(id)??{run_id:id});}
  for(const run of pool){if(chosen.length>=limit)break;add(run);}
  const total=pool.length;
  return {runs:chosen,total,hidden:Math.max(0,total-chosen.filter(run=>pool.includes(run)).length)};
}

export function windowSnapshots(snapshots:Snapshot[], {query,chosen}:{query:string;chosen:string}, limit=RUN_WINDOW) {
  const term=query.trim().toLowerCase();
  const pool=term?snapshots.filter(s=>matches(term,s.run_id,s.snapshot_id)):snapshots;
  const pinned=snapshots.filter(s=>s.snapshot_id===chosen);
  const newest=pool.filter(s=>s.snapshot_id!==chosen).slice(-Math.max(0,limit-pinned.length));
  return {snapshots:[...pinned,...newest],total:pool.length,hidden:Math.max(0,pool.length-newest.length-pinned.filter(s=>pool.includes(s)).length)};
}
