"""Prospective amendment02 metadata only; never run an admission or vendor."""
from pathlib import Path
import ast,hashlib,json
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
AUTH=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


raw=AUTH.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()=='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
def definition(source):return next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='canonical')
assert ast.dump(definition(raw))==ast.dump(definition(Path(__file__).read_bytes()))
old=(ROOT/'docs/plans/puck-cpu-held-qualification-10.json').read_bytes()
assert hashlib.sha256(old).hexdigest()=='b7da3957cd81f017f7c59beb764577551384d54c634062f9841053c839d12915'
candidate=(BASE/'configuration.json').read_bytes();value=json.loads(candidate)
assert value==json.loads(old),'Amendment must change serialization only'
assert candidate==canonical(value),'Canonical JSON bytes differ'
print(json.dumps(dict(status='PASS_CANONICAL_METADATA_ONLY',configuration_bytes=len(candidate),
    configuration_sha256=hashlib.sha256(candidate).hexdigest(),parsed_configuration_unchanged=True,
    canonical_function_ast_matches_authenticated_reader=True,admission_invoked=False,runtime_invoked=False),sort_keys=True))
