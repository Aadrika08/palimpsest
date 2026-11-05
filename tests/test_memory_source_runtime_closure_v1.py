"""Authored metadata and bytes only; no runtime import or actual adoption proof."""
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    path = ROOT / 'scripts/memory_source_runtime_closure_v1.py'
    assert path.exists(), 'new source-runtime helper is absent'
    spec = importlib.util.spec_from_file_location('runtime_reference_task1', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def descriptor(path, data=b''):
    return dict(path=str(path), size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def package(base='/authored', *, files=None, directories=None, roots=None):
    m = module()
    profile = dict(profile_id='memory-source-runtime-profile-v1-proposed',
                   profile_sha256=m.PROFILE_SHA256, load_policy='retained-unqualified-v1')
    roots = roots or [dict(root=base+'/runtime', kind='complete',
                          files=files if files is not None else [descriptor('owner.py', b'x')],
                          directories=directories or [])]
    records = [dict(row, path=root['root']+'/'+row['path']) for root in roots for row in root['files']]
    pin = records[0]
    pins = dict(python_alias=base+'/alias', python_elf=pin, owner_source=pin,
                pyvenv_config=pin, required_sources=[pin])
    recipe = dict(schema='memory-source-runtime-recipe-v1', preparation_id='1'*32,
                  **profile, intended_roots=[r['root'] for r in roots], intended_standalones=[],
                  method='externally-prepared-complete-runtime-input')
    recipe_raw = canonical(recipe)
    recipe_row = descriptor(base+'/recipe.json', recipe_raw)
    manifest = dict(schema='memory-source-runtime-manifest-v1', preparation_id='1'*32,
                    **profile, recipe=recipe_row, roots=roots, standalones=[], pins=pins)
    manifest_raw = canonical(manifest)
    manifest_row = descriptor(base+'/manifest.json', manifest_raw)
    evidence = descriptor(base+'/evidence', b'e')
    charge = dict(evidence=evidence, project_cpu_ns=11, memory_cpu_ns=7)
    ledger = dict(schema='memory-source-runtime-preparation-ledger-v1', preparation_id='1'*32,
                  state='completed', recipe=recipe_row, manifest=manifest_row,
                  baseline=dict(accounting_id='2'*32, project_cpu_ns=10, memory_cpu_ns=6, evidence=evidence),
                  operations=[dict(operation_id='3'*32, outcome='failed', memory_cpu_ns=1,
                                   evidence=descriptor(base+'/operation', b'o'))],
                  retained_files=[evidence, descriptor(base+'/operation', b'o')],
                  runtime_input_bytes=sum(r['size_bytes'] for r in records),
                  external_record_bytes=len(recipe_raw)+len(manifest_raw)+2,
                  totals=dict(project_cpu_ns=11, memory_cpu_ns=7), cumulative_charge_reference=charge)
    ledger_raw = canonical(ledger)
    reference = dict(schema='memory-source-runtime-reference-v1', **profile, recipe=recipe_row,
                     manifest=manifest_row, ledger=descriptor(base+'/ledger.json', ledger_raw))
    return m, reference, manifest, recipe, ledger, pins


def validate(p):
    m, ref, manifest, recipe, ledger, pins = p
    manifest = m.validate_runtime_manifest(canonical(manifest), ref,
        required_roots=tuple(r['root'] for r in manifest['roots']), required_pins=pins,
        output_root='/authored-output')
    recipe = m.validate_preparation_recipe(canonical(recipe), ref, manifest)
    return m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe)


def repin_manifest(p):
    m, ref, manifest, recipe, ledger, pins = p
    ref['manifest'] = descriptor(ref['manifest']['path'], canonical(manifest))
    ledger['manifest'] = ref['manifest']
    ledger['runtime_input_bytes'] = sum(f['size_bytes'] for r in manifest['roots'] for f in r['files'])
    ledger['external_record_bytes'] = ref['recipe']['size_bytes']+ref['manifest']['size_bytes']+sum(f['size_bytes'] for f in ledger['retained_files'])
    ref['ledger'] = descriptor(ref['ledger']['path'], canonical(ledger))
    return p


def test_reference_validation_has_no_io(monkeypatch):
    p = package(); m, ref = p[:2]
    def forbidden(*args, **kwargs):
        raise AssertionError('pure validator performed IO')
    monkeypatch.setattr(os, 'open', forbidden)
    got = m.validate_runtime_reference(ref)
    ref['recipe']['path'] = '/changed'
    assert got['recipe']['path'] == '/authored/recipe.json'
    for patch in ({'extra': 1}, {'load_policy': True}, {'ledger': None}):
        bad = dict(got, **patch)
        with pytest.raises(ValueError): m.validate_runtime_reference(bad)
    assert validate(package())['accounting_authority_qualified'] is False


def test_manifest_exact_boundaries_and_zero_byte_files():
    p = package(files=[descriptor('owner.py')]); assert validate(p)['runtime_input_bytes'] == 0
    for size, accepted in [(2**31, True), (2**31+1, False), (True, False)]:
        p = package(files=[dict(descriptor('owner.py'), size_bytes=size)])
        if accepted: assert validate(p)['runtime_input_bytes'] == size
        else:
            with pytest.raises(ValueError): validate(p)
    p = package(); m, ref, manifest, _, _, pins = p
    for raw in (canonical(manifest)+b'\n', b'{"x":1,"x":1}', b'['*33+b'0'+b']'*33,
                b'{"x":"\\ud800"}', b'{"x":NaN}', b'x'*(16*1024**2+1)):
        changed = copy.deepcopy(ref); changed['manifest'] = descriptor(ref['manifest']['path'], raw)
        with pytest.raises(ValueError): m.validate_runtime_manifest(raw, changed,
            required_roots=('/authored/runtime',), required_pins=pins, output_root='/out')
    ref['manifest']['size_bytes'] = 16*1024**2
    m.validate_runtime_reference(ref)
    ref['manifest']['size_bytes'] += 1
    with pytest.raises(ValueError): m.validate_runtime_reference(ref)


def test_global_counts_include_root_directories():
    # Removing the root from the census would admit the one-over case.
    files = [descriptor(f'f{i:05}') for i in range(32768)]
    dirs = [f'd{i:05}' for i in range(27231)]
    assert validate(package(files=files, directories=dirs))['runtime_input_bytes'] == 0
    with pytest.raises(ValueError): validate(package(files=files+[descriptor('z')]))
    with pytest.raises(ValueError): validate(package(files=files, directories=dirs+['z']))


def test_cross_root_bytes_do_not_multiply():
    roots = [dict(root=f'/authored/r{i}', kind='complete', directories=[],
                  files=[dict(descriptor(f'f{j}'), size_bytes=2**31) for j in range(4)]) for i in range(2)]
    assert validate(package(roots=roots))['runtime_input_bytes'] == 16*2**30
    roots[1]['files'].append(dict(descriptor('z'), size_bytes=1))
    with pytest.raises(ValueError): validate(package(roots=roots))


def test_required_roots_and_duplicate_pin_equality():
    p = package(); m, ref, manifest, _, _, pins = p
    for required in [('/missing',), (), ('/different/missing',)]:
        with pytest.raises(ValueError): m.validate_runtime_manifest(canonical(manifest), ref,
            required_roots=required, required_pins=pins, output_root='/out')
    altered = copy.deepcopy(pins); altered['owner_source']['sha256'] = '0'*64
    with pytest.raises(ValueError): m.validate_runtime_manifest(canonical(manifest), ref,
        required_roots=('/authored/runtime',), required_pins=altered, output_root='/out')
    manifest['pins']['owner_source']['size_bytes'] += 1
    with pytest.raises(ValueError): validate(repin_manifest(p))


def test_acyclic_ledger_sums_copies_and_operation_uniqueness():
    p = package(); result = validate(p)
    assert result['project_cpu_ns'] == 11 and result['memory_cpu_ns'] == 7
    assert result['external_input_bytes'] == sum(p[1][x]['size_bytes'] for x in ('recipe','manifest','ledger'))+3
    for change in ('total', 'evidence', 'duplicate', 'unknown', 'bool', 'extra', 'missing'):
        p = package(); ledger = p[4]
        if change == 'total': ledger['totals']['project_cpu_ns'] = 12
        elif change == 'evidence': ledger['operations'][0]['evidence'] = ledger['baseline']['evidence']
        elif change == 'duplicate': ledger['operations'] *= 2
        elif change == 'unknown': ledger['operations'][0]['outcome'] = 'unknown'
        elif change == 'bool': ledger['operations'][0]['memory_cpu_ns'] = True
        elif change == 'extra': ledger['freeze'] = '0'*64
        else: del ledger['baseline']
        p[1]['ledger'] = descriptor(p[1]['ledger']['path'], canonical(ledger))
        with pytest.raises(ValueError): validate(p)


def test_prior_cpu_uses_exact_upward_float():
    p = package(); m, ref, manifest, recipe, ledger, _ = p
    prior = dict(project_seconds=float.fromhex('0x1.79f505f35670dp-27'), memory_seconds=float.fromhex('0x1.e1094d643f785p-28'))
    # Both nearest values round below their exact rational; these are the next binary64 values.
    result = m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe,
        prior_charge_reference=ledger['cumulative_charge_reference'], prior_cpu=prior)
    assert result['project_cpu_ns'] == 11
    for bad in [dict(prior, project_seconds=11/10**9), dict(prior, memory_seconds=0),
                dict(prior, memory_seconds=float('nan'))]:
        with pytest.raises(ValueError): m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe,
            prior_charge_reference=ledger['cumulative_charge_reference'], prior_cpu=bad)
    with pytest.raises(ValueError): m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe, prior_cpu=prior)


def authored(tmp_path):
    base = str(tmp_path)
    p = package(base, directories=['empty'])
    runtime = tmp_path/'runtime'; runtime.mkdir(); (runtime/'empty').mkdir()
    (runtime/'owner.py').write_bytes(b'x'); (tmp_path/'alias').symlink_to(runtime/'owner.py')
    for key, value in [('recipe',p[3]), ('manifest',p[2]), ('ledger',p[4])]:
        (tmp_path/(key+'.json')).write_bytes(canonical(value))
    (tmp_path/'evidence').write_bytes(b'e'); (tmp_path/'operation').write_bytes(b'o')
    return p


def holder(p, *, check=lambda: None, deadline=None):
    m, ref, manifest, _, _, pins = p
    return m.hold_runtime_manifest(ref, required_roots=tuple(r['root'] for r in manifest['roots']),
        required_pins=pins, output_root='/authored-output', deadline=time.monotonic()+30 if deadline is None else deadline,
        check=check)


def test_retained_unqualified_never_grants_load_authority(tmp_path):
    p = authored(tmp_path)
    with holder(p) as held:
        summary = held.summary()
        assert summary['current_bytes_checked'] is True
        assert [summary[k] for k in ('runtime_qualified','source_qualified','execution_authorized')] == [False]*3
        assert summary['file_count'] == 1 and summary['directory_count'] == 2 and summary['input_bytes'] == 1
        assert len(canonical(summary)) <= 2048
        charge = p[4]['cumulative_charge_reference']
        assert held.accounting(prior_charge_reference=charge, prior_cpu=dict(
            project_seconds=float.fromhex('0x1.79f505f35670dp-27'), memory_seconds=float.fromhex('0x1.e1094d643f785p-28')))['accounting_authority_qualified'] is False
        row = held.descriptor(p[5]['owner_source']['path']); row['sha256'] = 'f'*64
        assert held.descriptor(p[5]['owner_source']['path'])['sha256'] != 'f'*64
    with pytest.raises(RuntimeError): held.recheck()


def test_complete_tree_empty_directories_and_aliases(tmp_path):
    p = authored(tmp_path)
    with pytest.raises(RuntimeError, match='failed before context exit'):
      with holder(p) as held:
        (tmp_path/'irrelevant').write_bytes(b'x'); held.recheck()
        (tmp_path/'runtime/empty/new').write_bytes(b'x')
        with pytest.raises((ValueError,RuntimeError)): held.recheck()
        (tmp_path/'runtime/empty/new').unlink()
        with pytest.raises(RuntimeError): held.recheck()


@pytest.mark.parametrize('change', ['replace','restore','hardlink','symlink','emptydir'])
def test_poison_on_replacement_mutation_restore_or_teardown(tmp_path, change):
    p = authored(tmp_path); before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with holder(p) as held:
            path = tmp_path/'runtime/owner.py'
            if change == 'replace': path.unlink(); path.write_bytes(b'x')
            elif change == 'restore': path.write_bytes(b'z'); path.write_bytes(b'x')
            elif change == 'hardlink': os.link(path, tmp_path/'alias2')
            elif change == 'symlink': path.unlink(); path.symlink_to(tmp_path/'evidence')
            else: (tmp_path/'runtime/empty').rmdir()
            held.recheck()
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): held.summary()


def test_manifest_is_held_before_parse(tmp_path, monkeypatch):
    p = authored(tmp_path); m = p[0]; original = m.validate_runtime_manifest
    def replace_then_validate(*args, **kwargs):
        path = tmp_path/'manifest.json'; raw = path.read_bytes(); path.unlink(); path.write_bytes(raw)
        return original(*args, **kwargs)
    monkeypatch.setattr(m, 'validate_runtime_manifest', replace_then_validate)
    with pytest.raises((ValueError,RuntimeError)):
        with holder(p): pass


def test_deadline_and_callback_cover_read_hash_census(tmp_path):
    p = authored(tmp_path); calls = []
    def check(): calls.append(1)
    with holder(p, check=check) as held:
        before = len(calls); held.recheck(); assert len(calls)-before > 10
    with pytest.raises(TimeoutError):
        with holder(p, deadline=time.monotonic()-1): pass
    def fail(): raise RuntimeError('authored budget refusal')
    with pytest.raises(RuntimeError, match='authored budget refusal'):
        with holder(p, check=fail): pass


def test_partial_acquisition_closes_descriptors(tmp_path):
    p = authored(tmp_path); (tmp_path/'runtime/owner.py').unlink()
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with holder(p): pass
    assert len(os.listdir('/proc/self/fd')) == before


def test_new_source_limits_leave_old_puck_policy_unchanged():
    from palimpsest.puck_retained_installation import HeldInstalledFiles
    rows = [dict(descriptor(f'f{i}'), size_bytes=2**30) for i in range(4)]
    with pytest.raises(ValueError): HeldInstalledFiles('/authored', rows, [], time.monotonic()+1)
    p = package(files=rows)
    # Construction only; metadata eligibility proves no actual hold feasibility.
    holder(p)
    p[0]._SourceNamespaceFiles([dict(r,path='/authored/'+r['path']) for r in rows], [],
                             time.monotonic()+1, lambda: None)


def test_reference_rejects_ancestor_metadata_paths():
    p = package(); m, ref = p[:2]
    ref['recipe']['path'] = '/authored'
    with pytest.raises(ValueError): m.validate_runtime_reference(ref)


def test_empty_selected_root_is_censused_and_nested_required_root_is_covered(tmp_path):
    p = authored(tmp_path)
    p[2]['roots'].append(dict(root=str(tmp_path/'zero'), kind='complete', files=[], directories=[]))
    p[3]['intended_roots'].append(str(tmp_path/'zero'))
    p[1]['recipe'] = descriptor(p[1]['recipe']['path'], canonical(p[3])); p[2]['recipe'] = p[1]['recipe']; p[4]['recipe'] = p[1]['recipe']
    repin_manifest(p)
    for key, value in [('recipe',p[3]),('manifest',p[2]),('ledger',p[4])]: (tmp_path/(key+'.json')).write_bytes(canonical(value))
    (tmp_path/'zero').mkdir()
    with pytest.raises((ValueError, RuntimeError)):
        with holder(p) as held:
            assert held.summary()['directory_count'] == 3
            (tmp_path/'zero/extra').write_bytes(b'x')
            held.recheck()
    p = package()
    p[0].validate_runtime_manifest(canonical(p[2]), p[1], required_roots=('/authored/runtime','/authored/runtime/pkg'),
                                  required_pins=p[5], output_root='/out')


@pytest.mark.parametrize('alias', ['metadata', 'cross-root'])
def test_global_inode_aliases_refuse_across_holders_and_roots(tmp_path, alias):
    p = authored(tmp_path)
    path = tmp_path/'runtime/owner.py'
    if alias == 'metadata':
        # Equal authored evidence/runtime bytes still represent two forbidden links.
        path.unlink(); os.link(tmp_path/'evidence', path)
        p[2]['roots'][0]['files'][0] = descriptor('owner.py', b'e')
        pin = descriptor(path,b'e')
        p[5].clear(); p[5].update(python_alias=str(tmp_path/'alias'), python_elf=pin,
            owner_source=pin, pyvenv_config=pin, required_sources=[pin])
        p[2]['pins'] = p[5]
    else:
        other = tmp_path/'zero'; other.mkdir(); os.link(path,other/'owner.py')
        p[2]['roots'].append(dict(root=str(other),kind='complete',files=[descriptor('owner.py', b'x')],directories=[]))
        p[3]['intended_roots'].append(str(other))
        p[1]['recipe'] = descriptor(p[1]['recipe']['path'],canonical(p[3])); p[2]['recipe']=p[1]['recipe']; p[4]['recipe']=p[1]['recipe']
    repin_manifest(p)
    for key, value in [('recipe',p[3]),('manifest',p[2]),('ledger',p[4])]: (tmp_path/(key+'.json')).write_bytes(canonical(value))
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError,RuntimeError)):
        with holder(p): pass
    assert len(os.listdir('/proc/self/fd')) == before


def test_teardown_close_failure_poison_closes_remaining_descriptors(tmp_path, monkeypatch):
    p = authored(tmp_path); m = p[0]; real_close = os.close; failed = []
    held = holder(p); held.__enter__(); before = len(os.listdir('/proc/self/fd'))
    def close(fd):
        real_close(fd)
        if not failed:
            failed.append(fd); raise OSError('authored close failure')
    monkeypatch.setattr(m.os, 'close', close)
    with pytest.raises(OSError,match='authored close failure'): held.__exit__(None,None,None)
    assert len(os.listdir('/proc/self/fd')) < before
    with pytest.raises(RuntimeError): held.summary()


def test_ledger_rejects_manifest_that_was_never_schema_validated():
    p = package(); p[2]['roots'][0]['kind'] = 'partial'; repin_manifest(p)
    with pytest.raises(ValueError): p[0].validate_preparation_ledger(canonical(p[4]), p[1], p[2], p[3])


@pytest.mark.parametrize('path', ['/','/a//b','/a/../b','/a/','/a:b','/a\\b','/a\x7f','/a/'+'x'*256])
def test_paths_are_closed_posix_unicode(path):
    p = package(); p[1]['manifest']['path'] = path
    with pytest.raises(ValueError): p[0].validate_runtime_reference(p[1])


def test_positive_zero_and_integer_allocation_boundary():
    p = package(); m, ref, manifest, recipe, ledger, _ = p
    ledger['baseline'].update(project_cpu_ns=0,memory_cpu_ns=0); ledger['operations'] = []
    ledger['totals'].update(project_cpu_ns=0,memory_cpu_ns=0)
    ledger['cumulative_charge_reference'].update(project_cpu_ns=0,memory_cpu_ns=0)
    ref['ledger'] = descriptor(ref['ledger']['path'], canonical(ledger))
    m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe,
        prior_charge_reference=ledger['cumulative_charge_reference'], prior_cpu=dict(project_seconds=0.0,memory_seconds=0.0))
    for value in (-0.0, 0, False, math.inf):
        with pytest.raises(ValueError): m.validate_preparation_ledger(canonical(ledger),ref,manifest,recipe,
            prior_charge_reference=ledger['cumulative_charge_reference'], prior_cpu=dict(project_seconds=value,memory_seconds=0.0))
    for ns, accepted in [(41400*10**9,True),(41400*10**9+1,False)]:
        ledger['baseline'].update(project_cpu_ns=ns,memory_cpu_ns=ns)
        ledger['totals'].update(project_cpu_ns=ns,memory_cpu_ns=ns)
        ledger['cumulative_charge_reference'].update(project_cpu_ns=ns,memory_cpu_ns=ns)
        ref['ledger'] = descriptor(ref['ledger']['path'], canonical(ledger))
        prior = dict(project_seconds=41400.0,memory_seconds=41400.0) if accepted else dict(
            project_seconds=math.nextafter(41400.0,math.inf),memory_seconds=math.nextafter(41400.0,math.inf))
        if accepted: m.validate_preparation_ledger(canonical(ledger),ref,manifest,recipe, prior_charge_reference=ledger['cumulative_charge_reference'],prior_cpu=prior)
        else:
            with pytest.raises(ValueError): m.validate_preparation_ledger(canonical(ledger),ref,manifest,recipe,prior_charge_reference=ledger['cumulative_charge_reference'],prior_cpu=prior)


def test_zero_byte_evidence_and_distinct_physical_copies_are_counted():
    p = package(); ledger = p[4]
    zero = descriptor('/authored/zero')
    ledger['retained_files'].append(zero)
    ledger['retained_files'].sort(key=lambda r:r['path'])
    repin_manifest(p)
    result = validate(p); first_ledger_size = p[1]['ledger']['size_bytes']
    copy_row = descriptor('/authored/another-copy', b'e')
    ledger['retained_files'].append(copy_row); ledger['retained_files'].sort(key=lambda r:r['path'])
    repin_manifest(p)
    result2 = validate(p)
    assert result2['external_input_bytes']-p[1]['ledger']['size_bytes'] == result['external_input_bytes']-first_ledger_size+1


def test_actual_manifest_canonical_byte_limit_is_exact():
    # Only authored JSON metadata: no large filesystem payload is created/read.
    files = [descriptor(f'f{i:05}'+('x'*249)) for i in range(32768)]
    p = package(files=files)
    manifest = p[2]
    remaining = 16*1024**2-len(canonical(manifest))
    # Each appended directory adds its quoted text and one comma, except first.
    count = (remaining+257)//258
    dirs = [f'd{i:05}'+('x'*249) for i in range(count)]
    manifest['roots'][0]['directories'] = dirs
    over = len(canonical(manifest))-16*1024**2
    dirs[-1] = dirs[-1][:-over] if over else dirs[-1]
    assert len(dirs[-1]) >= 6 and len(canonical(manifest)) == 16*1024**2
    assert validate(repin_manifest(p))['runtime_input_bytes'] == 0
    dirs[-1] += 'x'
    with pytest.raises(ValueError): validate(repin_manifest(p))


def test_standalone_file_ancestor_paths_refuse_in_manifest():
    p = package(); p[2]['standalones'] = [descriptor('/elsewhere/a'),descriptor('/elsewhere/a/b')]
    repin_manifest(p)
    with pytest.raises(ValueError): p[0].validate_runtime_manifest(canonical(p[2]),p[1],
        required_roots=('/authored/runtime',),required_pins=p[5],output_root='/out')


def test_ancestor_paths_refuse_despite_lexically_interposed_sibling():
    p = package(); p[2]['standalones'] = [descriptor('/elsewhere/a'),descriptor('/elsewhere/a-else'),descriptor('/elsewhere/a/b')]
    repin_manifest(p)
    with pytest.raises(ValueError): p[0].validate_runtime_manifest(canonical(p[2]),p[1],
        required_roots=('/authored/runtime',),required_pins=p[5],output_root='/out')


def test_combined_absolute_runtime_path_has_its_own_byte_bound():
    root = '/'+'/'.join(['r'*255]*13)
    relative = '/'.join(['d'*255]*4)
    dirs = ['/'.join(['d'*255]*n) for n in range(1,4)]
    p = package(roots=[dict(root=root,kind='complete',files=[descriptor('a'),descriptor(relative)],directories=dirs)])
    with pytest.raises(ValueError): p[0].validate_runtime_manifest(canonical(p[2]),p[1],
        required_roots=(root,),required_pins=p[5],output_root='/out')


@pytest.mark.parametrize('character', ['x', '"'])
def test_runtime_reference_accepts_schema_bounded_paths_above_charge_budget(character):
    p = package(); m, ref = p[:2]
    for kind in ('recipe', 'manifest', 'ledger'):
        prefix = '/'+kind+'/'
        remaining = 4096-len(prefix)
        components = []
        while remaining > 255:
            components.append(character*255)
            remaining -= 256
        components.append(character*remaining)
        ref[kind]['path'] = prefix+'/'.join(components)
        assert len(ref[kind]['path'].encode('utf-8')) == 4096
    assert len(canonical(ref)) > 8192
    if character == '"':
        assert len(canonical(ref)) > 16384
    normalized = m.validate_runtime_reference(ref)
    assert normalized == ref
    too_long = copy.deepcopy(ref)
    too_long['recipe']['path'] += character
    with pytest.raises(ValueError): m.validate_runtime_reference(too_long)
    ref['recipe']['path'] = '/changed'
    assert normalized['recipe']['path'] != ref['recipe']['path']


@pytest.mark.parametrize('charge,cpu', [(None,None), (None,{}), ({},None), ([],{}), ({},[])])
def test_handle_accounting_requires_prior_dictionaries_and_poisons(tmp_path, charge, cpu):
    p = authored(tmp_path)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with holder(p) as held:
            with pytest.raises(ValueError):
                held.accounting(prior_charge_reference=charge, prior_cpu=cpu)
            with pytest.raises(RuntimeError): held.summary()
            with pytest.raises(RuntimeError): held.recheck()
    assert len(os.listdir('/proc/self/fd')) == before


def test_pure_ledger_retains_explicit_both_absent_child_mode():
    p = package(); m, ref, manifest, recipe, ledger, _ = p
    result = m.validate_preparation_ledger(canonical(ledger), ref, manifest, recipe,
        prior_charge_reference=None, prior_cpu=None)
    assert result == dict(runtime_input_bytes=1,
        external_input_bytes=sum(ref[k]['size_bytes'] for k in ('recipe','manifest','ledger'))+3,
        project_cpu_ns=11, memory_cpu_ns=7, accounting_authority_qualified=False)
