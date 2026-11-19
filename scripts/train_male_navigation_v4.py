"""M7 navigation v4 S1: six-model matched-clock ORIGINAL-topology trainer; plan-only by default.

Re-pinned from ``train_male_navigation_v3.py`` (which stays untouched and pins the lost
``47c4523c...`` corpus). This trainer admits only the S0z-pinned v4 corpus:

* ``--corpus-pin`` names the S0z pin record (the S0f data manifest with sha256 and bytes, plus
  the T-f/T-h reader worktrees, S0f locator and data root). The lost v2/v3 corpus, the v3
  protocol and any corpus not named by a passed S0z record are refused.
* Every per-arm array (N, q/r, allocations, totals, seed starts, schedule SHA-256s) is
  derived by pure source (``palimpsest.male_matched_budget_v4``) from the pinned manifest
  bytes. ``--plan-only`` (the default) prints that derivation and never opens an array,
  imports Torch, or builds a model.
* Arrays follow v3's design, not a pinned bundle: in the GO route, before Torch, a child
  (``derive_male_navigation_v4_s1_data.py``) loads the old arrays from S0f's historical transfer
  and derives the 12 advice arrays from the S0e recordings with the T-f port reader (code hashes
  verified against the manifest's ``current_reader_sources`` before any read). Every source must
  hash to its manifest ``feature_target_sha256``; the transient result is re-validated here.
* Execution needs ``--go``: an owner GO record naming lane ``navigation``, stage ``S1``,
  the v4 protocol sha256, the corpus-pin sha256 and the derivation sha256. It runs only
  inside a ``scripts/run_research_stage.py`` unit, which owns RuntimeMaxSec, CPUQuota and
  the CPU census; this trainer keeps no CPU accounting of its own.
* Seeds 10/11/12 x old-corpus/augmented in that order, 1,440 Adam updates of exactly 32
  real rows (46,080 presentations) each, one zero_grad/backward/clip/step per update.
  Only the terminal update-1,440 state is checkpointed; success is the report plus its
  publication receipt after all six models. The first fault is retained in
  ``failure.json`` and leaves later models ``not_started``. There is no retry.
"""
import argparse
from dataclasses import dataclass
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time

from palimpsest import artifacts, male_matched_budget_v4 as budget, male_model

ROOT = Path(__file__).resolve().parents[1]
SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PROTOCOL_PATH = 'docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json'
PROTOCOL_SHA256 = 'cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477'
V3_PROTOCOL_SHA256 = 'ecfafd2b6bedaf5d073e0bf32571d1978084ec7ddfb0e8c6c98a298d38d70732'
V3_DATA_SHA256 = budget.V3_DATA_SHA256
LANE, STAGE = 'navigation', 'S1'
CORPUS_PIN_SCHEMA = 'm7-navigation-v4-corpus-pin-1'
REPORT_ID = 'male-navigation-v4-s1-report-v1'
PUBLICATION_ID = 'male-navigation-v4-s1-publication-v1'
CHECKPOINT_FORMAT = 'palimpsest-male-reduced-v1'
ARMS, SEEDS = budget.ARMS, budget.SEEDS
FEATURES = 388
MiB, GiB = 1024**2, 1024**3
MAX_JSON = 4 * MiB
MAX_FILE = 8 * MiB
MAX_ARRAYS = 512 * MiB
DATA_SECONDS = 180
OUTPUT_BYTES = 256 * MiB
FREE_FLOOR = GiB
RSS_BYTES = 2 * GiB
SOURCES = (
    PROTOCOL_PATH,
    'scripts/train_male_navigation_v4.py',
    'src/palimpsest/male_matched_budget_v4.py',
    'src/palimpsest/male_matched_budget.py',
    'src/palimpsest/male_model.py',
    'scripts/train_male_reduced.py',
    'scripts/derive_male_navigation_v4_s1_data.py',
)


class Refusal(ValueError):
    """An admission refusal before any training."""


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def planned_models():
    return tuple((seed, arm) for seed in SEEDS for arm in ARMS)


# --------------------------------------------------------------------------- protocol

def protocol(path=None, expected=PROTOCOL_SHA256):
    """The exact v4 protocol bytes; the v3 protocol is refused by name."""
    raw = artifacts._read(ROOT / PROTOCOL_PATH if path is None else path, MAX_JSON)
    digest = sha256_bytes(raw)
    if digest == V3_PROTOCOL_SHA256:
        raise Refusal('The v3 matched-budget protocol is not admissible for v4')
    if digest != expected:
        raise Refusal('v4 protocol bytes differ from the pin')
    value = json.loads(raw)
    if value.get('id') != budget.PROTOCOL_ID or value.get('version') != 1:
        raise Refusal('Protocol is not M7-NAV-V4-REGEN-MATCHED-BUDGET-1 version 1')
    return value


def fixed_training(seed, arm, study):
    if type(seed) is not int or seed not in SEEDS or arm not in ARMS:
        raise Refusal('Fixed seed 10/11/12 and old-corpus/augmented arm required')
    matched, training, runtime = study['matched_budget'], study['training'], study['runtime']
    settings = {
        'training_seed': seed, 'arm': arm, 'graph_variant': training['model']['graph_variant'],
        'schedule_version': budget.SCHEDULE_VERSION,
        'real_row_presentations': matched['real_loss_bearing_row_presentations_per_model'],
        'rows_per_update': matched['real_loss_bearing_rows_per_update'],
        'optimizer_updates': matched['optimizer_updates_per_model'],
        'selected_optimizer_update': matched['optimizer_updates_per_model'],
        'optimizer': training['optimizer'], 'learning_rate': training['learning_rate'],
        'gradient_norm_cap': training['gradient_norm_cap'], 'dtype': runtime['dtype'],
        'device': runtime['device'], 'threads': runtime['threads'], 'qualification_claims': [],
    }
    if ((settings['real_row_presentations'], settings['rows_per_update'],
         settings['optimizer_updates'], settings['graph_variant']) !=
            (budget.DEFAULT_PRESENTATIONS, budget.DEFAULT_ROWS_PER_UPDATE,
             budget.OPTIMIZER_UPDATES, 'original') or
            [(row['seed'], tuple(row['arms'])) for row in training['pair_order']] !=
            [(item, ARMS) for item in SEEDS] or
            (settings['optimizer'], settings['learning_rate'], settings['gradient_norm_cap'],
             settings['dtype'], settings['device'], settings['threads']) !=
            ('Adam', .001, 1., 'float32', 'cpu', 1)):
        raise Refusal('Frozen matched training-and-selection clock differs')
    return settings


# --------------------------------------------------------------------------- corpus pin and GO

def _hex64(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= set('0123456789abcdef')


def _file_pin(value, name):
    if (not isinstance(value, dict) or set(value) != {'path', 'sha256', 'bytes'} or
            not isinstance(value['path'], str) or not _hex64(value['sha256']) or
            type(value['bytes']) is not int or value['bytes'] <= 0):
        raise Refusal(f'Corpus pin {name} needs exact path, sha256 and bytes')
    return value


def _reader_pin(value):
    """The S0f reader context S0z pins: T-f and T-h worktrees at their port heads, locator, data root."""
    if not isinstance(value, dict) or set(value) != {'t_f', 't_h', 'locator', 'data_root'}:
        raise Refusal('Corpus pin reader needs exactly t_f, t_h, locator and data_root')
    for name in ('t_f', 't_h'):
        item = value[name]
        if (not isinstance(item, dict) or set(item) != {'path', 'head'} or not isinstance(item['path'], str) or
                not os.path.isabs(item['path']) or not isinstance(item['head'], str) or
                len(item['head']) != 40 or not set(item['head']) <= set('0123456789abcdef')):
            raise Refusal(f'Corpus pin reader {name} needs an absolute path and a 40-hex head')
    _file_pin(value['locator'], 'reader locator')
    if not isinstance(value['data_root'], str) or not os.path.isabs(value['data_root']):
        raise Refusal('Corpus pin reader data_root must be absolute')
    return value


def read_corpus_pin(path, protocol_sha256=PROTOCOL_SHA256):
    """The S0z pin record; anything unpinned, unpassed or v3-bound is refused."""
    if path is None:
        raise Refusal('Unpinned corpus: an S0z corpus pin record is required')
    raw = artifacts._read(path, MAX_JSON)
    record = json.loads(raw)
    if not isinstance(record, dict) or record.get('schema') != CORPUS_PIN_SCHEMA:
        raise Refusal('Unpinned corpus: S0z corpus pin schema differs')
    if record.get('protocol_sha256') == V3_PROTOCOL_SHA256:
        raise Refusal('Corpus pin binds the v3 protocol')
    if (record.get('protocol_sha256') != protocol_sha256 or record.get('stage') != 'S0z' or
            record.get('status') != 'passed' or record.get('qualification_claims') != []):
        raise Refusal('Unpinned corpus: pin record is not a passed S0z record of this protocol')
    manifest = _file_pin(record.get('data_manifest'), 'data_manifest')
    _reader_pin(record.get('reader'))
    if manifest['sha256'] == V3_DATA_SHA256:
        raise Refusal('Lost v2/v3 corpus 47c4523c... is not a v4 corpus')
    return record, sha256_bytes(raw)


def _pinned_bytes(item, limit):
    raw = artifacts._read(item['path'], limit)
    if len(raw) != item['bytes'] or sha256_bytes(raw) != item['sha256']:
        raise Refusal(f'Pinned input bytes differ: {Path(item["path"]).name}')
    return raw


def derive_schedules(record):
    """Pure post-pin derivation from the pinned manifest bytes; no array or Torch access."""
    item = record['data_manifest']
    if item['sha256'] == V3_DATA_SHA256:
        raise Refusal('Lost v2/v3 corpus 47c4523c... is not a v4 corpus')
    try:
        return budget.derive(_pinned_bytes(item, MAX_JSON), item['sha256'])
    except Refusal:
        raise
    except ValueError as error:
        raise Refusal(f'Corpus manifest refused: {error}') from None


def check_go(path, protocol_sha256, pin_sha256, derivation_sha256):
    """The GO names lane, stage S1, the v4 protocol, the corpus pin and the derivation."""
    try:
        raw = artifacts._read(path, 64 * 1024)
        value = json.loads(raw)
    except (OSError, ValueError) as error:
        raise Refusal(f'Unreadable GO record: {error}') from None
    if not isinstance(value, dict):
        raise Refusal('GO record must be an object')
    if value.get('protocol_sha256') == V3_PROTOCOL_SHA256:
        raise Refusal('GO record names the v3 protocol')
    expected = {'decision': 'GO', 'lane': LANE, 'stage': STAGE, 'protocol_sha256': protocol_sha256,
                'corpus_pin_sha256': pin_sha256, 'schedule_derivation_sha256': derivation_sha256}
    if any(value.get(key) != wanted for key, wanted in expected.items()):
        raise Refusal('GO record does not name lane navigation, stage S1, this protocol, '
                      'corpus pin and schedule derivation')
    for key in ('granted_by', 'granted_at'):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise Refusal(f'GO record lacks {key}')
    return sha256_bytes(raw)


def inside_research_stage(cgroup_file='/proc/self/cgroup', root='/sys/fs/cgroup'):
    """True only inside the `work` leaf that run_research_stage.py's inner registrar made."""
    try:
        line = Path(cgroup_file).read_text(encoding='utf-8').strip().splitlines()[0]
    except (OSError, IndexError):
        return False
    leaf = Path(root + line.split(':', 2)[2])
    return leaf.name == 'work' and (leaf.parent / 'sup').is_dir()


# --------------------------------------------------------------------------- arrays

def load_arrays(path, rosters, numpy=None):
    """Validate the transient array file the data child wrote; trust rests on the per-source
    hash equality to the S0z-pinned manifest, not on a pin of this file."""
    numpy = importlib.import_module('numpy') if numpy is None else numpy
    raw = artifacts._read(path, MAX_ARRAYS)
    with numpy.load(io.BytesIO(raw), allow_pickle=False) as bundle:
        arrays = {key: bundle[key] for key in bundle.files}
    wanted = rosters['augmented'] + rosters['dev']
    keys = {f'{source.feature_target_sha256}/{part}' for source in wanted
            for part in ('features', 'targets')}
    if set(arrays) != keys:
        raise Refusal('Array bundle must hold exactly the training and development sources')

    def episode(source):
        features = arrays[source.feature_target_sha256 + '/features']
        targets = arrays[source.feature_target_sha256 + '/targets']
        if (features.dtype != numpy.float32 or targets.dtype != numpy.float32 or
                features.shape != (source.rows, FEATURES) or targets.shape != (source.rows, 2) or
                not numpy.isfinite(features).all() or not numpy.isfinite(targets).all() or
                sha256_bytes(features.tobytes() + targets.tobytes()) != source.feature_target_sha256):
            raise Refusal('Pinned finite float32 source bytes differ from the manifest')
        return {'run_id': source.run_id, 'episode': source.episode,
                'features': numpy.ascontiguousarray(features),
                'targets': numpy.ascontiguousarray(targets)}

    dev = [episode(source) for source in rosters['dev']]
    return {arm: {'train': [episode(source) for source in rosters[arm]], 'dev': dev, 'held_out': []}
            for arm in ARMS}


# --------------------------------------------------------------------------- training

def run_update_units(model, optimizer, data, schedule, torch_module, loss_function,
                     resource_check):
    """Execute an admitted schedule: one zero_grad/backward/clip/step per 32-row unit."""
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not parameters:
        raise ValueError('Matched trainer requires trainable parameters')
    model.train()
    if hasattr(model, 'cell'):
        model.cell.invalidate_caches()
    total, count = 0., 0
    carried = {}
    for unit in schedule.updates:
        resource_check()
        if unit.rows != schedule.rows_per_update:
            raise ValueError('Optimizer unit does not contain the exact real-row budget')
        optimizer.zero_grad(set_to_none=True)
        summed = None
        for index, fragment in enumerate(unit.fragments):
            episode = data['train'][fragment.source_index]
            if fragment.reset_before:
                hidden = model.reset()
            else:
                previous = carried.get(fragment.source_index)
                if index != 0 or previous is None or previous[0] != fragment.start:
                    raise ValueError('Hidden continuation does not match the admitted fragment')
                hidden = previous[1].detach()
            inputs = torch_module.from_numpy(
                episode['features'][fragment.start:fragment.stop]).unsqueeze(1)
            targets = torch_module.from_numpy(
                episode['targets'][fragment.start:fragment.stop]).unsqueeze(1)
            hidden, actions = model(inputs, hidden)
            values = loss_function(actions, targets)
            if values.numel() != fragment.rows or not torch_module.isfinite(values).all():
                raise ValueError('Nonfinite or wrong-count fragment loss')
            part = values.sum()
            summed = part if summed is None else summed + part
            total += float(values.detach().sum())
            count += values.numel()
            carried[fragment.source_index] = (fragment.stop, hidden)
        loss = summed / schedule.rows_per_update
        if not torch_module.isfinite(loss).all():
            raise ValueError('Nonfinite matched-update loss')
        loss.backward()
        torch_module.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
        optimizer.step()
        if any(not torch_module.isfinite(parameter).all() for parameter in parameters):
            raise ValueError('Nonfinite male parameters after optimizer step')
    resource_check()
    if count != schedule.presentations or len(schedule.updates) * schedule.rows_per_update != count:
        raise ValueError('Executed matched budget differs from admitted schedule')
    if not math.isfinite(total) or total < 0:
        raise ValueError('Accumulated matched training loss is invalid')
    return {'optimizer_updates': len(schedule.updates), 'real_row_presentations': count,
            'train_loss': total / count}


def fit_terminal(hooks, graph, data, schedule, settings, torch_module, dev_rows, resource_check):
    model = hooks.make_model(graph, settings['training_seed'])
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch_module.optim.Adam(parameters, lr=settings['learning_rate'])
    result = run_update_units(model, optimizer, data, schedule, torch_module, hooks.loss_for,
                              resource_check)
    terminal_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
    result.update(selected_optimizer_update=len(schedule.updates),
                  selected_real_row_presentations=schedule.presentations,
                  selection='terminal-only-before-recorded-development',
                  trainable_parameters=sum(parameter.numel() for parameter in parameters),
                  trainable_names=[name for name, parameter in model.named_parameters()
                                   if parameter.requires_grad])
    development = hooks.evaluate(model, data['dev'], math.inf,
                                 {'window': 32, 'training_seed': settings['training_seed']})
    if (type(development.get('ticks')) is not int or development['ticks'] != dev_rows or
            any(type(development.get(key)) not in (int, float) or
                not math.isfinite(development[key]) or development[key] < 0
                for key in ('loss', 'velocity_mae', 'wrapped_heading_mae_radians'))):
        raise ValueError('Terminal recorded-development metrics differ')
    result['recorded_development'] = development
    return terminal_state, result


@dataclass
class Hooks:
    """Injectable heavy boundaries; defaults are the real model, graph and runtime."""
    args: object = None

    def load_torch(self):
        return importlib.import_module('torch')

    def admit_model_inputs(self, study):
        inputs = study['present_inputs']
        paths = {name: Path(os.path.abspath(getattr(self.args, name)))
                 for name in ('graph', 'graph_manifest', 'cell_source')}
        if paths != {name: Path(os.path.abspath(ROOT / inputs[name]['path'])) for name in paths}:
            raise Refusal('Pinned original graph, extraction manifest and cell paths required')
        observed = {name: sha256_bytes(artifacts._read(path, MAX_FILE)) for name, path in paths.items()}
        if observed != {name: inputs[name]['sha256'] for name in paths}:
            raise Refusal('Pinned original graph, extraction manifest or cell bytes differ')
        graph = male_model.load_graph(paths['graph'], paths['graph_manifest'])
        if graph.get('source_graph_sha256') != study['training']['model']['graph_sha256']:
            raise Refusal('Same pinned ORIGINAL graph required')
        return graph, {str(paths[name]): digest for name, digest in observed.items()}

    def derive_data(self, record, derivation, output):
        """v3's data path in a child: old transfer + advice arrays from the S0e recordings, hash-gated."""
        reader = record['reader']
        for name in ('t_f', 't_h'):
            done = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=reader[name]['path'], capture_output=True, text=True, timeout=10)
            if done.returncode != 0 or done.stdout.strip() != reader[name]['head']:
                raise Refusal(f'{name} worktree is not at its pinned port head')
            dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '--', 'src', 'scripts'], cwd=reader[name]['path'],
                                   capture_output=True, text=True, timeout=30)
            if dirty.returncode != 0 or dirty.stdout.strip():
                raise Refusal(f'{name} worktree has modified or untracked src/scripts files')
        _pinned_bytes({**reader['locator']}, MAX_JSON)
        target = Path(output) / 'transient-arrays.npz'
        config = {'port_root': reader['t_f']['path'], 'data_root': reader['data_root'], 'output': str(target),
                  'manifest': {'path': record['data_manifest']['path'], 'sha256': record['data_manifest']['sha256']},
                  'seconds': DATA_SECONDS}
        env = {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/nonexistent'), 'LANG': 'C.UTF-8',
               'PALIMPSEST_M7_V4_PINS': reader['locator']['path'], 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
               'MKL_NUM_THREADS': '1', 'CUDA_VISIBLE_DEVICES': '', 'MUJOCO_GL': 'egl'}
        done = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/derive_male_navigation_v4_s1_data.py'),
                               json.dumps(config)], capture_output=True, text=True, timeout=DATA_SECONDS + 30, env=env,
                              stdin=subprocess.DEVNULL)
        lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
        result = json.loads(lines[-1]) if lines else {}
        if done.returncode != 0 or result.get('status') != 'derived':
            raise Refusal(f'Data derivation refused: {result.get("reason", done.stderr[-300:])}')
        if result['forbidden_modules'] or result['sources'] != 26:
            raise Refusal('Data derivation loaded forbidden modules or the wrong source count')
        return target

    def make_model(self, graph, seed):
        return male_model.make_model(graph, self.args.cell_source, seed)

    def loss_for(self, actions, targets):
        return importlib.import_module('train_male_reduced').loss_for(actions, targets)

    def evaluate(self, model, episodes, deadline, training):
        return importlib.import_module('train_male_reduced').evaluate(model, episodes, deadline, training)

    def inside_stage(self):
        return inside_research_stage()

    def runtime(self, study, torch_module=None):
        expected = study['runtime']
        observed = {'python': platform.python_version(), 'numpy': importlib.metadata.version('numpy'),
                    'torch_distribution': importlib.metadata.version('torch')}
        if observed != {key: expected[key] for key in observed}:
            raise Refusal('Frozen Python/NumPy/Torch distribution runtime differs')
        if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
            raise Refusal('CUDA must be explicitly hidden')
        if torch_module is None:
            if {'torch', 'mujoco'} & set(sys.modules):
                raise Refusal('Torch/MuJoCo must stay unimported before admission')
            return observed
        observed['torch_build'] = torch_module.__version__
        if (observed['torch_build'] != expected['torch_build'] or torch_module.get_num_threads() != 1 or
                torch_module.cuda.is_initialized() or 'mujoco' in sys.modules):
            raise Refusal('Frozen CPU one-thread Torch runtime differs')
        return observed

    def rss_bytes(self):
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def source_identity(root=ROOT):
    return {name: sha256_bytes(artifacts._read(Path(root) / name, MAX_JSON)) for name in SOURCES}


# --------------------------------------------------------------------------- output and publication

def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_exclusive(path, payload, maximum=MAX_FILE):
    if len(payload) > maximum:
        raise ValueError(f'{Path(path).name} exceeds its byte cap')
    with Path(path).open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(Path(path).parent)
    return {'path': Path(path).name, 'sha256': sha256_bytes(payload), 'size_bytes': len(payload)}


def preflight_output(value):
    output = artifacts._safe_path(value)
    if not output.parent.is_dir():
        raise Refusal('Output parent must exist')
    if output.exists() or output.is_symlink():
        raise Refusal('S1 output is already consumed; one attempt, no retry')
    if output == ROOT or (ROOT in output.parents and not output.is_relative_to(ROOT / 'runs')):
        raise Refusal('S1 output inside the repository must be under runs/')
    if shutil.disk_usage(output.parent).free < FREE_FLOOR + OUTPUT_BYTES:
        raise Refusal('Free-space floor plus the S1 output cap is unavailable')
    return output


def initial_report(go_sha256, pin_sha256, derivation):
    return {
        'id': REPORT_ID, 'status': 'running-navigation-v4-training', 'training_completed': False,
        'protocol_id': budget.PROTOCOL_ID, 'protocol_sha256': PROTOCOL_SHA256,
        'go_sha256': go_sha256, 'corpus_pin_sha256': pin_sha256,
        'data_manifest_sha256': derivation['document']['data_manifest_sha256'],
        'schedule_derivation_sha256': derivation['sha256'],
        'models': [{'seed': seed, 'arm': arm, 'status': 'not_started'} for seed, arm in planned_models()],
        'files': [], 'held_out_status': 'locked_unopened', 'held_out_used_for_selection': False,
        'cpu_accounting': 'run_research_stage.py census unit (not measured by this trainer)',
        'qualification_claims': [],
    }


def _completed(report):
    return (isinstance(report, dict) and report.get('id') == REPORT_ID and
            report.get('status') == 'completed-navigation-v4-training' and
            report.get('training_completed') is True and
            [(m.get('seed'), m.get('arm'), m.get('status')) for m in report.get('models', [])] ==
            [(seed, arm, 'completed') for seed, arm in planned_models()] and
            all(m.get('selected_optimizer_update') == budget.OPTIMIZER_UPDATES and
                m.get('optimizer_updates') == budget.OPTIMIZER_UPDATES and
                m.get('real_row_presentations') == budget.DEFAULT_PRESENTATIONS
                for m in report['models']) and
            report.get('held_out_status') == 'locked_unopened' and
            report.get('qualification_claims') == [])


def publish_success(output, report):
    """Terminal-only publication: report, then the receipt that alone admits success."""
    if (output / 'failure.json').exists() or (output / 'report.json').exists():
        raise FileExistsError('Fresh failure-free S1 publication paths required')
    if not _completed(report):
        raise ValueError('Only a complete six-model terminal report is publishable')
    payload = male_model.canonical(report)
    write_exclusive(output / 'report.pending', payload, MAX_JSON)
    os.replace(output / 'report.pending', output / 'report.json')
    _fsync_directory(output)
    receipt = {'id': PUBLICATION_ID, 'status': 'durably-published', 'protocol_sha256': PROTOCOL_SHA256,
               'report_sha256': sha256_bytes(payload), 'report_size_bytes': len(payload),
               'qualification_claims': []}
    write_exclusive(output / 'publication.json', male_model.canonical(receipt), MAX_JSON)
    return receipt


def success_admitted(output):
    """Success evidence: report + matching receipt, no failure, every checkpoint unchanged."""
    output = Path(output)
    if (output / 'failure.json').exists() or (output / 'report.pending').exists():
        return None
    try:
        payload = artifacts._read(output / 'report.json', MAX_JSON)
        receipt = json.loads(artifacts._read(output / 'publication.json', MAX_JSON))
        report = json.loads(payload)
    except (OSError, ValueError):
        return None
    if not _completed(report) or receipt != {
            'id': PUBLICATION_ID, 'status': 'durably-published', 'protocol_sha256': PROTOCOL_SHA256,
            'report_sha256': sha256_bytes(payload), 'report_size_bytes': len(payload),
            'qualification_claims': []}:
        return None
    for model in report['models']:
        item = model.get('checkpoint', {})
        try:
            raw = artifacts._read(output / item['path'], MAX_FILE)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if len(raw) != item.get('size_bytes') or sha256_bytes(raw) != item.get('sha256'):
            return None
    return report


# --------------------------------------------------------------------------- orchestration

def plan(record=None, pin_sha256=None):
    study = protocol()
    value = {'mode': 'plan-only', 'protocol_sha256': PROTOCOL_SHA256, 'lane': LANE, 'stage': STAGE,
             'models': [fixed_training(seed, arm, study) for seed, arm in planned_models()]}
    if record is None:
        value['schedule_derivation'] = 'pending: no S0z corpus pin record given'
        return value
    derivation = derive_schedules(record)
    value.update(corpus_pin_sha256=pin_sha256, schedule_derivation_sha256=derivation['sha256'],
                 schedule_derivation=derivation['document'])
    return value


def train(args, hooks, study, record, pin_sha256, derivation, go_sha256):
    """Execute S1 after GO admission; the output directory is the durable reservation."""
    started = time.monotonic()
    output = preflight_output(args.output)
    before = source_identity()
    hooks.runtime(study)
    output.mkdir()
    _fsync_directory(output.parent)
    report = initial_report(go_sha256, pin_sha256, derivation)
    write_exclusive(output / 'reservation.json', male_model.canonical(
        {'id': 'male-navigation-v4-s1-reservation-v1', 'protocol_sha256': PROTOCOL_SHA256,
         'go_sha256': go_sha256, 'corpus_pin_sha256': pin_sha256,
         'models': [{'seed': seed, 'arm': arm} for seed, arm in planned_models()],
         'retry_allowed': False, 'qualification_claims': []}), MAX_JSON)
    active = None

    def check():
        observed = hooks.rss_bytes()
        if observed > RSS_BYTES:
            raise MemoryError(f'S1 RSS exceeds {RSS_BYTES} bytes')
        if sum(path.stat().st_size for path in output.iterdir() if path.is_file()) > OUTPUT_BYTES:
            raise ValueError('S1 output cap exceeded')

    def write(name, payload, maximum=MAX_FILE):
        if sum(path.stat().st_size for path in output.iterdir() if path.is_file()) + len(payload) > OUTPUT_BYTES:
            raise ValueError('S1 output cap exceeded')
        item = write_exclusive(output / name, payload, maximum)
        report['files'].append(item)
        return item

    try:
        graph, model_inputs = hooks.admit_model_inputs(study)
        data = load_arrays(hooks.derive_data(record, derivation, output), derivation['rosters'])
        if source_identity() != before:
            raise ValueError('S1 behaviour source changed during admission')
        run_protocol = {'id': budget.PROTOCOL_ID, 'protocol_sha256': PROTOCOL_SHA256,
                        'training': {f'{seed}:{arm}': fixed_training(seed, arm, study)
                                     for seed, arm in planned_models()},
                        'schedule_sha256': {f'{seed}:{arm}': derivation['schedules'][seed, arm].sha256
                                            for seed, arm in planned_models()},
                        'schedule_derivation_sha256': derivation['sha256'],
                        'corpus_pin_sha256': pin_sha256, 'source_code': before,
                        'model_inputs': model_inputs, 'held_out_status': 'locked_unopened',
                        'qualification_claims': []}
        report['run_protocol_sha256'] = male_model.digest(run_protocol)
        write('protocol.json', male_model.canonical(run_protocol), MAX_JSON)
        write('schedule-derivation.json', derivation['bytes'])
        check()
        torch_module = hooks.load_torch()  # Sole heavy import, after complete admission.
        torch_module.set_num_threads(1)
        torch_module.use_deterministic_algorithms(True)
        report['runtime'] = runtime = hooks.runtime(study, torch_module)
        roster = None
        for position, (seed, arm) in enumerate(planned_models()):
            active = position
            report['models'][position]['status'] = 'running'
            schedule = derivation['schedules'][seed, arm]
            settings = run_protocol['training'][f'{seed}:{arm}']
            terminal_state, result = fit_terminal(hooks, graph, data[arm], schedule, settings,
                                                  torch_module, derivation['document']['dev_rows'], check)
            if (result['optimizer_updates'], result['real_row_presentations'],
                    result['selected_optimizer_update'], result['selected_real_row_presentations']) != \
                    (budget.OPTIMIZER_UPDATES, budget.DEFAULT_PRESENTATIONS,
                     budget.OPTIMIZER_UPDATES, budget.DEFAULT_PRESENTATIONS):
                raise ValueError('Completed model differs from the matched terminal budget')
            names = result.pop('trainable_names')
            if roster is not None and names != roster:
                raise ValueError('Trainable parameter roster differs between models')
            roster = names
            if source_identity() != before:
                raise ValueError('S1 behaviour source changed during training')
            buffer = io.BytesIO()
            torch_module.save({'format': CHECKPOINT_FORMAT, 'protocol_sha256': report['run_protocol_sha256'],
                               'graph_sha256': male_model.digest(graph),
                               'ordered_ids_sha256': graph['ordered_ids_sha256'],
                               'state_dict': terminal_state}, buffer)
            checkpoint = write(f'seed-{seed}-{arm}.pt', buffer.getvalue())
            report['models'][position] = {'seed': seed, 'arm': arm, 'status': 'completed', **result,
                                          'schedule_sha256': schedule.sha256, 'checkpoint': checkpoint,
                                          'graph_variant': 'original'}
            check()
            active = None
        if hooks.runtime(study, torch_module) != runtime or source_identity() != before:
            raise ValueError('Runtime or behaviour source changed before publication')
        report.update(status='completed-navigation-v4-training', training_completed=True,
                      trainable_names=roster,
                      wall_seconds_before_publication=time.monotonic() - started)
        report['receipt'] = publish_success(output, report)
        return report
    except BaseException as error:
        if active is not None:
            report['models'][active] = {**report['models'][active], 'status': 'failed',
                                        'error': {'type': type(error).__name__, 'message': str(error)[:1024]}}
        report.update(status='failed-navigation-v4-training', training_completed=False,
                      error={'type': type(error).__name__, 'message': str(error)[:1024]})
        try:
            write_exclusive(output / 'failure.json', male_model.canonical(report), MAX_JSON)
        except BaseException as diagnostic:
            error.add_note('Failure retention also failed: ' + str(diagnostic)[:256])
        raise


def _emit(value):
    print(json.dumps(value, sort_keys=True, indent=1))


def main(argv=None, hooks=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--plan-only', action='store_true', help='Default: print the plan only')
    parser.add_argument('--go', type=Path, help='Owner GO record for lane navigation, stage S1')
    parser.add_argument('--corpus-pin', type=Path, help='S0z corpus pin record')
    parser.add_argument('--output', type=Path, help='Fresh S1 output directory')
    parser.add_argument('--graph', type=Path, default=ROOT / 'data/assets/flynn/male-reduced-v1/source-graph.json')
    parser.add_argument('--graph-manifest', type=Path,
                        default=ROOT / 'data/manifests/malecns-reduced-neighborhood-v1.json')
    parser.add_argument('--cell-source', type=Path,
                        default=ROOT / 'upstream/fly-gym/models/connectome_rnn_model.py')
    args = parser.parse_args(argv)
    hooks = Hooks(args) if hooks is None else hooks
    hooks.args = args
    try:
        study = protocol()
        if args.plan_only and args.go is not None:
            raise Refusal('--plan-only and --go are mutually exclusive')
        record = pin_sha = None
        if args.corpus_pin is not None or args.go is not None:
            record, pin_sha = read_corpus_pin(args.corpus_pin)
        if args.go is None:
            _emit(plan(record, pin_sha))
            return 0
        derivation = derive_schedules(record)
        go_sha = check_go(args.go, PROTOCOL_SHA256, pin_sha, derivation['sha256'])
        if args.output is None:
            raise Refusal('--go requires a fresh --output directory')
        if not hooks.inside_stage():
            raise Refusal('S1 runs only inside a run_research_stage.py census unit')
    except (Refusal, OSError, ValueError, KeyError) as error:
        _emit({'status': 'refused', 'stage': STAGE, 'reason': f'{type(error).__name__}: {error}'})
        return 2
    report = train(args, hooks, study, record, pin_sha, derivation, go_sha)
    _emit({'status': report['status'], 'stage': STAGE, 'output': str(args.output),
           'report_sha256': report['receipt']['report_sha256']})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
