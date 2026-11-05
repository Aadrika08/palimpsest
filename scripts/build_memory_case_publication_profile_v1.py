"""Build only prospective source profiles; never grant execution authority.

Static local Python imports are read as source, never imported or executed by
the closure walker. External numerical inputs remain separate qualification
obligations. Existing historical profiles are immutable inputs.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

from palimpsest import memory

BASE = 'docs/plans/memory-family-compact-evidence-v4-case-publication-v1-protocol.json'
CONDITION = 'docs/plans/memory-condition-seal-v1-case-publication-v1-protocol.json'
PUBLICATION = 'docs/plans/memory-case-publication-v1-protocol.json'
OLD_BASE = 'docs/plans/memory-family-compact-evidence-v4-retained-condition-v1-protocol.json'
OLD_CONDITION = 'docs/plans/memory-condition-seal-v1-retained-condition-v1-protocol.json'
OLD_HASHES = {
    OLD_BASE:'e71fc7ea6185f7de769b9879d4b581458074b925255b4712f0f6578fb0556261',
    OLD_CONDITION:'ca8f148526c4ce33a28583a33c4d0dc474e7264aba66e89946c8d2fe3cc6f93f'}
EXCLUDED = {BASE, CONDITION, PUBLICATION,
    'scripts/memory_case_execution_pins_v1.py',
    'scripts/memory_condition_qualification_pins_v1.py'}
SEEDS = {
    'scripts/memory_family_case_publication_v1.py',
    'scripts/memory_family_case_custody_v1.py',
    'scripts/memory_family_retained_case_v1.py',
    'scripts/memory_family_condition_seal_v4.py',
    'scripts/memory_condition_replay_admission_v1.py',
    'scripts/build_memory_case_publication_profile_v1.py',
    'tests/test_memory_family_case_publication_v1.py',
    'tests/test_memory_family_case_custody_v1.py',
    'tests/test_memory_family_case_publisher_v1.py',
    'tests/test_memory_case_publication_profile_v1.py',
    'tests/test_memory_publication_current_semantics_v1.py',
    'tests/test_memory_family_producer_v4.py',
    'tests/test_memory_family_condition_close_v4.py',
    'tests/test_memory_family_retained_case_v1.py',
    'tests/test_memory_retained_condition_profile_v1.py',
    'tests/memory_publication_authored_profiles.py',
    'tests/frozen_pins.py', 'tests/conftest.py',
    'docs/plans/memory-case-publication-v1.md',
    'docs/plans/memory-case-publication-v1-implementation.md', OLD_BASE}


def _descriptor(root, path):
    relative = Path(path)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != path:
        raise ValueError('Noncanonical profile dependency')
    p = root / path
    if any(part.is_symlink() for part in (p,*p.parents)) or not p.is_file():
        raise ValueError('Missing or aliased profile dependency: '+path)
    with p.open('rb') as stream:
        raw = stream.read(2*1024**2+1)
    if len(raw) > 2*1024**2:
        raise ValueError('Profile dependency exceeds source bound: '+path)
    return {'path':path, 'size_bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def _module_paths(root, name):
    parts = name.split('.')
    if parts[0] == 'palimpsest':
        stem = Path('src', *parts)
    elif parts[0] in ('scripts', 'tests'):
        stem = Path(*parts)
    elif len(parts) == 1:
        stem = Path('tests', *parts)
    else:
        return set()
    candidates = [stem.with_suffix('.py'), stem/'__init__.py']
    result = {p.as_posix() for p in candidates if (root/p).is_file()}
    if result:
        for parent in stem.parents:
            if parent.as_posix() in ('.', 'src'):
                break
            init = parent/'__init__.py'
            if (root/init).is_file(): result.add(init.as_posix())
    return result


def local_python_closure(root, seeds):
    """Conservative static local-import closure; no catalog/model traversal."""
    root = Path(root); pending = set(seeds); result = set()
    while pending:
        path = min(pending); pending.remove(path)
        if path in EXCLUDED or path in result:
            continue
        _descriptor(root, path)
        result.add(path)
        if len(result) > 512:
            raise ValueError('Declared publication closure exceeds 512 sources')
        if not path.endswith('.py'):
            continue
        tree = ast.parse((root/path).read_bytes(), filename=path)
        parts = list(Path(path).with_suffix('').parts)
        if parts[0] == 'src': parts.pop(0)
        if parts[-1] == '__init__':
            package = parts[:-1]
        elif parts[0] == 'tests':
            package = []
        else:
            package = parts[:-1]
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.level > len(package): continue
                    prefix = package[:len(package)-node.level+1]
                    base = '.'.join(prefix+([node.module] if node.module else []))
                else:
                    base = node.module or ''
                names.add(base)
                names.update(base+'.'+alias.name for alias in node.names if alias.name != '*')
        for name in names:
            pending.update(_module_paths(root, name)-result-EXCLUDED)
    return result


def build_profiles(root, *, write=False):
    """Explicit --write refreshes only three unaccepted prospective paths.

    Default verification is read-only. Once real acceptance pins exist, source
    generation refuses: further changes need a separately reviewed successor.
    """
    from scripts.memory_case_execution_pins_v1 import ACCEPTED_EXECUTION_AUDIT_SHA256
    from scripts.memory_condition_qualification_pins_v1 import TRUSTED_QUALIFICATION_PINS
    if write and (ACCEPTED_EXECUTION_AUDIT_SHA256 or TRUSTED_QUALIFICATION_PINS):
        raise PermissionError('Accepted source profiles require a reviewed successor')
    root = Path(root).resolve()
    old_base = (root/OLD_BASE).read_bytes(); old_condition = (root/OLD_CONDITION).read_bytes()
    for path,raw in ((OLD_BASE,old_base),(OLD_CONDITION,old_condition)):
        if hashlib.sha256(raw).hexdigest() != OLD_HASHES[path]:
            raise ValueError('Historical profile identity differs: '+path)
    base = json.loads(old_base); condition = json.loads(old_condition)
    inherited = copy.deepcopy(base['behavior_sources'])
    seeds = SEEDS | {r['path'] for r in inherited}
    closure = local_python_closure(root, seeds)
    sources = {p:_descriptor(root,p) for p in sorted(closure)}
    base['behavior_sources'] = [{'id':r['id'], **sources[r['path']]} for r in inherited]
    existing = {r['path'] for r in inherited}
    for i,path in enumerate(sorted(closure-existing)):
        base['behavior_sources'].append({'id':f'case_publication_dependency_{i:03d}', **sources[path]})
    base['source_revision'] = {'schema':'memory-case-publication-v1-source-profile',
        'status':'prospective-source-only', 'parent_protocol':_descriptor(root,OLD_BASE),
        'scientific_contract_changed':False, 'actual_runtime_qualified':False,
        'allocation_authorized':False}
    base_bytes = memory.canonical_bytes(base)
    base_descriptor = {'path':BASE, 'size_bytes':len(base_bytes),
                       'sha256':hashlib.sha256(base_bytes).hexdigest()}
    condition['base_protocol_sha256'] = base_descriptor['sha256']
    condition['source_pins'] = [_descriptor(root,r['path']) for r in condition['source_pins']]
    condition['source_revision'] = {'schema':'memory-condition-seal-case-publication-v1',
        'status':'prospective-source-only', 'parent_extension':_descriptor(root,OLD_CONDITION),
        'scientific_contract_changed':False, 'allocation_authorized':False}
    condition_bytes = memory.canonical_bytes(condition)
    condition_descriptor = {'path':CONDITION, 'size_bytes':len(condition_bytes),
                            'sha256':hashlib.sha256(condition_bytes).hexdigest()}

    def install(path, payload):
        destination = root/path
        if write:
            if destination.is_symlink(): raise ValueError('Aliased prospective profile')
            destination.write_bytes(payload)
        elif not destination.is_file() or destination.read_bytes() != payload:
            raise ValueError('Prospective profile requires explicit source refresh: '+path)

    # Import the consumer only after the two selected dependency profiles exist.
    install(BASE,base_bytes); install(CONDITION,condition_bytes)
    from scripts import memory_family_case_publication_v1 as publication
    rows = {p:d for p,d in sources.items()}
    for row in condition['source_pins']: rows[row['path']] = row
    if EXCLUDED & set(rows): raise ValueError('Output/trust-anchor source cycle')
    pub = {'schema':'memory-case-publication-v1-protocol',
        'base_protocol':base_descriptor, 'condition_extension':condition_descriptor,
        'schemas':copy.deepcopy(publication.PUBLICATION_SCHEMAS),
        'bounds':copy.deepcopy(publication.PUBLICATION_BOUNDS),
        'source_pins':[rows[p] for p in sorted(rows)], 'claims':copy.deepcopy(base['claims'])}
    install(PUBLICATION,memory.canonical_bytes(pub))
    for path,row in sources.items():
        if _descriptor(root,path) != row: raise RuntimeError('Source changed while generating: '+path)
    if (root/OLD_BASE).read_bytes() != old_base or (root/OLD_CONDITION).read_bytes() != old_condition:
        raise RuntimeError('Historical input changed while generating')
    return {p:_descriptor(root,p) for p in (BASE,CONDITION,PUBLICATION)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args = parser.parse_args()
    print(json.dumps(build_profiles(Path(__file__).resolve().parents[1],write=args.write),indent=2))
