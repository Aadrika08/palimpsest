import hashlib,json,resource,time,uuid,wave,struct
from pathlib import Path
import numpy as np
from palimpsest.records import RunWriter
from palimpsest.sonification import sonify
root=Path('runs/choir-review-2026-10-21')
run=root/uuid.uuid4().hex
start=time.monotonic()
w=RunWriter(run/'recording',dict(run_id=run.name,controller='flynn',profile='flynn',scenario={'id':'synthetic-capacity-only'},control_interval_seconds=.02,population_names=['visual_left','visual_right','descending'],population_columns=['count','mean','min','max'],population_scale=[-1.,1.],evidence_class='synthetic capacity fixture; no model inference'),max_bytes=2*1024**3)
w.event('policy_loaded',run_id=run.name,provenance={'edge_sha256':'a'*64,'checkpoint_sha256':'b'*64,'ordered_neuron_ids_sha256':'c'*64})
frame=np.zeros((128,128,3),dtype=np.uint8)
for ep in range(10):
 w.event('episode_started',run_id=run.name,episode=ep,episode_step=0,world={'arena':7.,'pose':[0.,0.,0.],'obstacles':[],'goal':[3.,3.,.5]})
 for tick in range(600):
  w.tick(ep,tick,pose=np.zeros(3),next_pose=np.zeros(3),reward=np.array(0.),sensors=np.zeros(4),simulation_time=np.array((tick+1)*.02),population_stats=np.array([[8.,.5,.5,.5],[8.,0.,0.,0.],[2.,.5,.5,.5]]),cam_left=frame,cam_right=frame,raw_cam_left=frame,raw_cam_right=frame)
w.finish({})
w.close()
created=time.monotonic()
output=root/'capacity.wav'
sonify(run,output,populations=['visual_left','visual_right','descending'],episode=None)
finished=time.monotonic()
with wave.open(str(output),'rb') as a:
 assert a.getnframes()==5760000 and a.getframerate()==48000
 pcm=a.readframes(a.getnframes())
b=output.read_bytes();p=12
while p<len(b):
 kind,n=struct.unpack_from('<4sI',b,p)
 if kind==b'plmp': meta=json.loads(b[p+8:p+8+n]);break
 p+=8+n+n%2
assert meta['pcm_sha256']==hashlib.sha256(pcm).hexdigest()
assert len(meta['timing']['segments'])==10 and not meta['timing']['final_episode_prefix']
assert meta['timing']['segments'][-1]['output_end_sample_exclusive']==5760000
result=dict(evidence='synthetic capacity fixture, no FLYNN inference',run=str(run),source_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),output_bytes=output.stat().st_size,metadata_bytes=n,source_write_seconds=created-start,export_seconds=finished-created,peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,samples=5760000,episodes=10,pcm_sha256=meta['pcm_sha256'],checks_passed=True)
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
