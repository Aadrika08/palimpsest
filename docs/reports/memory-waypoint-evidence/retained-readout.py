import copy,json,math,time,hashlib,os
from pathlib import Path
import numpy as np
from scripts import memory_decision_pilot as p
from palimpsest import memory_decision as md
from palimpsest.replay import _initial_snapshot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
root=Path('runs/memory-waypoint-20261004T120942Z').resolve()
r=p.read_json(root/'execution.json'); deadline=r['readout_deadline_monotonic']; p.deadline_check(deadline)
result={'schema':'memory-waypoint-retained-readout-v1','started_monotonic':time.monotonic(),'execution_sha256':p.file_hash(root/'execution.json'),'indexed_files':len(r['artifact_index']),'owners':[],'qualification_claims':[]}
for entry in r['artifact_index']:
 p.deadline_check(deadline); f=root/entry['path']
 if f.stat().st_size!=entry['bytes'] or p.file_hash(f)!=entry['sha256']: raise ValueError('Artifact differs: '+str(f))
result['all_original_indexed_hashes_match']=True
plots=[]
for stage in ('development','prerequisites'):
 for scored in r['stages'][stage]['attempted']:
  p.deadline_check(deadline); ident=scored['run_id']; job=p.read_json(root/stage/'jobs'/f'{ident}.json'); supervised=p.read_json(root/stage/'supervision'/ident/'supervisor.json')
  audited=p.audit_run(job,supervised,deadline)
  if any(audited[k]!=v for k,v in scored.items() if k!='supervision'): raise ValueError('Published owner audit differs')
  data=p.read_raw(job['output'],deadline); snapshot,_,_=_initial_snapshot(data)
  terminal=None
  if (scored.get('outcome') or {}).get('type')=='CueUnavailable':
   p.replay_memory_audit(job,data,snapshot,p.read_json(Path(job['output'])/'worker-report.json'),require_terminal_cue=True)
   packet=[e['packet'] for e in data['events'] if e['kind']=='memory_sensed'][-1]
   state=copy.deepcopy(scored['final_memory']);sup=state['supervisor']; target=sup['waypoint_ids'][sup['waypoint_index']]
   try: md.advance_memory(state,packet)
   except md.CueUnavailable as error:
    if str(error)!=scored['outcome']['message']:raise
   else:raise ValueError('Terminal cue exception not reproduced')
   pose=data['rows'][-1]['next_pose'].tolist(); xy=job['case']['landmarks'][target]
   bearing=math.degrees(math.remainder(math.atan2(xy[1]-pose[1],xy[0]-pose[0])-pose[2],2*math.pi))
   terminal={'tick':packet['tick'],'target':target,'target_xy':xy,'pose':pose,'range_m':math.dist(pose[:2],xy),'relative_bearing_degrees':bearing,'abs_fov_excess_degrees':abs(bearing)-90,'line_of_sight_scope':'packet reconstructed by audit_run with circular occluders','exact_exception_reproduced':True,'sensor_only_terminal_packet':True}
   result['terminal_failure']=terminal
  owner={'job_id':scored['job_id'],'run_id':ident,'raw_rows':len(data['rows']),'symbolic_packets':sum(e['kind']=='memory_sensed' for e in data['events']),'policy_calls':sum(e['kind']=='neural_policy_call' for e in data['events']),'raw_audit_pass':True,'policy_binding_pass':True,'packet_memory_commitment_replay_pass':True,'goal':scored['goal'],'retreat_completed':scored['retreat_completed'],'replans':scored['replans'],'profile_sha256':job['case']['profile_sha256'],'terminal_failure':terminal}
  result['owners'].append(owner)
  poses=np.array([row['pose'] for row in data['rows']]+[data['rows'][-1]['next_pose']])
  plots.append((scored,job['case'],poses,terminal))
for item in r['detached_owner_cleanup']:
 owner=item['owner']
 try: actual=Path(f"/proc/{owner['pid']}/stat").read_text().rsplit(')',1)[1].split(); live=int(actual[19])==owner['starttime'] and os.getpgid(owner['pid'])==owner['pgid']
 except (FileNotFoundError,ProcessLookupError):live=False
 if live:raise ValueError('Matching owner still active')
result['all_recorded_owners_exited']=True
profile=p.read_json(root/'candidates.json')['candidates'][0]['profile']
fig,axes=plt.subplots(1,len(plots),figsize=(5*len(plots),5),squeeze=False)
for ax,(scored,case,poses,terminal) in zip(axes[0],plots):
 for xy in profile['obstacles']:ax.add_patch(Circle(xy,profile['obstacle_radius'],facecolor='#dedede',edgecolor='#aaa'))
 for side in ('a','z'):
  points=[case['landmarks'][f"{case['case_id']}-subject-{side}-inspection"]]+[case['landmarks'][f"{case['case_id']}-subject-{side}-retreat-{i}"] for i in range(7)]+[case['landmarks'][case['decision_landmark_id']]]
  ax.plot(*np.array(points).T,'--',color='#999',lw=.8)
 ax.plot(poses[:,0],poses[:,1],color='#236b8e',lw=1.4,label='Measured rover path')
 if case['event_enabled'] and scored['operation']=='full':ax.add_patch(Circle(profile['closed_gates'][0],.4,facecolor='#c36b6b',alpha=.6))
 ax.scatter(*case['goal_xy'],marker='*',s=100,color='#48783f',label='Goal')
 if terminal:
  x,y,yaw=terminal['pose'];ax.scatter(x,y,color='#b02b32',marker='x',s=65);ax.plot([x,terminal['target_xy'][0]],[y,terminal['target_xy'][1]],color='#b02b32',lw=1)
  ax.arrow(x,y,.5*math.cos(yaw),.5*math.sin(yaw),head_width=.10,color='#b02b32',length_includes_head=True)
  ax.text(-3.8,2.7,f"CueUnavailable at {terminal['tick']}\nExit bearing {terminal['relative_bearing_degrees']:.3f}°",fontsize=9,color='#b02b32')
 ax.set_title(f"{scored['job_id']}\n{scored['total_ticks']} control ticks; goal={scored['goal']}",fontsize=11)
 ax.set(xlim=(-4,3.5),ylim=(-3.2,3.2),xlabel='x (m)',ylabel='y (m)');ax.set_aspect('equal');ax.grid(alpha=.15)
axes[0][0].legend(loc='lower right',fontsize=8)
fig.suptitle('Frozen radius 1.4 m: acquisition succeeds; changed-route completion fails',fontsize=13)
fig.tight_layout();fig.savefig(root/'measured-paths.svg');fig.savefig('/tmp/memory-waypoint-paths.png',dpi=120);plt.close(fig)
p.deadline_check(deadline)
result['completed_monotonic']=time.monotonic();result['conservative_readout_seconds']=result['completed_monotonic']-r['readout_started_monotonic'];result['conservative_total_seconds']=result['completed_monotonic']-r['phase_started_monotonic'];result['readout_deadline_monotonic']=deadline
result['output_bytes_after_readout']=sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
(root/'readout-completion.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2))
