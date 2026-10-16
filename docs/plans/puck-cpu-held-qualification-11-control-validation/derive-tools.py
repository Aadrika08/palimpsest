"""Derive distinct11 run-once tools from retained terminal10 tools; never invoke them."""
from pathlib import Path
import hashlib,json
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OLD=ROOT/'docs/reports/puck-cpu-held-qualification-10/tools'
NEW=ROOT/'docs/plans/puck-cpu-held-qualification-11-control-validation/tools'
EXECUTION=("'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/execution.json'","'docs/plans/puck-cpu-held-qualification-11-execution.json'",1)
STEM=('palimpsest-held10-amendment02-','palimpsest-held11-')
CONTROL=("control='796359a099131157b5b91db38f14784628d5d7c5'","control='@CONTROL@'",1)
PLAN={
    'run-admission-once.py.in':('run-admission-template.py',[EXECUTION,STEM+(3,)]),
    'run-observer-once.py.in':('run-observer-once.py',[CONTROL,EXECUTION,STEM+(3,),
        ('sole bounded actual runtime10 observer','sole bounded actual runtime11 observer',1)]),
    'run-audit-once.py.in':('run-audit-once.py',[CONTROL,EXECUTION,STEM+(2,),
        ('measured actual runtime10 transport','measured actual runtime11 transport',1)]),
    'bind-audit-command.py':('bind-audit-command.py',[
        ('complete measured10 observer transport','complete measured11 observer transport',1),
        ("BASE=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'","BASE='docs/plans/puck-cpu-held-qualification-11'",1),
        ("(BASE/'freeze.json')","(ROOT/(BASE+'-freeze.json'))",1),("(BASE/'execution.json')","(ROOT/(BASE+'-execution.json'))",1),
        ('puck-cpu-held10-amendment02-external-transport-v1','puck-cpu-held11-external-transport-v1',1),
        ('runs/puck-cpu-held-qualification-10-external-cli-transport.json','runs/puck-cpu-held-qualification-11-external-cli-transport.json',1),
        ('4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170','6e28bef8bebd6daecfdf34e762584312f984e0d77c7a822a119e0c89e136b212',1)]),
    'make-observer-guard.py':('make-observer-guard.py',[STEM+(7,),
        ("base=root/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'","base=root/'docs/plans/puck-cpu-held-qualification-11-control-validation'",1),
        ("Path('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-02.json')","Path('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json')",1),
        # Attempt11 has no failed earlier admission; refuse any second admission11 receipt instead.
        ("assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json')",
         "assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-02.json')",1),
        ("a['admission_check_id']==2 and a['qualification10_invoked'] is False","a['admission_check_id']==1 and a['qualification11_invoked'] is False",1),
        ('historical_missing_receipts=16','historical_missing_receipts=17',1),
        ('historical_records_unchanged=79','historical_records_unchanged=102',2)]),
}
rows=[]
for target,(source,pairs) in PLAN.items():
    old=(OLD/('palimpsest-held10-amendment02-'+source)).read_text();text=old
    for a,b,count in pairs:
        assert text.count(a)==count,(target,a,text.count(a))
        text=text.replace(a,b)
    assert 'held10' not in text and 'qualification-10' not in text and 'runtime10' not in text and '796359a0' not in text,target
    compile(text.replace('@CONTROL@','0'*40),target,'exec')
    with (NEW/target).open('x') as out:out.write(text)
    rows.append(dict(target=target,source='docs/reports/puck-cpu-held-qualification-10/tools/palimpsest-held10-amendment02-'+source,
        old_sha256=hashlib.sha256(old.encode()).hexdigest(),new_sha256=hashlib.sha256(text.encode()).hexdigest(),replacements=len(pairs)))
print(json.dumps(dict(derived=rows,tools_invoked=False,admission_invoked=False,runtime_invoked=False),indent=2,sort_keys=True))
