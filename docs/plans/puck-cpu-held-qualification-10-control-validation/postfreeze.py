from pathlib import Path
import hashlib,json,subprocess
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base='docs/plans/puck-cpu-held-qualification-10'
def raw(name):return (root/name).read_bytes()
def pin_bytes(value):return dict(size_bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
freeze=raw(base+'-freeze.json');f=json.loads(freeze);fp=pin_bytes(freeze)
assert fp==dict(size_bytes=480590,sha256='f0e56235825dc549c43d58e02b9d47de9bd81edab122a5786bd8038a3a6d47fc')
old_wrapper=raw('docs/plans/puck-cpu-held-qualification-09-external.py')
replacements=[(b'puck-cpu-held-qualification-09',b'puck-cpu-held-qualification-10'),(b'held09',b'held10'),(b'qualification09',b'qualification10'),
    (b'efb5bbe5ad22dfb5c2559e64a4565b35424f51ba3bbbc6d080b7eda81acd85a5',fp['sha256'].encode()),(b'len(raw)==301670',b'len(raw)==480590')]
wrapper=old_wrapper
for a,b in replacements:wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(replacements):restored=restored.replace(b,a)
assert restored==old_wrapper
compile(wrapper,base+'-external.py','exec')
for p in (root/(base+'-external.py'),Path('/tmp/palimpsest-held10-external.py')):
    with p.open('xb') as out:out.write(wrapper)
def names(value):
    if isinstance(value,str):return value.replace('puck-cpu-held-qualification-09','puck-cpu-held-qualification-10').replace('qualification09','qualification10').replace('held09','held10')
    if isinstance(value,list):return [names(v) for v in value]
    if isinstance(value,dict):return {k:names(v) for k,v in value.items()}
    return value
envelope=names(json.loads(raw('docs/plans/puck-cpu-held-qualification-09-execution.json')))
envelope['source_commit']=f['source_commit']
envelope['freeze'].update(fp)
envelope['wrapper'].update(pin_bytes(wrapper))
envelope['scope']='one separately admitted q4 CPU four-import qualification10; no episode, renderer, operator or study'
assert all(not Path(p).exists() for phase in envelope['phase_outputs'].values() for p in phase.values())
with (root/(base+'-execution.json')).open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(kind='held10-external-wrapper-compatibility-v1',status='PASS_SOURCE_METADATA_ONLY',
    old_sha256=hashlib.sha256(old_wrapper).hexdigest(),old_size_bytes=len(old_wrapper),
    new_sha256=hashlib.sha256(wrapper).hexdigest(),new_size_bytes=len(wrapper),
    source_previous='docs/plans/puck-cpu-held-qualification-09-external.py',source_new=base+'-external.py',
    inverse_names_size_sha_restores_old_bytes=True,external_caps_unchanged=True,
    timeout_version_observed=subprocess.check_output(['/usr/bin/timeout','--version'],text=True).splitlines()[0],
    scope='source inverse and local binary identity only; historical wrapper evidence separate',
    wrapper_invoked=False,admission_main_invoked=False,runtime_invoked=False)
with (root/(base+'-wrapper-proof.json')).open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
selfcheck=raw('docs/plans/puck-cpu-held-qualification-09-control-selfcheck.py').decode()
for a,b in [('frozen09','frozen10'),('puck-cpu-held-qualification-09','puck-cpu-held-qualification-10'),('held09','held10'),
    ('efb5bbe5ad22dfb5c2559e64a4565b35424f51ba3bbbc6d080b7eda81acd85a5',fp['sha256']),
    ('size_bytes=301670','size_bytes=480590'),('==1259','==1998'),
    ('96ace37062fd14e20ae1ebd2371b90fa88f8d7ab',f['source_commit']),
    ('actual09_invoked_at_freeze','actual10_invoked_at_freeze'),('actual09_admission_invoked_at_freeze','actual10_admission_invoked_at_freeze'),
    ("old=read('docs/plans/puck-cpu-held-qualification-08.json')","old=read('docs/plans/puck-cpu-held-qualification-09.json')"),
    ('qualifications01_02_03_04_05_06_07_08_failed_consumed','qualifications01_02_03_04_05_06_07_08_09_failed_consumed'),
    ("['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py']","['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_runtime_qualification.py']"),
    ('historical08_replaced_live_sources','historical09_replaced_live_sources'),
    ("'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py'}","'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py','src/palimpsest/puck_runtime_qualification.py'}"),
    ("len(freeze['process_identity_samples'])==9","len(freeze['process_identity_samples'])==12"),
    ("absence['historical_missing_receipts']==14","absence['historical_missing_receipts']==16"),
    ('set(admission.HISTORICAL08_JSON)','set(admission.HISTORICAL08_JSON)|set(admission.HISTORICAL09_JSON)'),
    ('changed_config_sources=2,changed_live_sources=4','changed_config_sources=3,changed_live_sources=5'),
    ('historical_missing_receipts=14','historical_missing_receipts=16'),('process_identity_samples=9','process_identity_samples=12')]:
    selfcheck=selfcheck.replace(a,b)
anchor='for name in (BASE+\'-admission.py\',BASE+\'-external.py\'):compile'
extra='''for folder in ('docs/reports/puck-cpu-held-qualification-09','docs/plans/puck-cpu-guard-contract-v4','docs/plans/puck-cpu-q4-qualification-epoch10'):
    index=read(folder+'/evidence-index.json')
    for row in index['artifacts']:
        assert roster[folder+'/'+row['archived_path']]==dict(path=folder+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256'])
files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
depraw=(ROOT/'runs/puck-cpu-held-preparation-01/payload/dependencies.json').read_bytes()
legacy,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'])
q4,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=4)
assert legacy['qualification']['version']==3
assert q4['qualification']['kind']=='puck-held-runtime-import-qualification-v4' and q4['qualification']['version']==4
'''
assert anchor in selfcheck
selfcheck=selfcheck.replace(anchor,extra+anchor)
compile(selfcheck,base+'-control-selfcheck.py','exec')
with (root/(base+'-control-selfcheck.py')).open('x') as out:out.write(selfcheck)
print(json.dumps(dict(freeze=fp,wrapper=pin_bytes(wrapper),wrapper_inverse_exact=True,admission_invoked=False,runtime_invoked=False)))
