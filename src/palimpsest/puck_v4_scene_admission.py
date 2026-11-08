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
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

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
SOURCE_FILES = ('src/palimpsest/puck_v4_scene_admission.py',
                'src/palimpsest/puck_scene_markdown.py',
                'scripts/admit_puck_v4_scene_ids.py')

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
                       or record['supersedes_protocol_state'] != protocol_state):
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


def _git_blobs(repo, tips):
    listing = _git(repo, 'rev-list', '--objects', '--stdin',
                   stdin=''.join(tip + '\n' for tip in tips).encode())
    wanted = {}
    for line in listing.decode('utf-8', errors='surrogateescape').splitlines():
        oid, _, path = line.partition(' ')
        if path.endswith(SCANNED_SUFFIXES) and oid not in wanted:
            wanted[oid] = path
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
            if typed and re.fullmatch(r'\d{1,7}', key):
                occurrences.append((pointer + '/' + key, int(key)))
            child_typed = (typed or _key_is_scene(key)) and not _key_is_non_scene(key)
            if geometry and key in _ID_KEYS:
                child_typed = True  # bare id beside geometry is a scene identity
            if key in _GEOMETRY_KEYS:
                child_typed = False  # geometry values are never scene IDs nor compared
            _walk(child, pointer + '/' + _escape(key), child_typed, occurrences,
                  held_out_payloads)
    elif type(value) is list:
        for index, child in enumerate(value):
            _walk(child, f'{pointer}/{index}', typed, occurrences, held_out_payloads)
    elif typed and type(value) is int:
        occurrences.append((pointer, value))
    elif typed and type(value) is str:
        occurrences.extend((pointer, item) for item in _ids_in_text(value))


def _raw_only_hits(relative, raw):
    """Classify new-ID hits in untyped formats: (ambiguous_ids, non_scene_ids)."""
    text = raw.decode('utf-8', errors='replace')
    ambiguous, non_scene = set(), set()
    if relative.endswith('.csv'):
        rows = list(csv.reader(io.StringIO(text)))
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
    except (ValueError, AdmissionRefused):
        return None
    return occurrences, held_out, unsupported


# Root scanning -------------------------------------------------------------------

def _walk_error(error):
    raise AdmissionRefused(f'directory walk failed (refusing, not skipping): {error}')


class _Scan:
    def __init__(self, lost_root, roots, git_covered):
        self.lost_root = lost_root
        self.directories = [root for root in roots if root['kind'] == 'directory']
        self.root_paths = [root['path'] for root in roots]
        self.git_covered = git_covered  # git root paths and their registered worktrees
        self.collisions, self.ambiguous, self.untyped = [], [], []
        self.reuse, self.held_out_ids, self.held_out_payloads = {}, {}, []
        self.lineage, self.unparsed, self.max_puck = [], [], None
        self.clones = []

    def document(self, root, relative, raw, oid=None):
        where = {'root': root, 'path': relative}
        if oid is not None:
            where['oid'] = oid
        digest = _sha(raw)
        if digest in LINEAGE_SHA256:
            self.lineage.append({**where, 'sha256': digest, 'lineage': LINEAGE_SHA256[digest]})
            return
        raw_new = _raw_new_ids(raw)
        if relative.endswith(RAW_SUFFIXES):
            ambiguous, non_scene = _raw_only_hits(relative, raw)
            if ambiguous:
                self.ambiguous.append({**where, 'reason': 'untyped format mentions new IDs',
                                       'scene_ids': sorted(ambiguous)})
            for scene_id in sorted(non_scene - ambiguous):
                self.untyped.append({**where, 'scene_id': scene_id})
            return
        parsed = _parse_document(relative, raw)
        if parsed is None:
            self.unparsed.append(where)
            if raw_new:
                self.ambiguous.append({**where, 'reason': 'unparsed document contains new IDs',
                                       'scene_ids': sorted(raw_new)})
            return
        occurrences, held_out, unsupported = parsed
        for text in unsupported:
            hits = sorted(_raw_new_ids(text.encode()))
            if hits:
                self.ambiguous.append({**where, 'reason': 'unsupported typed declaration',
                                       'scene_ids': hits})
        typed_ids = set()
        for pointer, scene_id in occurrences:
            typed_ids.add(scene_id)
            if scene_id in NEW_SCENE_IDS:
                self.collisions.append({**where, 'pointer': pointer, 'scene_id': scene_id})
            elif PUCK_NAMESPACE[0] <= scene_id <= PUCK_NAMESPACE[1]:
                self.max_puck = max(self.max_puck or scene_id, scene_id)
            for stage, ids in INTENTIONAL_REUSE.items():
                if scene_id in ids:
                    self.reuse[stage, scene_id] = self.reuse.get((stage, scene_id), 0) + 1
            if scene_id in HELD_OUT_SCENE_IDS:
                self.held_out_ids[str(scene_id)] = self.held_out_ids.get(str(scene_id), 0) + 1
        for scene_id in sorted(raw_new - typed_ids):
            self.untyped.append({**where, 'scene_id': scene_id})
        for pointer, scene_id in held_out:
            self.held_out_payloads.append({**where, 'pointer': pointer, 'scene_id': scene_id})

    def _git_storage(self, root, directory, full):
        if directory in self.git_covered:
            return 'covered'
        if os.path.isfile(full) and not os.path.islink(full):
            target = _gitfile_target(full)
            if target is not None and _under(target, self.lost_root) and root['lost_root_clone']:
                self.clones.append(directory)
                return 'lost-root-clone'
        raise AdmissionRefused(f'git storage at {full} is not covered by a declared git root')

    def _symlink(self, root, full):
        target = os.path.realpath(full)
        if not any(_under(target, path) for path in self.root_paths):
            raise AdmissionRefused(f'symlink {full} -> {target} leaves the declared roots; '
                                   'exclude it with a reason')

    def _inventory(self, root):
        base = root['path']
        files, symlinks, skipped, git_storage = [], [], 0, []
        for directory, dirnames, filenames in os.walk(base, followlinks=False,
                                                      onerror=_walk_error):
            keep = []
            for name in sorted(dirnames):
                full = os.path.join(directory, name)
                if _excluded(full, root):
                    continue
                if os.path.islink(full):
                    self._symlink(root, full)
                    symlinks.append(os.path.relpath(full, base))
                elif name == '.git':
                    git_storage.append([os.path.relpath(full, base),
                                        self._git_storage(root, directory, full)])
                else:
                    keep.append(name)
            dirnames[:] = keep
            for name in sorted(filenames):
                full = os.path.join(directory, name)
                if _excluded(full, root):
                    continue
                relative = os.path.relpath(full, base)
                info = os.lstat(full)
                if stat.S_ISLNK(info.st_mode):
                    self._symlink(root, full)
                    symlinks.append(relative)
                elif name == '.git':
                    git_storage.append([relative, self._git_storage(root, directory, full)])
                elif not stat.S_ISREG(info.st_mode):
                    continue
                elif name.endswith(SCANNED_SUFFIXES):
                    files.append([relative, info.st_size, info.st_mtime_ns, info.st_ino])
                else:
                    skipped += 1
        return {'files': sorted(files), 'symlinks': sorted(symlinks), 'skipped': skipped,
                'git_storage': sorted(git_storage)}

    def scan_directory(self, root):
        before = self._inventory(root)
        digest_rows = []
        for relative, size, _, _ in before['files']:
            if size > MAX_FILE_BYTES:
                raise AdmissionRefused(f'{root["name"]}:{relative} exceeds {MAX_FILE_BYTES} bytes')
            raw = Path(root['path'], relative).read_bytes()
            digest_rows.append([relative, _sha(raw), len(raw)])
            self.document(root['name'], relative, raw)
        clones_before = list(self.clones)
        after = self._inventory(root)
        self.clones = clones_before
        if after != before:
            raise AdmissionRefused(f'root {root["name"]} changed during inventory')
        return {'name': root['name'], 'kind': 'directory', 'path': root['path'],
                'held_out_payloads': root['held_out_payloads'],
                'lost_root_clone': root['lost_root_clone'],
                'excluded': sorted(root['exclude'], key=lambda row: row['path']),
                'files_scanned': len(before['files']),
                'files_skipped_by_suffix': before['skipped'],
                'unfollowed_symlinks': before['symlinks'],
                'git_storage': before['git_storage'],
                'inventory_before_sha256': _sha(canonical_bytes(before)),
                'inventory_after_sha256': _sha(canonical_bytes(after)),
                'content_digest': _sha(canonical_bytes(digest_rows))}

    def scan_git(self, root, record):
        repo = root['path']
        before = {'refs': record['refs'], 'worktrees': _git_worktrees(repo)}
        if _git_refs(repo) != record['refs']:
            raise AdmissionRefused(f'git root {root["name"]} refs changed since preflight')
        blobs = _git_blobs(repo, record['scanned_tips'])
        for path, oid, raw in blobs:
            self.document(root['name'], path, raw, oid)
        after = {'refs': _git_refs(repo), 'worktrees': _git_worktrees(repo)}
        if after != before:
            raise AdmissionRefused(f'git root {root["name"]} changed during inventory')
        return {**record, 'blobs_scanned': len(blobs),
                'inventory_before_sha256': _sha(canonical_bytes(before)),
                'inventory_after_sha256': _sha(canonical_bytes(after)),
                'content_digest': _sha(canonical_bytes(sorted(oid for _, oid, _ in blobs)))}


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
    return hashes


def _inside_unexcluded(path, roots):
    """Inside a directory root and not below one of its exclusions (git roots read commits only)."""
    return _covered(path, [root for root in roots if root['kind'] == 'directory'])


# Entry points --------------------------------------------------------------------

def _preflight(roots, lost_root, ledger):
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
    if os.path.lexists(os.path.join(ledger, ATTEMPT_RECEIPT_NAME)):
        blockers.append(f'the single S1 attempt is already consumed: {ledger}/'
                        f'{ATTEMPT_RECEIPT_NAME} exists')
    if _inside_unexcluded(ledger, roots) or _under(ledger, lost_root):
        blockers.append(f'attempt ledger {ledger} lies inside a comparison root outside its '
                        'exclusions')
    return blockers, clones, git_records, sorted(lost_worktrees), git_covered


def admit(*, protocol_path, comparison_set_path, output_path, execute=False,
          go_record_path=None, held_out_go_record_path=None, lost_root=None,
          attempt_ledger=None):
    """Plan (default) or execute S1. Returns the plan or a verdict summary."""
    protocol_raw, protocol, roster = _load_protocol(protocol_path)
    declaration_raw, declaration = _load_declaration(comparison_set_path)
    derived = lost_root is None
    lost_root = lost_root_from_protocol(protocol) if derived else _canonical_path(
        lost_root, 'lost root')
    ledger = _canonical_path(attempt_ledger or DEFAULT_ATTEMPT_LEDGER, 'attempt ledger')
    lost = _lost_root_record(protocol, lost_root, derived)
    roots = declaration['roots']
    blockers, clones, git_records, lost_worktrees, git_covered = _preflight(
        roots, lost_root, ledger)
    if lost['status'] == 'present-refused':
        blockers.append(f'frozen lost root {lost_root} is present; its exception premise fails')
    needs_held_out_go = any(root['held_out_payloads'] for root in roots)
    if not execute:
        return {'mode': 'plan-only', 'stage': S1_GO_STAGE, 'writes': [], 'contents_read': False,
                'git_metadata_read': bool(git_records),
                'protocol_sha256': PROTOCOL_SHA256, 'comparison_set_sha256': _sha(declaration_raw),
                'roster': roster, 'roots': [{key: root[key] for key in ('name', 'kind', 'path')}
                                            for root in roots],
                'git': list(git_records.values()), 'unscanned': declaration['unscanned'],
                'lost_root': {**lost, 'git_worktrees_excluded': lost_worktrees},
                'lost_root_clones': clones, 'blockers': blockers,
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

    scan = _Scan(lost_root, roots, git_covered)
    root_reports = []
    for root in roots:
        if root['kind'] == 'directory':
            root_reports.append(scan.scan_directory(root))
        else:
            root_reports.append(scan.scan_git(root, git_records[root['name']]))

    reasons = []
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
    verdict = 'refused' if reasons else 'admitted'
    lost.update({'git_worktrees_excluded': lost_worktrees,
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
        },
        'sources': sources,
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
        'scope': {
            'typed_suffixes': list(TYPED_SUFFIXES), 'raw_suffixes': list(RAW_SUFFIXES),
            'puck_namespace': list(PUCK_NAMESPACE),
            'typed_fields': 'JSON keys with scene/layout/seed/roster/split/held_out/'
                            'reservation/collection/development tokens (not model/training/rng '
                            'seeds, not counts/bytes/hashes), their descendants, and bare ids '
                            'beside geometry; Markdown via puck_scene_markdown',
            'raw_formats': 'yaml/yml/toml/csv/txt hits are ambiguous unless keyed or headed '
                           'as non-scene',
            'untyped_mentions': 'diagnostic only, never collisions (v3 semantic parsing rule)',
            'content_digests': 'hash every scanned file, including held-out task-v5 copies',
        },
        'claims': {'held_out_payloads_compared': False, 'held_out_read': False,
                   'scenes_minted': False, 'simulator_executed': False,
                   'models_loaded': False, 'qualification_claims': []},
    }
    for path, raw in ((protocol_path, protocol_raw), (comparison_set_path, declaration_raw),
                      (go_record_path, go_raw), (held_out_go_record_path, held_raw)):
        if raw is not None and Path(path).read_bytes() != raw:
            raise AdmissionRefused(f'input changed during admission: {path}')
    if _source_hashes() != sources:
        raise AdmissionRefused('admission source changed during the attempt')
    raw = canonical_bytes(report)
    if len(raw) > MAX_OUTPUT_BYTES:
        raise AdmissionRefused(f'report of {len(raw)} bytes exceeds the S1 output cap '
                               f'{MAX_OUTPUT_BYTES}; attempt consumed')
    _publish(output, raw)
    return {'verdict': verdict, 'output': str(output), 'report_sha256': _sha(raw),
            'refusal_reasons': reasons}


def main(argv=None, *, attempt_ledger=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--comparison-set', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--execute', action='store_true',
                        help='run the admission (default: --plan-only)')
    parser.add_argument('--plan-only', action='store_true', help='default; never writes')
    parser.add_argument('--go-record')
    parser.add_argument('--held-out-go-record')
    args = parser.parse_args(argv)
    if args.execute and args.plan_only:
        parser.error('--execute and --plan-only are exclusive')
    try:
        result = admit(protocol_path=args.protocol, comparison_set_path=args.comparison_set,
                       output_path=args.output, execute=args.execute,
                       go_record_path=args.go_record,
                       held_out_go_record_path=args.held_out_go_record,
                       attempt_ledger=attempt_ledger)
    except AdmissionRefused as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return 2
    sys.stdout.write(canonical_bytes(result).decode())
    if not args.execute:
        return 1 if result['blockers'] else 0
    return 0 if result['verdict'] == 'admitted' else 1
