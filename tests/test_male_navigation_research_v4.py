"""NavigationBindingV4 (Amendment 2): synthetic S1 fixtures only; real S1 evidence is used for hash-constant checks."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from palimpsest import male_model, male_navigation_research_v4 as v4, male_policy  # noqa: E402

EVIDENCE = ROOT/'docs/reports/male-v4-s1'
BASE = v4.BASE_PROTOCOL_SHA256


def sha(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value): return male_model.canonical(value)


def tiny_checkpoint(tag):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED) as archive:
        archive.writestr('archive/data.pkl', tag.encode())
    return stream.getvalue()


@pytest.fixture
def s1(tmp_path, monkeypatch):
    """A synthetic six-checkpoint S1 output whose hashes are patched into the module constants."""
    out = tmp_path/'train'; out.mkdir()
    run_protocol = {'id': 'x', 'protocol_sha256': BASE, 'held_out_status': 'locked_unopened', 'qualification_claims': []}
    protocol_raw = canonical(run_protocol)
    checkpoints, models = {}, []
    for seed in v4.PAIR_SEEDS:
        for arm in v4.ARMS:
            payload = tiny_checkpoint(f'{seed}-{arm}')
            name = f'seed-{seed}-{arm}.pt'; (out/name).write_bytes(payload)
            checkpoints[seed, arm] = sha(payload)
            models.append({'seed': seed, 'arm': arm, 'status': 'completed', 'optimizer_updates': 1440, 'real_row_presentations': 46080,
                           'selected_optimizer_update': 1440, 'selection': 'terminal-only-before-recorded-development',
                           'checkpoint': {'path': name, 'sha256': sha(payload), 'size_bytes': len(payload)}})
    report = {'id': v4.REPORT_ID, 'status': 'completed-navigation-v4-training', 'training_completed': True, 'protocol_sha256': BASE,
              'held_out_status': 'locked_unopened', 'held_out_used_for_selection': False, 'qualification_claims': [],
              'models': models, 'run_protocol_sha256': male_model.digest(run_protocol), 'data_manifest_sha256': 'd' * 64,
              'corpus_pin_sha256': 'e' * 64}
    report_raw = canonical(report)
    receipt = {'id': v4.PUBLICATION_ID, 'status': 'durably-published', 'protocol_sha256': BASE, 'report_sha256': sha(report_raw),
               'report_size_bytes': len(report_raw), 'qualification_claims': []}
    (out/'report.json').write_bytes(report_raw); (out/'publication.json').write_bytes(canonical(receipt))
    (out/'protocol.json').write_bytes(protocol_raw)
    monkeypatch.setattr(v4, 'S1_OUTPUT', out)
    monkeypatch.setattr(v4, 'REPORT_SHA256', sha(report_raw))
    monkeypatch.setattr(v4, 'PUBLICATION_SHA256', sha((out/'publication.json').read_bytes()))
    monkeypatch.setattr(v4, 'S1_PROTOCOL_JSON_SHA256', sha(protocol_raw))
    monkeypatch.setattr(v4, 'CHECKPOINT_SHA256', checkpoints)
    graph = {'topology_sha256': 'a1' * 32, 'ordered_ids_sha256': 'b2' * 32, 'source_graph_sha256': 'c3' * 32,
             'graph_manifest_sha256': 'd4' * 32, 'type_missing_ids': []}
    monkeypatch.setattr(v4, '_graph', lambda root, assets: (graph, Path('/cell')))
    monkeypatch.setattr(v4, '_runtime_ok', lambda: True)
    return {'out': out, 'report': report, 'graph': graph, 'run_protocol': run_protocol}


def rewrite(s1, monkeypatch, name, value):
    path = s1['out']/name
    raw = value if isinstance(value, bytes) else canonical(value)
    path.write_bytes(raw)
    monkeypatch.setattr(v4, {'report.json': 'REPORT_SHA256', 'publication.json': 'PUBLICATION_SHA256',
                             'protocol.json': 'S1_PROTOCOL_JSON_SHA256'}[name], sha(raw))


def test_binding_takes_only_seed_and_arm_and_nothing_can_redirect_it():
    import inspect
    assert [p for p in inspect.signature(v4.Binding).parameters] == ['training_seed', 'arm']
    with pytest.raises(TypeError):
        v4.Binding(10, 'augmented', manifest_path='/x')
    with pytest.raises(TypeError):
        v4.Binding(10, 'augmented', '/x')
    assert not any(token in inspect.getsource(v4.Binding) for token in ('manifest_path', 'index_path', 'output_dir'))


def test_a_good_s1_output_resolves_to_a_valid_identity_and_provenance(s1):
    binding = v4.Binding(11, 'augmented')
    identity, arguments = binding.resolve(Path('/repo'), Path('/assets'), 'male-original', 'cpu', 'reproduction', 'checker', {'x': 1}) \
        if False else (None, None)
    identity, arguments = v4.resolve(Path('/repo'), Path('/assets'), 11, 'augmented', 'male-original')
    assert set(identity) == {'controller', 'variant', 'profile', *male_policy.IDENTITY_HASHES}
    assert identity['checkpoint_sha256'] == v4.CHECKPOINT_SHA256[11, 'augmented'] and identity['protocol_sha256'] == s1['report']['run_protocol_sha256']
    assert identity['model_manifest_sha256'] == identity['training_report_sha256'] == v4.REPORT_SHA256
    assert identity['topology_sha256'] == 'a1' * 32 and identity['feature_protocol_sha256'] == male_model.digest(male_model.FEATURE_PROTOCOL)
    provenance = binding.provenance()
    assert provenance['research_protocol_sha256'] == BASE and provenance['arm'] == 'augmented' and provenance['training_seed'] == 11
    again, _ = v4.resolve(Path('/repo'), Path('/assets'), 11, 'augmented', 'male-original', expected_identity=identity)
    assert again == identity
    with pytest.raises(ValueError, match='Expected'):
        v4.resolve(Path('/repo'), Path('/assets'), 11, 'augmented', 'male-original', expected_identity={**identity, 'checkpoint_sha256': '0' * 64})


def test_resolve_through_the_binding_requires_cpu_reproduction_checker_and_an_expected_identity(s1):
    binding = v4.Binding(10, 'old-corpus')
    identity, _ = v4.resolve(Path('/r'), Path('/a'), 10, 'old-corpus', 'male-original')
    got, args = binding.resolve(Path('/r'), Path('/a'), 'male-original', 'cpu', 'reproduction', 'checker', identity)
    assert got == identity and set(args) == {'repo_root', 'asset_root', 'training_seed', 'arm', 'expected_identity'}
    for changed in (('cuda', 'reproduction', 'checker', identity), ('cpu', 'other', 'checker', identity),
                    ('cpu', 'reproduction', 'noise', identity), ('cpu', 'reproduction', 'checker', None)):
        with pytest.raises(ValueError, match='requires pinned'):
            binding.resolve(Path('/r'), Path('/a'), 'male-original', *changed)


@pytest.mark.parametrize('seed, arm, controller', [(13, 'augmented', 'male-original'), (10, 'rewired', 'male-original'),
                                                   (True, 'augmented', 'male-original'), (10, 'augmented', 'male-control')])
def test_wrong_seed_arm_or_controller_is_refused(s1, seed, arm, controller):
    with pytest.raises(ValueError, match='Fixed v4'):
        v4.resolve(Path('/r'), Path('/a'), seed, arm, controller)
    if controller == 'male-original':
        with pytest.raises(ValueError):
            v4.Binding(seed, arm).provenance()


def test_tampered_checkpoint_report_publication_or_protocol_bytes_are_refused(s1, monkeypatch):
    victim = s1['out']/'seed-12-augmented.pt'
    original = victim.read_bytes()
    victim.write_bytes(tiny_checkpoint('other'))
    with pytest.raises(ValueError, match='hard-coded sha256'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')        # any seed: all six are admitted first
    victim.write_bytes(original)
    for name in ('report.json', 'publication.json', 'protocol.json'):
        path = s1['out']/name; raw = path.read_bytes()
        path.write_bytes(raw + b' ')
        with pytest.raises(ValueError, match='hard-coded sha256'):
            v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')
        path.write_bytes(raw)


def test_a_receipt_or_report_naming_another_protocol_is_refused_even_with_matching_hard_coded_shas(s1, monkeypatch):
    receipt = json.loads((s1['out']/'publication.json').read_bytes())
    rewrite(s1, monkeypatch, 'publication.json', {**receipt, 'protocol_sha256': 'f' * 64})
    with pytest.raises(ValueError, match='receipt'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')
    rewrite(s1, monkeypatch, 'publication.json', receipt)
    report = copy.deepcopy(s1['report']); report['protocol_sha256'] = '0' * 64
    rewrite(s1, monkeypatch, 'report.json', report)
    with pytest.raises(ValueError, match='receipt'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')


@pytest.mark.parametrize('mutate', [
    lambda r: r['models'].reverse(), lambda r: r['models'][0].update(status='failed'), lambda r: r.update(training_completed=False),
    lambda r: r['models'][1].update(optimizer_updates=1439), lambda r: r.update(held_out_status='open'),
    lambda r: r['models'][2].update(selection='best-dev-loss')])
def test_an_incomplete_or_reordered_six_model_report_is_not_admitted(s1, monkeypatch, mutate):
    report = copy.deepcopy(s1['report']); mutate(report)
    raw = canonical(report)
    rewrite(s1, monkeypatch, 'report.json', raw)
    receipt = {'id': v4.PUBLICATION_ID, 'status': 'durably-published', 'protocol_sha256': BASE, 'report_sha256': sha(raw),
               'report_size_bytes': len(raw), 'qualification_claims': []}
    rewrite(s1, monkeypatch, 'publication.json', receipt)
    with pytest.raises(ValueError, match='receipt'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')


def test_failure_file_pending_report_and_run_protocol_digest_mismatch_are_refused(s1, monkeypatch):
    (s1['out']/'failure.json').write_text('{}')
    with pytest.raises(ValueError, match='failure'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')
    (s1['out']/'failure.json').unlink()
    rewrite(s1, monkeypatch, 'protocol.json', {**s1['run_protocol'], 'id': 'changed'})
    with pytest.raises(ValueError, match='run protocol'):
        v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')


def test_a_v2_or_v3_index_cannot_reach_the_binding_and_the_v2_module_is_untouched(s1):
    import inspect
    from palimpsest import male_navigation_research as v2
    source = inspect.getsource(v4)
    assert 'f938d979' not in source and '76a502de' not in source and 'male-navigation-research-development-v2' not in source
    assert 'ecfafd2b' not in source and '47c4523c' not in source
    assert v2.PROTOCOL_SHA256 != v4.BASE_PROTOCOL_SHA256 and v2.Binding is not v4.Binding


def test_load_policy_needs_hidden_cuda_the_expected_identity_and_delegates_tensor_admission(s1, monkeypatch):
    identity, arguments = v4.resolve(Path('/r'), Path('/a'), 10, 'augmented', 'male-original')
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '0')
    with pytest.raises(ValueError, match='hidden CUDA'):
        v4.load_policy(**arguments, seed=0)
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '')
    with pytest.raises(ValueError, match='Expected'):
        v4.load_policy(**{**arguments, 'expected_identity': {**identity, 'graph_sha256': '0' * 64}}, seed=0)
    seen = {}
    monkeypatch.setitem(sys.modules, 'torch', type('T', (), {'__version__': v4.RUNTIME['torch_build'],
                                                              'cuda': type('C', (), {'is_initialized': staticmethod(lambda: False)})})())
    monkeypatch.setattr(male_policy, '_load_checked_policy', lambda graph, payload, provenance, cell, **k: seen.update(
        payload=payload, provenance=provenance, cell=cell, k=k) or 'policy')
    assert v4.load_policy(**arguments, seed=7) == 'policy'
    assert seen['payload'] == (s1['out']/'seed-10-augmented.pt').read_bytes() and seen['k'] == {'device': 'cpu', 'seed': 7}
    assert seen['provenance']['protocol_sha256'] == s1['report']['run_protocol_sha256']        # lineage the checkpoint must carry
    assert seen['provenance']['ordered_ids_sha256'] == s1['graph']['ordered_ids_sha256']
    assert seen['provenance']['graph_sha256'] == male_model.digest(s1['graph'])


# ------------------------------------------------------------------- hard-coded constants vs the published evidence

@pytest.mark.skipif(not (EVIDENCE/'report.json').exists(), reason='S1 evidence absent')
def test_hard_coded_constants_equal_the_published_s1_evidence():
    assert sha((EVIDENCE/'report.json').read_bytes()) == v4.REPORT_SHA256
    assert sha((EVIDENCE/'publication.json').read_bytes()) == v4.PUBLICATION_SHA256
    assert sha((EVIDENCE/'protocol.json').read_bytes()) == v4.S1_PROTOCOL_JSON_SHA256
    lines = [line.split() for line in (EVIDENCE/'checkpoints.sha256').read_text().splitlines() if line.strip()]
    assert {name: digest for digest, name in lines} == {f'seed-{s}-{a}.pt': d for (s, a), d in v4.CHECKPOINT_SHA256.items()}
    report = json.loads((EVIDENCE/'report.json').read_text())
    assert report['runtime'] == {'numpy': v4.RUNTIME['numpy'], 'python': v4.RUNTIME['python'],
                                 'torch_build': v4.RUNTIME['torch_build'], 'torch_distribution': v4.RUNTIME['torch_distribution']}
    protocol = json.loads((EVIDENCE/'protocol.json').read_text())
    assert male_model.digest(protocol) == report['run_protocol_sha256']
    assert sorted(protocol['model_inputs'].values()) == sorted(item[1] for item in v4.MODEL_INPUTS.values())
    assert report['protocol_sha256'] == v4.BASE_PROTOCOL_SHA256
    assert 'S1_OUTPUT' and str(v4.S1_OUTPUT).endswith('male-v4-data/S1/train')
