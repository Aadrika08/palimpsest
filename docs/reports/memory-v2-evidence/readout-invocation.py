"""Retained-input readout only; no native calls, fitting or replacement trials."""
import argparse, hashlib, json, math, time
from pathlib import Path
started=time.monotonic()
parser=argparse.ArgumentParser();parser.add_argument('--phase-root',type=Path,required=True);args=parser.parse_args()
p=args.phase_root.resolve(); d=json.loads((p/'diagnostics/report.json').read_text()); f=json.loads((p/'prerequisites/report.json').read_text())
from scripts.memory_decision_pilot import read_raw, policy_bindings
from palimpsest import memory_decision as md, memory_decision_world as world
from palimpsest.storage import StorageBudget,StorageLimits
budget=StorageBudget((p,),StorageLimits(max_bytes=8*1024**3,min_free_bytes=2*1024**3))
run=Path(f['attempted'][0]['run']); data=read_raw(run);policy_bindings(data)
job=json.loads((p/'prerequisites/jobs'/f'{run.name}.json').read_text()); r=json.loads((run/'worker-report.json').read_text())
state=md.initialize(job['case']); rows={int(x['tick']):x for x in data['rows']};expected=[]; caught=None
for e in data['events']:
 if e['kind']=='memory_sensed':
  tick=e['episode_step'];pose=(rows[tick]['pose'] if tick in rows else data['rows'][-1]['next_pose']).tolist()
  packet=md.capture_symbolic(*world.reconstruct_inputs(job['case'],pose,tick,event_tick=None,gate_result='not_requested'),episode_id='episode-0',tick=tick)
  assert packet==e['packet']
  try:state,bearing,expected=md.advance_memory(state,packet)
  except md.CueUnavailable as error:caught={'tick':tick,'message':str(error),'pose':pose}
 elif e['kind']=='memory_decision':assert expected and expected.pop(0)==e['detail']
assert state==r['final_memory'] and caught and len(rows)==101
name=caught['message'].split(': ',1)[1];xy=job['case']['landmarks'][name];pose=caught['pose']
angle=math.degrees(math.remainder(math.atan2(xy[1]-pose[1],xy[0]-pose[0])-pose[2],2*math.pi))
assert angle < -90 and math.dist(pose[:2],xy)<4
summary={'schema':'memory-v2-readout-v1','phase_root':str(p),'execution_head':json.loads((p/'execution.json').read_text())['implementation_head'],
 'failure':{'raw_rows':len(rows),'packets':sum(e['kind']=='memory_sensed' for e in data['events']),'policy_calls':sum(e['kind']=='neural_policy_call' for e in data['events']),'raw_policy_bindings_verified':True,'packets_reconstructed':True,'memory_replay_exact':True,'tick':caught['tick'],'pose':pose,'target':name,'target_xy':xy,'bearing_degrees':angle,'range_m':math.dist(pose[:2],xy)},
 'puck_nearest':{k:v['dev']['all'] for k,v in d['puck']['nearest_neighbor_contrasts'].items()},
 'puck_models':[{'rung':m['rung'],'seed':m['seed'],'dev':m['dev']['all'],'heading_bins':m['dev']['target_heading_magnitude'],'retained_match':m['retained_metric_comparison']['status']} for m in d['puck']['models']],
 'nav_models':[{'candidate':m['candidate'],'arm':m['arm'],'seed':m['seed'],'panels':{k:{'all':v['all'],'active_recovery':v['active_recovery'],'outside_recovery':v['outside_recovery'],'gates':v['original_recovery_gates'],'retained_match':v['retained_metric_comparison']['status']} for k,v in m['panels'].items()}} for m in d['navigation']['models']],
 'native_prerequisite_pass':False,'qualification_claims':[],'fit_performed':False}
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Wedge
fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained'); case=job['case']
trajectory=[row['pose'][:2] for row in data['rows']]+[data['rows'][-1]['next_pose'][:2]]
for ax in axes:
 for x,y in world.PROFILE['obstacles']:ax.add_patch(Circle((x,y),.4,color='#b8b9bc'))
 ids=world.public_graph(case)['acquisition_ids'];coords=[case['landmarks'][i] for i in ids]
 ax.plot([a[0] for a in coords],[a[1] for a in coords],':',color='#8a80aa',lw=1,label='Authored acquisition chain')
 ax.plot([a[0] for a in trajectory],[a[1] for a in trajectory],color='#186e9b',lw=2,label='Measured CPU FLYNN path')
 ax.scatter(*pose[:2],color='#be3e35',zorder=5);ax.scatter(*xy,marker='x',s=80,color='#be3e35',zorder=6)
 ax.set_aspect('equal');ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.grid(alpha=.15)
axes[0].set(xlim=(-3,3),ylim=(-2.3,2.3),title='First native prerequisite: incomplete acquisition');axes[0].legend(loc='upper left',fontsize=8)
yaw=math.degrees(pose[2]);axes[1].add_patch(Wedge(pose[:2],1.3,yaw-90,yaw+90,color='#dbeaf0',alpha=.6,zorder=0))
axes[1].arrow(*pose[:2],.3*math.cos(pose[2]),.3*math.sin(pose[2]),head_width=.05,color='#186e9b')
axes[1].plot([pose[0],xy[0]],[pose[1],xy[1]],'--',color='#be3e35',lw=1)
axes[1].set(xlim=(-1.6,-.1),ylim=(-2,-.5),title=f'Tick101: target bearing {angle:.3f} degrees')
axes[1].annotate('Requested marker\n0.449 degrees outside FOV',xy,xytext=(-1.55,-1.9),fontsize=9)
fig.suptitle('Retained failure; no retry or geometry revision',fontsize=12)
svg=p/'prerequisite-path.svg';budget.check(1024**2,path=svg);fig.savefig(svg);plt.close(fig)
summary['readout_tool_seconds']=time.monotonic()-started
assert summary['readout_tool_seconds']<600
payload=(json.dumps(summary,indent=2,sort_keys=True)+'\n').encode();budget.check(len(payload),path=p/'readout.json');(p/'readout.json').write_bytes(payload)
print(json.dumps({'readout_seconds':summary['readout_tool_seconds'],'bearing_degrees':angle,'output':str(p/'readout.json')}))
