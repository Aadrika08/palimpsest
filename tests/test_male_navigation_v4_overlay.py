"""M7 navigation v4 S0 overlay, pin copies and hand-off: synthetic worktrees only.

No producer at a real producing commit is imported or run and no real data is opened.
The only real-repository reads are git source objects and the pin documents.
"""
import copy
import functools
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import regenerate_male_navigation_v4 as driver

PROTOCOL_SHA = 'cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477'
ORIGINAL_BASELINE = 'b'*64
ORIGINAL_DATA = 'd'*64
FAKE_MODULES = ('fake_reader', 'fake_producer', 'fake_stale', 'fake_inline', 'fake_import_time', 'fakepkg', 'ghost_mod')


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


FAKE_DOC = {'baseline_sha256': ORIGINAL_BASELINE, 'source_sha256': {'src/fakepkg/__init__.py': 'pinned-by-guard'}, 'limit': 3}
READER = '''
    """Synthetic reader with a protocol-wrapper pin (like prepare_male_recovery_data)."""
    import hashlib
    import json
    from pathlib import Path
    import fakepkg
    ROOT = Path(__file__).resolve().parents[1]
    PROTOCOL_PATH = 'docs/plans/fake-protocol.json'
    PROTOCOL_SHA256 = '{protocol_sha}'

    def protocol():
        raw = (ROOT/PROTOCOL_PATH).read_bytes()
        if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
            raise ValueError('Frozen protocol differs')
        return json.loads(raw)
'''
PRODUCER = '''
    """Synthetic producer with a data-identity pin (like train_male_recovery)."""
    import argparse
    import hashlib
    import json
    from pathlib import Path
    import fake_reader
    DATA_SHA256 = '{data}'

    def observed():
        return {{'protocol_path': fake_reader.PROTOCOL_PATH, 'protocol': fake_reader.protocol(), 'data': DATA_SHA256}}

    def main(argv=None):
        parser = argparse.ArgumentParser()
        parser.add_argument('--input', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args = parser.parse_args(argv)
        if hashlib.sha256(args.input.read_bytes()).hexdigest() != DATA_SHA256:
            raise ValueError('Pinned input differs')
        p = fake_reader.protocol()
        args.output.mkdir()
        (args.output/'result.json').write_text(json.dumps({{'baseline': p['baseline_sha256'], 'data': DATA_SHA256}}))
        return 0
'''


def make_worktree(base, extra=None, *, detach=True):
    root = Path(base)
    doc = json.dumps(FAKE_DOC, indent=2) + '\n'
    files = {'docs/plans/fake-protocol.json': doc,
             'src/fakepkg/__init__.py': 'def pinned():\n    return "helper"\n',
             'scripts/fake_reader.py': textwrap.dedent(READER.format(protocol_sha=sha(doc.encode()))),
             'scripts/fake_producer.py': textwrap.dedent(PRODUCER.format(data=ORIGINAL_DATA)),
             'scripts/fake_s0a.py': 'import sys\nfrom pathlib import Path\nPath(sys.argv[2]).mkdir()\n'
                                    '(Path(sys.argv[2])/"data.json").write_text("{}")\n',
             **(extra or {})}
    for name, text in files.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    git(root.parent, 'init', '-q', str(root))
    git(root, 'add', '-A'); git(root, 'commit', '-q', '-m', 'producing commit')
    commit = git(root, 'rev-parse', 'HEAD')
    if detach: git(root, 'checkout', '-q', '--detach', commit)
    return root, commit


def specs(root, commit):
    reader_rebinds = [
        {'module': 'fake_reader', 'attribute': 'PROTOCOL_PATH', 'kind': 'document-path', 'document': 'fake-protocol.json'},
        {'module': 'fake_reader', 'attribute': 'PROTOCOL_SHA256', 'kind': 'document-sha256', 'document': 'fake-protocol.json'}]
    return {
        'S0a': {'stage': 'S0a', 'producer': 'scripts/fake_s0a.py', 'module': 'fake_s0a', 'commit': commit,
                'producer_sha256': sha((root/'scripts/fake_s0a.py').read_bytes()), 'source_guards': {},
                'documents': [], 'rebinds': [], 'upstream_values': [], 'execution': 'subprocess',
                'args': {'--output': {'kind': 'output'}}},
        'S0b': {'stage': 'S0b', 'producer': 'scripts/fake_producer.py', 'module': 'fake_producer', 'commit': commit,
                'producer_sha256': sha((root/'scripts/fake_producer.py').read_bytes()),
                'source_guards': {'src/fakepkg/__init__.py': sha((root/'src/fakepkg/__init__.py').read_bytes())},
                'documents': ['fake-protocol.json'],
                'rebinds': reader_rebinds + [{'module': 'fake_producer', 'attribute': 'DATA_SHA256', 'kind': 'output-sha256',
                                              'stage': 'S0a', 'output': 'data.json'}],
                'upstream_values': [], 'execution': 'in-process',
                'args': {'--input': {'kind': 'record', 'stage': 'S0a'}, '--output': {'kind': 'output'}}},
    }


def declarations(root):
    raw = (root/'docs/plans/fake-protocol.json').read_bytes()
    return {'schema': driver.DECLARATION_SCHEMA, 'protocol_sha256': PROTOCOL_SHA, 'documents': {'fake-protocol.json': {
        'original_path': 'docs/plans/fake-protocol.json', 'original_sha256': sha(raw), 'consumed_by': ['S0b'],
        'fields': [{'pointer': '/baseline_sha256', 'class': 'sha256', 'stage': 'S0a', 'placeholder': 'PENDING-S0a'}]}}}


@pytest.fixture
def isolated_imports(monkeypatch):
    saved_path, saved_cwd, saved_argv = list(sys.path), os.getcwd(), list(sys.argv)
    yield
    for name in list(sys.modules):
        if name.partition('.')[0] in FAKE_MODULES: del sys.modules[name]
    sys.path[:] = saved_path; os.chdir(saved_cwd); sys.argv[:] = saved_argv


@pytest.fixture
def chain(tmp_path):
    """Producing worktree, a synthetic S0a pin record and a filled v4 pin copy."""
    root, commit = make_worktree(tmp_path/'wt')
    stage = specs(root, commit)
    s0a_out = tmp_path/'s0a-out'; s0a_out.mkdir(); (s0a_out/'data.json').write_text('{"rows": 1}')
    record = driver.make_pin_record(stage['S0a'], 'S0a', root, s0a_out, None, protocol_sha256=PROTOCOL_SHA)
    record_path = tmp_path/'s0a-record.json'; driver.write_pin_record(record_path, record)
    pins = tmp_path/'pins'; pins.mkdir()
    decl = declarations(root)
    template = json.loads((root/'docs/plans/fake-protocol.json').read_text()); template['baseline_sha256'] = 'PENDING-S0a'
    (pins/'fake-protocol.json').write_text(json.dumps(template, indent=2) + '\n')
    filled = driver.fill_document((pins/'fake-protocol.json').read_bytes(), decl['documents']['fake-protocol.json'],
                                  {'/baseline_sha256': record['outputs']['data.json']['sha256']})
    (pins/'fake-protocol.json').write_bytes(filled)
    (pins/'declared-fields.json').write_text(json.dumps(decl))
    return {'root': root, 'commit': commit, 'specs': stage, 'record': record, 'record_path': record_path,
            'pins': pins, 'decl': decl, 'tmp': tmp_path, 'input': s0a_out/'data.json'}


def overlay_values(c):
    chain_records = driver.check_pin_record(c['record'], 'S0b', c['specs'], protocol_sha256=PROTOCOL_SHA)
    documents = driver.load_pin_documents(c['specs']['S0b'], c['pins'], c['decl'], c['root'], chain_records)
    return driver.overlay_values(c['specs']['S0b'], c['pins'], documents, chain_records)


# ------------------------------------------------------------------- overlay rebinding

def test_overlay_rebinds_exactly_the_declared_pins_and_every_read_site_sees_v4(chain, isolated_imports):
    values = overlay_values(chain)
    module, report = driver.apply_overlay(chain['root'], chain['specs']['S0b'], values)
    seen = module.observed()
    assert seen['protocol_path'] == str(chain['pins']/'fake-protocol.json')
    assert seen['protocol']['baseline_sha256'] == chain['record']['outputs']['data.json']['sha256']
    assert seen['data'] == chain['record']['outputs']['data.json']['sha256']
    assert sorted(report['changed']) == ['fake_producer.DATA_SHA256', 'fake_reader.PROTOCOL_PATH',
                                         'fake_reader.PROTOCOL_SHA256']
    assert report['import_order'] == ['fake_reader', 'fake_producer']
    assert all(Path(p).is_relative_to(chain['root']) for p in report['origins'].values())


def test_unchanged_attributes_and_guards_survive_overlay(chain, isolated_imports):
    values = overlay_values(chain)
    module, _ = driver.apply_overlay(chain['root'], chain['specs']['S0b'], values)
    assert sys.modules['fake_reader'].ROOT == chain['root'].resolve()
    assert sys.modules['fakepkg'].pinned() == 'helper'


def test_dependent_module_imported_before_overlay_is_refused(chain, isolated_imports):
    sys.path.insert(0, str(chain['root']/'scripts')); sys.path.insert(0, str(chain['root']/'src'))
    import fake_reader  # noqa: F401 - simulates a read-site import before rebinding
    with pytest.raises(driver.Refusal, match='already imported'):
        driver.apply_overlay(chain['root'], chain['specs']['S0b'], overlay_values(chain))


def test_module_resolving_outside_worktree_is_refused(chain, isolated_imports, tmp_path):
    elsewhere = tmp_path/'elsewhere'; elsewhere.mkdir(); (elsewhere/'ghost_mod.py').write_text('X = 1\n')
    sys.path.append(str(elsewhere))
    spec = copy.deepcopy(chain['specs']['S0b'])
    spec['rebinds'].append({'module': 'ghost_mod', 'attribute': 'X', 'kind': 'output-sha256', 'stage': 'S0a', 'output': 'data.json'})
    values = overlay_values(chain); values[('ghost_mod', 'X')] = 'v'
    with pytest.raises(driver.Refusal, match='outside the producing worktree'):
        driver.apply_overlay(chain['root'], spec, values)


@pytest.mark.parametrize('name,source,match', [
    ('fake_stale', 'from fake_reader import PROTOCOL_SHA256\n', 'copies rebound pin'),
    ('fake_inline', 'def check(raw):\n    return raw == "{data}"\n', 'inline literal'),
    ('fake_import_time', 'import fake_reader\nPROTOCOL = fake_reader.protocol()\n', 'import-time read'),
])
def test_unreachable_read_sites_are_refused(tmp_path, name, source, match):
    root, commit = make_worktree(tmp_path/'wt', {f'scripts/{name}.py': source.format(data=ORIGINAL_DATA)})
    producer = (root/'scripts/fake_producer.py').read_text().replace('import fake_reader\n', f'import fake_reader\nimport {name}\n', 1)
    (root/'scripts/fake_producer.py').write_text(producer)
    spec = specs(root, commit)['S0b']
    findings = driver.static_reachability(lambda rel: driver.read_text_or_none(root/rel), spec, {'fake_reader.PROTOCOL_SHA256': 'x'*64,
                                          'fake_producer.DATA_SHA256': ORIGINAL_DATA, 'fake_reader.PROTOCOL_PATH': 'docs/plans/fake-protocol.json'})
    assert any(match in finding for finding in findings), findings


def test_child_reexecution_of_rebound_module_is_refused_but_allowed_without_rebinds(tmp_path):
    reexec = ('import subprocess, sys\nSCRIPT = __file__\n'
              'def spawn():\n    subprocess.run([sys.executable, SCRIPT, "--worker"])\n')
    root, commit = make_worktree(tmp_path/'wt', {'scripts/fake_producer.py': textwrap.dedent(PRODUCER.format(data=ORIGINAL_DATA)) + reexec})
    spec = specs(root, commit)['S0b']
    read = lambda rel: driver.read_text_or_none(root/rel)
    originals = {'fake_producer.DATA_SHA256': ORIGINAL_DATA}
    assert any('re-executes' in f for f in driver.static_reachability(read, spec, originals))
    spec['rebinds'] = []
    assert not any('re-executes' in f for f in driver.static_reachability(read, spec, {}))


def test_clean_synthetic_closure_has_no_reachability_findings(chain):
    read = lambda rel: driver.read_text_or_none(chain['root']/rel)
    originals = {'fake_reader.PROTOCOL_SHA256': sha((chain['root']/'docs/plans/fake-protocol.json').read_bytes()),
                 'fake_reader.PROTOCOL_PATH': 'docs/plans/fake-protocol.json', 'fake_producer.DATA_SHA256': ORIGINAL_DATA}
    assert driver.static_reachability(read, chain['specs']['S0b'], originals) == []


# ------------------------------------------------------------------- producer bytes and guards

def test_detached_worktree_at_producing_commit_passes(chain):
    report = driver.verify_worktree(chain['root'], chain['specs']['S0b'])
    assert report['head'] == chain['commit'] and report['detached'] is True


def test_worktree_at_other_commit_or_on_branch_is_refused(tmp_path):
    root, commit = make_worktree(tmp_path/'wt', detach=False)
    spec = specs(root, commit)['S0b']
    with pytest.raises(driver.Refusal, match='detached'):
        driver.verify_worktree(root, spec)
    git(root, 'checkout', '-q', '--detach')
    spec['commit'] = '0'*40
    with pytest.raises(driver.Refusal, match='producing commit'):
        driver.verify_worktree(root, spec)


@pytest.mark.parametrize('mutation,match', [
    (lambda r: (r/'scripts/fake_producer.py').write_text('# edited\n'), 'tracked files differ'),
    (lambda r: (r/'scripts/planted.py').write_text('X = 1\n'), 'untracked source'),
    (lambda r: (r/'src/fakepkg/__init__.py').write_text('def pinned():\n    return 1\n'), 'tracked files differ'),
])
def test_changed_producer_bytes_are_refused(chain, mutation, match):
    mutation(chain['root'])
    with pytest.raises(driver.Refusal, match=match):
        driver.verify_worktree(chain['root'], chain['specs']['S0b'])


def test_source_guard_and_producer_pin_mismatches_are_refused(chain):
    spec = copy.deepcopy(chain['specs']['S0b']); spec['source_guards'] = {'src/fakepkg/__init__.py': '0'*64}
    with pytest.raises(driver.Refusal, match='source guard'):
        driver.verify_worktree(chain['root'], spec)
    spec = copy.deepcopy(chain['specs']['S0b']); spec['producer_sha256'] = '0'*64
    with pytest.raises(driver.Refusal, match='producer bytes'):
        driver.verify_worktree(chain['root'], spec)


def git_source(commit):
    @functools.lru_cache(maxsize=None)
    def read(rel):
        done = subprocess.run(['git', 'show', f'{commit}:{rel}'], cwd=ROOT, capture_output=True)
        return done.stdout.decode() if done.returncode == 0 else None
    return read


def test_real_stage_table_pins_producer_bytes_and_guards_at_producing_commits():
    assert list(driver.STAGES) == ['S0a', 'S0b', 'S0c', 'S0d', 'S0e', 'S0f']
    for stage, spec in driver.STAGES.items():
        read = git_source(spec['commit'])
        assert sha(read(spec['producer']).encode()) == spec['producer_sha256'], stage
        for rel, pin in spec['source_guards'].items():
            assert sha(read(rel).encode()) == pin, (stage, rel)
    assert driver.STAGES['S0f']['historical_commit'] == '217cbee8399dcb25045a079af012beecbbdae29e'
    assert not any(spec['rebinds'] for stage, spec in driver.STAGES.items() if stage in ('S0a', 'S0b'))


def test_real_stage_reachability_finds_unreachable_s0e_and_s0f_sites():
    """In-process rebinding reaches S0c/S0d; S0e/S0f re-execute rebound modules or inline pins."""
    results = {stage: driver.static_reachability(git_source(spec['commit']), spec,
                                                 driver.original_values(spec, git_source(spec['commit'])))
               for stage, spec in driver.STAGES.items()}
    assert results['S0a'] == results['S0b'] == results['S0c'] == results['S0d'] == []
    assert any('re-executes' in f and 'collect_male_navigation_v2' in f for f in results['S0e'])
    assert any('inline literal' in f and 'male_recovery_research' in f for f in results['S0e'])
    assert any('import-time read' in f for f in results['S0e'])
    assert any('re-executes' in f and 'prepare_male_navigation_v2' in f for f in results['S0f'])


# ------------------------------------------------------------------- v4 pin-document copies

def real_declarations():
    return json.loads((ROOT/'docs/plans/m7-navigation-v4-pins/declared-fields.json').read_text())


def test_real_v4_pin_copies_differ_only_in_declared_fields():
    decl = real_declarations()
    assert decl['protocol_sha256'] == PROTOCOL_SHA
    assert set(decl['documents']) == {'m7-recovery-learning-protocol.json', 'm7-navigation-contact-v2-protocol.json',
                                      'm7-navigation-data-v2-protocol.json', 'male-recovery-research-development-v1.json'}
    for name, item in decl['documents'].items():
        original = (ROOT/item['original_path']).read_bytes()
        assert sha(original) == item['original_sha256'], name
        copy_bytes = (ROOT/'docs/plans/m7-navigation-v4-pins'/name).read_bytes()
        declared = {f['pointer'] for f in item['fields']}
        assert driver.field_diff(json.loads(original), json.loads(copy_bytes)) == declared, name
        driver.check_pin_document(original, copy_bytes, item, consumer=False)


def test_real_v4_pin_copies_hold_explicit_stage_placeholders_and_are_refused_by_consumers():
    decl = real_declarations()
    for name, item in decl['documents'].items():
        doc = json.loads((ROOT/'docs/plans/m7-navigation-v4-pins'/name).read_text())
        for field in item['fields']:
            assert field['placeholder'] == 'PENDING-' + field['stage']
            assert driver.pointer_get(doc, field['pointer']) == field['placeholder']
            assert field['stage'] in driver.STAGES
        original = (ROOT/item['original_path']).read_bytes()
        with pytest.raises(driver.Refusal, match='PENDING'):
            driver.check_pin_document(original, (ROOT/'docs/plans/m7-navigation-v4-pins'/name).read_bytes(), item, consumer=True)


def test_real_v4_source_behaviour_fields_are_unchanged():
    decl = real_declarations()['documents']
    learning = json.loads((ROOT/'docs/plans/m7-navigation-v4-pins/m7-recovery-learning-protocol.json').read_text())
    original = json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
    for key in ('source_code_sha256', 'recovery_protocol_sha256', 'recovery_source_commit', 'training', 'counts'):
        assert learning[key] == original[key]
    contact = json.loads((ROOT/'docs/plans/m7-navigation-v4-pins/m7-navigation-contact-v2-protocol.json').read_text())
    assert contact['contact_profile']['sha256'] == '1593421ae2cc1a12b0d9aeae6646fda77da1d11a885ffac3406e52dc6af12186'
    assert all(f['stage'] in ('S0a', 'S0b', 'S0c', 'S0d', 'S0e', 'S0f') for d in decl.values() for f in d['fields'])


def test_field_level_diff_fixture_refuses_undeclared_change(chain):
    item = chain['decl']['documents']['fake-protocol.json']
    original = (chain['root']/'docs/plans/fake-protocol.json').read_bytes()
    changed = json.loads(original); changed['limit'] = 4
    with pytest.raises(driver.Refusal, match='undeclared'):
        driver.check_pin_document(original, json.dumps(changed).encode(), item, consumer=False)
    nested = json.loads(original); nested['source_sha256']['src/fakepkg/__init__.py'] = 'other'
    assert driver.field_diff(json.loads(original), nested) == {'/source_sha256/src~1fakepkg~1__init__.py'}
    with pytest.raises(driver.Refusal, match='undeclared'):
        driver.check_pin_document(original, json.dumps(nested).encode(), item, consumer=False)


def test_fill_document_refuses_undeclared_pointer_and_double_fill(chain):
    item = chain['decl']['documents']['fake-protocol.json']
    template = json.loads((chain['root']/'docs/plans/fake-protocol.json').read_text()); template['baseline_sha256'] = 'PENDING-S0a'
    raw = json.dumps(template).encode()
    with pytest.raises(driver.Refusal, match='undeclared'):
        driver.fill_document(raw, item, {'/limit': 4})
    filled = driver.fill_document(raw, item, {'/baseline_sha256': 'e'*64})
    with pytest.raises(driver.Refusal, match='placeholder'):
        driver.fill_document(filled, item, {'/baseline_sha256': 'f'*64})


# ------------------------------------------------------------------- pin hand-off

def test_matching_previous_record_input_is_accepted(chain):
    records = driver.check_pin_record(chain['record'], 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)
    checked = driver.check_arguments(chain['specs']['S0b'], ['--input', str(chain['input']), '--output', str(chain['tmp']/'out')],
                                     chain['root'], records, open_inputs=True)
    assert checked['--input']['sha256'] == chain['record']['outputs']['data.json']['sha256']


def test_input_outside_previous_record_or_changed_is_refused(chain):
    records = driver.check_pin_record(chain['record'], 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)
    other = chain['tmp']/'other.json'; other.write_text('{"rows": 1}')
    with pytest.raises(driver.Refusal, match='previous sub-stage'):
        driver.check_arguments(chain['specs']['S0b'], ['--input', str(other), '--output', str(chain['tmp']/'o')],
                               chain['root'], records, open_inputs=True)
    chain['input'].write_text('{"rows": 2}')
    with pytest.raises(driver.Refusal, match='pin record'):
        driver.check_arguments(chain['specs']['S0b'], ['--input', str(chain['input']), '--output', str(chain['tmp']/'o')],
                               chain['root'], records, open_inputs=True)


@pytest.mark.parametrize('argv,match', [
    (['--input', 'X', '--output', 'O', '--extra', '1'], 'undeclared argument'),
    (['--input', 'X', 'positional'], 'undeclared argument'),
    (['--input', 'X'], 'missing'),
])
def test_undeclared_or_missing_arguments_are_refused(chain, argv, match):
    records = driver.check_pin_record(chain['record'], 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)
    argv = [str(chain['input']) if a == 'X' else str(chain['tmp']/'o') if a == 'O' else a for a in argv]
    with pytest.raises(driver.Refusal, match=match):
        driver.check_arguments(chain['specs']['S0b'], argv, chain['root'], records, open_inputs=True)


def test_existing_output_and_fixed_value_violations_are_refused(chain):
    records = driver.check_pin_record(chain['record'], 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)
    with pytest.raises(driver.Refusal, match='fresh'):
        driver.check_arguments(chain['specs']['S0b'], ['--input', str(chain['input']), '--output', str(chain['tmp'])],
                               chain['root'], records, open_inputs=True)
    assert driver.STAGES['S0a']['args']['--research-stage'] == {'kind': 'value', 'allowed': ['development']}
    spec = {'args': {'--research-stage': {'kind': 'value', 'allowed': ['development']}}}
    with pytest.raises(driver.Refusal, match='not allowed'):
        driver.check_arguments(spec, ['--research-stage', 'held_out'], chain['root'], {}, open_inputs=True)


@pytest.mark.parametrize('mutate,match', [
    (lambda r: r.update(stage='S0c'), 'previous sub-stage'),
    (lambda r: r.update(protocol_sha256='0'*64), 'protocol'),
    (lambda r: r.update(schema='other'), 'schema'),
    (lambda r: r['chain'].pop('S0a'), 'chain'),
    (lambda r: r['outputs'].update({'data.json': {'sha256': '0'*64, 'bytes': 1}}), 'chain'),
])
def test_wrong_previous_record_is_refused(chain, mutate, match):
    record = copy.deepcopy(chain['record']); mutate(record)
    with pytest.raises(driver.Refusal, match=match):
        driver.check_pin_record(record, 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)


def test_filled_document_values_must_trace_to_the_record_chain(chain):
    records = driver.check_pin_record(chain['record'], 'S0b', chain['specs'], protocol_sha256=PROTOCOL_SHA)
    template = json.loads((chain['root']/'docs/plans/fake-protocol.json').read_text()); template['baseline_sha256'] = 'PENDING-S0a'
    item = chain['decl']['documents']['fake-protocol.json']
    bad = driver.fill_document(json.dumps(template, indent=2).encode() + b'\n', item, {'/baseline_sha256': 'e'*64})
    (chain['pins']/'fake-protocol.json').write_bytes(bad)
    with pytest.raises(driver.Refusal, match='not an output of S0a'):
        driver.load_pin_documents(chain['specs']['S0b'], chain['pins'], chain['decl'], chain['root'], records)


def test_pin_record_hashes_every_output_and_carries_the_chain(chain, tmp_path):
    out = tmp_path/'s0b-out'; (out/'nested').mkdir(parents=True)
    (out/'result.json').write_text('{}'); (out/'nested/x.bin').write_bytes(b'\0\1')
    record = driver.make_pin_record(chain['specs']['S0b'], 'S0b', chain['root'], out, chain['record'], protocol_sha256=PROTOCOL_SHA)
    assert record['outputs'] == {'nested/x.bin': {'sha256': sha(b'\0\1'), 'bytes': 2}, 'result.json': {'sha256': sha(b'{}'), 'bytes': 2}}
    assert list(record['chain']) == ['S0a', 'S0b']
    assert record['previous_record_sha256'] == sha(driver.canonical(chain['record']))
    path = tmp_path/'r.json'; driver.write_pin_record(path, record)
    with pytest.raises(FileExistsError):
        driver.write_pin_record(path, record)


# ------------------------------------------------------------------- CLI, plan-only and GO

def run_main(c, *extra, go=None):
    argv = ['--stage', 'S0b', '--worktree', str(c['root']), '--previous-pins', str(c['record_path']), *extra]
    if go is not None: argv += ['--go', str(go), '--pin-record-out', str(c['tmp']/'s0b-record.json')]
    argv += ['--', '--input', str(c['input']), '--output', str(c['tmp']/'s0b-out')]
    return driver.main(argv, stages=c['specs'], pins_dir=c['pins'], root=c['root'], protocol_sha256=PROTOCOL_SHA)


def write_go(c, **fields):
    path = c['tmp']/'go.json'
    path.write_text(json.dumps({'decision': 'GO', 'stage': 'S0b', 'protocol_sha256': PROTOCOL_SHA, **fields}))
    return path


def test_default_is_refusal_and_never_executes(chain, capsys, isolated_imports):
    assert run_main(chain) == 2
    assert 'refused' in capsys.readouterr().out
    assert not (chain['tmp']/'s0b-out').exists() and 'fake_producer' not in sys.modules


def test_plan_only_prints_plan_and_never_executes(chain, capsys, isolated_imports):
    assert run_main(chain, '--plan-only') == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['mode'] == 'plan-only' and plan['status'] == 'admissible'
    assert [r['attribute'] for r in plan['rebinds']] == ['PROTOCOL_PATH', 'PROTOCOL_SHA256', 'DATA_SHA256']
    assert plan['would_run'][-4:] == ['--input', str(chain['input']), '--output', str(chain['tmp']/'s0b-out')]
    assert not (chain['tmp']/'s0b-out').exists() and 'fake_producer' not in sys.modules


def test_plan_only_reports_pending_documents_as_refusal(chain, capsys, isolated_imports):
    template = json.loads((chain['root']/'docs/plans/fake-protocol.json').read_text()); template['baseline_sha256'] = 'PENDING-S0a'
    (chain['pins']/'fake-protocol.json').write_text(json.dumps(template, indent=2) + '\n')
    assert run_main(chain, '--plan-only') == 3
    plan = json.loads(capsys.readouterr().out)
    assert plan['status'] == 'refused' and 'PENDING' in plan['reason']


def test_plan_only_and_go_are_mutually_exclusive(chain, isolated_imports):
    assert run_main(chain, '--plan-only', go=write_go(chain)) == 2
    assert not (chain['tmp']/'s0b-out').exists()


@pytest.mark.parametrize('fields,raw', [
    ({'stage': 'S0c'}, None), ({'protocol_sha256': '0'*64}, None), ({'decision': 'HOLD'}, None),
    ({}, 'not json'), ({'stage': None}, None),
])
def test_go_record_must_name_exact_stage_and_protocol(chain, fields, raw, isolated_imports):
    go = write_go(chain, **fields)
    if raw is not None: go.write_text(raw)
    assert run_main(chain, go=go) == 2
    assert not (chain['tmp']/'s0b-out').exists() and 'fake_producer' not in sys.modules


def test_missing_go_file_is_refused(chain, isolated_imports):
    assert run_main(chain, go=chain['tmp']/'absent.json') == 2


def test_go_executes_overlaid_producer_and_publishes_pin_record(chain, capsys, isolated_imports):
    assert run_main(chain, go=write_go(chain)) == 0
    result = json.loads((chain['tmp']/'s0b-out/result.json').read_text())
    assert result == {'baseline': chain['record']['outputs']['data.json']['sha256'],
                      'data': chain['record']['outputs']['data.json']['sha256']}
    record = json.loads((chain['tmp']/'s0b-record.json').read_text())
    assert record['stage'] == 'S0b' and list(record['chain']) == ['S0a', 'S0b']
    assert record['outputs']['result.json']['sha256'] == sha((chain['tmp']/'s0b-out/result.json').read_bytes())
    assert record['overlay']['changed'] == ['fake_reader.PROTOCOL_PATH', 'fake_reader.PROTOCOL_SHA256', 'fake_producer.DATA_SHA256']


def test_first_stage_runs_unchanged_producer_as_subprocess(chain, tmp_path, isolated_imports):
    go = tmp_path/'go-s0a.json'; go.write_text(json.dumps({'decision': 'GO', 'stage': 'S0a', 'protocol_sha256': PROTOCOL_SHA}))
    argv = ['--stage', 'S0a', '--worktree', str(chain['root']), '--go', str(go), '--pin-record-out', str(tmp_path/'a.json'),
            '--', '--output', str(tmp_path/'a-out')]
    assert driver.main(argv, stages=chain['specs'], pins_dir=chain['pins'], root=chain['root'], protocol_sha256=PROTOCOL_SHA) == 0
    assert json.loads((tmp_path/'a.json').read_text())['outputs'] == {'data.json': {'sha256': sha(b'{}'), 'bytes': 2}}


def test_later_stage_without_previous_record_is_refused(chain, isolated_imports):
    argv = ['--stage', 'S0b', '--worktree', str(chain['root']), '--plan-only', '--', '--input', str(chain['input'])]
    assert driver.main(argv, stages=chain['specs'], pins_dir=chain['pins'], root=chain['root'], protocol_sha256=PROTOCOL_SHA) == 2


def test_real_cli_refuses_worktree_not_at_producing_commit(chain, capsys):
    argv = ['--stage', 'S0a', '--worktree', str(chain['root']), '--plan-only', '--', '--output', str(chain['tmp']/'x')]
    assert driver.main(argv) == 3
    assert 'producing commit' in json.loads(capsys.readouterr().out)['reason']
    assert driver.PROTOCOL_SHA256 == PROTOCOL_SHA
    assert sha((ROOT/driver.PROTOCOL_PATH).read_bytes()) == PROTOCOL_SHA


# ------------------------------------------------------------------- S0a execution manifest (no producer runs)

def test_s0a_manifest_launch_matches_the_saved_plan_the_driver_rules_and_the_protocol_budget():
    import re
    folder = ROOT/'docs/reports/male-v4-s0a'
    text, plan_raw = (folder/'MANIFEST.md').read_text(), (folder/'plan-only.json').read_bytes()
    plan = json.loads(plan_raw)
    assert plan['status'] == 'admissible' and plan['mode'] == 'plan-only' and plan['stage'] == 'S0a'
    assert plan['protocol_sha256'] == PROTOCOL_SHA and sha(plan_raw) in text
    spec = driver.STAGES['S0a']
    assert plan['producing_commit'] == spec['commit'] and plan['worktree_check']['producer_sha256'] == spec['producer_sha256']
    assert plan['worktree_check']['source_guards'] == spec['source_guards'] and plan['worktree_check']['detached'] is True
    block = re.search(r'<!-- s0a-command -->\n```sh\n(.*?)\n```', text, re.S).group(1)
    argv = block.replace('\\\n', ' ').split()
    cut = argv.index('--')
    unit, command = argv[:cut], argv[cut + 1:]
    flag = lambda name, words: words[words.index(name) + 1]
    row = next(r for r in json.loads((ROOT/driver.PROTOCOL_PATH).read_text())['amendment_1']['lane_budget']['stage_costs_seconds']
               if r['stage'] == 'S0a')
    assert unit[1].endswith('scripts/run_research_stage.py')
    assert (flag('--lane', unit), flag('--stage', unit), int(flag('--cpu-quota-k', unit)), int(flag('--runtime-max-sec', unit)),
            int(flag('--worst-case-cpu', unit))) == ('navigation', 'S0a', row['cpu_quota_k'], row['runtime_max_sec_kill_target'],
                                                      row['worst_case_cpu'])
    inner = command.index('--')
    driver_args, producer_args = command[:inner], command[inner + 1:]
    assert driver_args[2].endswith('scripts/regenerate_male_navigation_v4.py') and '--plan-only' not in driver_args
    assert flag('--stage', driver_args) == 'S0a' and flag('--worktree', driver_args) == plan['worktree']
    assert '--previous-pins' not in driver_args                                      # first sub-stage
    assert producer_args == plan['would_run'][2:]                                    # exactly the planned producer argv
    assert flag('--research-stage', producer_args) == 'development'
    output, record = Path(flag('--output', producer_args)), Path(flag('--pin-record-out', driver_args))
    data_root = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a')
    assert output.parent == data_root and record.parent == data_root and record not in output.parents
    receipt, go_record = Path(flag('--receipt-dir', unit)), Path(flag('--go-record', unit))
    assert flag('--go', driver_args) == str(go_record) and data_root not in receipt.parents
    for path in (receipt, go_record, output, record):
        assert not driver.under(path, plan['worktree']) and not driver.under(path, flag('--assets', producer_args))
    assert 'scientific_attempt": true' in text and 'ends v4' in text.lower()


def test_s0b_manifest_launch_matches_the_saved_plan_the_s0a_record_the_launcher_rule_and_the_protocol_budget():
    import re
    import run_research_stage as launcher
    folder = ROOT/'docs/reports/male-v4-s0b'
    text, plan_raw = (folder/'MANIFEST.md').read_text(), (folder/'plan-only.json').read_bytes()
    plan = json.loads(plan_raw)
    assert plan['status'] == 'admissible' and plan['mode'] == 'plan-only' and plan['stage'] == 'S0b'
    assert plan['protocol_sha256'] == PROTOCOL_SHA and sha(plan_raw) in text
    spec = driver.STAGES['S0b']
    assert plan['producing_commit'] == spec['commit'] and plan['worktree_check']['producer_sha256'] == spec['producer_sha256']
    assert plan['worktree_check']['detached'] is True and plan['worktree_check']['source_guards'] == {}
    s0a_record = (ROOT/'docs/reports/male-v4-s0a/pin-record.json').read_bytes()
    assert plan['previous_record_sha256'] == sha(s0a_record) == 'd8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901'
    assert json.loads(s0a_record)['stage'] == 'S0a' and sha(s0a_record) in text
    block = re.search(r'<!-- s0b-command -->\n```sh\n(.*?)\n```', text, re.S).group(1)
    argv = block.replace('\\\n', ' ').split()
    cut = argv.index('--')
    unit, command = argv[:cut], argv[cut + 1:]
    flag = lambda name, words: words[words.index(name) + 1]
    row = next(r for r in json.loads((ROOT/driver.PROTOCOL_PATH).read_text())['amendment_1']['lane_budget']['stage_costs_seconds']
               if r['stage'] == 'S0b')
    k, kill, worst = int(flag('--cpu-quota-k', unit)), int(flag('--runtime-max-sec', unit)), int(flag('--worst-case-cpu', unit))
    assert unit[1].endswith('scripts/run_research_stage.py') and (flag('--lane', unit), flag('--stage', unit)) == ('navigation', 'S0b')
    assert (k, kill, worst) == (row['cpu_quota_k'], row['runtime_max_sec_kill_target'], row['worst_case_cpu']) == (2, 480, 970)
    assert worst >= k * (kill + launcher.STOP_TIMEOUT) == row['worst_case_cpu']   # the launcher's admission rule agrees
    inner = command.index('--')
    driver_args, producer_args = command[:inner], command[inner + 1:]
    assert driver_args[2].endswith('scripts/regenerate_male_navigation_v4.py') and '--plan-only' not in driver_args
    assert flag('--stage', driver_args) == 'S0b' and flag('--worktree', driver_args) == plan['worktree']
    assert flag('--previous-pins', driver_args) == '/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json'
    assert producer_args == plan['would_run'][2:]                                    # exactly the planned producer argv
    assert driver.probe.ENTRYPOINTS['S0b']['thread_env'] == {'OMP_NUM_THREADS': '2'}   # the driver's producer env (k=2)
    output, record = Path(flag('--output', producer_args)), Path(flag('--pin-record-out', driver_args))
    data_root = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b')
    assert output.parent == data_root and record.parent == data_root and record not in output.parents
    receipt, go_record = Path(flag('--receipt-dir', unit)), Path(flag('--go-record', unit))
    assert flag('--go', driver_args) == str(go_record) and data_root not in receipt.parents
    for path in (receipt, go_record, output, record):
        assert not driver.under(path, plan['worktree']) and not driver.under(path, flag('--assets', producer_args))
    assert 'scientific_attempt": true' in text and 'ends v4' in text.lower() and '"cpu_quota_k": 2' in text
    for phrase in ('writer.lock', 'previous_pin_record_sha256', 'Throttling risk', 'mesa 1:26.2.5-1', 'Post-run gate',
                   '1..120', 'recovery-north-2100', 'recovery-south-2101'):
        assert phrase in text, phrase
