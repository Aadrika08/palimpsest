"""Bind the baseline11b runner to accepted preparation02 and record d83dab3 as never invoked (GREEN).

Writes the byte-identical port of review 01 and edits the runner once. Reads metadata only;
never runs admission, census, guards, observer, auditor main or touches the preparation02 stage.
"""
from pathlib import Path
import ast,hashlib,json,os,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-11'
OLD='d83dab3c92387c80e81af528fea25dd3f8931598'
REVIEW_COMMIT='0b9c67f5fbf70f7bd3af4277ae9a10fb9b60a7d3'
REVIEW=BASE+'-independent-controls-review-01.md'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
path=ROOT/(BASE+'-admission.py');text=path.read_text()
assert 'def check_preparation02' not in text and 'def check_unexecuted11' not in text
review=git('show',REVIEW_COMMIT+':'+REVIEW)
assert git('rev-parse',REVIEW_COMMIT+'^').decode().strip()==OLD
with (ROOT/REVIEW).open('xb') as out:out.write(review)
# Every /tmp output the d83dab3 controls would have created, from its own envelope and tools.
envelope=json.loads(git('show',OLD+':'+BASE+'-execution.json'))
outputs=[p for phase in ('admission','observer','audit') for p in envelope['phase_outputs'][phase].values()]
outputs+=[envelope['admission_output'],envelope['auditor_output'],envelope['concrete_audit_command_path']]
outputs+=['/tmp/palimpsest-held11-'+phase+'-tool'+suffix for phase in ('admission','observer','audit') for suffix in ('-command.json','-terminal.json','.stdout','.stderr')]
outputs+=['/tmp/palimpsest-held11-'+name+'.json' for name in ('pre-admission-guard01','pre-observer-guard01','independent-admission-review','independent-outcome-review','post-outcome-observation')]
tree=ast.parse(git('show',OLD+':'+BASE+'-control-validation/tools/instantiate.py').decode())
templates=[k.value for k in next(n.value for n in tree.body if isinstance(n,ast.Assign) and getattr(n.targets[0],'id',None)=='TEMPLATES').keys]
outputs+=['/tmp/palimpsest-held11-'+name+'.py' for name in sorted(templates) if name!='external']+['/tmp/palimpsest-held11-pre-observer-guard.py']
outputs+=[str(ROOT/'docs/reports/puck-cpu-held-qualification-11')]
assert len(outputs)==len(set(outputs))==39 and all(not os.path.lexists(p) for p in outputs)
empty=[]
for name in ['runs/puck-cpu-held-qualification-'+str(i).zfill(2) for i in range(1,11)]+['runs/puck-cpu-held-preparation-01','runs/puck-cpu-held-preparation-02']:
    for directory,dirs,files in os.walk(ROOT/name,followlinks=False):
        if not dirs and not files:empty.append(str(Path(directory).relative_to(ROOT)))
empty.sort();assert len(empty)==35
prep02=json.loads((ROOT/'runs/puck-cpu-held-preparation-02/result.json').read_bytes())
roots=[dict(device=r['device'],inode=r['inode'],root_index=r['root_index']) for r in prep02['staged_roots']]
assert roots==[dict(device=55,inode=10400+i,root_index=i) for i in range(4)]
constants='''PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-02.json'
PREP_OUTPUT='runs/puck-cpu-held-preparation-02'
PREP_STAGE='/tmp/palimpsest-puck-cpu-held-02'
PREP_ROOTS='''+repr(roots)+'''
UNEXECUTED11='''+repr(dict(control_commit=OLD,review_commit=REVIEW_COMMIT,branch='research/puck-cpu-held-qualification-11',
    review=dict(path=REVIEW,size_bytes=len(review),sha256=sha(review)),outputs=outputs))+'''
EMPTY_DIRECTORIES='''+repr(empty)+'''


def check_preparation02(held,m,current,frozen):
    """Accepted preparation02 metadata only; its staged forest is re-hashed separately by forest()."""
    config,configraw=held.json(ROOT/PREP_CONFIGURATION,maximum=1024**2,lf=True)
    assert m.sha(configraw)==PREP_SHA;current.configuration(config,False)
    assert config['root']==str(ROOT) and config['phase']=='prepare' and config['stage_parent']==PREP_STAGE
    assert current.preparation_output(config)==current.preparation_output(frozen)==PREP_OUTPUT
    prepbase=ROOT/PREP_OUTPUT
    prep,prepraw=held.json(prepbase/'result.json',maximum=1024**2,lf=True)
    assert m.sha(prepraw)==RESULT_SHA;m.outcome(prep,config,PREP_SHA)
    assert prep['staged_roots']==PREP_ROOTS and prep['dependencies']['sha256']==DEP_SHA
    assert held.file(prepbase/'configuration.json',maximum=1024**2,raw=True)==configraw
    for folder,names in [('parent-source',m.SOURCES),('worker-source',m.WORKER)]:
        for row in config['sources']:
            if row['path'] in names:held.file(prepbase/folder/row['path'],row,1024**2)
    prior,accepted,audit=current.historical_acceptance(held,frozen,False)
    assert prior==config and accepted==prep and audit['allocation_id']==12 and audit['status']=='PASS'
    return config,configraw,prep,prepraw,dict(status='ACCEPTED_PREPARATION02',configuration_sha256=PREP_SHA,
        result_sha256=RESULT_SHA,independent_audit_sha256=frozen['preparation_acceptance']['independent_audit']['sha256'],
        stage_parent=PREP_STAGE,staged_roots=PREP_ROOTS,scope='accepted preparation metadata only; staged bytes re-hashed by forest')


def record_preparation01():
    # Preparation01's tmpfs forest was lost on reboot; it is history, not an input.
    return dict(status='ACCEPTED_SUPERSEDED_STAGE_LOST',required=False,stage_parent='/tmp/palimpsest-puck-cpu-held-01',
        stage_present=os.path.lexists('/tmp/palimpsest-puck-cpu-held-01'),
        configuration_sha256='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6',
        result_sha256='9d49c6ee3a0be61505cfe7d2267b659290be17365d6e35fb5fdbdc38e103f47d')


def check_unexecuted11(held):
    """The d83dab3 attempt-11 controls were reviewed NO-GO and never invoked; none of their outputs exist."""
    row=UNEXECUTED11['review'];held.file(ROOT/row['path'],row,1024**2)
    assert all(not os.path.lexists(path) for path in UNEXECUTED11['outputs'])
    return dict(status='NEVER_INVOKED',control_commit=UNEXECUTED11['control_commit'],review_commit=UNEXECUTED11['review_commit'],
        review='NO-GO: preparation01 stage lost on reboot',absent_outputs=len(UNEXECUTED11['outputs']),
        scope='absence of every d83dab3 /tmp output and archive; /tmp absence alone would not survive a reboot, the Git NO-GO record does')


def check_empty_directories():
    for name in EMPTY_DIRECTORIES:
        path=ROOT/name
        assert os.path.isdir(path) and not os.path.islink(path) and os.listdir(path)==[],name
    return dict(directories=len(EMPTY_DIRECTORIES),scope='historical allocation directories hold no unpinned entries')


'''
anchor='def resources('
assert text.count(anchor)==1
text=text.replace(anchor,constants+anchor)


def replace(old,new,count=1):
    global text
    assert text.count(old)==count,(old[:90],text.count(old))
    text=text.replace(old,new)


replace("PREP_SHA='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6'",
    "PREP_SHA='1acfb10b40d561b8e56c96f4cd0d59ee1f00b4d0a14f62c80ffe64e22e1de3ed'")
replace("RESULT_SHA='9d49c6ee3a0be61505cfe7d2267b659290be17365d6e35fb5fdbdc38e103f47d'",
    "RESULT_SHA='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'")
replace("held=m.Held(deadline);prepbase=ROOT/m.OUTPUTS['prepare']","held=m.Held(deadline);prepbase=ROOT/PREP_OUTPUT")
replace("""            config,configraw=held.json(ROOT/'docs/plans/puck-cpu-held-preparation-01.json',maximum=1024**2,lf=True)
            assert m.sha(configraw)==PREP_SHA;m.configuration(config,False)
            assert config['root']==str(ROOT) and config['phase']=='prepare'
            prep,prepraw=held.json(prepbase/'result.json',maximum=1024**2,lf=True)
            assert m.sha(prepraw)==RESULT_SHA;m.outcome(prep,config,PREP_SHA)
            assert held.file(prepbase/'configuration.json',maximum=1024**2,raw=True)==configraw
            for folder,names in [('parent-source',m.SOURCES),('worker-source',m.WORKER)]:
                for row in config['sources']:
                    if row['path'] in names:held.file(prepbase/folder/row['path'],row,1024**2)
""","""            config,configraw,prep,prepraw,preparation02=check_preparation02(held,m,current,frozen)
""")
replace("            current.historical_acceptance(held,frozen,False)\n","")
replace("assert invocation==dict(command=m.namespace_command(config,data,'prepare',command),configuration_sha256=PREP_SHA)",
    "assert invocation==dict(command=current.namespace_command(config,data,'prepare',command),configuration_sha256=PREP_SHA)")
replace("            consumed10=check_consumed10(held)\n","""            consumed10=check_consumed10(held)
            unexecuted11=check_unexecuted11(held)
            empty_directories=check_empty_directories()
            preparation01=record_preparation01()
""")
replace("qualification10_failure=consumed10,",
    "qualification10_failure=consumed10,preparation02=preparation02,preparation01=preparation01,attempt11_d83dab3=unexecuted11,historical_empty_directories=empty_directories,")
compile(text,str(path),'exec');path.write_text(text)
print(json.dumps(dict(preparation02_bound=True,preparation01_recorded_not_required=True,unexecuted11_outputs=len(outputs),
    empty_directories=len(empty),review_port=dict(path=REVIEW,size_bytes=len(review),sha256=sha(review)),
    admission_or_runtime_invoked=False,stage_touched=False),indent=2,sort_keys=True))
