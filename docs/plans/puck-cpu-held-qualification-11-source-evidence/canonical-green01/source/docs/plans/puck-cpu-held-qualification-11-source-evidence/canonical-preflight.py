"""Prospective11 configuration metadata only; never run an admission, qualifier main or vendor."""
from pathlib import Path
import ast,hashlib,json,sys,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONFIG=ROOT/'docs/plans/puck-cpu-held-qualification-11.json'
AMENDMENT=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
AUTH=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


def module(path):
    value=types.ModuleType('held11_preflight_'+path.stem);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value


assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
raw=AUTH.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()=='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
def definition(source):return next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='canonical')
assert ast.dump(definition(raw))==ast.dump(definition(Path(__file__).read_bytes()))
old=AMENDMENT.read_bytes()
assert len(old)==8988 and hashlib.sha256(old).hexdigest()=='4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'
previous=json.loads(old)
candidate=CONFIG.read_bytes();value=json.loads(candidate)
assert candidate==canonical(value),'Canonical JSON bytes differ'
assert candidate!=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
assert set(value)==set(previous)
same=('root','stage_parent','inputs','preparation_acceptance','interpreter','environment','expected_versions','limits','claims','phase')
assert all(value[key]==previous[key] for key in same)
assert (value['kind'],value['version'],value['allocation_id'])==('puck-cpu-held-runtime-allocation-v11',11,11)
added=sorted(set(value['negative_imports'])-set(previous['negative_imports']))
assert set(previous['negative_imports'])<set(value['negative_imports']) and len(value['negative_imports'])==32 and len(added)==13
changed=[a['path'] for a,b in zip(previous['sources'],value['sources']) if a!=b]
assert [r['path'] for r in previous['sources']]==[r['path'] for r in value['sources']]
assert changed==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_runtime_qualification.py']
for row in value['sources']:
    data=(ROOT/row['path']).read_bytes()
    assert len(data)==row['size_bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
parent=module(ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
auditor=module(ROOT/'scripts/audit_puck_cpu_held_runtime.py')
parent.validate_configuration(value);auditor.configuration(value,False)
assert value['negative_imports']==parent.QUALIFY11_NEGATIVE_IMPORTS
assert parent.allocation_output(value)==auditor.allocation_output(value)=='runs/puck-cpu-held-qualification-11'
assert not any(n.split('.')[0] in {'numpy','torch','torchvision','mujoco'} for n in sys.modules)
print(json.dumps(dict(status='PASS_CANONICAL_V11_METADATA_ONLY',configuration_bytes=len(candidate),
    configuration_sha256=hashlib.sha256(candidate).hexdigest(),canonical_function_ast_matches_authenticated_reader=True,
    compact_not_pretty=True,qualifier_validate_configuration=True,auditor_configuration=True,
    added_negative_imports=added,changed_config_sources=changed,unchanged_fields=list(same),
    allocation_output=parent.allocation_output(value),admission_invoked=False,runtime_invoked=False),sort_keys=True))
