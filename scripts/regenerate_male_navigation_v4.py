"""M7 navigation v4 Stage 0 overlay driver: data/path-only pin rebinding; refuses by default.

Each S0 sub-stage runs its UNCHANGED producer from a detached worktree at the producing
commit. This driver (1) verifies the worktree is detached at that commit with clean
tracked bytes, the pinned producer bytes and every declared source guard; (2) loads the
previous sub-stage's pin record and refuses any producer input not matching it; (3) loads
the v4 pin-document copies, refusing undeclared field changes, PENDING placeholders and
values that do not trace to the pin-record chain; (4) statically refuses read sites an
in-process overlay cannot reach (copied pins, inline pinned literals, import-time reads,
child re-execution of a rebound module); (5) imports the producer closure and rebinds
EXACTLY the declared data/path module attributes before any dependent import.

Amendment 1 (owner decision A1): S0c-S0f run instead from committed port trees
(``port/male-v4-<tree>``, see ``docs/plans/m7-navigation-v4-pins/ports.json``). For those
stages the worktree HEAD must be the recorded port branch commit (and the branch must still
point at it) before anything is planned; the port's H1 hunks read every pin from a locator
document named by ``PALIMPSEST_M7_V4_PINS``, written by this driver next to the pin record,
so no attribute is rebound in-process.

Reconstructed controllers (``CONTROLLED``): S0d runs this driver once per training seed and S0e
once, each writing ``<stage root>/seed-N`` or ``<stage root>/collection``. The next stage takes
those producer records as one ordered set (seeds 10, 11, 12) and merges them with the
controller record at ``<stage root>/control/controller-record.json``, which binds the
controller documents (terminal, supervisors, drain, audit, index) so that every declared
path, sha256 and byte count in the v4 pin documents traces to the merged chain.

``--plan-only`` prints what would run and never imports or executes a producer and never
opens a data input. Execution requires ``--go`` naming a GO record whose content names the
exact stage and the protocol sha256; anything else is refused. After a normal producer
exit the driver hashes every output into a fsynced, exclusive v4 pin record that the next
sub-stage must present. One attempt per GO; there is no retry.
"""
import argparse
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import probe_male_navigation_v4_imports as probe

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = 'docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json'
PROTOCOL_SHA256 = 'cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477'
PINS_DIR = ROOT/'docs/plans/m7-navigation-v4-pins'
# Amendment 1 (owner decision A1): S0c-S0f run from committed port trees listed here.
PORTS_PATH = PINS_DIR/'ports.json'
PORTS_SCHEMA = 'm7-navigation-v4-ports-1'
PORT_LOCATOR_SCHEMA = 'm7-navigation-v4-port-pins-1'
PORT_LOCATOR_ENV = 'PALIMPSEST_M7_V4_PINS'
DECLARATION_SCHEMA = 'm7-navigation-v4-pin-declarations-1'
RECORD_SCHEMA = 'm7-navigation-v4-pin-record-1'
CONTROLLER_RECORD_SCHEMA = 'm7-navigation-v4-controller-record-1'
CONTROLLER_RECORD = 'control/controller-record.json'   # relative to a controlled stage's root
# Stages run by a reconstructed Amendment 1 controller. The next stage takes their producer pin
# records (S0d: one per training seed, in this order) as one ordered set; the controller record at
# <stage root>/control binds the controller documents, so every declared path and sha traces.
CONTROLLED = {'S0d': {'seeds': (10, 11, 12), 'output': 'seed-{seed}'}, 'S0e': {'seeds': None, 'output': 'collection'}}
PENDING = 'PENDING-'
HEX64 = re.compile(r'[0-9a-f]{64}')
MAX_DOCUMENT = 4*1024**2
MAX_GO = 64*1024

RECOVERY_LEARNING = 'm7-recovery-learning-protocol.json'
CONTACT_V2 = 'm7-navigation-contact-v2-protocol.json'
DATA_V2 = 'm7-navigation-data-v2-protocol.json'
RECOVERY_INDEX = 'male-recovery-research-development-v1.json'
STUDY_PLAN = 'm7-navigation-study-protocol.json'
# Per-source count sub-schemas (declared-fields.json amendment_1_pending.count_schemas).
RECOVERY_CASES = ('recovery-north-2100', 'recovery-south-2101')
ADVICE_CASES = tuple(f'learner-{scene}-seed-{seed}' for scene in range(3100, 3104) for seed in (10, 11, 12))
RECOVERY_MAX_ROWS, ADVICE_MAX_ROWS = 120, 600
PORT_READER_SHA = 'ddefc34d4b1c3512a0751f4597be537a380b6823efc31fdbfd838ec04e4ae24c'
PORT_COLLECTOR_V2_SHA = '5d7ddef2104a2ec9bb9446aaaa2e8b8db6c77b23ce0d3afd903abc6c6c074a09'
ORIGINAL_RECOVERY_LEARNING_SHA = '091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28'
ORIGINAL_DATA_SHA = '402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014'
ORIGINAL_INDEX_SHA = 'cf50fd2f6a96cfb1afd43e23eae05b76522116abdcf544ef41735033dc52b6b5'
READER_SOURCES = {
    'scripts/collect_male_recovery.py': '17d948322bbf124c7eeee3d55e4034e12c4b3436d933dab1df4245f278c46f60',
    'src/palimpsest/artifacts.py': '7a5f4a1080abffe82f8296468c6d8ca3a2b975277b96925fdf75bb9ac1ed034a',
    'src/palimpsest/body_profile.py': '796df9ab2a109606432c7a97bfbea5f58ab7acc75768e638b5b8731a390cbb54',
    'src/palimpsest/male_model.py': '9327bca1db3cbeda7aab8b222ccfa59daef4e01f3f1b4689f83009955d970cad',
    'src/palimpsest/male_research.py': 'a3fb8f64937c509351cc7cbd120bf86c0b543fd4e6531d957a7204a6da1df8ce',
    'src/palimpsest/records.py': 'c4be6f1699c1d8550a7f2db2979f7f9f18196ac986eef2aefe3ba665cae99ac3',
}
RECOVERY_PROTOCOL_REBINDS = [
    {'module': 'prepare_male_recovery_data', 'attribute': 'PROTOCOL_PATH', 'kind': 'document-path', 'document': RECOVERY_LEARNING},
    {'module': 'prepare_male_recovery_data', 'attribute': 'PROTOCOL_SHA256', 'kind': 'document-sha256', 'document': RECOVERY_LEARNING},
]
CONTACT_REBINDS = [
    {'module': 'collect_male_navigation_v2', 'attribute': 'PLAN', 'kind': 'document-path', 'document': CONTACT_V2},
    {'module': 'collect_male_navigation_v2', 'attribute': 'PLAN_SHA', 'kind': 'document-sha256', 'document': CONTACT_V2},
]
OUTPUT = {'kind': 'output'}
REPO = {'kind': 'repo', 'optional': True}
ASSETS = {'kind': 'assets'}

STAGES = {
    'S0a': {'stage': 'S0a', 'producer': 'scripts/collect_male_teachers.py', 'module': 'collect_male_teachers',
            'commit': 'cc1cea93d4c3333a0ee2a091dd34fff0b2986887',
            'producer_sha256': 'ca633269b4710782647f505438ad521fe65b8fce643f48f26bdb3bd2b410025b',
            'source_guards': {'docs/plans/m7-training-v2-protocol.json':
                              '8f360289ce286f56e31051c7bcfc6932a8f413dce662b83ddb9817b3e509d69b'},
            'documents': [], 'rebinds': [], 'upstream_values': [], 'execution': 'subprocess',
            'args': {'--repo': {'kind': 'repo'}, '--assets': ASSETS, '--output': OUTPUT,
                     '--protocol': {'kind': 'fixed-file',
                                    'sha256': '8f360289ce286f56e31051c7bcfc6932a8f413dce662b83ddb9817b3e509d69b'},
                     # Development teacher stage only; held-out teacher scenes 1012-1015 are not run.
                     '--research-stage': {'kind': 'value', 'allowed': ['development']}},
            'records_counts': 'teacher-collection'},
    'S0b': {'stage': 'S0b', 'producer': 'scripts/collect_male_recovery.py', 'module': 'collect_male_recovery',
            'commit': 'c382c86781a7a5d6651af721119789729cc890ae',
            'producer_sha256': '17d948322bbf124c7eeee3d55e4034e12c4b3436d933dab1df4245f278c46f60',
            'source_guards': {}, 'documents': [], 'rebinds': [], 'upstream_values': [], 'execution': 'subprocess',
            'args': {'--repo': REPO, '--assets': ASSETS, '--output': OUTPUT}, 'records_counts': 'recovery-cases'},
    'S0c': {'stage': 'S0c', 'producer': 'scripts/prepare_male_recovery_data.py', 'module': 'prepare_male_recovery_data',
            'commit': '7d5fc1f4ecd1bbd6a5a139bde3585fb2255ce2fe',
            'producer_sha256': '2b5c7b78e84a782838cf51b5b4682ea6c3ab4bbb5c11180984ccdc8f03cc06ca',
            'source_guards': dict(READER_SOURCES), 'documents': [RECOVERY_LEARNING],
            'rebinds': RECOVERY_PROTOCOL_REBINDS, 'upstream_values': [], 'execution': 'in-process',
            'port_tree': 'T-c', 'port_producer_sha256': PORT_READER_SHA, 'port_documents': [RECOVERY_LEARNING],
            'args': {'--baseline-collection': {'kind': 'record', 'stage': 'S0a'},
                     '--recovery-report': {'kind': 'record', 'stage': 'S0b'}, '--output': OUTPUT}},
    'S0d': {'stage': 'S0d', 'producer': 'scripts/train_male_recovery.py', 'module': 'train_male_recovery',
            'commit': '19d275d7ba3d8c7da642a4b41d3a6a8f2d5c720f',
            'producer_sha256': '1b828d68daf4db6186d5ccc0804d35ce6a8918279cb74834d16291f6d5679877',
            'source_guards': {**READER_SOURCES,
                              'scripts/prepare_male_recovery_data.py': '2b5c7b78e84a782838cf51b5b4682ea6c3ab4bbb5c11180984ccdc8f03cc06ca',
                              'scripts/train_male_reduced.py': '75d3fc1fd71bab6b749c158a58fe9d802fc10253f4416d1c8f5739a2bdf4ff4a',
                              'uv.lock': '8a7a880d020c1907e221575fda65642241f809fc628a55381f1b6137bff1b732'},
            'documents': [RECOVERY_LEARNING],
            'rebinds': RECOVERY_PROTOCOL_REBINDS + [
                {'module': 'train_male_recovery', 'attribute': 'DATA_SHA256', 'kind': 'output-sha256',
                 'stage': 'S0c', 'output': 'data-manifest.json'}],
            'upstream_values': [], 'execution': 'in-process',
            'port_tree': 'T-d', 'port_producer_sha256': 'b9cc181f7caec71cbd890fdb17d4cdaa73c1b0a847e4a3d6b437b2d3be0bed37',
            'port_source_guards': {'scripts/prepare_male_recovery_data.py': PORT_READER_SHA},
            'port_documents': [RECOVERY_LEARNING],
            'args': {'--data-manifest': {'kind': 'record', 'stage': 'S0c'},
                     '--training-seed': {'kind': 'value', 'allowed': ['10', '11', '12']},
                     '--graph': {'kind': 'fixed-file', 'optional': True,
                                 'sha256': '5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0'},
                     '--graph-manifest': {'kind': 'fixed-file', 'optional': True,
                                          'sha256': '7a205342b4ada8ab8b78d6ca866c61735003e601531c65a1c1b6c819df00026f'},
                     '--cell-source': {'kind': 'fixed-file', 'optional': True,
                                       'sha256': '707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80'},
                     '--output': OUTPUT}},
    'S0e': {'stage': 'S0e', 'producer': 'scripts/collect_male_navigation_v2.py', 'module': 'collect_male_navigation_v2',
            'commit': '736e0cf0a71f6d700bd67836ee5f83911ceff90a',
            'producer_sha256': '21d2cb104dfe0ea34e52b5d93c835affb9cebeb7bccb85b7314f18404971053f',
            'source_guards': {'scripts/collect_male_navigation.py':
                              'd0decc66112a9f138823ec06414e211299f1ae81527f472e3b6341c33118868f'},
            # Port tree T-e: the v1 collector reached via source_pins is the port (PLAN/PLAN_SHA -> v4 study-plan
            # copy); contact-v2 /prior_version/collector_sha256 cascades to these bytes (amendment_1_pending).
            'port_tree': 'T-e', 'port_producer_sha256': PORT_COLLECTOR_V2_SHA,
            'port_source_guards': {'scripts/collect_male_navigation.py':
                                   'f96552012646b4cac5c7feeb253a6c16ab15d1948b67a6a8799da5341f74d1a0'},
            'port_documents': [CONTACT_V2, RECOVERY_INDEX, RECOVERY_LEARNING, STUDY_PLAN],
            'documents': [CONTACT_V2, RECOVERY_INDEX],
            # The recovery index pin lives in male_recovery_research (not in the protocol inventory).
            'rebinds': [{'module': 'palimpsest.male_recovery_research', 'attribute': 'INDEX_PATH',
                         'kind': 'document-path', 'document': RECOVERY_INDEX},
                        {'module': 'palimpsest.male_recovery_research', 'attribute': 'INDEX_SHA256',
                         'kind': 'document-sha256', 'document': RECOVERY_INDEX}] + CONTACT_REBINDS,
            'upstream_values': [ORIGINAL_RECOVERY_LEARNING_SHA, ORIGINAL_DATA_SHA], 'execution': 'in-process',
            'args': {'--repo': REPO, '--assets': ASSETS, '--output': OUTPUT}, 'records_counts': 'advice-cases'},
    'S0f': {'stage': 'S0f', 'producer': 'scripts/prepare_male_navigation_v2.py', 'module': 'prepare_male_navigation_v2',
            'commit': '4ecb354efa4223abdbe3d09be118fe5402fec1a1',
            'producer_sha256': 'ef32434826c04398c5c98e9b8debbe0b9d90adea2f9ac558a05ec00ce5eff333',
            'historical_commit': '217cbee8399dcb25045a079af012beecbbdae29e',
            'port_tree': 'T-f', 'historical_port_tree': 'T-h',
            'port_producer_sha256': 'b819af261cea449aae01cae90e994aeebefba672b1bbbad43099bc64fab449e0',
            # Erratum 1: T-f carries the collector port its admission compares against (:325).
            'port_source_guards': {'scripts/collect_male_navigation_v2.py': PORT_COLLECTOR_V2_SHA},
            'port_documents': [DATA_V2, RECOVERY_LEARNING, CONTACT_V2],
            'source_guards': {}, 'documents': [DATA_V2, CONTACT_V2],
            # The S0e report carries the v4 contact-plan sha, which this reader compares to PLAN_SHA.
            'rebinds': CONTACT_REBINDS + [
                {'module': 'prepare_male_navigation_v2', 'attribute': 'PROTOCOL', 'kind': 'document-path', 'document': DATA_V2},
                {'module': 'prepare_male_navigation_v2', 'attribute': 'PROTOCOL_SHA', 'kind': 'document-sha256', 'document': DATA_V2}],
            'upstream_values': [ORIGINAL_RECOVERY_LEARNING_SHA, ORIGINAL_DATA_SHA, ORIGINAL_INDEX_SHA],
            'execution': 'in-process', 'args': {'--output': OUTPUT}},
}


class Refusal(Exception):
    """A v4 stop: nothing is executed or published after it."""


# --------------------------------------------------------------------------- small helpers

def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        while block := stream.read(1024*1024): digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def read_text_or_none(path):
    try: return Path(path).read_text()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError): return None


def read_bounded(path, maximum=MAX_DOCUMENT):
    path = Path(path)
    if path.is_symlink() or not path.is_file(): raise Refusal(f'Regular file required: {path}')
    with path.open('rb') as stream: payload = stream.read(maximum+1)
    if len(payload) > maximum: raise Refusal(f'File exceeds {maximum} bytes: {path}')
    return payload


def under(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path == root or root in path.parents


def _escape(key): return str(key).replace('~', '~0').replace('/', '~1')
def _unescape(token): return token.replace('~1', '/').replace('~0', '~')


def pointer_get(doc, pointer):
    node = doc
    for token in pointer.split('/')[1:]:
        token = _unescape(token)
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def pointer_set(doc, pointer, value):
    tokens = [_unescape(t) for t in pointer.split('/')[1:]]
    node = doc
    for token in tokens[:-1]: node = node[int(token)] if isinstance(node, list) else node[token]
    node[int(tokens[-1]) if isinstance(node, list) else tokens[-1]] = value


def field_diff(original, changed, pointer=''):
    """Leaf-level JSON pointers whose value, type or presence differs."""
    if type(original) is not type(changed): return {pointer}
    if isinstance(original, dict):
        found = set()
        for key in original.keys() | changed.keys():
            child = f'{pointer}/{_escape(key)}'
            found |= field_diff(original[key], changed[key], child) if key in original and key in changed else {child}
        return found
    if isinstance(original, list):
        if len(original) != len(changed): return {pointer}
        return set().union(*(field_diff(a, b, f'{pointer}/{i}') for i, (a, b) in enumerate(zip(original, changed))))
    return set() if original == changed else {pointer}


def _pending(value, pointer=''):
    if isinstance(value, str): return [pointer] if value.startswith(PENDING) else []
    if isinstance(value, dict): return [p for k, v in value.items() for p in _pending(v, f'{pointer}/{_escape(k)}')]
    if isinstance(value, list): return [p for i, v in enumerate(value) for p in _pending(v, f'{pointer}/{i}')]
    return []


def _git(worktree, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.run(['git', *args], cwd=worktree, capture_output=True, text=True, timeout=30, env=env)


# --------------------------------------------------------------------------- pin documents

def load_declarations(pins_dir, protocol_sha256):
    value = json.loads(read_bounded(Path(pins_dir)/'declared-fields.json'))
    if value.get('schema') != DECLARATION_SCHEMA or value.get('protocol_sha256') != protocol_sha256:
        raise Refusal('v4 pin declarations do not bind this protocol')
    return value


def check_pin_document(original_bytes, copy_bytes, item, *, consumer):
    """A v4 copy may differ from its original only in declared data/path fields."""
    original, copy = json.loads(original_bytes), json.loads(copy_bytes)
    declared = [f['pointer'] for f in item['fields']]
    undeclared = sorted(p for p in field_diff(original, copy)
                        if not any(p == d or p.startswith(d + '/') for d in declared))
    if undeclared: raise Refusal('v4 pin copy changes undeclared fields: ' + ', '.join(undeclared))
    if consumer and (pending := _pending(copy)):
        raise Refusal('v4 pin copy still holds PENDING placeholders at: ' + ', '.join(pending))
    return copy


def fill_document(raw, item, values):
    """Replace declared PENDING placeholders only; refuses anything else."""
    doc, fields = json.loads(raw), {f['pointer']: f for f in item['fields']}
    for pointer, value in values.items():
        if pointer not in fields: raise Refusal(f'Fill targets an undeclared field: {pointer}')
        if pointer_get(doc, pointer) != fields[pointer]['placeholder']:
            raise Refusal(f'Field {pointer} no longer holds its placeholder')
        pointer_set(doc, pointer, value)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + ('\n' if raw.endswith(b'\n') else '')
    return text.encode()


CASCADE_CLASSES = ('doc-path', 'doc-sha256', 'port-sha256')


def doc_path_value(pins_dir, document):
    """A v4 copy's path as recorded in other copies: repo-relative like the originals (absolute outside the repo)."""
    path = (Path(pins_dir)/document).resolve()
    try: return path.relative_to(ROOT.resolve()).as_posix()
    except ValueError: return str(path)


def _output_json(record, fill, where):
    """A JSON value from recorded outputs: each file re-hashed against its record; identical across ``same_in``."""
    values = []
    for rel in [fill['output_json'], *fill.get('same_in', [])]:
        if rel not in record['outputs']: raise Refusal(f'{where}: the record has no output {rel}')
        raw = read_bounded(Path(record['output_root'])/rel)
        if sha256_bytes(raw) != record['outputs'][rel]['sha256']: raise Refusal(f'{where}: {rel} differs from its pin record')
        values.append(pointer_get(json.loads(raw), fill['pointer']))
    if any(value != values[0] for value in values): raise Refusal(f'{where}: {fill["pointer"]} differs across {fill["output_json"]} and {fill.get("same_in")}')
    return values[0]


def _port_file(field, worktree, where):
    """A port-byte cascade: the declared value, which must equal the file in the port tree being run."""
    if worktree is not None:
        path = Path(worktree)/field['port_file']
        if not path.is_file() or sha256_file(path) != field['cascade_value']:
            raise Refusal(f'{where}: {field["port_file"]} in {worktree} is not the {field["port_tree"]} port bytes')
    return field['cascade_value']


def _recorded_path(record, fill, where):
    if fill.get('worktree'): return record['worktree']
    rel = fill['path_of']
    if rel not in record['outputs'] and not any(k.startswith(rel + '/') for k in record['outputs']):
        raise Refusal(f'{where}: the record has no output {rel}')
    path = Path(record['output_root'])/rel
    return path.relative_to(record['worktree']).as_posix() if fill.get('relative_to') == 'worktree' else str(path)


def fill_values(name, item, doc, original, chain, *, pins_dir=None, worktree=None, doc_sha=None):
    """Values for every declared field still at its placeholder.

    Read only from pin records, the files they bind and validated v4 copies. A sha256 is a named
    output's recorded sha256 (or a controller-declared value); a path is a recorded output's path
    or the producing worktree; a run id is the single run directory recorded under a case; a commit
    is the producing commit; a source-map or path-keys value is read from a recorded output JSON
    that is re-hashed and identical across seeds; counts are derived by the sub-schemas that check
    them; doc-path/doc-sha256 name a validated copy; port-sha256 is a port byte pin checked against
    the port tree. Anything else is refused, never guessed."""
    values = {}
    for field in item['fields']:
        pointer, kind = field['pointer'], field['class']
        if pointer_get(doc, pointer) != field['placeholder']: continue
        where, fill = f'{name}{pointer}', field.get('fill', {})
        if kind in ('count-map', 'count-list', 'window-list'):
            if kind == 'count-map': value = expected_count_map(field.get('schema'), original, chain, where)
            elif field.get('schema') == 'recovery-ticks-v4': value = _recovery_ticks(chain, where)
            elif field.get('schema') == 'recovery-windows-v4': value = [windows_for(n) for n in _recovery_ticks(chain, where)]
            else: raise Refusal(f'{where} has class {kind} with unknown schema {field.get("schema")}')
        elif kind == 'doc-path':
            value = doc_path_value(pins_dir, field['document'])
        elif kind == 'doc-sha256':
            if doc_sha is None: raise Refusal(f'{where} needs the validated copy {field["document"]}')
            value = doc_sha(field['document'])
        elif kind == 'port-sha256':
            value = _port_file(field, worktree, where)
        else:
            record = _outputs(chain, field['stage'], where)
            outputs = record['outputs']
            if kind == 'sha256' and 'output' in fill:
                if fill['output'] not in outputs: raise Refusal(f'{where}: {field["stage"]} recorded no {fill["output"]}')
                value = outputs[fill['output']]['sha256']
            elif kind == 'sha256' and 'declared_value' in fill:
                declared = record.get('declared_values', [])
                if len(declared) <= fill['declared_value']: raise Refusal(f'{where}: {field["stage"]} declared no value')
                value = declared[fill['declared_value']]
            elif kind == 'path' and (fill.get('worktree') or 'path_of' in fill):
                value = _recorded_path(record, fill, where)
            elif kind == 'commit' and fill.get('producing_commit'):
                value = record['producing_commit']
            elif kind in ('source-map', 'path-keys') and 'output_json' in fill:
                value = _output_json(record, fill, where)
            elif kind == 'run-id' and 'run_dir_of' in fill:
                runs = {Path(rel).parts[1] for rel in outputs if Path(rel).parts[0] == fill['run_dir_of'] and len(Path(rel).parts) > 3
                        and Path(rel).parts[2] in ('recording', 'snapshots')}
                if len(runs) != 1: raise Refusal(f'{where}: {fill["run_dir_of"]} must record exactly one run directory, got {sorted(runs)}')
                value = runs.pop()
            else:
                raise Refusal(f'{where} ({kind}) names no fill source')
        values[pointer] = value
    return values


def referenced_copy_sha(pins_dir, declarations, worktree, name):
    """sha256 of a v4 copy another copy cascades to; the copy must already be placeholder-free."""
    item = declarations['documents'][name]
    original = read_bounded(Path(worktree)/item['original_path'])
    if sha256_bytes(original) != item['original_sha256']: raise Refusal(f'Original {item["original_path"]} differs in {worktree}')
    raw = read_bounded(Path(pins_dir)/name)
    check_pin_document(original, raw, item, consumer=True)
    return sha256_bytes(raw)


def fill_copy(name, stage, worktree, previous_paths, *, pins_dir, protocol_sha256, stages):
    """--fill-document: fill a v4 copy consumed by ``stage`` in place, from the previous pin records only.

    Every field whose stage is in the chain must end filled and traced (check_document_values);
    fields of later stages keep their placeholders. Writes via an exclusive temporary and rename."""
    if name not in stages[stage]['documents']: raise Refusal(f'{stage} does not consume {name}')
    raws = [read_bounded(path) for path in previous_paths]
    chain = previous_chain([json.loads(raw) for raw in raws], stage, stages, protocol_sha256=protocol_sha256)
    item = load_declarations(pins_dir, protocol_sha256)['documents'][name]
    original_raw = read_bounded(Path(worktree)/item['original_path'])
    if sha256_bytes(original_raw) != item['original_sha256']:
        raise Refusal(f'Original {item["original_path"]} differs in {worktree}')
    target = Path(pins_dir)/name
    raw = read_bounded(target)
    original = json.loads(original_raw)
    declarations = load_declarations(pins_dir, protocol_sha256)
    doc_sha = lambda other: referenced_copy_sha(pins_dir, declarations, worktree, other)
    values = fill_values(name, item, check_pin_document(original_raw, raw, item, consumer=False), original, chain,
                         pins_dir=pins_dir, worktree=worktree, doc_sha=doc_sha)
    if not values: raise Refusal(f'{name} holds no placeholder that this chain can fill')
    filled = fill_document(raw, item, values)
    doc = check_pin_document(original_raw, filled, item, consumer=False)
    due = {f['pointer'] for f in item['fields'] if f['stage'] in chain or f['class'] in CASCADE_CLASSES}
    left = [p for p in _pending(doc) if any(p == d or p.startswith(d + '/') for d in due)]
    if left: raise Refusal(f'{name} still holds placeholders this chain should fill: {left}')
    check_document_values(name, doc, original, {**item, 'fields': [f for f in item['fields'] if f['pointer'] in values]},
                          chain, doc_sha, pins_dir, worktree=worktree)
    temporary = target.with_name(target.name + '.filling')
    with temporary.open('xb') as stream:
        stream.write(filled); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, target)
    directory = os.open(target.parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return {'document': name, 'path': str(target.resolve()), 'sha256': sha256_bytes(filled), 'fields': sorted(values),
            'previous_record_sha256': [sha256_bytes(r) for r in raws], 'remaining_placeholders': _pending(doc)}


def _outputs(chain, stage, where):
    if stage not in chain: raise Refusal(f'{where}: {stage} is not in the pin-record chain')
    return chain[stage]


def check_document_values(name, doc, original, item, chain, doc_sha, pins_dir, *, worktree=None):
    """Every filled value must trace to the pin-record chain (or to a validated v4 copy or port bytes)."""
    for field in item['fields']:
        where, value, kind = f'{name}{field["pointer"]}', pointer_get(doc, field['pointer']), field['class']
        if kind in ('doc-sha256', 'doc-path'):
            target = Path(pins_dir)/field['document']
            if (kind == 'doc-sha256' and value != doc_sha(field['document'])) or \
                    (kind == 'doc-path' and (not isinstance(value, str) or (value != doc_path_value(pins_dir, field['document'])
                                                                           and Path(value).resolve() != target.resolve()))):
                raise Refusal(f'{where} does not name the validated v4 copy {field["document"]}')
            continue
        if kind == 'port-sha256':
            if value != _port_file(field, worktree, where): raise Refusal(f'{where} is not the {field["port_tree"]} port bytes')
            continue
        if kind in ('count-map', 'count-list', 'window-list'):
            check_count_field(where, kind, field.get('schema'), doc, original, value, chain)
            continue
        if kind == 'worktree-path':
            if not isinstance(value, str) or _git(value, 'rev-parse', 'HEAD').stdout.strip() != field['commit']:
                raise Refusal(f'{where} is not a worktree at {field["commit"]}')
            continue
        record = _outputs(chain, field['stage'], where)
        outputs = record['outputs']
        if kind == 'sha256':
            if not (isinstance(value, str) and HEX64.fullmatch(value)) or \
                    value not in {o['sha256'] for o in outputs.values()} | set(record.get('declared_values', [])):
                raise Refusal(f'{where} is not an output of {field["stage"]}')
        elif kind == 'bytes':
            sibling = pointer_get(doc, field['pointer'].rpartition('/')[0] + '/sha256')
            if value not in [o['bytes'] for o in outputs.values() if o['sha256'] == sibling]:
                raise Refusal(f'{where} is not the recorded size of a {field["stage"]} output')
        elif kind == 'run-id':
            if not isinstance(value, str) or not any(value in Path(rel).parts for rel in outputs):
                raise Refusal(f'{where} is not a run id among {field["stage"]} outputs')
        elif kind == 'path':
            if not isinstance(value, str) or not _traced_path(value, record):
                raise Refusal(f'{where} is not inside the {field["stage"]} output root or worktree')
        elif kind == 'path-keys':
            if not isinstance(value, dict) or list(value.values()) != list(pointer_get(original, field['pointer']).values()) \
                    or not all(Path(k).is_absolute() and under(k, record['worktree']) for k in value):
                raise Refusal(f'{where} must keep pinned hashes and name paths in the {field["stage"]} worktree')
            if 'output_json' in field.get('fill', {}) and value != _output_json(record, field['fill'], where):
                raise Refusal(f'{where} differs from the recorded {field["fill"]["output_json"]}')
        elif kind == 'commit':
            if value != record['producing_commit']: raise Refusal(f'{where} is not the {field["stage"]} producing commit')
        elif kind == 'source-map':
            if 'output_json' not in field.get('fill', {}) or value != _output_json(record, field['fill'], where):
                raise Refusal(f'{where} differs from the recorded {field.get("fill", {}).get("output_json")}')
        else:
            raise Refusal(f'{where} has unknown class {kind}')


def windows_for(ticks):
    """Recovery windows: 32-row chunks then the remainder (Amendment 1 H3)."""
    return [32]*(ticks//32) + ([ticks % 32] if ticks % 32 else [])


def _counts(values, length, maximum=None):
    return isinstance(values, list) and len(values) == length and \
        all(type(n) is int and n > 0 and (maximum is None or n <= maximum) for n in values)


def _recorded(chain, stage, where):
    counts = _outputs(chain, stage, where).get('counts')
    if counts is None: raise Refusal(f'{where}: the {stage} pin record carries no per-source counts')
    return counts


def _teacher_ticks(chain, where):
    teacher = _recorded(chain, 'S0a', where)
    if not (isinstance(teacher, dict) and _counts(teacher.get('baseline_train'), 8) and _counts(teacher.get('dev'), 4)):
        raise Refusal(f'{where}: S0a must record 8 train and 4 dev teacher sources, each > 0')
    return teacher['baseline_train'], teacher['dev']


def _recovery_ticks(chain, where):
    recovery = _recorded(chain, 'S0b', where)
    ticks = [recovery.get(case) for case in RECOVERY_CASES] if isinstance(recovery, dict) else None
    if not _counts(ticks, 2, RECOVERY_MAX_ROWS) or set(recovery) != set(RECOVERY_CASES):
        raise Refusal(f'{where}: S0b must record both recovery sources, each 1..{RECOVERY_MAX_ROWS} rows')
    return ticks


def _advice_ticks(chain, where):
    advice = _recorded(chain, 'S0e', where)
    ticks = [advice.get(case) for case in ADVICE_CASES] if isinstance(advice, dict) else None
    if not _counts(ticks, 12, ADVICE_MAX_ROWS) or set(advice) != set(ADVICE_CASES):
        raise Refusal(f'{where}: S0e must record all 12 advice sources, each 1..{ADVICE_MAX_ROWS} rows')
    return ticks


def expected_count_map(schema, original, chain, where):
    """The exact count map a v4 copy must hold, derived from the pin-record chain."""
    base, dev = _teacher_ticks(chain, where)
    recovery = _recovery_ticks(chain, where)
    if schema == 'recovery-learning-counts-v4':
        return {'baseline_train': sum(base), 'dev': sum(dev), 'held_out': 0, 'recovery_train': sum(recovery),
                'train': sum(base) + sum(recovery), 'per_source': {'baseline_train': base, 'dev': dev},
                'v2_reference_counts': original['counts']}
    if schema == 'data-v2-counts-v4':
        old, advice = base + recovery, _advice_ticks(chain, where)
        return {'old_sources': 14, 'new_sources': 12, 'combined_unique_sources': 26, 'old_train_rows': sum(old),
                'new_advice_train_rows': sum(advice), 'augmented_train_rows': sum(old) + sum(advice),
                'recorded_dev_rows': sum(dev), 'combined_rows': sum(old) + sum(advice) + sum(dev),
                'held_out_sources': 0, 'held_out_rows': 0, 'per_source': {'old_train': old, 'dev': dev, 'advice': advice},
                'v2_reference_counts': original['counts']}
    raise Refusal(f'{where} names unknown count schema {schema}')


def check_count_field(where, kind, schema, doc, original, value, chain):
    """count-map / count-list / window-list: exact, order-preserving, traced to S0a/S0b/S0e records."""
    if kind == 'count-map':
        expected = expected_count_map(schema, original, chain, where)
    elif kind == 'count-list' and schema == 'recovery-ticks-v4':
        if [s.get('case_id') for s in doc.get('recovery_sources', [])] != list(RECOVERY_CASES):
            raise Refusal(f'{where}: recovery_sources order differs from {RECOVERY_CASES}')
        expected = _recovery_ticks(chain, where)
    elif kind == 'window-list' and schema == 'recovery-windows-v4':
        expected = [windows_for(n) for n in _recovery_ticks(chain, where)]
    else:
        raise Refusal(f'{where} has class {kind} with unknown schema {schema}')
    if canonical(value) != canonical(expected):
        raise Refusal(f'{where} differs from the per-source counts in the S0a/S0b/S0e pin records')


def stage_counts(kind, output_root):
    """Per-source tick counts read from a finished stage's own output documents (never recordings)."""
    root = Path(output_root)
    if kind == 'teacher-collection':  # collect_male_teachers.py: runs[*].ticks, one episode per run
        runs = json.loads(read_bounded(root/'collection.json'))['runs']
        return {split: [r['ticks'] for r in runs if r['split'] == key] for split, key in (('baseline_train', 'train'), ('dev', 'dev'))}
    if kind in ('recovery-cases', 'advice-cases'):
        counts = {}
        for case in (RECOVERY_CASES if kind == 'recovery-cases' else ADVICE_CASES):
            result = json.loads(read_bounded(root/case/'result.json'))
            rows = len(result['rows'])
            if kind == 'recovery-cases' and result.get('recorded_ticks') != rows:
                raise Refusal(f'{case}: recorded_ticks differs from the result rows')
            counts[case] = rows
        return counts
    raise Refusal(f'Unknown count source {kind}')


def _traced_path(value, record):
    path = Path(value)
    if path.is_absolute():
        return under(path, record['output_root']) or under(path, record['worktree'])
    if any(Path(rel).parts[:len(path.parts)] == path.parts for rel in record['outputs']): return True
    return under(Path(record['worktree'])/path, record['output_root'])


def load_pin_documents(spec, pins_dir, declarations, worktree, chain):
    """Validated, placeholder-free v4 copies for this stage: {name: {path, sha256, value}}."""
    pins_dir, cache = Path(pins_dir), {}

    def load(name):
        if name in cache: return cache[name]
        if name not in declarations['documents']: raise Refusal(f'Undeclared v4 pin document {name}')
        item = declarations['documents'][name]
        original = read_bounded(Path(worktree)/item['original_path'])
        if sha256_bytes(original) != item['original_sha256']:
            raise Refusal(f'Original {item["original_path"]} differs at the producing commit')
        raw = read_bounded(pins_dir/name)
        doc = check_pin_document(original, raw, item, consumer=True)
        cache[name] = {'path': str((pins_dir/name).resolve()), 'sha256': sha256_bytes(raw), 'value': doc,
                       'original': json.loads(original), 'item': item}
        return cache[name]
    for name in spec['documents']:
        entry = load(name)
        check_document_values(name, entry['value'], entry['original'], entry['item'], chain,
                              lambda other: load(other)['sha256'], pins_dir, worktree=worktree)
    return {name: {k: cache[name][k] for k in ('path', 'sha256')} for name in spec['documents']}


# --------------------------------------------------------------------------- pin records

def _hash_tree(output_root):
    outputs = {}
    for path in sorted(Path(output_root).rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise Refusal(f'Nonregular output {path}')
        if path.is_file():
            outputs[path.relative_to(output_root).as_posix()] = {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
    return outputs


def make_pin_record(spec, stage, worktree, output_root, previous, *, protocol_sha256, overlay=None, go_sha256=None,
                    port=None, counts=None, training_seed=None):
    output_root, worktree = Path(output_root).resolve(), Path(worktree).resolve()
    outputs = _hash_tree(output_root)
    own = {'producing_commit': spec['commit'], 'worktree': str(worktree), 'output_root': str(output_root), 'outputs': outputs,
           **({} if counts is None else {'counts': counts}),
           **({} if training_seed is None else {'training_seed': training_seed})}
    return {'schema': RECORD_SCHEMA, 'protocol_sha256': protocol_sha256, 'stage': stage, **own,
            'producer_sha256': spec['producer_sha256'], 'go_sha256': go_sha256,
            'previous_record_sha256': None if previous is None else sha256_bytes(canonical(previous)),
            'chain': json.loads(json.dumps({**({} if previous is None else previous['chain']), stage: own})),
            'overlay': overlay, 'qualification_claims': [], **({} if port is None else {'port': port})}


def write_pin_record(path, record):
    path = Path(path)
    with path.open('xb') as stream:
        stream.write(canonical(record)); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def check_pin_record(record, stage, stages, *, protocol_sha256):
    """The previous sub-stage's record, with a consistent cumulative chain; returns the chain."""
    order = list(stages)
    if order.index(stage) == 0: raise Refusal(f'{stage} is the first sub-stage and takes no previous record')
    previous = order[order.index(stage)-1]
    if record.get('schema') != RECORD_SCHEMA: raise Refusal('Pin record schema differs')
    if record.get('protocol_sha256') != protocol_sha256: raise Refusal('Pin record binds another protocol')
    if record.get('stage') != previous: raise Refusal(f'{stage} requires the previous sub-stage ({previous}) pin record')
    if record.get('producing_commit') != stages[previous]['commit']:
        raise Refusal(f'Pin record producing commit differs from {previous}')
    chain = record.get('chain')
    own = {k: record.get(k) for k in ('producing_commit', 'worktree', 'output_root', 'outputs')}
    for key in ('counts', 'training_seed'):
        if key in record: own[key] = record[key]
    if not isinstance(chain, dict) or list(chain) != order[:order.index(stage)] or chain[previous] != own:
        raise Refusal('Pin record chain is incomplete or differs from its own outputs')
    return chain


def merge_controlled(records, stage, stages, *, protocol_sha256):
    """One chain from a controlled stage's ordered producer records plus its controller record."""
    order = list(stages)
    previous = order[order.index(stage)-1]
    rule = CONTROLLED[previous]
    expected = list(rule['seeds']) if rule['seeds'] else [None]
    if len(records) != len(expected):
        raise Refusal(f'{stage} requires exactly {len(expected)} {previous} pin record(s), got {len(records)}')
    chains = [check_pin_record(r, stage, stages, protocol_sha256=protocol_sha256) for r in records]
    seeds = [r.get('training_seed') for r in records]
    if seeds != expected: raise Refusal(f'{previous} pin records must be seeds {expected} in order, got {seeds}')
    prefixes = [{k: v for k, v in c.items() if k != previous} for c in chains]
    if any(p != prefixes[0] for p in prefixes) or \
            len({(r['worktree'], r['producing_commit'], r.get('previous_record_sha256')) for r in records}) != 1:
        raise Refusal(f'{previous} pin records do not share one worktree, commit and previous chain')
    names = [rule['output'].format(seed=s) for s in seeds]
    roots = {Path(r['output_root']).parent for r in records}
    if len(roots) != 1 or [Path(r['output_root']).name for r in records] != names:
        raise Refusal(f'{previous} outputs must be {names} under one stage root')
    root = roots.pop()
    raw = read_bounded(root/CONTROLLER_RECORD)
    controller = json.loads(raw)
    shas = [sha256_bytes(canonical(r)) for r in records]
    if (controller.get('schema') != CONTROLLER_RECORD_SCHEMA or controller.get('stage') != previous or
            controller.get('protocol_sha256') != protocol_sha256 or controller.get('stage_root') != str(root) or
            controller.get('producer_records') != shas):
        raise Refusal(f'{previous} controller record does not bind these producer records and stage root')
    documents = controller.get('documents')
    if not isinstance(documents, dict) or not documents: raise Refusal(f'{previous} controller record binds no documents')
    for rel, item in documents.items():
        path, parts = root/rel, Path(rel).parts
        if Path(rel).is_absolute() or parts[0] != 'control' or '..' in parts or path.is_symlink() or not path.is_file() or \
                path.stat().st_size != item.get('bytes') or sha256_file(path) != item.get('sha256'):
            raise Refusal(f'{previous} controller document differs from its record: {rel}')
    outputs = {f'{name}/{rel}': value for record, name in zip(records, names) for rel, value in record['outputs'].items()}
    own = {'producing_commit': records[0]['producing_commit'], 'worktree': records[0]['worktree'], 'output_root': str(root),
           'outputs': {**outputs, **documents}, 'producer_records': shas, 'controller_record_sha256': sha256_bytes(raw),
           'declared_values': list(controller.get('declared_values', []))}
    if 'counts' in records[0]: own['counts'] = records[0]['counts']
    return {**prefixes[0], previous: own}


def previous_chain(records, stage, stages, *, protocol_sha256):
    """The previous sub-stage's chain: one record, or a controlled stage's ordered set (CONTROLLED)."""
    order = list(stages)
    if order.index(stage) == 0: raise Refusal(f'{stage} is the first sub-stage and takes no previous record')
    if order[order.index(stage)-1] in CONTROLLED:
        return merge_controlled(records, stage, stages, protocol_sha256=protocol_sha256)
    if len(records) != 1: raise Refusal(f'{stage} takes exactly one previous pin record, got {len(records)}')
    return check_pin_record(records[0], stage, stages, protocol_sha256=protocol_sha256)


# --------------------------------------------------------------------------- arguments and GO

def check_arguments(spec, argv, worktree, chain, *, open_inputs):
    """Every producer argument is declared; data inputs must match the pin-record chain."""
    rules, given, index = spec['args'], {}, 0
    while index < len(argv):
        token = argv[index]
        flag, _, inline = token.partition('=')
        if not flag.startswith('--') or flag not in rules or flag in given:
            raise Refusal(f'Refused undeclared argument {token!r}')
        if inline or '=' in token: value = inline
        else:
            if index+1 >= len(argv): raise Refusal(f'{flag} needs a value')
            index += 1; value = argv[index]
        given[flag] = value; index += 1
    missing = [f for f, r in rules.items() if f not in given and not r.get('optional')]
    if missing: raise Refusal('Producer arguments missing: ' + ', '.join(missing))
    checked = {}
    for flag, value in given.items():
        rule, path = rules[flag], Path(value)
        kind = rule['kind']
        if kind == 'value':
            if value not in rule['allowed']: raise Refusal(f'{flag}={value} is not allowed')
            checked[flag] = {'value': value}
        elif kind == 'repo':
            if not under(path, worktree) or path.resolve() != Path(worktree).resolve():
                raise Refusal(f'{flag} must be the producing worktree')
            checked[flag] = {'path': str(path.resolve())}
        elif kind == 'assets':
            if not path.is_dir(): raise Refusal(f'{flag} must be an existing assets directory')
            checked[flag] = {'path': str(path.resolve())}
        elif kind == 'output':
            if path.exists() or path.is_symlink(): raise Refusal(f'{flag} must be a fresh path')
            if any(under(path, record['output_root']) or under(record['output_root'], path) for record in chain.values()):
                raise Refusal(f'{flag} overlaps an earlier pin-record output')
            checked[flag] = {'path': str(path.resolve())}
        elif kind == 'record':
            record = _outputs(chain, rule['stage'], flag)
            relative = path.resolve().relative_to(record['output_root']).as_posix() \
                if under(path, record['output_root']) else None
            if relative not in record['outputs']:
                raise Refusal(f'{flag} is not an output in the previous sub-stage pin record chain ({rule["stage"]})')
            expected = record['outputs'][relative]
            if open_inputs and (path.is_symlink() or path.stat().st_size != expected['bytes'] or
                                sha256_file(path) != expected['sha256']):
                raise Refusal(f'{flag} bytes differ from the {rule["stage"]} pin record')
            checked[flag] = {'path': str(path.resolve()), **expected}
        elif kind == 'fixed-file':
            if open_inputs and (not path.is_file() or sha256_file(path) != rule['sha256']):
                raise Refusal(f'{flag} differs from its pinned bytes')
            checked[flag] = {'path': str(path.resolve()), 'sha256': rule['sha256']}
        else:
            raise Refusal(f'Unknown argument rule {kind}')
    return checked


def check_go(path, stage, protocol_sha256):
    """The GO record must name exactly this stage and the protocol sha256."""
    try: raw = read_bounded(path, MAX_GO); value = json.loads(raw)
    except (OSError, ValueError, Refusal) as error: raise Refusal(f'Unreadable GO record: {error}') from None
    if not isinstance(value, dict) or value.get('decision') != 'GO' or value.get('stage') != stage or \
            value.get('protocol_sha256') != protocol_sha256:
        raise Refusal(f'GO record does not name stage {stage} and protocol {protocol_sha256}')
    return sha256_bytes(raw)


# --------------------------------------------------------------------------- worktree and sources

def verify_worktree(worktree, spec, *, commit=None):
    worktree, commit = Path(worktree), commit or spec['commit']
    head = _git(worktree, 'rev-parse', 'HEAD').stdout.strip()
    if _git(worktree, 'symbolic-ref', '-q', 'HEAD').returncode == 0:
        raise Refusal('Producer worktree must be a detached worktree')
    if head != commit: raise Refusal(f'Worktree HEAD {head or "?"} is not the producing commit {commit}')
    status = _git(worktree, 'status', '--porcelain', '--untracked-files=no')
    if status.returncode != 0 or status.stdout.strip():
        raise Refusal('Producer worktree tracked files differ from the producing commit')
    others = _git(worktree, 'ls-files', '--others', '--', 'src', 'scripts').stdout.split()
    others = [o for o in others if '__pycache__' not in o and not o.endswith('.pyc')]
    if others: raise Refusal('Producer worktree has untracked source files: ' + ', '.join(others[:8]))
    report = {'head': head, 'detached': True}
    if 'producer' in spec:
        if sha256_file(worktree/spec['producer']) != spec['producer_sha256']:
            raise Refusal(f'Pinned producer bytes differ: {spec["producer"]}')
        report['producer_sha256'] = spec['producer_sha256']
        for rel, pin in spec['source_guards'].items():
            if not (worktree/rel).is_file() or sha256_file(worktree/rel) != pin:
                raise Refusal(f'Pinned source guard differs: {rel}')
        report['source_guards'] = dict(spec['source_guards'])
    return report


# --------------------------------------------------------------------------- Amendment 1 port trees

def load_ports(path=PORTS_PATH, protocol_sha256=PROTOCOL_SHA256):
    value = json.loads(read_bounded(path))
    if value.get('schema') != PORTS_SCHEMA or value.get('protocol_sha256') != protocol_sha256 or \
            value.get('locator', {}).get('env') != PORT_LOCATOR_ENV:
        raise Refusal('v4 port manifest does not bind this protocol')
    return value


def port_spec(spec, ports):
    """The stage as run from its port tree: port commit, port bytes, no in-process rebinding.

    H1 hunks read every pin from the locator document instead of rebound attributes, so the
    overlay's rebinds and stale-value scan do not apply; documents are the tree's locator set."""
    tree = ports['trees'][spec['port_tree']]
    if tree['base'] != spec['commit']: raise Refusal(f'{spec["port_tree"]} is not based on the producing commit {spec["commit"]}')
    derived = {**spec, 'commit': tree['port_commit'], 'base_commit': spec['commit'],
               'producer_sha256': spec['port_producer_sha256'],
               'source_guards': {**spec['source_guards'], **spec.get('port_source_guards', {})},
               'documents': list(spec['port_documents']), 'rebinds': [], 'upstream_values': [],
               'port': {'tree': spec['port_tree'], 'branch': tree['branch'], 'base': tree['base'],
                        'locator_values': list(tree.get('locator_values', []))}}
    if 'historical_port_tree' in spec:
        historical = ports['trees'][spec['historical_port_tree']]
        if historical['base'] != spec['historical_commit']:
            raise Refusal(f'{spec["historical_port_tree"]} is not based on {spec["historical_commit"]}')
        derived['historical_commit'] = historical['port_commit']
        derived['port']['historical_tree'] = spec['historical_port_tree']
    return derived


def port_stages(stages, ports):
    return {name: port_spec(spec, ports) if 'port_tree' in spec else spec for name, spec in stages.items()}


def verify_port_tree(worktree, tree_id, ports, *, repo=ROOT):
    """The worktree HEAD must be the expected port branch commit (detached, clean)."""
    tree = ports['trees'][tree_id]
    expected, branch = tree.get('port_commit'), tree['branch']
    if not expected: raise Refusal(f'{tree_id} has no recorded port commit; build the port branches first')
    actual = (_git(repo, 'rev-parse', '--verify', '-q', f'refs/heads/{branch}^{{commit}}').stdout.strip()
              or _git(repo, 'rev-parse', '--verify', '-q',
                      f'refs/remotes/origin/{branch}^{{commit}}').stdout.strip())
    if actual != expected:
        raise Refusal(f'Port branch {branch} is at {actual or "nothing"}, not the recorded port commit {expected}')
    parents = _git(repo, 'rev-list', '--parents', '-n', '1', expected).stdout.split()[1:]
    if parents != [tree['base']]: raise Refusal(f'Port commit {expected} is not a child of the producing commit')
    head = _git(worktree, 'rev-parse', 'HEAD').stdout.strip()
    if head != expected:
        raise Refusal(f'Worktree HEAD {head or "?"} is not the port branch commit {expected} ({branch})')
    report = verify_worktree(worktree, {}, commit=expected)
    return {**report, 'tree': tree_id, 'branch': branch, 'base': tree['base']}


def port_locator(spec, documents, chain):
    """The locator the H1 hunks read: v4 documents (path, sha256) and upstream output pins."""
    value = {'schema': PORT_LOCATOR_SCHEMA, 'documents': {k: dict(v) for k, v in documents.items()}}
    absolute = lambda path: isinstance(path, str) and path != '' and Path(path).is_absolute()
    for name, entry in value['documents'].items():
        if not absolute(entry.get('path')): raise Refusal(f'Locator path for {name} must be absolute: {entry.get("path")!r}')
    for name in spec['port']['locator_values']:
        if name != 'data_manifest': raise Refusal(f'Unknown locator value {name}')
        record = _outputs(chain, 'S0c', 'data_manifest')
        if 'data-manifest.json' not in record['outputs']: raise Refusal('S0c recorded no data-manifest.json')
        value['data_manifest'] = {'path': str(Path(record['output_root'])/'data-manifest.json'),
                                  'sha256': record['outputs']['data-manifest.json']['sha256']}
        if not absolute(record['output_root']): raise Refusal('Locator data_manifest path must be absolute')
    return value


def _module_paths(name):
    parts = name.split('.')
    paths = [f'src/{"/".join(parts)}.py', f'src/{"/".join(parts)}/__init__.py']
    return ([f'scripts/{name}.py'] if len(parts) == 1 else []) + paths


def _resolve(read, name, cache):
    if name not in cache:
        cache[name] = next(((rel, text) for rel in _module_paths(name) if (text := read(rel)) is not None), None)
    return cache[name]


def static_closure(read, start, cache=None, graph=None):
    """Local modules reachable from ``start`` through any import statement: {name: (rel, source)}.

    ``graph`` (optional) receives each module's direct local imports."""
    cache = {} if cache is None else cache
    closure, pending = {}, [start]
    while pending:
        name = pending.pop()
        if name in closure or (found := _resolve(read, name, cache)) is None: continue
        closure[name] = found
        parents = name.split('.')
        edges = ['.'.join(parents[:i]) for i in range(1, len(parents))]
        for target, names, *_ in probe.static_imports(found[1], name, found[0].endswith('__init__.py')):
            edges.append(target); edges += [f'{target}.{n}' for n in names]
        edges = [e for e in edges if _resolve(read, e, cache) is not None]
        if graph is not None: graph[name] = set(edges)
        pending += edges
    return closure


def _reaches(graph, start, targets):
    seen, pending = set(), [start]
    while pending:
        name = pending.pop()
        if name in seen: continue
        if name in targets: return True
        seen.add(name); pending += graph.get(name, ())
    return False


def original_values(spec, read):
    """Pinned values of every rebound attribute at the producing commit, plus upstream pins."""
    values = {}
    for rebind in spec['rebinds']:
        found = _resolve(read, rebind['module'], {})
        if found is None: raise Refusal(f'Rebound module {rebind["module"]} is absent at the producing commit')
        for node in ast.parse(found[1]).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == rebind['attribute'] for t in node.targets) \
                    and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                values[f'{rebind["module"]}.{rebind["attribute"]}'] = node.value.value
        if f'{rebind["module"]}.{rebind["attribute"]}' not in values:
            raise Refusal(f'{rebind["module"]}.{rebind["attribute"]} is not a module-level string pin')
    return values


def _module_level(tree):
    """Statements executed at import (module and class bodies), minus __main__ guards."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
        if isinstance(node, ast.If) and '__name__' in ast.unparse(node.test) and '__main__' in ast.unparse(node.test):
            continue
        if isinstance(node, ast.ClassDef):
            yield from (n for n in node.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            continue
        yield node


def _mentions_file(node, aliases):
    return any((isinstance(n, ast.Name) and (n.id == '__file__' or n.id in aliases)) for n in ast.walk(node))


def static_reachability(read, spec, originals):
    """Read sites that an in-process attribute rebinding would NOT reach; [] means reachable."""
    graph = {}
    closure = static_closure(read, spec['module'], {}, graph)
    rebound = {}
    for key in originals:
        module, _, attribute = key.rpartition('.')
        rebound.setdefault(module, set()).add(attribute)
    pinned = {v: k for k, v in originals.items()} | {v: 'upstream pin' for v in spec.get('upstream_values', [])}
    findings = []
    for name, (rel, source) in sorted(closure.items()):
        tree = ast.parse(source)
        own = rebound.get(name, set())
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in rebound: aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if f'{node.module}.{alias.name}' in rebound: aliases[alias.asname or alias.name] = f'{node.module}.{alias.name}'
                    if node.module in rebound and alias.name in rebound[node.module]:
                        findings.append(f'{name} ({rel}:{node.lineno}) copies rebound pin {node.module}.{alias.name} at import')
        allowed = {id(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id in own for t in node.targets)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in pinned and id(node) not in allowed:
                findings.append(f'{name} ({rel}:{node.lineno}) inline literal of pinned value {pinned[node.value]} '
                                f'({node.value[:16]}...); a rebinding cannot reach it')
        local_defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for statement in _module_level(tree):
            if isinstance(statement, ast.Assign) and id(statement.value) in allowed: continue
            for node in ast.walk(statement):
                hit = (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in own) or \
                      (own and isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in local_defs) or \
                      (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases)
                if hit:
                    findings.append(f'{name} ({rel}:{statement.lineno}) import-time read of a rebound pin '
                                    'happens before any rebinding')
                    break
        file_names = {t.id for n in tree.body if isinstance(n, ast.Assign) and _mentions_file(n.value, set())
                      for t in n.targets if isinstance(t, ast.Name)}
        affected = _reaches(graph, name, set(rebound))
        for node in ast.walk(tree):
            if affected and isinstance(node, (ast.List, ast.Tuple)) and \
                    any(ast.unparse(e) == 'sys.executable' for e in node.elts) and \
                    any(_mentions_file(e, file_names) for e in node.elts):
                findings.append(f'{name} ({rel}:{node.lineno}) re-executes {name} in a child process; '
                                'the in-process overlay does not reach it')
    return sorted(set(findings))


# --------------------------------------------------------------------------- overlay

def overlay_values(spec, pins_dir, documents, chain):
    values = {}
    for rebind in spec['rebinds']:
        key, kind = (rebind['module'], rebind['attribute']), rebind['kind']
        if kind == 'document-path': values[key] = documents[rebind['document']]['path']
        elif kind == 'document-sha256': values[key] = documents[rebind['document']]['sha256']
        elif kind == 'output-sha256':
            outputs = _outputs(chain, rebind['stage'], f'{key}')['outputs']
            if rebind['output'] not in outputs: raise Refusal(f'{rebind["stage"]} recorded no {rebind["output"]}')
            values[key] = outputs[rebind['output']]['sha256']
        else: raise Refusal(f'Unknown rebind kind {kind}')
    return values


def apply_overlay(worktree, spec, values):
    """Import the unchanged closure from ``worktree`` and rebind exactly the declared pins."""
    worktree = Path(worktree).resolve()
    local = probe.local_namespace(worktree)
    preloaded = sorted(n for n in sys.modules if n.partition('.')[0] in local)
    if preloaded: raise Refusal('Producer modules already imported before the overlay: ' + ', '.join(preloaded))
    ours = {str(ROOT/'scripts'), str(ROOT/'src'), ''}
    sys.path[:] = [str(worktree/'scripts'), str(worktree/'src')] + [p for p in sys.path if p not in ours]
    importlib.invalidate_caches()
    order = list(dict.fromkeys([r['module'] for r in spec['rebinds']] + [spec['module']]))
    snapshots, originals, changed, origins = {}, {}, [], {}
    for name in order:
        module = importlib.import_module(name)
        origin = getattr(module, '__file__', None)
        if origin is None or not under(origin, worktree):
            raise Refusal(f'{name} resolves outside the producing worktree: {origin}')
        origins[name] = str(Path(origin).resolve())
        snapshots[name] = dict(vars(module))
        for rebind in (r for r in spec['rebinds'] if r['module'] == name):
            attribute = rebind['attribute']
            if not isinstance(getattr(module, attribute, None), str):
                raise Refusal(f'{name}.{attribute} is not a string pin')
            originals[f'{name}.{attribute}'] = getattr(module, attribute)
            setattr(module, attribute, values[(name, attribute)])
            changed.append(f'{name}.{attribute}')
    for name in order:
        module = sys.modules[name]
        differ = sorted(f'{name}.{k}' for k in vars(module).keys() | snapshots[name].keys()
                        if vars(module).get(k, snapshots) is not snapshots[name].get(k, snapshots))
        if differ != sorted(c for c in changed if c.rpartition('.')[0] == name):
            raise Refusal(f'Overlay changed undeclared attributes of {name}: {differ}')
    stale = set(originals.values()) | set(spec.get('upstream_values', []))
    for name, module in list(sys.modules.items()):
        origin = getattr(module, '__file__', None) if module is not None else None
        if origin is None or not under(origin, worktree): continue
        for attribute, value in list(vars(module).items()):
            if isinstance(value, str) and value in stale and f'{name}.{attribute}' not in changed:
                raise Refusal(f'{name}.{attribute} keeps a stale copy of a rebound pin')
    return sys.modules[spec['module']], {'changed': changed, 'import_order': order, 'origins': origins,
                                         'original_values': originals}


# --------------------------------------------------------------------------- driver

def _split(argv):
    if '--' in argv:
        cut = argv.index('--'); return argv[:cut], argv[cut+1:]
    return argv, []


def _emit(value):
    print(json.dumps(value, indent=1, sort_keys=True))


def prepare(spec, stage, worktree, previous_path, producer_args, *, stages, pins_dir, protocol_sha256,
            historical_worktree, execute, ports=None, repo=ROOT):
    report = {'stage': stage, 'protocol_sha256': protocol_sha256, 'producing_commit': spec['commit'],
              'worktree': str(Path(worktree).resolve()), 'producer': spec['producer'], 'execution': spec['execution']}
    if 'port' in spec:  # Amendment 1: the port tree's HEAD is checked before anything is planned.
        report['port_check'] = verify_port_tree(worktree, spec['port']['tree'], ports, repo=repo)
    report['worktree_check'] = verify_worktree(worktree, spec)
    if 'historical_commit' in spec:
        if historical_worktree is None: raise Refusal(f'{stage} requires --historical-worktree')
        if 'port' in spec:
            report['historical_port_check'] = verify_port_tree(historical_worktree, spec['port']['historical_tree'],
                                                               ports, repo=repo)
        report['historical_check'] = verify_worktree(historical_worktree, {}, commit=spec['historical_commit'])
    previous, chain = None, {}
    paths = [] if previous_path is None else [previous_path] if isinstance(previous_path, (str, Path)) else list(previous_path)
    if paths:
        raws = [read_bounded(path) for path in paths]
        records = [json.loads(raw) for raw in raws]
        chain = previous_chain(records, stage, stages, protocol_sha256=protocol_sha256)
        if len(records) == 1 and chain == records[0].get('chain'):
            previous, report['previous_record_sha256'] = records[0], sha256_bytes(raws[0])
        else:  # a controlled stage: the merged chain stands for its records and controller record
            report['previous_record_sha256'] = [sha256_bytes(raw) for raw in raws]
            previous = {'chain': chain, 'records': report['previous_record_sha256']}
    documents = {}
    if spec['documents']:
        declarations = load_declarations(pins_dir, protocol_sha256)
        documents = load_pin_documents(spec, pins_dir, declarations, worktree, chain)
    report['documents'] = documents
    values = overlay_values(spec, pins_dir, documents, chain)
    read = lambda rel: read_text_or_none(Path(worktree)/rel)
    findings = static_reachability(read, spec, original_values(spec, read)) if spec['rebinds'] else []
    if findings: raise Refusal('Overlay cannot reach every read site: ' + ' | '.join(findings))
    report['rebinds'] = [{**r, 'value': values[(r['module'], r['attribute'])]} for r in spec['rebinds']]
    if 'port' in spec:
        report['locator'] = {'env': PORT_LOCATOR_ENV, 'value': port_locator(spec, documents, chain)}
    report['arguments'] = check_arguments(spec, producer_args, worktree, chain, open_inputs=execute)
    if spec['execution'] == 'subprocess':
        report['would_run'] = [sys.executable, str(Path(worktree).resolve()/spec['producer']), *producer_args]
    else:
        report['would_run'] = ['<in-process overlay>', f'{spec["module"]}.main', *producer_args]
    return report, previous, values


def _run(spec, worktree, values, producer_args, locator_path=None):
    worktree = Path(worktree).resolve()
    if 'port' in spec:  # H1 hunks read the locator, at import time where the original read a literal
        if locator_path is None: raise Refusal('A port stage needs its locator document')
        os.environ[PORT_LOCATOR_ENV] = str(locator_path)
    if spec['execution'] == 'subprocess':
        thread_env = probe.ENTRYPOINTS.get(spec['stage'], {}).get('thread_env', {})
        env = {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/nonexistent'), 'LANG': 'C.UTF-8',
               'MUJOCO_GL': 'egl', 'CUDA_VISIBLE_DEVICES': '', 'PYTHONPATH': f'{worktree/"src"}:{worktree/"scripts"}',
               **thread_env, **({PORT_LOCATOR_ENV: str(locator_path)} if 'port' in spec else {})}
        done = subprocess.run([sys.executable, str(worktree/spec['producer']), *producer_args], cwd=worktree, env=env)
        return done.returncode, None
    module, overlay = apply_overlay(worktree, spec, values)
    if not callable(getattr(module, 'main', None)): raise Refusal(f'{spec["module"]} has no main()')
    os.chdir(worktree); sys.argv = [str(worktree/spec['producer']), *producer_args]
    try: code = module.main()
    except SystemExit as stop: code = stop.code
    overlay = {k: v for k, v in overlay.items() if k != 'original_values'}
    return (0 if code is None else code if isinstance(code, int) else 1), overlay


def main(argv=None, *, stages=None, pins_dir=None, root=None, protocol_sha256=None, ports=None, repo=None):
    stages = STAGES if stages is None else stages
    repo = ROOT if repo is None else Path(repo)
    pins_dir = PINS_DIR if pins_dir is None else Path(pins_dir)
    own, producer_args = _split(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--stage', required=True, choices=list(stages))
    parser.add_argument('--worktree', type=Path, required=True, help='Detached worktree at the producing commit')
    parser.add_argument('--previous-pins', type=Path, nargs='+',
                        help="Previous sub-stage's v4 pin record (after S0d: the seed 10, 11, 12 records in order)")
    parser.add_argument('--historical-worktree', type=Path, help='S0f historical reader worktree (217cbee)')
    parser.add_argument('--plan-only', action='store_true', help='Print the plan; never executes a producer')
    parser.add_argument('--go', type=Path, help='GO record naming this exact stage and the protocol sha256')
    parser.add_argument('--pin-record-out', type=Path, help='Fresh path for the published pin record')
    parser.add_argument('--fill-document', metavar='NAME',
                        help='Fill this v4 copy (consumed by --stage) in place from the --previous-pins records only; no producer')
    args = parser.parse_args(own)
    refused = lambda reason: (_emit({'status': 'refused', 'stage': args.stage, 'reason': reason}), 2)[1]
    if protocol_sha256 is None:
        protocol_sha256 = PROTOCOL_SHA256
        if sha256_file(ROOT/PROTOCOL_PATH) != PROTOCOL_SHA256: return refused('v4 protocol bytes differ from the pin')
    if args.fill_document is not None:
        if args.plan_only or args.go is not None or producer_args: return refused('--fill-document takes no --plan-only, --go or producer arguments')
        try:
            if any('port_tree' in s for s in stages.values()):
                stages = port_stages(stages, load_ports(protocol_sha256=protocol_sha256) if ports is None else ports)
            filled = fill_copy(args.fill_document, args.stage, args.worktree, args.previous_pins or [], pins_dir=pins_dir,
                               protocol_sha256=protocol_sha256, stages=stages)
        except (Refusal, OSError, ValueError, KeyError) as error:
            _emit({'mode': 'fill', 'status': 'refused', 'stage': args.stage,
                   'reason': str(error) if isinstance(error, Refusal) else f'{type(error).__name__}: {error}'})
            return 3
        _emit({'mode': 'fill', 'status': 'filled', 'stage': args.stage, **filled}); return 0
    if args.plan_only and args.go is not None: return refused('--plan-only and --go are mutually exclusive')
    if not args.plan_only and args.go is None:
        return refused('Default is refusal: pass --plan-only, or --go with an owner GO record')
    if any('port_tree' in s for s in stages.values()):
        try:
            ports = load_ports(protocol_sha256=protocol_sha256) if ports is None else ports
            stages = port_stages(stages, ports)
        except (Refusal, OSError, ValueError, KeyError) as error: return refused(f'Port manifest: {error}')
    spec = stages[args.stage]
    first = list(stages).index(args.stage) == 0
    if first != (args.previous_pins is None):
        return refused('The first sub-stage takes no previous record; every later one requires --previous-pins')
    go_sha = None
    if args.go is not None:
        try: go_sha = check_go(args.go, args.stage, protocol_sha256)
        except Refusal as error: return refused(str(error))
        if args.pin_record_out is None or args.pin_record_out.exists():
            return refused('--go requires a fresh --pin-record-out path')
    try:
        plan, previous, values = prepare(spec, args.stage, args.worktree, args.previous_pins, producer_args,
                                         stages=stages, pins_dir=pins_dir, protocol_sha256=protocol_sha256,
                                         historical_worktree=args.historical_worktree, execute=not args.plan_only,
                                         ports=ports, repo=repo)
    except (Refusal, OSError, ValueError, KeyError) as error:
        _emit({'mode': 'plan-only' if args.plan_only else 'go', 'status': 'refused', 'stage': args.stage,
               'reason': f'{type(error).__name__}: {error}' if not isinstance(error, Refusal) else str(error)})
        return 3
    if args.plan_only:
        _emit({'mode': 'plan-only', 'status': 'admissible', **plan}); return 0
    port = None
    if 'port' in spec:
        locator_path = args.pin_record_out.with_name(args.pin_record_out.name + '.port-pins.json')
        payload = canonical(plan['locator']['value'])
        with locator_path.open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        port = {'tree': spec['port']['tree'], 'branch': spec['port']['branch'], 'head': spec['commit'],
                'base_commit': spec['base_commit'], 'locator_path': str(locator_path.resolve()),
                'locator_sha256': sha256_bytes(payload)}
    code, overlay = _run(spec, args.worktree, values, producer_args, None if port is None else port['locator_path'])
    output = plan['arguments'].get('--output', {}).get('path')
    if code != 0 or output is None:
        _emit({'mode': 'go', 'status': 'producer-failed', 'stage': args.stage, 'returncode': code}); return 1
    verify_worktree(args.worktree, spec)
    try: counts = stage_counts(spec['records_counts'], output) if 'records_counts' in spec else None
    except (Refusal, OSError, ValueError, KeyError, TypeError) as error:
        _emit({'mode': 'go', 'status': 'record-refused', 'stage': args.stage, 'reason': str(error)}); return 1
    seed = plan['arguments'].get('--training-seed', {}).get('value')
    record = make_pin_record(spec, args.stage, args.worktree, output, previous, protocol_sha256=protocol_sha256,
                             overlay=overlay, go_sha256=go_sha, port=port, counts=counts,
                             training_seed=None if seed is None else int(seed))
    write_pin_record(args.pin_record_out, record)
    _emit({'mode': 'go', 'status': 'completed', 'stage': args.stage, 'pin_record': str(args.pin_record_out),
           'outputs': len(record['outputs'])})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
