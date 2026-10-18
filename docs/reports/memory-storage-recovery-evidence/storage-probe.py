"""Bounded storage-only qualification; no policy, simulator, or native owner."""
import hashlib,json,math,shutil,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from palimpsest.records import RunWriter,iter_ticks
from palimpsest.storage import StorageBudget,StorageLimits,MiB,GiB
from scripts.memory_waypoint_study import replace_control
repo=Path(sys.argv[1]).resolve();historical=repo/'runs/memory-travel-handoff-20261004T125507Z'
output=repo/'runs'/('memory-storage-probe-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
if output.exists():raise ValueError('Probe output must be absent')
started=time.monotonic();deadline=started+240
before=shutil.disk_usage(repo).free
if before<10*GiB:raise ValueError('10 GiB free required at probe admission')
index=json.loads((historical/'readout-completion.json').read_text())['retained_inventory_before_readout']
def unchanged():
 for row in index:
  f=historical/row['path']
  if f.stat().st_size!=row['bytes'] or hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Historical evidence changed')
unchanged()
events=next(historical.rglob('events.jsonl'))
for line in events.read_text().splitlines():
 event=json.loads(line)
 if event['kind']=='chunk':schema=event['arrays'];break
else:raise ValueError('No historical recording schema')
base={name:np.zeros(desc['shape'],dtype=desc['dtype']) for name,desc in schema.items()}
for name in ('cam_left','cam_right','raw_cam_left','raw_cam_right'):
 base[name][:]=np.arange(base[name].size,dtype=np.uint32).reshape(base[name].shape)%256
base['encoded_input'][:]=np.arange(4813,dtype=np.float32)/4813
bytes_per_tick=sum(a.nbytes for a in base.values())
def expected(tick):
 arrays={k:v.copy() for k,v in base.items()}
 arrays['revision'][...]=tick;arrays['simulation_time'][...]=tick*.02
 arrays['pose'][0]=tick/2100;arrays['next_pose'][0]=(tick+1)/2100
 return arrays
budget=StorageBudget([output],StorageLimits(max_bytes=640*MiB,min_free_bytes=2*GiB,max_runs=1,max_snapshots=1),headroom_bytes=64*MiB)
result={'schema':'palimpsest-storage-probe-v1','purpose':'synthetic-storage-only','source_head':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
 'started_utc':datetime.now(timezone.utc).isoformat(),'output':str(output),'ticks':2100,
 'bytes_per_tick':bytes_per_tick,'recording_limit_bytes':512*MiB,'probe_limit_bytes':640*MiB,
 'timeout_seconds':240,'free_bytes_before':before,'qualification_claims':[],'native_owners_started':0}
with budget.lock():
 writer=RunWriter(output/'recording',{'purpose':'synthetic-storage-only','controller':'synthetic-storage-probe','qualification_claims':[]},max_bytes=512*MiB,storage_budget=budget)
 try:
  for tick in range(2100):
   if time.monotonic()>deadline:raise TimeoutError('Probe deadline')
   writer.event('storage_probe_tick',tick=tick)
   writer.tick(0,tick,**expected(tick))
   if (tick+1)%32==0:replace_control(output/'progress.json',{'published_ticks':tick+1},budget)
  writer.finish({'synthetic':True})
 finally:writer.close()
 count=0
 for row in iter_ticks(output/'recording'):
  if time.monotonic()>deadline:raise TimeoutError('Probe readback deadline')
  if row['episode']!=0 or row['tick']!=count:raise ValueError('Wrong readback tick')
  arrays=expected(count)
  if any(not np.array_equal(row[k],v) for k,v in arrays.items()):raise ValueError('Readback payload differs')
  count+=1
 if count!=2100:raise ValueError('Incomplete readback')
 unchanged();result.update(status='passed',readback_ticks=count,chunk_count=len(list((output/'recording/chunks').glob('*.npz'))),
  progress_atomic_replacements=2100//32,manifest_terminal=True,historical_inventory_unchanged=True,
  free_bytes_after=shutil.disk_usage(repo).free,used_bytes=budget.usage()['used_bytes'],elapsed_seconds=time.monotonic()-started)
 (output/'qualification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
Path('/tmp/palimpsest-storage-probe-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2))
