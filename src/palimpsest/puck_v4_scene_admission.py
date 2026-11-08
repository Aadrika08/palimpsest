"""Puck v4 stage S1: scene-ID collision admission over declared comparison roots.

ID comparison only. Given the hash-pinned v4 protocol and an explicit
comparison-set declaration, prove that the fresh collection (6510-6513) and
development (6520-6523) IDs do not occur as typed scene fields anywhere outside
v4's own lineage (matched by content sha256, never by path), record S0a/S0d
intentional reuse of 6000-6019 / 6100-6103, and record (never scan, never treat
as clean) the frozen lost ``brain`` root.

Default is plan-only: root file contents are not read and nothing is written;
only directory/Git metadata (stat, worktree list, refs, advertised OIDs) is
inspected. Executing requires a GO record naming stage and scope ``S1`` and the
protocol sha256, and consumes the single S1 attempt by writing a durable receipt
before the first content read. Roots that may hold authored held-out 6200-6207
payloads need a separate D2 GO record with scope ``S1``.

Held-out payload values are never parsed into the report, compared with each
other or with new scenes, loaded, or executed. They ARE read as bytes: the
per-root content digests hash every scanned file, including any task-v5 copies
holding authored 6200-6207 rows. No simulator, model, Torch, MuJoCo, or scene
minter is imported.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time

from .puck_scene_markdown import parse_puck_markdown_document

PROTOCOL_SHA256 = 'f885fc8d857cc47ec696ad65501b70ac80e16dfa5439fd5bf62919f868bc286b'
COMPANION_SHA256 = 'ed9c1c9d5b39ef9864faa9589c53248beeece650cc762e006182aa37c64ebd84'
# Every v4 protocol/companion version reachable from 70874e2 (drafts at 745bfc5).
LINEAGE_SHA256 = {
    PROTOCOL_SHA256: 'v4 protocol JSON (frozen, 8dc8141)',
    COMPANION_SHA256: 'v4 companion Markdown (frozen, 8dc8141)',
    'e52c3c5f44559564a06d790877f0a4f2230e812a7d8e0999691c4a6cc44958ed': 'v4 protocol draft 745bfc5',
    '68454591e01ad64b3b46a26172d3f736b0f824cea034641d737a5a243255a2b3': 'v4 companion draft 745bfc5',
}
PROTOCOL_ID = 'M6-PUCK-NAV-V4-REGENERATED-ON-POLICY-RELABEL-1'
PROTOCOL_RELATIVE_PATH = (
    'docs/plans/m6-puck-navigation-v4-regenerated-on-policy-relabeling-protocol.json')
COMPANION_RELATIVE_PATH = 'docs/plans/m6-puck-navigation-v4-regenerated-on-policy-relabeling.md'
COLLECTION_SCENE_IDS = (6510, 6511, 6512, 6513)
DEVELOPMENT_SCENE_IDS = (6520, 6521, 6522, 6523)
NEW_SCENE_IDS = COLLECTION_SCENE_IDS + DEVELOPMENT_SCENE_IDS
INTENTIONAL_REUSE = {'S0a': tuple(range(6000, 6020)), 'S0d': (6100, 6101, 6102, 6103)}
HELD_OUT_SCENE_IDS = tuple(range(6200, 6208))
MAX_HISTORICAL_PUCK_ID = 6207
PUCK_NAMESPACE = (6000, 6999)
S1_GO_STAGE = 'S1'
HELD_OUT_GO_STAGE = 'D2-heldout-pure-comparison'
GO_KIND = 'puck-v4-stage-go-v1'
DECLARATION_KIND = 'puck-v4-s1-comparison-set-v1'
REPORT_KIND = 'puck-v4-s1-scene-id-admission-report-v1'
RECEIPT_KIND = 'puck-v4-s1-attempt-receipt-v1'
ATTEMPT_RECEIPT_NAME = 'S1.attempt.json'
DEFAULT_ATTEMPT_LEDGER = (
    '/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-attempt-ledger')
TYPED_SUFFIXES = ('.json', '.jsonl', '.md')
RAW_SUFFIXES = ('.yaml', '.yml', '.toml', '.csv', '.txt')
SCANNED_SUFFIXES = TYPED_SUFFIXES + RAW_SUFFIXES
MAX_FILE_BYTES = 256 * 1024 ** 2
MAX_SMALL_INPUT_BYTES = 4 * 1024 ** 2
MAX_OUTPUT_BYTES = 64 * 1024 ** 2  # protocol S1 output_cap_bytes 67108864
MAX_RANGE = 4096
GIT = '/usr/bin/git'
_REPO = Path(__file__).resolve().parents[2]
SOURCE_FILES = ('src/palimpsest/__init__.py',
                'src/palimpsest/puck_v4_scene_admission.py',
                'src/palimpsest/puck_scene_markdown.py',
                'scripts/admit_puck_v4_scene_ids.py')
SUPERSEDED_PROTOCOL_STATE = 'prospective-docs-only; no source or numerical execution authorized'
THROUGHPUT_BLOCKER_FRACTION = 0.8
EXECUTION_REQUIREMENTS = (
    'No other process may write in any declared root (or the attempt ledger) during '
    'execute; the inventory change check refuses, it does not tolerate, concurrent writes.',
    'The launcher keeps its logs and any temporary files outside every declared root.',
    'Run Python with -B (no bytecode writes into the source tree); execute refuses otherwise.',
    'Execute only the reviewed declaration: rebuild with build_puck_v4_s1_comparison_set.py '
    '--compare-manifest <reviewed> immediately before execute.',
)
PREFILTER_RESIDUAL = (
    'Files are parsed only if their raw bytes contain a decimal 6xxx token (leading zeros '
    'allowed), any exponent-form number, or a numeric range whose bounds could cover '
    '6000-6999. Undetectable residual: IDs written only via JSON \\u escapes, non-ASCII '
    'digits, words, arithmetic, or split across lines.')

_SCENE_TOKENS = {'scene', 'scenes', 'layout', 'layouts', 'seed', 'seeds', 'roster', 'rosters',
                 'split', 'splits', 'reservation', 'reservations', 'collection',
                 'development', 'heldout'}
_OTHER_SEED_TOKENS = {'model', 'training', 'rng', 'random', 'environment'}
_NON_SCENE_TOKENS = {'byte', 'bytes', 'count', 'counts', 'size', 'seconds', 'ticks', 'rows',
                     'sha256', 'hash', 'epochs', 'owners', 'steps', 'wall', 'cpu', 'usec'}
_ID_KEYS = {'scene_id', 'scene', 'seed', 'layout_id', 'layout_seed', 'scene_seed', 'id'}
_GEOMETRY_KEYS = {'rover_pose', 'puck_xy', 'goal_xy', 'initial_qvel', 'layout', 'geometry',
                  'puck_pose', 'goal_pose'}
_DASHES = '-‐‑‒–—―−'
_TOKEN = re.compile(r'(?<![0-9A-Za-z_.])(\d{1,7})(?![0-9A-Za-z_])')
_RANGE = re.compile(r'(?<![0-9A-Za-z_.])(\d{1,7})\s*(?:[' + _DASHES + r']|\.\.)\s*(\d{1,7})'
                    r'(?![0-9A-Za-z_])')
_GO_FIELDS = {'kind', 'version', 'stage', 'scope', 'protocol_sha256', 'granted_by',
              'granted_at'}
_GO_OPTIONAL = {'supersedes_protocol_state'}
_ROOT_FIELDS = {'directory': {'name', 'kind', 'path', 'exclude', 'held_out_payloads',
                              'lost_root_clone'},
                'git': {'name', 'kind', 'path', 'advertisement', 'held_out_payloads'}}


class AdmissionRefused(Exception):
    """S1 cannot proceed; nothing usable was published."""


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8') + b'\n'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _strict_json(raw, label):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('nonfinite number')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise AdmissionRefused(f'{label}: strict JSON required ({error})') from error


def _read_small(path, label):
    path = Path(path)
    try:
        info = os.lstat(path)
    except OSError as error:
        raise AdmissionRefused(f'{label} is missing: {path}') from error
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SMALL_INPUT_BYTES:
        raise AdmissionRefused(f'{label} must be a regular, non-symlinked, bounded file: {path}')
    return path.read_bytes()


def _canonical_path(value, label):
    if (type(value) is not str or not value.startswith('/') or value.startswith('//')
            or value != str(PurePosixPath(value))
            or any(part in ('.', '..') for part in value.split('/'))):
        raise AdmissionRefused(f'{label} must be a canonical absolute path')
    return value


def _under(path, root):
    return path == root or root == '/' or path.startswith(root.rstrip('/') + '/')


def _excluded(path, root):
    return next((row for row in root['exclude'] if _under(path, row['path'])), None)


def _covered(path, directories):
    """A path is covered when a directory root contains it outside that root's exclusions."""
    return any(_under(path, root['path']) and _excluded(path, root) is None
               for root in directories)


# Protocol ------------------------------------------------------------------------

def _id_range(text, label):
    match = re.fullmatch(r'(\d+)-(\d+)', text)
    if not match or int(match[1]) > int(match[2]):
        raise AdmissionRefused(f'{label}: decimal range required')
    return tuple(range(int(match[1]), int(match[2]) + 1))


def derive_roster(protocol):
    """Cross-check the protocol's scene declarations against the frozen v4 roster."""
    try:
        reservations = protocol['scene_reservations']
        contamination = protocol['contamination_admission_before_mint']
        stage0 = protocol['stage_0_regeneration']
        choices = protocol['owner_decisions_resolution']['choices']
    except (KeyError, TypeError) as error:
        raise AdmissionRefused(f'protocol is missing S1 fields: {error}') from error
    if protocol.get('id') != PROTOCOL_ID or contamination.get('stage') != 'S1':
        raise AdmissionRefused('protocol id or S1 stage differs')
    if tuple(reservations.get('collection', ())) != COLLECTION_SCENE_IDS:
        raise AdmissionRefused('protocol collection IDs differ from frozen 6510-6513')
    if tuple(reservations.get('development', ())) != DEVELOPMENT_SCENE_IDS:
        raise AdmissionRefused('protocol development IDs differ from frozen 6520-6523')
    exceptions = contamination.get('intentional_reuse_exceptions')
    if type(exceptions) is not dict or set(exceptions) != {'6000-6019', '6100-6103'}:
        raise AdmissionRefused('intentional reuse exceptions differ from S0a/S0d declaration')
    declared = {key: _id_range(key, 'intentional reuse') for key in exceptions}
    s0a = (_id_range(stage0['S0a']['train_scenes'], 'S0a train')
           + _id_range(stage0['S0a']['recorded_dev_scenes'], 'S0a recorded-dev'))
    if declared['6000-6019'] != s0a or s0a != INTENTIONAL_REUSE['S0a']:
        raise AdmissionRefused('intentional reuse 6000-6019 differs from S0a splits')
    if (declared['6100-6103'] != INTENTIONAL_REUSE['S0d']
            or '6100-6103' not in stage0['S0d'].get('justification', '')):
        raise AdmissionRefused('intentional reuse 6100-6103 differs from S0d')
    held_out = tuple(reservations['held_out_options']['authored_task_v5_never_run'])
    if (held_out != HELD_OUT_SCENE_IDS
            or not str(choices.get('D1_heldout_roster', '')).startswith('authored 6200-6207')):
        raise AdmissionRefused('D1 held-out roster differs from authored 6200-6207')
    if not str(choices.get('D2_heldout_read_scope', '')).startswith('executing or loading'):
        raise AdmissionRefused('D2 held-out read scope differs')
    if choices.get('D9_order') != 'S1 before S0':
        raise AdmissionRefused('D9 order differs from S1 before S0')
    if (reservations.get('max_historical_puck_id') != MAX_HISTORICAL_PUCK_ID
            or min(NEW_SCENE_IDS) <= MAX_HISTORICAL_PUCK_ID):
        raise AdmissionRefused('max historical puck ID premise differs')
    reuse = set().union(*INTENTIONAL_REUSE.values())
    if set(NEW_SCENE_IDS) & (reuse | set(HELD_OUT_SCENE_IDS)):
        raise AdmissionRefused('new IDs overlap intentional reuse or held-out IDs')
    return {
        'new_scene_ids': list(NEW_SCENE_IDS),
        'collection': list(COLLECTION_SCENE_IDS),
        'development': list(DEVELOPMENT_SCENE_IDS),
        'intentional_reuse': {stage: list(ids) for stage, ids in INTENTIONAL_REUSE.items()},
        'held_out_authored': list(HELD_OUT_SCENE_IDS),
        'max_historical_puck_id': MAX_HISTORICAL_PUCK_ID,
    }


def lost_root_from_protocol(protocol):
    exception = protocol['contamination_admission_before_mint']['lost_root_exception']
    return _canonical_path(exception['root'].split(' (', 1)[0], 'lost root')


def _load_protocol(path):
    raw = _read_small(path, 'protocol')
    if _sha(raw) != PROTOCOL_SHA256:
        raise AdmissionRefused(f'protocol sha256 {_sha(raw)} differs from frozen {PROTOCOL_SHA256}')
    protocol = _strict_json(raw, 'protocol')
    return raw, protocol, derive_roster(protocol)


# Declarations and GO records -----------------------------------------------------

def _reason_rows(rows, label):
    if type(rows) is not list:
        raise AdmissionRefused(f'{label} must be a list')
    for row in rows:
        if (type(row) is not dict or set(row) != {'path', 'reason'}
                or type(row['reason']) is not str or not row['reason'].strip()):
            raise AdmissionRefused(f'{label} rows need path and nonempty reason')
        _canonical_path(row['path'], label)
    return rows


def _load_declaration(path):
    raw = _read_small(path, 'comparison set')
    document = _strict_json(raw, 'comparison set')
    if (type(document) is not dict or set(document) != {'kind', 'version', 'roots', 'unscanned'}
            or document['kind'] != DECLARATION_KIND or document['version'] != 1
            or type(document['roots']) is not list):
        raise AdmissionRefused('comparison set requires the exact v1 schema')
    names, directories = set(), []
    for root in document['roots']:
        if type(root) is not dict or root.get('kind') not in _ROOT_FIELDS:
            raise AdmissionRefused('comparison root kind must be directory or git')
        if set(root) != _ROOT_FIELDS[root['kind']]:
            raise AdmissionRefused(f'comparison root {root.get("name")!r} has wrong fields')
        if type(root['name']) is not str or not root['name'] or root['name'] in names:
            raise AdmissionRefused('comparison root names must be unique nonempty text')
        names.add(root['name'])
        _canonical_path(root['path'], f'root {root["name"]} path')
        if type(root['held_out_payloads']) is not bool:
            raise AdmissionRefused('held_out_payloads must be boolean')
        if root['kind'] == 'directory':
            if type(root['lost_root_clone']) is not bool:
                raise AdmissionRefused('lost_root_clone must be boolean')
            for row in _reason_rows(root['exclude'], 'exclusion'):
                if not _under(row['path'], root['path']) or row['path'] == root['path']:
                    raise AdmissionRefused('exclusions must lie strictly below their root')
            directories.append(root)
        elif root['advertisement'] is not None:
            _canonical_path(root['advertisement'], 'advertisement')
    for index, root in enumerate(directories):
        for other in directories[:index]:
            outer, inner = (other, root) if _under(root['path'], other['path']) else (root, other)
            if not _under(inner['path'], outer['path']):
                continue
            if inner['path'] == outer['path'] or _excluded(inner['path'], outer) is None:
                raise AdmissionRefused(f'directory roots overlap: {inner["name"]} lies in '
                                       f'{outer["name"]} outside its exclusions')
    for row in _reason_rows(document['unscanned'], 'unscanned'):
        if any(_under(row['path'], root['path']) or _under(root['path'], row['path'])
               for root in document['roots']):
            raise AdmissionRefused(f'unscanned path overlaps a comparison root: {row["path"]}')
    return raw, document


def _load_go(path, stage, label, protocol_state):
    if path is None:
        raise AdmissionRefused(f'{label} required: stage {stage!r} GO record is missing')
    raw = _read_small(path, label)
    record = _strict_json(raw, label)
    if (type(record) is not dict or not _GO_FIELDS <= set(record)
            or set(record) - _GO_FIELDS - _GO_OPTIONAL):
        raise AdmissionRefused(f'{label} requires exactly fields {sorted(_GO_FIELDS)} '
                               f'(optional {sorted(_GO_OPTIONAL)})')
    if record['kind'] != GO_KIND or record['version'] != 1:
        raise AdmissionRefused(f'{label} kind/version differs')
    if record['stage'] != stage:
        raise AdmissionRefused(f'{label} names stage {record["stage"]!r}, not {stage!r}')
    if record['scope'] != S1_GO_STAGE:
        raise AdmissionRefused(f'{label} scope {record["scope"]!r} is not S1; it cannot be '
                               'reused for another stage')
    if record['protocol_sha256'] != PROTOCOL_SHA256:
        raise AdmissionRefused(f'{label} protocol_sha256 differs from {PROTOCOL_SHA256}')
    if any(type(record[key]) is not str or not record[key].strip()
           for key in ('granted_by', 'granted_at')):
        raise AdmissionRefused(f'{label} needs granted_by and granted_at text')
    supersedes = 'supersedes_protocol_state' in record
    if supersedes and (stage != S1_GO_STAGE
                       or record['supersedes_protocol_state'] != SUPERSEDED_PROTOCOL_STATE
                       or protocol_state != SUPERSEDED_PROTOCOL_STATE):
        raise AdmissionRefused(f'{label} may supersede only the exact protocol state, '
                               'and only in the S1 GO')
    return raw, {'path': str(path), 'sha256': _sha(raw),
                 **({'supersedes_protocol_state_for_s1': supersedes}
                    if stage == S1_GO_STAGE else {})}


# Git metadata ---------------------------------------------------------------------

def _git(repo, *args, stdin=None):
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
           'HOME': os.environ.get('HOME', '/nonexistent'), 'GIT_OPTIONAL_LOCKS': '0'}
    result = subprocess.run([GIT, '-C', repo, *args], input=stdin, env=env,
                            capture_output=True, check=False)
    if result.returncode != 0:
        raise AdmissionRefused(f'git {" ".join(args[:2])} failed in {repo}: '
                               f'{result.stderr.decode(errors="replace").strip()}')
    return result.stdout


def _git_refs(repo):
    refs = {}
    for line in _git(repo, 'for-each-ref', '--format=%(refname)%00%(objectname)').splitlines():
        name, oid = line.decode().split('\0')
        refs[name] = oid
    return refs


def _git_worktrees(repo):
    rows, current = [], {}
    for line in _git(repo, 'worktree', 'list', '--porcelain').decode().splitlines() + ['']:
        if not line:
            if current:
                rows.append(current)
            current = {}
        else:
            key, _, value = line.partition(' ')
            current[key] = value
    return rows


def _object_present(repo, oid):
    return subprocess.run([GIT, '-C', repo, 'cat-file', '-e', oid + '^{object}'],
                          capture_output=True, env={'PATH': '/usr/bin:/bin'}).returncode == 0


def _git_wanted(repo, tips):
    listing = _git(repo, 'rev-list', '--objects', '--stdin',
                   stdin=''.join(tip + '\n' for tip in tips).encode())
    wanted = {}
    for line in listing.decode('utf-8', errors='surrogateescape').splitlines():
        oid, _, path = line.partition(' ')
        if path.endswith(SCANNED_SUFFIXES) and oid not in wanted:
            wanted[oid] = path
    return wanted


def _git_blob_sizes(repo, tips):
    """Object headers only: [(path, oid, size)] for scanned-suffix blobs."""
    wanted = _git_wanted(repo, tips)
    if not wanted:
        return []
    check = _git(repo, 'cat-file', '--batch-check',
                 stdin=''.join(o + '\n' for o in sorted(wanted)).encode())
    rows = []
    for line in check.decode().splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] == 'missing':
            raise AdmissionRefused(f'git object {parts[0]} is missing: incomplete history')
        if parts[1] == 'blob':
            rows.append((wanted[parts[0]], parts[0], int(parts[2])))
    return rows


def _git_blobs(repo, tips):
    wanted = _git_wanted(repo, tips)
    if not wanted:
        return []
    oids = sorted(wanted)
    batch = _git(repo, 'cat-file', '--batch', stdin=''.join(o + '\n' for o in oids).encode())
    blobs, offset = [], 0
    for oid in oids:
        end = batch.index(b'\n', offset)
        header = batch[offset:end].decode().split()
        if header[0] != oid or header[1] == 'missing':
            raise AdmissionRefused(f'git object {oid} ({wanted[oid]}) is missing: '
                                   'incomplete history')
        size = int(header[2])
        if header[1] == 'blob':
            if size > MAX_FILE_BYTES:
                raise AdmissionRefused(f'git blob {oid} exceeds {MAX_FILE_BYTES} bytes')
            blobs.append((wanted[oid], oid, batch[end + 1:end + 1 + size]))
        offset = end + 1 + size + 1
    return blobs


def _git_preflight(root, directories, lost_root):
    """Metadata-only checks shared by plan and execute; returns (record, blockers)."""
    repo, blockers = root['path'], []
    refs = _git_refs(repo)
    tips = set(refs.values())
    covered, excluded, lost = [], [], []
    for row in _git_worktrees(repo):
        path = row['worktree']
        if _under(path, lost_root):
            lost.append(path)
            continue
        if not os.path.isdir(path):
            blockers.append(f'git worktree is missing: {path}')
        elif _covered(path, directories):
            covered.append(path)
        elif any(_under(path, d['path']) and _excluded(path, d) for d in directories):
            excluded.append(path)
        else:
            blockers.append(f'git worktree not covered by a directory root or exclusion: {path}')
        if 'HEAD' in row:
            tips.add(row['HEAD'])
    remotes = _git(repo, 'remote').decode().split()
    advert_sha = None
    if remotes and root['advertisement'] is None:
        blockers.append(f'git root {root["name"]} has remotes {remotes} but no fresh '
                        'remote advertisement')
    if root['advertisement'] is not None:
        try:
            advert = _read_small(root['advertisement'], 'remote advertisement')
        except AdmissionRefused as error:
            blockers.append(str(error))
            advert = b''
        advert_sha = _sha(advert) if advert else None
        if not advert.strip() and os.path.isfile(root['advertisement']):
            blockers.append(f'remote advertisement for {root["name"]} is empty')
        for line in advert.decode(errors='replace').splitlines():
            oid = line.split('\t')[0].strip()
            if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', oid):
                blockers.append(f'remote advertisement line is malformed: {line[:80]!r}')
            elif not _object_present(repo, oid):
                blockers.append(f'remote advertisement names {oid} absent locally: '
                                'stale inventory')
            else:
                tips.add(oid)
    record = {'name': root['name'], 'kind': 'git', 'path': repo,
              'held_out_payloads': root['held_out_payloads'], 'refs': refs,
              'scanned_tips': sorted(tips), 'worktrees_covered': sorted(covered),
              'worktrees_excluded': sorted(excluded), 'remotes': sorted(remotes),
              'advertisement_sha256': advert_sha}
    return record, sorted(lost), blockers


def _gitfile_target(path):
    try:
        text = Path(path).read_text(errors='replace')[:4096]
    except OSError:
        return None
    match = re.match(r'gitdir:\s*(\S.*?)\s*$', text, re.M)
    if not match:
        return None
    return os.path.normpath(os.path.join(os.path.dirname(path), match[1]))


# Root preflight ------------------------------------------------------------------

def _root_problems(root, lost_root):
    path = root['path']
    if _under(path, lost_root):
        return [f'root {root["name"]} lies in the frozen lost root {lost_root}; '
                'excluded by name and never scanned']
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return [f'root {root["name"]} is missing: {path}']
    if stat.S_ISLNK(info.st_mode):
        return [f'root {root["name"]} is a symlink: {path}']
    if not stat.S_ISDIR(info.st_mode):
        return [f'root {root["name"]} is not a directory: {path}']
    if root['kind'] == 'git' and not os.path.exists(os.path.join(path, '.git')):
        return [f'git root {root["name"]} has no .git: {path}']
    return []


def _clone_problems(root, lost_root):
    """Top-level gitfile of a directory root pointing into the lost root."""
    gitfile = os.path.join(root['path'], '.git')
    target = _gitfile_target(gitfile) if os.path.isfile(gitfile) else None
    clone = target is not None and _under(target, lost_root)
    row = {'root': root['name'], 'path': root['path'], 'gitdir': target} if clone else None
    if clone and not root['lost_root_clone']:
        return row, [f'root {root["name"]} is a clone of the lost root; declare it '
                     'lost_root_clone under the lost-root exception']
    if root['lost_root_clone'] and not clone:
        return row, [f'root {root["name"]} is declared lost_root_clone but its gitfile does '
                     'not point into the lost root']
    return row, []


def _lost_root_record(protocol, lost_root, derived):
    exception = protocol['contamination_admission_before_mint']['lost_root_exception']
    present = os.path.lexists(lost_root)
    return {
        'path': lost_root, 'derived_from_protocol': derived,
        'status': 'present-refused' if present else 'absent-recorded-not-scanned',
        'treated_as_clean': False, 'treatment': exception['treatment'],
        'risk': exception['risk'], 'mitigation': exception['mitigation'],
    }


# Typed scene-field extraction ---------------------------------------------------

def _tokens(key):
    tokens = set(re.split(r'[^a-z0-9]+', key.lower())) - {''}
    if {'held', 'out'} <= tokens:
        tokens.add('heldout')
    return tokens


def _key_is_scene(key):
    tokens = _tokens(key)
    return bool(tokens & _SCENE_TOKENS) and not tokens & (_OTHER_SEED_TOKENS | _NON_SCENE_TOKENS)


def _key_is_non_scene(key):
    return bool(_tokens(key) & (_NON_SCENE_TOKENS | _OTHER_SEED_TOKENS))


def _ids_in_text(text):
    found, spans = [], []
    for match in _RANGE.finditer(text):
        low, high = int(match[1]), int(match[2])
        if low <= high and high - low <= MAX_RANGE:
            found.extend(range(low, high + 1))
            spans.append(match.span())
    for match in _TOKEN.finditer(text):
        if not any(start <= match.start() < end for start, end in spans):
            found.append(int(match[1]))
    return found


def _raw_new_ids(raw):
    """New IDs mentioned anywhere in raw bytes, with ranges and all dash forms expanded."""
    return set(_ids_in_text(raw.decode('utf-8', errors='replace'))) & set(NEW_SCENE_IDS)


def _escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def _walk(value, pointer, typed, occurrences, held_out_payloads):
    if type(value) is dict:
        geometry = bool(_GEOMETRY_KEYS & set(value))
        ids = [value[key] for key in value if key in _ID_KEYS]
        if geometry and any(type(item) is int and item in HELD_OUT_SCENE_IDS for item in ids):
            held_out_payloads.append((pointer, next(
                item for item in ids if type(item) is int and item in HELD_OUT_SCENE_IDS)))
        for key, child in value.items():
            child_pointer = pointer + '/' + _escape(key)
            child_geometry = type(child) is dict and bool(_GEOMETRY_KEYS & set(child))
            if re.fullmatch(r'\d{1,7}', key) and (typed or child_geometry):
                # A numeric key is a scene ID in typed context, or when it maps to geometry.
                occurrences.append((child_pointer, int(key)))
                if child_geometry and int(key) in HELD_OUT_SCENE_IDS:
                    held_out_payloads.append((child_pointer, int(key)))
            child_typed = (typed or _key_is_scene(key)) and not _key_is_non_scene(key)
            if geometry and key in _ID_KEYS:
                child_typed = True  # bare id beside geometry is a scene identity
            if key in _GEOMETRY_KEYS:
                child_typed = False  # geometry values are never scene IDs nor compared
            _walk(child, child_pointer, child_typed, occurrences, held_out_payloads)
    elif type(value) is list:
        for index, child in enumerate(value):
            _walk(child, f'{pointer}/{index}', typed, occurrences, held_out_payloads)
    elif typed and type(value) is int:
        occurrences.append((pointer, value))
    elif typed and type(value) is float and math.isfinite(value) and value.is_integer():
        occurrences.append((pointer, int(value)))  # e.g. 6510.0 or 6.51e3
    elif typed and type(value) is str:
        occurrences.extend((pointer, item) for item in _ids_in_text(value))


def _raw_only_hits(relative, raw):
    """Classify new-ID hits in untyped formats: (ambiguous_ids, non_scene_ids)."""
    text = raw.decode('utf-8', errors='replace')
    ambiguous, non_scene = set(), set()
    if relative.endswith('.csv'):
        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error:
            return set(_ids_in_text(text)) & set(NEW_SCENE_IDS), set()  # raw-scan only
        header = rows[0] if rows else []
        for number, row in enumerate(rows):
            for column, cell in enumerate(row):
                hits = set(_ids_in_text(cell)) & set(NEW_SCENE_IDS)
                name = header[column] if number and column < len(header) else ''
                typed_non_scene = bool(name) and _key_is_non_scene(name) \
                    and not _key_is_scene(name)
                (non_scene if typed_non_scene else ambiguous).update(hits)
        return ambiguous, non_scene
    for line in text.splitlines():
        hits = set(_ids_in_text(line)) & set(NEW_SCENE_IDS)
        if not hits:
            continue
        match = None if relative.endswith('.txt') else re.match(
            r'\s*"?([A-Za-z0-9_.\- ]+?)"?\s*[:=]\s*[^:=]*$', line)
        if match and _key_is_non_scene(match[1]) and not _key_is_scene(match[1]):
            non_scene.update(hits)
        else:
            ambiguous.update(hits)
    return ambiguous, non_scene


def _parse_document(relative, raw):
    """Return (occurrences, held_out_payload_objects, unsupported_texts) or None if unparsed."""
    occurrences, held_out, unsupported = [], [], []
    try:
        if relative.endswith('.md'):
            result = parse_puck_markdown_document(raw)
            occurrences = [(row['pointer'], row['scene_id']) for row in result['mentions']]
            unsupported = [row['text'] for row in result['unsupported_declarations']]
        elif relative.endswith('.jsonl'):
            for number, line in enumerate(raw.split(b'\n'), 1):
                if line.strip():
                    _walk(_strict_json(line, 'jsonl'), f'/lines/{number}', False,
                          occurrences, held_out)
        else:
            _walk(_strict_json(raw, 'json'), '', False, occurrences, held_out)
    except (ValueError, AdmissionRefused, RecursionError):
        return None
    return occurrences, held_out, unsupported


# The prefilter mirrors the detector exactly, never more broadly than needed:
#   * _TOKEN tokens (same lookarounds, same Unicode \d) whose value is in 6000-6999;
#     on ASCII text that is exactly a maximal digit run 0{0,3}6ddd;
#   * _RANGE ranges (same regex) whose bounds could cover 6000-6999;
#   * JSON numbers that json parses to an integral float in 6000-6999: exponent
#     forms (6.51e3, 651e1) and decimals rounding up from 5999.x (6xxx.y is a token);
#   * the same three checks after decoding \uXXXX escapes, when any are present.
_PRE_TOKEN_ASCII = re.compile(r'(?<![0-9A-Za-z_.])0{0,3}6[0-9]{3}(?![0-9A-Za-z_])')
_PRE_FLOAT = re.compile(r'(?<![0-9A-Za-z_.])[-+]?(?:[0-9]+(?:\.[0-9]+)?[eE][+-]?[0-9]+'
                        r'|0*5999\.[0-9]+)')
_UNICODE_ESCAPE = re.compile(r'\\u([0-9a-fA-F]{4})')


def _in_namespace(value):
    return PUCK_NAMESPACE[0] <= value <= PUCK_NAMESPACE[1]


def _prefilter_text(text):
    if text.isascii():
        if _PRE_TOKEN_ASCII.search(text):
            return True
    elif any(_in_namespace(int(match[1])) for match in _TOKEN.finditer(text)):
        return True
    for match in _PRE_FLOAT.finditer(text):
        try:
            value = float(match[0])
        except (ValueError, OverflowError):
            continue
        if math.isfinite(value) and value.is_integer() and _in_namespace(value):
            return True
    for match in _RANGE.finditer(text):
        low, high = int(match[1]), int(match[2])
        if (low <= high and high - low <= MAX_RANGE
                and low <= PUCK_NAMESPACE[1] and high >= PUCK_NAMESPACE[0]):
            return True
    return False


def prefilter_hit(raw):
    """Could the detector find any puck-namespace ID in these bytes?

    Every detector path (typed JSON ints, integral floats, numeric keys, strings,
    Markdown mentions and unsupported declarations, raw YAML/TOML/CSV/TXT text)
    reads decimal digits through _TOKEN, _RANGE or json number parsing, so a
    content with none of the forms above cannot produce a new, reused, held-out
    or mitigation-relevant ID. Proven by property tests against the detector.
    """
    text = raw.decode('utf-8', errors='replace')
    if _prefilter_text(text):
        return True
    if '\\u' in text:
        return _prefilter_text(_UNICODE_ESCAPE.sub(lambda m: chr(int(m[1], 16)), text))
    return False


def _utf8(path):
    try:
        path.encode('utf-8')
        return True
    except UnicodeEncodeError:
        return False


# Root scanning -------------------------------------------------------------------

DEDUPE = True  # analyse each unique (content sha256, suffix) once across all roots


def _analyze(relative, raw, digest):
    """Pure content analysis; depends only on the bytes and the file suffix."""
    result = {'lineage': LINEAGE_SHA256.get(digest), 'prefiltered': False, 'unparsed': False,
              'ambiguous': [], 'untyped': [], 'occurrences': [], 'held_out': []}
    if result['lineage'] is not None:
        return result
    if not prefilter_hit(raw):
        result['prefiltered'] = True
        return result
    raw_new = _raw_new_ids(raw)
    if relative.endswith(RAW_SUFFIXES):
        ambiguous, non_scene = _raw_only_hits(relative, raw)
        if ambiguous:
            result['ambiguous'].append(('untyped format mentions new IDs', sorted(ambiguous)))
        result['untyped'] = sorted(non_scene - ambiguous)
        return result
    parsed = _parse_document(relative, raw)
    if parsed is None:
        result['unparsed'] = True
        if raw_new:
            result['ambiguous'].append(('unparsed document contains new IDs', sorted(raw_new)))
        return result
    occurrences, held_out, unsupported = parsed
    for text in unsupported:
        hits = sorted(_raw_new_ids(text.encode()))
        if hits:
            result['ambiguous'].append(('unsupported typed declaration', hits))
    result['occurrences'] = occurrences
    result['untyped'] = sorted(raw_new - {scene_id for _, scene_id in occurrences})
    result['held_out'] = held_out
    return result


class _Scan:
    def __init__(self, lost_root, roots, git_covered, *, dedupe=None):
        self.lost_root = lost_root
        self.root_paths = [root['path'] for root in roots]
        self.git_covered = git_covered  # git root paths and their registered worktrees
        self.collisions, self.ambiguous, self.untyped = [], [], []
        self.reuse, self.held_out_ids, self.held_out_payloads = {}, {}, []
        self.lineage, self.unparsed, self.max_puck = [], [], None
        self.clones, self.errors = [], []
        self.parsed = self.prefiltered = self.unique = 0
        self.dedupe = DEDUPE if dedupe is None else dedupe
        self.memo = {}

    def document(self, root, relative, raw, oid=None):
        where = {'root': root, 'path': relative}
        if oid is not None:
            where['oid'] = oid
        digest = _sha(raw)
        key = (digest, _suffix(relative))
        result = self.memo.get(key) if self.dedupe else None
        if result is None:
            result = _analyze(relative, raw, digest)
            self.unique += 1
            if self.dedupe:
                self.memo[key] = result
        self._apply(where, digest, result)

    def _apply(self, where, digest, result):
        """Record one path's findings; a content's hits are reported for every path."""
        if result['lineage'] is not None:
            self.lineage.append({**where, 'sha256': digest, 'lineage': result['lineage']})
            return
        if result['prefiltered']:
            self.prefiltered += 1
            return
        self.parsed += 1
        if result['unparsed']:
            self.unparsed.append(where)
        for reason, ids in result['ambiguous']:
            self.ambiguous.append({**where, 'reason': reason, 'scene_ids': ids})
        for pointer, scene_id in result['occurrences']:
            if scene_id in NEW_SCENE_IDS:
                self.collisions.append({**where, 'pointer': pointer, 'scene_id': scene_id})
            elif PUCK_NAMESPACE[0] <= scene_id <= PUCK_NAMESPACE[1]:
                self.max_puck = max(self.max_puck or scene_id, scene_id)
            for stage, ids in INTENTIONAL_REUSE.items():
                if scene_id in ids:
                    self.reuse[stage, scene_id] = self.reuse.get((stage, scene_id), 0) + 1
            if scene_id in HELD_OUT_SCENE_IDS:
                self.held_out_ids[str(scene_id)] = self.held_out_ids.get(str(scene_id), 0) + 1
        for scene_id in result['untyped']:
            self.untyped.append({**where, 'scene_id': scene_id})
        for pointer, scene_id in result['held_out']:
            self.held_out_payloads.append({**where, 'pointer': pointer, 'scene_id': scene_id})

    def _git_storage(self, root, directory, full, problems):
        if directory in self.git_covered:
            return 'covered'
        if os.path.isfile(full) and not os.path.islink(full):
            target = _gitfile_target(full)
            if target is not None and _under(target, self.lost_root) and root['lost_root_clone']:
                self.clones.append(directory)
                return 'lost-root-clone'
        problems.append(f'git storage at {full} is not covered by a declared git root')
        return 'uncovered'

    def _symlink(self, full, problems):
        target = os.path.realpath(full)
        if not any(_under(target, path) for path in self.root_paths):
            problems.append(f'symlink {full} -> {target} leaves the declared roots; '
                            'exclude it with a reason')

    def _inventory(self, root, problems):
        """Metadata-only walk; every hazard is appended to problems, never skipped."""
        base = root['path']
        files, symlinks, skipped, git_storage = [], [], 0, []

        def onerror(error):
            problems.append(f'directory walk failed under {root["name"]} '
                            f'(refusing, not skipping): {error}')
        for directory, dirnames, filenames in os.walk(base, followlinks=False, onerror=onerror):
            keep = []
            for name in sorted(dirnames):
                full = os.path.join(directory, name)
                if _excluded(full, root):
                    continue
                if not _utf8(full):
                    problems.append(f'path is not UTF-8 (not scannable): {full!r}')
                elif os.path.islink(full):
                    self._symlink(full, problems)
                    symlinks.append(os.path.relpath(full, base))
                elif name == '.git':
                    git_storage.append([os.path.relpath(full, base),
                                        self._git_storage(root, directory, full, problems)])
                else:
                    keep.append(name)
            dirnames[:] = keep
            for name in sorted(filenames):
                full = os.path.join(directory, name)
                if _excluded(full, root):
                    continue
                if not _utf8(full):
                    problems.append(f'path is not UTF-8 (not scannable): {full!r}')
                    continue
                relative = os.path.relpath(full, base)
                try:
                    info = os.lstat(full)
                except OSError as error:
                    problems.append(f'stat failed for {full}: {error}')
                    continue
                if stat.S_ISLNK(info.st_mode):
                    self._symlink(full, problems)
                    symlinks.append(relative)
                elif name == '.git':
                    git_storage.append([relative,
                                        self._git_storage(root, directory, full, problems)])
                elif not stat.S_ISREG(info.st_mode):
                    continue
                elif name.endswith(SCANNED_SUFFIXES):
                    if info.st_size > MAX_FILE_BYTES:
                        problems.append(f'{root["name"]}:{relative} exceeds {MAX_FILE_BYTES} '
                                        'bytes; exclude it with a reason')
                    elif not os.access(full, os.R_OK):
                        problems.append(f'unreadable file {full}')
                    files.append([relative, info.st_size, info.st_mtime_ns, info.st_ino])
                else:
                    skipped += 1
        return {'files': sorted(files), 'symlinks': sorted(symlinks), 'skipped': skipped,
                'git_storage': sorted(git_storage)}

    def scan_directory(self, root, before):
        parsed = self.parsed
        digest_rows = []
        for relative, _, _, _ in before['files']:
            try:
                raw = Path(root['path'], relative).read_bytes()
            except OSError as error:
                self.errors.append(f'read failed for {root["name"]}:{relative}: {error}')
                continue
            if len(raw) > MAX_FILE_BYTES:
                self.errors.append(f'{root["name"]}:{relative} grew past {MAX_FILE_BYTES} bytes')
                continue
            digest_rows.append([relative, _sha(raw), len(raw)])
            self.document(root['name'], relative, raw)
        problems, clones = [], list(self.clones)
        after = self._inventory(root, problems)
        self.clones = clones
        if problems or after != before:
            self.errors.append(f'root {root["name"]} changed during inventory'
                               + (f': {"; ".join(problems)}' if problems else ''))
        return {'name': root['name'], 'kind': 'directory', 'path': root['path'],
                'held_out_payloads': root['held_out_payloads'],
                'lost_root_clone': root['lost_root_clone'],
                'excluded': sorted(root['exclude'], key=lambda row: row['path']),
                'files_scanned': len(before['files']),
                'files_parsed_after_prefilter': self.parsed - parsed,
                'files_skipped_by_suffix': before['skipped'],
                'unfollowed_symlinks': before['symlinks'],
                'git_storage': before['git_storage'],
                'inventory_before_sha256': _sha(canonical_bytes(before)),
                'inventory_after_sha256': _sha(canonical_bytes(after)),
                'content_digest': _sha(canonical_bytes(digest_rows))}

    def scan_git(self, root, record):
        repo, parsed = root['path'], self.parsed
        before = {'refs': record['refs'], 'worktrees': _git_worktrees(repo)}
        if _git_refs(repo) != record['refs']:
            self.errors.append(f'git root {root["name"]} refs changed since preflight')
        blobs = _git_blobs(repo, record['scanned_tips'])
        for path, oid, raw in blobs:
            self.document(root['name'], path, raw, oid)
        after = {'refs': _git_refs(repo), 'worktrees': _git_worktrees(repo)}
        if after != before:
            self.errors.append(f'git root {root["name"]} changed during inventory')
        return {**record, 'blobs_scanned': len(blobs),
                'files_parsed_after_prefilter': self.parsed - parsed,
                'inventory_before_sha256': _sha(canonical_bytes(before)),
                'inventory_after_sha256': _sha(canonical_bytes(after)),
                'content_digest': _sha(canonical_bytes(sorted(oid for _, oid, _ in blobs)))}


# Throughput projection -------------------------------------------------------------

_RATE_CACHE = {}
RATE_MODEL = (
    'Two measured CPU rates, no name-based discount. Unique bytes (every git blob of a '
    'scanned suffix, plus directory files not proven identical to a scanned blob) are costed '
    'at the full digest+prefilter+parse rate measured on a bundled synthetic sample whose '
    'every document passes the prefilter (conservative). Directory files that git reports '
    'as tracked and clean in a worktree of a declared git root carry exactly the bytes of an '
    'already scanned blob, so execute only digests them and replays the memoised analysis; '
    'they are costed at the measured memo-hit rate. A cheaper rate for files whose names do '
    'not suggest registries is NOT used: names do not predict prefilter misses (routine '
    'JSON floats such as 1e-05 and dates near 6xxx tokens pass it), so that discount would '
    'not be justified. Directory walking, git process CPU and read syscalls are not costed.')


def _synthetic_sample():
    """Deterministic bundled sample of unique documents that all pass the prefilter."""
    docs = []
    for index in range(48):
        rows = [{'scene_id': 6000 + i % 20, 'seed': i, 'rover_pose': [0.1 * i, 0.2, 0.3],
                 'note': 'sample ' * 6, 'date': '2026-11-07', 'doc': index} for i in range(60)]
        payload = {'scene_reservations': {'collection': [6000 + index % 20, 6100],
                                          'development': '6120-6123'}, 'rows': rows}
        docs.append((f'sample/{index}.json', json.dumps(payload).encode()))
        docs.append((f'sample/{index}.md', (f'# Sample {index}\nScene IDs: 6100..6103\n' + (
            'Prose that mentions 6512 bytes on 2026-11-07, for timing only.\n' * 100)).encode()))
        docs.append((f'sample/{index}.jsonl', b'\n'.join(json.dumps(
            {'doc': index, 'tick': i, 'scene_id': 6001, 'inputs': [0.5] * 9}).encode()
            for i in range(80))))
    return docs


def _measure_rates():
    """CPU MB/s for first-sight analysis and for memo-hit replays of the same contents."""
    if not _RATE_CACHE:
        docs = _synthetic_sample()
        total = sum(len(raw) for _, raw in docs)
        scan = _Scan('/nonexistent-lost-root', [], set(), dedupe=True)
        start = time.process_time()
        for relative, raw in docs:
            scan.document('sample', relative, raw)
        full = max(time.process_time() - start, 1e-6)
        repeats, start = 0, time.process_time()
        while repeats < 3 or (time.process_time() - start < 0.05 and repeats < 50):
            for relative, raw in docs:
                scan.document('sample', relative, raw)
            repeats += 1
        hit = max(time.process_time() - start, 1e-6) / repeats
        _RATE_CACHE.update(full=total / full / 1e6, hit=total / hit / 1e6)
    return _RATE_CACHE


def _sample_rate():
    return _measure_rates()['full']


def _digest_rate():
    return _measure_rates()['hit']


def _suffix(path):
    return next((s for s in sorted(SCANNED_SUFFIXES, key=len, reverse=True)
                 if path.endswith(s)), '')


def _clean_tracked(worktree):
    """Git metadata only: {path: blob oid} for tracked files that are clean in a worktree."""
    tracked = {}
    for entry in _git(worktree, 'ls-files', '-s', '-z').split(b'\0'):
        if not entry:
            continue
        meta, _, path = entry.partition(b'\t')
        mode, oid, stage = meta.decode().split()
        if mode != '160000' and stage == '0':
            tracked[path.decode('utf-8', 'surrogateescape')] = oid
    status = _git(worktree, 'status', '--porcelain=v1', '-z', '--untracked-files=no',
                  '--ignore-submodules=all').split(b'\0')
    index = 0
    while index < len(status):
        item, index = status[index], index + 1
        if not item:
            continue
        tracked.pop(item[3:].decode('utf-8', 'surrogateescape'), None)
        if item[:1] in (b'R', b'C') or item[1:2] in (b'R', b'C'):
            if index < len(status):
                tracked.pop(status[index].decode('utf-8', 'surrogateescape'), None)
                index += 1
    return tracked


def _throughput(protocol, roots, inventories, git_records, git_sizes, calibrate=False,
                held_out_reads=False):
    raw, unique, covered, notes = {}, {}, 0, []

    def add(table, suffix, size):
        table[suffix] = table.get(suffix, 0) + size
    worktrees = []
    for name, rows in git_sizes.items():
        oids = set()
        for path, oid, size in rows:
            add(raw, _suffix(path), size)
            add(unique, _suffix(path), size)
            oids.add(oid)
        record = git_records[name]
        for worktree in sorted({record['path'], *record['worktrees_covered']}):
            try:
                worktrees.append((worktree, _clean_tracked(worktree), oids))
            except AdmissionRefused as error:
                notes.append(f'worktree {worktree} counted fully: {error}')
    worktrees.sort(key=lambda row: len(row[0]), reverse=True)  # deepest worktree first
    eligible = []  # unique files in non-held-out directory roots: calibration candidates
    for root in roots:
        inventory = inventories.get(root['name'])
        if inventory is None:
            continue
        for relative, size, _, _ in inventory['files']:
            suffix, full = _suffix(relative), os.path.join(root['path'], relative)
            add(raw, suffix, size)
            match = next((row for row in worktrees if _under(full, row[0])), None)
            if match is not None and match[1].get(os.path.relpath(full, match[0])) in match[2]:
                covered += size
            else:
                add(unique, suffix, size)
                if held_out_reads or not root['held_out_payloads']:
                    eligible.append((root['name'], full, suffix, size))
    limit = next(row['enclosing_hard_seconds'] for row in
                 protocol['expected_cost_table']['pre_held_out'] if row['stage'] == 'S1')
    full_rate, hit_rate = _sample_rate(), _digest_rate()
    projected = sum(unique.values()) / (full_rate * 1e6) + covered / (hit_rate * 1e6)
    calibration = (_calibrate(eligible, unique, covered, full_rate, hit_rate)
                   if calibrate else None)
    basis = projected if calibration is None else calibration['projected_cpu_seconds']
    return {'bytes_by_suffix': dict(sorted(raw.items())), 'total_bytes': sum(raw.values()),
            'calibration': calibration,
            'blocker_basis': 'conservative' if calibration is None else 'calibrated',
            'deduplicated_bytes_by_suffix': dict(sorted(unique.items())),
            'deduplicated_total_bytes': sum(unique.values()),
            'covered_by_git_blobs_bytes': covered,
            'sample_mb_per_s': full_rate, 'digest_mb_per_s': hit_rate,
            'projected_cpu_seconds': projected, 'limit_seconds': limit,
            'blocker_fraction': THROUGHPUT_BLOCKER_FRACTION, 'rate_model': RATE_MODEL,
            'dedupe_notes': notes,
            'method': 'raw bytes = every directory file plus every reachable git blob of a '
                      'scanned suffix; deduplicated bytes drop directory files that git '
                      '(ls-files -s minus status --untracked-files=no) reports tracked and '
                      'clean in a worktree of a declared git root whose blob is in the scan; '
                      'untracked, ignored, dirty and non-git files count fully; no '
                      'size/name dedupe across directory roots',
            'blocked': basis > THROUGHPUT_BLOCKER_FRACTION * limit}


CALIBRATION_RULE = (
    'Contents are read only from directory roots with held_out_payloads=false, or also from '
    'held-out-flagged directory roots when a D2 GO scoped to S1 is supplied (never git blobs). Per suffix, eligible files (unique bytes in '
    'those roots) are ordered by sha256 of their absolute path and taken until the sample '
    'covers >= 10% of the eligible bytes (all, if smaller). Measured: the byte fraction '
    'passing the prefilter per suffix; the digest+prefilter rate on sampled prefilter misses '
    '(all sampled bytes if none miss); and the full rate on sampled hits, capped at the '
    'synthetic conservative rate. Every unique byte (including held-out roots and git blobs, '
    'which are not read) is projected as pass_upper x bytes / full_rate + (1 - pass_upper) x '
    'bytes / miss_rate with pass_upper = min(1, 2 x observed pass fraction + 0.05) per '
    'suffix (1 for suffixes without eligible bytes); clean tracked worktree bytes stay at '
    'the memo-hit rate. The blocker uses this calibrated projection; limits are unchanged.')


def _calibrate(eligible, unique, covered, synthetic_full_rate, hit_rate):
    started = time.process_time()
    eligible_bytes, sample = {}, []
    for _, _, suffix, size in eligible:
        eligible_bytes[suffix] = eligible_bytes.get(suffix, 0) + size
    taken = {}
    for row in sorted(eligible, key=lambda row: (row[2], _sha(os.fsencode(row[1])), row[1])):
        suffix = row[2]
        if taken.get(suffix, 0) < 0.1 * eligible_bytes[suffix] or suffix not in taken:
            sample.append(row)
            taken[suffix] = taken.get(suffix, 0) + row[3]
    passed, sampled, notes = {}, {}, []
    miss_bytes = miss_cpu = hit_bytes = hit_cpu = all_bytes = all_cpu = 0
    for root, full, suffix, _ in sample:
        try:
            raw = Path(full).read_bytes()
        except OSError as error:
            notes.append(f'{full} unreadable; counted as a prefilter pass: {error}')
            sampled[suffix] = sampled.get(suffix, 0) + 1
            passed[suffix] = passed.get(suffix, 0) + 1
            continue
        start = time.process_time()
        digest = _sha(raw)
        hit = prefilter_hit(raw)
        cheap = time.process_time() - start
        all_bytes, all_cpu = all_bytes + len(raw), all_cpu + cheap
        sampled[suffix] = sampled.get(suffix, 0) + len(raw)
        if hit:
            passed[suffix] = passed.get(suffix, 0) + len(raw)
            start = time.process_time()
            _analyze(full, raw, digest)
            hit_bytes, hit_cpu = hit_bytes + len(raw), hit_cpu + cheap + (
                time.process_time() - start)
        else:
            miss_bytes, miss_cpu = miss_bytes + len(raw), miss_cpu + cheap
    if miss_bytes:
        miss_rate = miss_bytes / max(miss_cpu, 1e-6) / 1e6
    else:
        miss_rate = all_bytes / max(all_cpu, 1e-6) / 1e6 if all_bytes else synthetic_full_rate
    full_rate = synthetic_full_rate
    if hit_bytes:
        full_rate = min(synthetic_full_rate, hit_bytes / max(hit_cpu, 1e-6) / 1e6)
    miss_rate = max(miss_rate, full_rate)  # a miss never costs more than a full analysis
    by_suffix, projected = {}, covered / (hit_rate * 1e6)
    for suffix, size in sorted(unique.items()):
        fraction = (passed.get(suffix, 0) / sampled[suffix]
                    if sampled.get(suffix) else None)
        upper = 1.0 if fraction is None else min(1.0, 2 * fraction + 0.05)
        by_suffix[suffix] = {'eligible_bytes': eligible_bytes.get(suffix, 0),
                             'sample_bytes': sampled.get(suffix, 0),
                             'sample_files': sum(1 for row in sample if row[2] == suffix),
                             'pass_fraction': fraction, 'pass_upper': upper,
                             'unique_bytes_projected': size}
        projected += size * (upper / (full_rate * 1e6) + (1 - upper) / (miss_rate * 1e6))
    return {'rule': CALIBRATION_RULE, 'by_suffix': by_suffix,
            'read_scope': sorted({row[0] for row in sample}),
            'sample_digest': _sha(canonical_bytes(sorted(row[1] for row in sample))),
            'full_mb_per_s': full_rate, 'miss_mb_per_s': miss_rate,
            'full_rate_source': 'sampled hits (capped at synthetic)' if hit_bytes
                                else 'synthetic conservative (no sampled hits)',
            'projected_cpu_seconds': projected, 'notes': notes,
            'cpu_seconds': time.process_time() - started}


# Publication ---------------------------------------------------------------------

def _fsync_directory(path):
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _write_exclusive(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def _publish(output, raw):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / f'.{output.name}.{os.getpid()}.tmp'
    _write_exclusive(temporary, raw)
    try:
        os.link(temporary, output)  # never replaces an existing report
    finally:
        os.unlink(temporary)
    _fsync_directory(output.parent)


def _source_hashes():
    hashes = {}
    for relative in SOURCE_FILES:
        path = _REPO / relative
        if not path.is_file():
            raise AdmissionRefused(f'source file missing for reservation binding: {relative}')
        hashes[relative] = _sha(path.read_bytes())
    version = subprocess.run([GIT, '--version'], capture_output=True, text=True,
                             env={'PATH': '/usr/bin:/bin'})
    hashes['git_version'] = version.stdout.strip()
    hashes['interpreter'] = {'path': sys.executable, 'version': sys.version}
    return hashes


def _bytecode_disabled():
    return bool(sys.flags.dont_write_bytecode)


def _inside_unexcluded(path, roots):
    """Inside a directory root and not below one of its exclusions (git roots read commits only)."""
    return _covered(path, [root for root in roots if root['kind'] == 'directory'])


# Entry points --------------------------------------------------------------------

def _load_calibration_record(path, declaration_raw):
    raw = _read_small(path, 'calibration record')
    record = _strict_json(raw, 'calibration record')
    if (type(record) is not dict or record.get('mode') != 'plan-only'
            or record.get('protocol_sha256') != PROTOCOL_SHA256
            or record.get('comparison_set_sha256') != _sha(declaration_raw)
            or type(record.get('throughput')) is not dict
            or type(record['throughput'].get('calibration')) is not dict):
        raise AdmissionRefused('calibration record must be a calibrated plan-only output for '
                               'this protocol and this exact comparison set')
    return raw, record


def _preflight(protocol, roots, lost_root, ledger, *, calibrate=False, calibration=None,
               held_out_reads=False):
    """Everything checkable without reading root file contents (except the opt-in plan-time
    calibration sample from non-held-out directory roots): plan and execute share it."""
    blockers = [problem for root in roots for problem in _root_problems(root, lost_root)]
    directories = [root for root in roots if root['kind'] == 'directory']
    clones, git_records, lost_worktrees, git_covered = [], {}, [], set()
    for root in directories:
        if not _root_problems(root, lost_root):
            row, problems = _clone_problems(root, lost_root)
            blockers.extend(problems)
            if row:
                clones.append(row)
    for root in roots:
        if root['kind'] != 'git' or _root_problems(root, lost_root):
            continue
        try:
            record, lost, problems = _git_preflight(root, directories, lost_root)
        except AdmissionRefused as error:
            blockers.append(str(error))
            continue
        git_records[root['name']] = record
        lost_worktrees.extend(lost)
        blockers.extend(problems)
        git_covered.update([root['path'], *record['worktrees_covered'],
                            *record['worktrees_excluded']])
    scan = _Scan(lost_root, roots, git_covered)
    inventories, git_sizes = {}, {}
    for root in directories:
        if not _root_problems(root, lost_root):
            inventories[root['name']] = scan._inventory(root, blockers)
    for name, record in git_records.items():
        try:
            git_sizes[name] = _git_blob_sizes(record['path'], record['scanned_tips'])
        except AdmissionRefused as error:
            blockers.append(str(error))
            continue
        blockers.extend(f'git blob {oid} ({path}) exceeds {MAX_FILE_BYTES} bytes'
                        for path, oid, size in git_sizes[name] if size > MAX_FILE_BYTES)
    throughput = _throughput(protocol, roots, inventories, git_records, git_sizes,
                             calibrate=calibrate, held_out_reads=held_out_reads)
    if calibration is not None:
        fields = ('bytes_by_suffix', 'deduplicated_bytes_by_suffix', 'covered_by_git_blobs_bytes')
        recorded = calibration['throughput']
        if any(recorded.get(field) != throughput[field] for field in fields):
            blockers.append('calibration record differs from the current inventory '
                            '(bytes by suffix changed since the calibrated plan)')
        else:
            calibrated = recorded['calibration']['projected_cpu_seconds']
            throughput = {**throughput, 'calibration': recorded['calibration'],
                          'blocker_basis': 'calibration record',
                          'blocked': calibrated > THROUGHPUT_BLOCKER_FRACTION
                          * throughput['limit_seconds']}
    if throughput['blocked']:
        basis = (throughput['projected_cpu_seconds'] if throughput['calibration'] is None
                 else throughput['calibration']['projected_cpu_seconds'])
        blockers.append(f'throughput projection {basis:.0f} CPU-s '
                        f'({throughput["blocker_basis"]}) exceeds '
                        f'{THROUGHPUT_BLOCKER_FRACTION:.0%} of the '
                        f'{throughput["limit_seconds"]} s S1 limit')
    if os.path.lexists(os.path.join(ledger, ATTEMPT_RECEIPT_NAME)):
        blockers.append(f'the single S1 attempt is already consumed: {ledger}/'
                        f'{ATTEMPT_RECEIPT_NAME} exists')
    if _inside_unexcluded(ledger, roots) or _under(ledger, lost_root):
        blockers.append(f'attempt ledger {ledger} lies inside a comparison root outside its '
                        'exclusions')
    return {'blockers': blockers, 'clones': clones, 'git': git_records, 'scan': scan,
            'lost_worktrees': sorted(lost_worktrees), 'inventories': inventories,
            'throughput': throughput}


_SCAN_FAILURES = (OSError, ValueError, RecursionError, csv.Error, UnicodeError, MemoryError,
                  subprocess.SubprocessError, AdmissionRefused)


def admit(*, protocol_path, comparison_set_path, output_path, execute=False,
          go_record_path=None, held_out_go_record_path=None, lost_root=None,
          attempt_ledger=None, calibrate=False, calibration_record_path=None):
    """Plan (default) or execute S1. Returns the plan or a verdict summary."""
    if calibrate and execute:
        raise AdmissionRefused('--calibrate is plan-only: execute must not read contents before '
                               'its receipt; pass the calibrated plan as a calibration record')
    protocol_raw, protocol, roster = _load_protocol(protocol_path)
    declaration_raw, declaration = _load_declaration(comparison_set_path)
    derived = lost_root is None
    lost_root = lost_root_from_protocol(protocol) if derived else _canonical_path(
        lost_root, 'lost root')
    ledger = _canonical_path(attempt_ledger or DEFAULT_ATTEMPT_LEDGER, 'attempt ledger')
    lost = _lost_root_record(protocol, lost_root, derived)
    roots = declaration['roots']
    record_raw, record = None, None
    if calibration_record_path is not None:
        record_raw, record = _load_calibration_record(calibration_record_path, declaration_raw)
    # D2 (scope S1) lets plan-time calibration byte-read held-out-flagged directory roots;
    # git blobs are still never read in plan mode, and nothing is loaded into a simulator.
    held_out_reads = False
    if calibrate and held_out_go_record_path is not None:
        _load_go(held_out_go_record_path, HELD_OUT_GO_STAGE, 'held-out GO record',
                 protocol.get('state'))
        held_out_reads = True
    pre = _preflight(protocol, roots, lost_root, ledger, calibrate=calibrate,
                     calibration=record, held_out_reads=held_out_reads)
    if calibrate:
        pre['throughput'].setdefault('calibration', {})['held_out_roots_read'] = held_out_reads
    blockers = pre['blockers']
    if lost['status'] == 'present-refused':
        blockers.append(f'frozen lost root {lost_root} is present; its exception premise fails')
    needs_held_out_go = any(root['held_out_payloads'] for root in roots)
    if not execute:
        return {'mode': 'plan-only', 'stage': S1_GO_STAGE, 'writes': [],
                'contents_read': (('calibration sample from directory roots, including '
                                   'held-out-flagged roots under a D2 GO scoped to S1'
                                   if held_out_reads else
                                   'calibration sample from non-held-out directory roots only')
                                  if calibrate else False),
                'metadata_read': 'stat/walk of directory roots; git refs, worktrees, object '
                                 'headers and advertised OIDs',
                'protocol_sha256': PROTOCOL_SHA256, 'comparison_set_sha256': _sha(declaration_raw),
                'roster': roster, 'roots': [{key: root[key] for key in ('name', 'kind', 'path')}
                                            for root in roots],
                'git': list(pre['git'].values()), 'unscanned': declaration['unscanned'],
                'lost_root': {**lost, 'git_worktrees_excluded': pre['lost_worktrees']},
                'lost_root_clones': pre['clones'], 'blockers': blockers,
                'throughput': pre['throughput'],
                'execution_requirements': list(EXECUTION_REQUIREMENTS),
                'required_go': {'stage': S1_GO_STAGE, 'scope': S1_GO_STAGE,
                                'protocol_sha256': PROTOCOL_SHA256},
                'required_held_out_go': ({'stage': HELD_OUT_GO_STAGE, 'scope': S1_GO_STAGE,
                                          'protocol_sha256': PROTOCOL_SHA256}
                                         if needs_held_out_go else None),
                'attempt_ledger': ledger, 'would_write_on_execute': str(output_path)}
    go_raw, go_input = _load_go(go_record_path, S1_GO_STAGE, 'S1 GO record', protocol['state'])
    held_raw, held_input = None, None
    if held_out_go_record_path is not None:
        held_raw, held_input = _load_go(held_out_go_record_path, HELD_OUT_GO_STAGE,
                                        'D2 held-out GO record', protocol['state'])
    if needs_held_out_go and held_raw is None:
        raise AdmissionRefused('a root declares held-out payloads; D2 requires a separate '
                               f'{HELD_OUT_GO_STAGE!r} GO record with scope S1')
    if not _bytecode_disabled():
        raise AdmissionRefused('execute requires the interpreter to run with -B '
                               '(no bytecode writes into declared roots)')
    output = Path(_canonical_path(os.path.abspath(output_path), 'output'))
    if os.path.lexists(output):
        raise AdmissionRefused(f'output must be a fresh path: {output}')
    if _inside_unexcluded(str(output), roots) or _under(str(output), lost_root):
        raise AdmissionRefused('output lies inside a comparison root outside its exclusions')
    if blockers:
        raise AdmissionRefused('; '.join(blockers))
    sources = _source_hashes()

    # Durable attempt receipt before the first content read; it consumes the attempt.
    receipt = {'kind': RECEIPT_KIND, 'version': 1, 'stage': S1_GO_STAGE,
               'protocol_sha256': PROTOCOL_SHA256,
               'comparison_set_sha256': _sha(declaration_raw), 'go_record_sha256': _sha(go_raw),
               'held_out_go_record_sha256': None if held_raw is None else _sha(held_raw),
               'sources': sources}
    receipt_raw = canonical_bytes(receipt)
    Path(ledger).mkdir(parents=True, exist_ok=True)
    try:
        _write_exclusive(Path(ledger) / ATTEMPT_RECEIPT_NAME, receipt_raw)
    except FileExistsError as error:
        raise AdmissionRefused('the single S1 attempt is already consumed') from error

    # From here on every failure becomes a recorded refusal in the published report.
    scan, root_reports, reasons = pre['scan'], [], []
    try:
        for root in roots:
            if root['kind'] == 'directory':
                root_reports.append(scan.scan_directory(root, pre['inventories'][root['name']]))
            else:
                root_reports.append(scan.scan_git(root, pre['git'][root['name']]))
    except _SCAN_FAILURES as error:
        reasons.append(f'scan aborted: {type(error).__name__}: {error}')
    reasons.extend(scan.errors)
    if scan.collisions:
        reasons.append(f'{len(scan.collisions)} new scene-ID collision(s) outside v4 lineage')
    if scan.ambiguous:
        reasons.append(f'{len(scan.ambiguous)} ambiguous document(s) mention new IDs')
    mitigation = scan.max_puck is None or scan.max_puck <= MAX_HISTORICAL_PUCK_ID
    if not mitigation:
        reasons.append(f'prior puck ID {scan.max_puck} > {MAX_HISTORICAL_PUCK_ID}: '
                       'lost-root mitigation premise fails')
    if scan.held_out_payloads and held_raw is None:
        reasons.append('held-out 6200-6207 payload objects found without the D2 GO record')
    for path, raw in ((protocol_path, protocol_raw), (comparison_set_path, declaration_raw),
                      (go_record_path, go_raw), (held_out_go_record_path, held_raw)):
        try:
            if raw is not None and Path(path).read_bytes() != raw:
                reasons.append(f'input changed during admission: {path}')
        except OSError as error:
            reasons.append(f'input unreadable at final recheck: {path}: {error}')
    try:
        if _source_hashes() != sources:
            reasons.append('admission source changed during the attempt')
    except (OSError, AdmissionRefused) as error:
        reasons.append(f'source recheck failed: {error}')
    verdict = 'refused' if reasons else 'admitted'
    lost.update({'git_worktrees_excluded': pre['lost_worktrees'],
                 'clones_scanned': sorted(set(scan.clones)),
                 'max_observed_prior_puck_id': scan.max_puck, 'mitigation_holds': mitigation})

    def key(row):
        return (row['root'], row['path'], row.get('pointer', ''), row.get('scene_id', 0))

    report = {
        'kind': REPORT_KIND, 'version': 1, 'stage': S1_GO_STAGE, 'protocol_id': PROTOCOL_ID,
        'verdict': verdict, 'refusal_reasons': reasons,
        'inputs': {
            'protocol': {'path': str(protocol_path), 'sha256': _sha(protocol_raw)},
            'comparison_set': {'path': str(comparison_set_path), 'sha256': _sha(declaration_raw)},
            'go_record': go_input, 'held_out_go_record': held_input,
            'calibration_record': None if record_raw is None else {
                'path': str(calibration_record_path), 'sha256': _sha(record_raw)},
        },
        'sources': sources,
        'execution_requirements': list(EXECUTION_REQUIREMENTS),
        'attempt': {'receipt_name': ATTEMPT_RECEIPT_NAME, 'receipt_sha256': _sha(receipt_raw),
                    'ledger_is_default': ledger == DEFAULT_ATTEMPT_LEDGER},
        'roster': roster,
        'reservation': None if reasons else {
            'scene_ids': list(NEW_SCENE_IDS), 'collection': list(COLLECTION_SCENE_IDS),
            'development': list(DEVELOPMENT_SCENE_IDS), 'lineage_protocol_sha256': PROTOCOL_SHA256,
            'lineage_sha256': sorted(LINEAGE_SHA256), 'output_cap_bytes': MAX_OUTPUT_BYTES},
        'roots': root_reports,
        'unscanned': declaration['unscanned'],
        'lost_root': lost,
        'lineage_documents': sorted(scan.lineage, key=key),
        'collisions': sorted(scan.collisions, key=key),
        'ambiguous': sorted(scan.ambiguous, key=key),
        'unparsed_documents': sorted(scan.unparsed, key=key),
        'untyped_new_id_mentions': sorted(scan.untyped, key=key),
        'intentional_reuse_occurrences': [
            {'stage': stage, 'scene_id': scene_id, 'occurrences': count}
            for (stage, scene_id), count in sorted(scan.reuse.items())],
        'held_out_id_occurrences': dict(sorted(scan.held_out_ids.items())),
        'held_out_payload_objects_not_compared': sorted(scan.held_out_payloads, key=key),
        'prefilter': {'files_parsed': scan.parsed, 'files_prefiltered_out': scan.prefiltered,
                      'unique_contents_analyzed': scan.unique,
                      'dedupe': 'content sha256 + suffix memo across all roots' if scan.dedupe else 'off',
                      'rule_and_residual': PREFILTER_RESIDUAL},
        'scope': {
            'typed_suffixes': list(TYPED_SUFFIXES), 'raw_suffixes': list(RAW_SUFFIXES),
            'puck_namespace': list(PUCK_NAMESPACE),
            'typed_fields': 'JSON keys with scene/layout/seed/roster/split/held_out/'
                            'reservation/collection/development tokens (not model/training/rng '
                            'seeds, not counts/bytes/hashes), their descendants, bare ids '
                            'beside geometry, numeric keys mapping to geometry, and integral '
                            'floats; Markdown via puck_scene_markdown',
            'raw_formats': 'yaml/yml/toml/csv/txt hits are ambiguous unless keyed or headed '
                           'as non-scene; malformed CSV falls back to raw-scan (ambiguous)',
            'untyped_mentions': 'diagnostic only, never collisions (v3 semantic parsing rule)',
            'content_digests': 'hash every scanned file, including held-out task-v5 copies',
        },
        'claims': {'held_out_payloads_compared': False, 'held_out_read': False,
                   'scenes_minted': False, 'simulator_executed': False,
                   'models_loaded': False, 'qualification_claims': []},
    }
    raw = canonical_bytes(report)
    if len(raw) > MAX_OUTPUT_BYTES:
        raise AdmissionRefused(f'report of {len(raw)} bytes exceeds the S1 output cap '
                               f'{MAX_OUTPUT_BYTES}; attempt consumed')
    _publish(output, raw)
    return {'verdict': verdict, 'output': str(output), 'report_sha256': _sha(raw),
            'refusal_reasons': reasons}


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n')[0] + ' Default --plan-only; execute needs python -B.',
        epilog='Execution requirements:\n' + '\n'.join(
            f'  - {row}' for row in EXECUTION_REQUIREMENTS),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--comparison-set', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--execute', action='store_true',
                        help='run the admission (default: --plan-only); requires python -B')
    parser.add_argument('--plan-only', action='store_true', help='default; never writes')
    parser.add_argument('--go-record')
    parser.add_argument('--held-out-go-record')
    parser.add_argument('--calibrate', action='store_true',
                        help='plan-only: read a deterministic >=10%% sample of non-held-out '
                             'directory roots to calibrate the throughput projection')
    parser.add_argument('--calibration-record',
                        help='execute: saved calibrated plan output for this exact comparison '
                             'set; its calibrated projection gates throughput')
    return parser


def main(argv=None, *, attempt_ledger=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.execute and args.plan_only:
        parser.error('--execute and --plan-only are exclusive')
    try:
        result = admit(protocol_path=args.protocol, comparison_set_path=args.comparison_set,
                       output_path=args.output, execute=args.execute,
                       go_record_path=args.go_record,
                       held_out_go_record_path=args.held_out_go_record,
                       attempt_ledger=attempt_ledger, calibrate=args.calibrate,
                       calibration_record_path=args.calibration_record)
    except AdmissionRefused as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return 2
    sys.stdout.write(canonical_bytes(result).decode())
    if not args.execute:
        return 1 if result['blockers'] else 0
    return 0 if result['verdict'] == 'admitted' else 1
