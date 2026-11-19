"""v4 navigation research binding (Amendment 2): the six terminal S1 checkpoints, fresh roots only.

``Binding(training_seed, arm)`` is the only constructor surface: no manifest, index or output
directory argument exists, so nothing can redirect it. Every identity it trusts is a hard-coded
constant taken from the published S1 evidence (``docs/reports/male-v4-s1/RESULT.md`` and
``checkpoints.sha256``): the S1 output root, the sha256 of ``report.json``, ``publication.json`` and
S1's ``protocol.json``, the six checkpoint payload hashes, the pinned runtime and graph inputs.

Admission mirrors ``train_male_navigation_v4.success_admitted`` (that script is not importable from
``src``): no failure file, a completed six-model report, the exact durable-publication receipt with
``protocol_sha256`` equal to the base protocol sha (``cd4eb130…``), and every checkpoint unchanged.
It then pins the checkpoint lineage: S1's ``run_protocol`` digest (the value every checkpoint carries
as ``protocol_sha256``) must equal ``report.run_protocol_sha256``, and the graph digest and ordered
ids come from the pinned graph. Nothing is deserialized until all six payloads are admitted; the
five-key checkpoint format and lineage are then enforced by the shared
``male_policy._load_checked_policy`` (no new tensor-admission code).
"""
from dataclasses import dataclass
import importlib.metadata
import json
import os
from pathlib import Path
import platform

from . import artifacts, male_model, male_policy

BASE_PROTOCOL_SHA256 = 'cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477'
S1_OUTPUT = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S1/train')
REPORT_SHA256 = '6ca8af5f9969fd1227d6e9494e9efc334e425c03145998da7a3de3a9d06c3cd2'
PUBLICATION_SHA256 = 'fb6f1f38b492979a29e7bb70c091626bb2037354ea26f7e52140751b36c30f90'
S1_PROTOCOL_JSON_SHA256 = '3769df742b694d16f7d41903214bf52423c19131075a041515b5ff2cb0faf8a4'
CHECKPOINT_SHA256 = {
    (10, 'augmented'): '7642ae2dbda19ff749a6da5b3263b8d7bce43b6bec8b1717ebe8fbd53089ea65',
    (10, 'old-corpus'): '7598c31e6c59303b34391b50d6e9ef182d3b0aa99bd21c688b39ca3c81889a3e',
    (11, 'augmented'): '0c5afe9140430b2a468928fedfb072cb281f2f5b32d477f7b7c98ead467fc794',
    (11, 'old-corpus'): 'e0e8b4e96ecb97d4b69f7b1e753038d0f4262a2e93df9281b1e21eb438d68212',
    (12, 'augmented'): '780d04e1dbb6e161660054243dcc3f506718d0065fa6f94fc7dc012ac002274c',
    (12, 'old-corpus'): 'b3d58553d5c62818589be70e4f7c0706ab68bb38425448efcf44f547206fe2a8',
}
RUNTIME = {'python': '3.11.15', 'numpy': '2.2.5', 'torch_distribution': '2.9.0', 'torch_build': '2.9.0+cu128'}
# Pinned model inputs of S1's run protocol (graph, extraction manifest, cell), by repo-relative role.
MODEL_INPUTS = {'graph': ('data/assets/flynn/male-reduced-v1/source-graph.json',
                          '5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0'),
                'manifest': ('data/manifests/malecns-reduced-neighborhood-v1.json',
                             '7a205342b4ada8ab8b78d6ca866c61735003e601531c65a1c1b6c819df00026f'),
                'cell': ('upstream/fly-gym/models/connectome_rnn_model.py',
                         '707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80')}
PAIR_SEEDS = (10, 11, 12)
ARMS = ('old-corpus', 'augmented')
TRAIN_ROWS = {'old-corpus': 2117, 'augmented': 7197}
REPORT_ID = 'male-navigation-v4-s1-report-v1'
PUBLICATION_ID = 'male-navigation-v4-s1-publication-v1'
MAX_JSON = 4 * 1024**2


def _choice(training_seed, arm, controller='male-original'):
    if (type(training_seed) is not int or training_seed not in PAIR_SEEDS or arm not in ARMS or
            controller != 'male-original'):
        raise ValueError('Fixed v4 navigation seed/arm and male-original required')


def _read(name, pin):
    raw = artifacts._read(Path(S1_OUTPUT) / name, MAX_JSON)
    if male_policy._sha(raw) != pin:
        raise ValueError(f'Frozen S1 artifact differs from its hard-coded sha256: {name}')
    return raw


def _completed(report):
    models = report.get('models')
    return (report.get('id') == REPORT_ID and report.get('status') == 'completed-navigation-v4-training' and
            report.get('training_completed') is True and report.get('protocol_sha256') == BASE_PROTOCOL_SHA256 and
            report.get('held_out_status') == 'locked_unopened' and report.get('held_out_used_for_selection') is False and
            report.get('qualification_claims') == [] and isinstance(models, list) and
            [(m.get('seed'), m.get('arm'), m.get('status')) for m in models] ==
            [(seed, arm, 'completed') for seed in PAIR_SEEDS for arm in ARMS] and
            all(m.get('selected_optimizer_update') == 1440 and m.get('optimizer_updates') == 1440 and
                m.get('real_row_presentations') == 46080 and
                m.get('selection') == 'terminal-only-before-recorded-development' for m in models))


def _admit_s1():
    """Re-verify the S1 publication as success_admitted does, against hard-coded shas; no deserialization."""
    output = Path(S1_OUTPUT)
    if (output / 'failure.json').exists() or (output / 'report.pending').exists():
        raise ValueError('S1 output holds a failure or pending report')
    payload = _read('report.json', REPORT_SHA256)
    receipt_raw = _read('publication.json', PUBLICATION_SHA256)
    protocol_raw = _read('protocol.json', S1_PROTOCOL_JSON_SHA256)
    report, receipt = json.loads(payload), json.loads(receipt_raw)
    if not _completed(report) or receipt != {
            'id': PUBLICATION_ID, 'status': 'durably-published', 'protocol_sha256': BASE_PROTOCOL_SHA256,
            'report_sha256': male_policy._sha(payload), 'report_size_bytes': len(payload), 'qualification_claims': []}:
        raise ValueError('S1 report/publication receipt does not admit six terminal checkpoints')
    run_protocol = json.loads(protocol_raw)
    if (report.get('run_protocol_sha256') != male_model.digest(run_protocol) or
            run_protocol.get('protocol_sha256') != BASE_PROTOCOL_SHA256 or run_protocol.get('held_out_status') != 'locked_unopened'):
        raise ValueError('S1 run protocol digest differs from the report')
    payloads = {}
    for model in report['models']:
        key, item = (model['seed'], model['arm']), model.get('checkpoint', {})
        raw = artifacts._read(output / f'seed-{key[0]}-{key[1]}.pt', male_policy.MAX_FILE_BYTES)
        if (item.get('path') != f'seed-{key[0]}-{key[1]}.pt' or item.get('sha256') != CHECKPOINT_SHA256[key] or
                item.get('size_bytes') != len(raw) or male_policy._sha(raw) != CHECKPOINT_SHA256[key]):
            raise ValueError(f'Checkpoint differs from its hard-coded sha256: {key}')
        male_policy._check_archive(raw)
        payloads[key] = raw
    if not (output / 'report.json').is_file():
        raise ValueError('S1 report missing')
    return report, run_protocol, payloads


def runtime_identity():
    return {'python': platform.python_version(), 'numpy': importlib.metadata.version('numpy'),
            'torch_distribution': importlib.metadata.version('torch')}


def _graph(root, assets):
    paths = {'graph': Path(assets) / 'male-reduced-v1/source-graph.json',
             'manifest': Path(root) / MODEL_INPUTS['manifest'][0], 'cell': Path(root) / MODEL_INPUTS['cell'][0]}
    for name, path in paths.items():
        if male_policy._sha(artifacts._read(path, MAX_JSON)) != MODEL_INPUTS[name][1]:
            raise ValueError(f'Pinned S1 model input differs: {name}')
    return male_model.load_graph(paths['graph'], paths['manifest']), paths['cell']


def _admit(root, assets, training_seed, arm):
    _choice(training_seed, arm)
    report, run_protocol, payloads = _admit_s1()
    graph, cell = _graph(root, assets)
    provenance = {'profile': male_policy.PROFILE, 'variant': 'original', 'training_seed': training_seed, 'arm': arm,
        'training_report_sha256': REPORT_SHA256, 'protocol_sha256': report['run_protocol_sha256'],
        'checkpoint_sha256': CHECKPOINT_SHA256[training_seed, arm], 'graph_sha256': male_model.digest(graph),
        **{key: graph[key] for key in ('topology_sha256', 'ordered_ids_sha256', 'source_graph_sha256', 'graph_manifest_sha256', 'type_missing_ids')},
        'cell_source_sha256': male_model.CELL_SHA256, 'feature_protocol': male_model.FEATURE_PROTOCOL,
        'feature_protocol_sha256': male_model.digest(male_model.FEATURE_PROTOCOL),
        'data_manifest_sha256': report['data_manifest_sha256'], 'corpus_pin_sha256': report['corpus_pin_sha256'],
        'training_runtime': dict(RUNTIME), 'base_protocol_sha256': BASE_PROTOCOL_SHA256, 'train_rows': TRAIN_ROWS[arm],
        'qualification_claims': [], 'biological_sensor_mapping': False,
        'evaluation_limit': 'fixed v4 same-graph navigation research candidate; no task or production qualification'}
    return graph, payloads[training_seed, arm], provenance, cell


def _identity(provenance):
    # No separate index file exists: the S1 report sha stands for the model manifest and the training report.
    return male_policy.validate_identity({'controller': 'male-original', 'variant': 'original', 'profile': male_policy.PROFILE,
        'model_manifest_sha256': REPORT_SHA256, **{key: provenance[key] for key in male_policy.IDENTITY_HASHES
                                                   if key != 'model_manifest_sha256'}}, 'male-original')


def _runtime_ok():
    return runtime_identity() == {key: RUNTIME[key] for key in ('python', 'numpy', 'torch_distribution')}


def resolve(root, assets, training_seed, arm, controller, expected_identity=None):
    _choice(training_seed, arm, controller)
    if not _runtime_ok():
        raise ValueError('Pinned v4 navigation CPU runtime differs')
    _, _, provenance, _ = _admit(root, assets, training_seed, arm)
    identity = _identity(provenance)
    if expected_identity is not None and male_policy.validate_identity(expected_identity, controller) != identity:
        raise ValueError('Expected v4 navigation candidate differs')
    return identity, {'repo_root': Path(root), 'asset_root': Path(assets), 'training_seed': training_seed, 'arm': arm,
                      'expected_identity': identity}


def load_policy(*, repo_root, asset_root, training_seed, arm, expected_identity, seed=0):
    if type(seed) is not int or not 0 <= seed < 2**31 or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Bounded scene seed and hidden CUDA required')
    _choice(training_seed, arm)
    if not _runtime_ok():
        raise ValueError('Pinned v4 navigation CPU runtime differs')
    graph, payload, provenance, cell = _admit(repo_root, asset_root, training_seed, arm)
    if male_policy.validate_identity(expected_identity, 'male-original') != _identity(provenance):
        raise ValueError('Expected v4 navigation candidate differs')
    import torch  # Only explicit policy construction, after every artifact admission.
    if torch.__version__ != RUNTIME['torch_build'] or torch.cuda.is_initialized():
        raise ValueError('Pinned v4 navigation Torch build/uninitialized CUDA required')
    return male_policy._load_checked_policy(graph, payload, provenance, cell, device='cpu', seed=seed)


@dataclass(frozen=True)
class Binding:
    """Exactly ``(training_seed, arm)``; every other identity is a module constant."""
    training_seed: int
    arm: str

    def resolve(self, root, assets, controller, device, scenario, texture, expected):
        if (device, scenario, texture) != ('cpu', 'reproduction', 'checker') or expected is None:
            raise ValueError('v4 navigation requires pinned CPU/reproduction/checker identity')
        return resolve(root, assets, self.training_seed, self.arm, controller, expected)

    def load_policy(self, arguments, seed):
        return load_policy(**arguments, seed=seed)

    def provenance(self):
        _choice(self.training_seed, self.arm)
        return {'research_protocol_sha256': BASE_PROTOCOL_SHA256, 'research_manifest_sha256': REPORT_SHA256,
                'publication_sha256': PUBLICATION_SHA256, 'training_seed': self.training_seed, 'arm': self.arm,
                'checkpoint_sha256': CHECKPOINT_SHA256[self.training_seed, self.arm],
                'scope': 'same-original-graph v4 navigation research development; fresh roots only; held-out locked'}
