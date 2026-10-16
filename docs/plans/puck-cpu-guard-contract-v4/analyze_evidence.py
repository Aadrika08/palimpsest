from pathlib import Path
import hashlib,json,statistics
ROOT=Path('/home/utkarsh/.codex/worktrees/293b/brain');BASE=ROOT/'docs/plans/puck-cpu-guard-contract-v4'
def read_rows(path,kind):
 rows=[]
 for line in path.read_text().splitlines():
  try:row=json.loads(line.lstrip('.'))
  except ValueError:continue
  if type(row) is dict and row.get('kind')==kind:rows.append(row)
 return rows
old_path=ROOT/'docs/reports/puck-cpu-guard-cost-v1/validation/baseline01/stdout.txt'
old_source=ROOT/'docs/reports/puck-cpu-guard-cost-v1/source/scripts/puck_worker_bootstrap.py'
old=read_rows(old_path,'authored-guard-cost-v1');new=read_rows(BASE/'validation/cost01/stdout.log','authored-q4-guard-cost-v1')
assert [r['synthetic_cache_entries'] for r in old]==[128,512,2048]==[r['synthetic_cache_entries'] for r in new]
rows=[]
for a,b in zip(old,new):
 assert a['checks_per_sample']==b['checks_per_sample']==3
 assert len(a['elapsed_ns'])==len(b['elapsed_ns'])==3
 assert all(type(n) is int and n>0 for n in a['elapsed_ns']+b['elapsed_ns'])
 assert b['cache_clean'] is b['allowances_clean'] is b['profile_restored'] is True
 assert b['dependency_keys_calls_per_profiled_check']==0
 rows.append(dict(entries=b['synthetic_cache_entries'],historical_three_check_ns=a['elapsed_ns'],q4_three_check_ns=b['elapsed_ns'],
  historical_median_batch_divided_by_three_ms=statistics.median(a['elapsed_ns'])/3/1e6,
  q4_median_batch_divided_by_three_ms=statistics.median(b['elapsed_ns'])/3/1e6,
  historical_original_dependency_keys_calls=a['dependency_keys_calls_per_profiled_check'],q4_original_dependency_keys_calls=b['dependency_keys_calls_per_profiled_check']))
def pin(path):
 raw=path.read_bytes();return dict(path=str(path.relative_to(ROOT)),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
comparison=dict(kind='puck-q4-authored-guard-cost-comparison-v1',status='USEFUL_BOUNDED_REDUCTION_OBSERVED_NOT_INSTALLED_QUALIFICATION',
 baseline=pin(old_path),baseline_source=pin(old_source),q4_source=pin(ROOT/'scripts/puck_worker_bootstrap.py'),rows=rows,
 caveats=['Unpaired historical source and different q4 initializer context/semantics/diagnostics; do not attribute the full difference to whitelist construction.',
  'Each raw sample times three sequential complete light checks; batch divided by3 is descriptive, not a per-check latency distribution or hard bound.',
  'No newly attached profiler in timed batches; one separate profiled check counts only C keys calls on original deps.loaded. Zero does not mean zero key work or allocations.',
  '128-entry median is slightly worse; publish all raw samples without selection. No installed throughput, actual09 cause, model capability, physics, renderer or runtime qualification follows.'],
 runtime_qualified=False,actual10_invoked=False)
(BASE/'cost-comparison.json').write_text(json.dumps(comparison,sort_keys=True,indent=2)+'\n')
terminals=[];pincount=0
for directory in sorted((BASE/'validation').iterdir()):
 command=json.loads((directory/'command.json').read_text());terminal=json.loads((directory/'terminal.json').read_text());assert terminal['outer_timeout'] is False
 for row in command['pins']:
  blob=(directory/'source'/row['path']).read_bytes();assert len(blob)==row['size_bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'];pincount+=1
 terminals.append(terminal)
notes=json.loads((BASE/'validation-notes.json').read_text());notes['legacy01']=notes['legacy01'].replace('33 deselected','29 deselected');(BASE/'validation-notes.json').write_text(json.dumps(notes,sort_keys=True,indent=2)+'\n')
outcome=dict(kind='puck-q4-guard-source-unit-outcome-v1',status='SOURCE_AND_AUTHORED_EVIDENCE_PASS_PENDING_INDEPENDENT_OUTCOME_REVIEW',
 implementation_commit='1fa94213f583a30e6c5533a45bef5575b45e9095',final_source_review='GO_SOURCE_REVIEW_ONLY',
 authored_q4_unique_cases=41,legacy_unique_passing_cases=397,cost_cases=3,unique_passing_cases=441,
 single_all_green_397_case_run=False,pin_copies_verified=pincount,terminals=terminals,
 production_paths_changed=['scripts/puck_worker_bootstrap.py','src/palimpsest/puck_runtime_qualification.py'],
 outer_epochs_changed=False,actual10_controls_created=False,actual10_invoked=False,installed_runtime_invoked=False,
 runtime_qualified=False,all_seven_release_gates_open=True,
 scope='Source unit and tiny authored packages/native fixtures only.39/40 earlier q4 rounds overlap; report41 distinct final cases, not sum of repeated invocations.')
(BASE/'outcome.json').write_text(json.dumps(outcome,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(pin_copies_verified=pincount,rows=rows,unique_passing_cases=441),sort_keys=True))
