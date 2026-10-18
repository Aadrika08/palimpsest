from pathlib import Path
import ast,json
root=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
roster=json.loads(Path('/tmp/palimpsest-autograd-publication-profile-01/roster.json').read_bytes())
constant="AUTOGRAD_EXPORT=dict(name='torch._C._autograd',producer='torch.autograd',\n    phase='module_exec_publish',attributes=['torch','_C','_autograd'],class_binding=None,\n    delegate_attributes="+repr(roster)+")\n"
# Same literal admission boundary; the standalone auditor does not import the parent.
parent=root/'scripts/qualify_puck_cpu_held_runtime.py';s=parent.read_text()
s=s.replace("QUALIFY04='runs/puck-cpu-held-qualification-04'", "QUALIFY04='runs/puck-cpu-held-qualification-04'\nQUALIFY05='runs/puck-cpu-held-qualification-05'\n"+constant.rstrip())
s=s.replace("epoch=4 if kind==", "epoch=5 if kind=='puck-cpu-held-runtime-allocation-v5' else 4 if kind==")
s=s.replace('(2,3,4)','(2,3,4,5)').replace('(3,4)','(3,4,5)')
s=s.replace("if config['version']==4:return QUALIFY04", "if config['version']==5:return QUALIFY05\n    if config['version']==4:return QUALIFY04")
s=s.replace("'CPU amendment02,03 or04 configuration required'", "'CPU amendment02–05 configuration required'")
old="""    if any(prior[k]!=config[k] for k in shared):raise ValueError('CPU amendment changed prepared data or policy')
    changed={old['path'] for old,new in zip(prior['sources'],config['sources']) if old!=new}
    if config['version']==4:"""
new="""    if config['version']==5:
        shared=tuple(k for k in shared if k!='inputs')
        if (any(prior['inputs'][k]!=config['inputs'][k] for k in INPUT_ROLES if k!='candidate')
                or any(prior['inputs']['candidate'][k]==config['inputs']['candidate'][k] for k in ('path','sha256'))):
            raise ValueError('CPU publication amendment must change only a distinct candidate pin')
    if any(prior[k]!=config[k] for k in shared):raise ValueError('CPU amendment changed prepared data or policy')
    changed={old['path'] for old,new in zip(prior['sources'],config['sources']) if old!=new}
    if config['version']==5:
        if changed!={BOOTSTRAP,'scripts/qualify_puck_cpu_held_runtime.py',DIAGNOSTIC_BINDINGS,'src/palimpsest/puck_dependency_imports.py'}:
            raise ValueError('CPU publication amendment requires exactly four changed source paths')
    elif config['version']==4:"""
assert s.count(old)==1;s=s.replace(old,new)
helper="""def validate_publication_candidate(prior,current):
    if type(prior) is not dict or type(current) is not dict:
        raise ValueError('CPU publication candidate objects required')
    profile=prior.get('import_profile')
    rows=profile.get('exports') if type(profile) is dict else None
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        raise ValueError('Historical CPU export declarations required')
    targets=[i for i,row in enumerate(rows) if row.get('name')==AUTOGRAD_EXPORT['name']]
    old=dict(name=AUTOGRAD_EXPORT['name'],producer='torch._C',phase='native_create',attributes=['_autograd'],class_binding=None)
    if len(targets)!=1 or rows[targets[0]]!=old:
        raise ValueError('Exact historical autograd export declaration required')
    expected=copy.deepcopy(prior)
    expected['import_profile']['exports'][targets[0]]=copy.deepcopy(AUTOGRAD_EXPORT)
    if canonical(current)!=canonical(expected):
        raise ValueError('CPU publication candidate must change only the exact autograd declaration')


"""
marker='def validate_preparation_acceptance(config,blobs):';assert s.count(marker)==1;s=s.replace(marker,helper+marker)
ast.parse(s);parent.write_text(s)
audit=root/'scripts/audit_puck_cpu_held_runtime.py';s=audit.read_text()
s=s.replace("BINDINGS='src/palimpsest/puck_dependency_bindings.py'", "BINDINGS='src/palimpsest/puck_dependency_bindings.py'\n"+constant.rstrip())
s=s.replace("'puck-cpu-held-runtime-allocation-v4':4", "'puck-cpu-held-runtime-allocation-v4':4,'puck-cpu-held-runtime-allocation-v5':5")
s=s.replace("4:'runs/puck-cpu-held-qualification-04'", "4:'runs/puck-cpu-held-qualification-04',5:'runs/puck-cpu-held-qualification-05'")
s=s.replace("4:'qualify04'", "4:'qualify04',5:'qualify05'")
s=s.replace('(2,3,4)','(2,3,4,5)').replace('(3,4)','(3,4,5)')
old="""    require(all(canonical(current[k])==canonical(historical[k]) for k in shared),'Historical preparation data or policy changed')"""
new="""    if current['version']==5:
        shared=tuple(k for k in shared if k!='inputs')
        require(all(current['inputs'][k]==historical['inputs'][k] for k in ROLES if k!='candidate') and
                all(current['inputs']['candidate'][k]!=historical['inputs']['candidate'][k] for k in ('path','sha256')),
                'Publication05 requires only a distinct candidate input pin')
    require(all(canonical(current[k])==canonical(historical[k]) for k in shared),'Historical preparation data or policy changed')"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("    if current['version']==4:\n", "    if current['version']==5:\n        require(changed=={PARENT,BOOTSTRAP,BINDINGS,'src/palimpsest/puck_dependency_imports.py'},'Publication05 requires exactly four changed source paths')\n    elif current['version']==4:\n")
helper="""def publication_candidate(prior,current):
    require(type(prior) is dict and type(current) is dict,'Publication candidate objects required')
    profile=prior.get('import_profile')
    rows=profile.get('exports') if type(profile) is dict else None
    require(type(rows) is list and all(type(row) is dict for row in rows),'Historical publication export list required')
    targets=[i for i,row in enumerate(rows) if row.get('name')==AUTOGRAD_EXPORT['name']]
    original=dict(name='torch._C._autograd',producer='torch._C',phase='native_create',attributes=['_autograd'],class_binding=None)
    require(len(targets)==1 and rows[targets[0]]==original,'Exact historical autograd declaration required')
    expected=json.loads(canonical(prior))
    expected['import_profile']['exports'][targets[0]]=AUTOGRAD_EXPORT
    require(canonical(current)==canonical(expected),'Only the exact autograd publication declaration may change')


"""
marker='def preparation_epoch(current,historical,prep):';assert s.count(marker)==1;s=s.replace(marker,helper+marker)
ast.parse(s);audit.write_text(s)
observer=root/'scripts/observe_puck_cpu_held_allocation.py';s=observer.read_text()
s=s.replace("'puck-cpu-held-runtime-allocation-v4':4", "'puck-cpu-held-runtime-allocation-v4':4,'puck-cpu-held-runtime-allocation-v5':5")
s=s.replace("4:'runs/puck-cpu-held-qualification-04'", "4:'runs/puck-cpu-held-qualification-04',5:'runs/puck-cpu-held-qualification-05'")
ast.parse(s);observer.write_text(s)
