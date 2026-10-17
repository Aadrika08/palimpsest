"""Prospective14 configuration metadata only; never run an admission, qualifier main or vendor."""
from pathlib import Path
import ast,hashlib,json,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONFIG=ROOT/'docs/plans/puck-cpu-held-qualification-14.json'
OLD=ROOT/'docs/plans/puck-cpu-held-qualification-11.json'
AUTH=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


def module(path):
    value=types.ModuleType('held14_preflight_'+path.stem);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value


assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
raw=AUTH.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()=='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
def definition(source):return next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='canonical')
assert ast.dump(definition(raw))==ast.dump(definition(Path(__file__).read_bytes()))
old=json.loads(OLD.read_bytes())
candidate=CONFIG.read_bytes();value=json.loads(candidate)
assert candidate==canonical(value),'Canonical JSON bytes differ'
assert candidate!=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
changed=sorted(k for k in old if old[k]!=value[k])
assert set(old)==set(value) and changed==['allocation_id','kind','limits','preparation_acceptance','sources','stage_parent','version']
prep03=json.loads((ROOT/'docs/plans/puck-cpu-held-preparation-03.json').read_bytes())
assert value['sources']==prep03['sources'] and value['stage_parent']==prep03['stage_parent']=='/tmp/palimpsest-puck-cpu-held-03'
parent=module(ROOT/'scripts/qualify_puck_cpu_held_runtime.py');auditor=module(ROOT/'scripts/audit_puck_cpu_held_runtime.py')
assert value['limits']==parent.QUALIFY14_LIMITS and (value['limits']['normal_seconds'],value['limits']['child_hard_seconds'],value['limits']['hard_seconds'])==(360,375,390)
parent.validate_configuration(value);auditor.configuration(value,False)
blobs={role:(ROOT/row['path']).read_bytes() for role,row in value['preparation_acceptance'].items()}
prior,prep=parent.validate_preparation_acceptance(value,blobs);auditor.preparation_epoch(value,prior,prep)
held=auditor.Held(time.monotonic()+60)
try:auditor.historical_acceptance(held,value,False)
finally:held.close()
assert value['negative_imports']==parent.QUALIFY11_NEGATIVE_IMPORTS and len(value['negative_imports'])==32
assert parent.allocation_output(value)==auditor.allocation_output(value)=='runs/puck-cpu-held-qualification-14'
assert not any(n.split('.')[0] in {'numpy','torch','torchvision','mujoco'} for n in sys.modules)
print(json.dumps(dict(status='PASS_CANONICAL_EPOCH14_ON_PREPARATION03_METADATA_ONLY',configuration_bytes=len(candidate),
    configuration_sha256=hashlib.sha256(candidate).hexdigest(),canonical_function_ast_matches_authenticated_reader=True,
    changed_vs_11b=changed,limits=value['limits'],parent_validate_configuration=True,parent_validate_preparation_acceptance=True,
    auditor_configuration=True,auditor_preparation_epoch=True,auditor_historical_acceptance=True,
    preparation_acceptance=value['preparation_acceptance'],admission_invoked=False,runtime_invoked=False,stages_touched=False),sort_keys=True))
