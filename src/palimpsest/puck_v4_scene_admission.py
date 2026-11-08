"""Puck v4 stage S1: scene-ID collision admission over declared comparison roots.

Pure ID comparison only. Given the hash-pinned v4 protocol and an explicit
comparison-set declaration, prove that the fresh collection (6510-6513) and
development (6520-6523) IDs do not occur as typed scene fields anywhere outside
v4's own lineage, record S0a/S0d intentional reuse of 6000-6019 / 6100-6103,
and record (never scan, never treat as clean) the frozen lost ``brain`` root.

Default is plan-only: no root content is read and nothing is written. Executing
requires a GO record naming stage ``S1`` and the protocol sha256. Any root that
may hold authored held-out 6200-6207 payloads needs a separate D2 GO record;
held-out payload values are never hashed, compared, loaded, or executed here.
No simulator, model, Torch, MuJoCo, or scene minter is imported.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

from .puck_scene_markdown import parse_puck_markdown_document

PROTOCOL_SHA256 = 'f885fc8d857cc47ec696ad65501b70ac80e16dfa5439fd5bf62919f868bc286b'
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
SCANNED_SUFFIXES = ('.json', '.jsonl', '.md')
MAX_FILE_BYTES = 256 * 1024 ** 2
MAX_SMALL_INPUT_BYTES = 4 * 1024 ** 2
MAX_RANGE = 4096
GIT = '/usr/bin/git'

_SCENE_TOKENS = {'scene', 'scenes', 'layout', 'layouts', 'seed', 'seeds'}
_OTHER_SEED_TOKENS = {'model', 'training', 'rng', 'random', 'environment'}
_NON_SCENE_TOKENS = {'byte', 'bytes', 'count', 'counts', 'size', 'seconds', 'ticks', 'rows',
                     'sha256', 'hash', 'epochs', 'owners', 'steps', 'wall', 'cpu', 'usec'}
_ID_KEYS = {'scene_id', 'scene', 'seed', 'layout_id', 'layout_seed', 'scene_seed', 'id'}
_GEOMETRY_KEYS = {'rover_pose', 'puck_xy', 'goal_xy', 'initial_qvel', 'layout', 'geometry',
                  'puck_pose', 'goal_pose'}
_TOKEN = re.compile(r'(?<![0-9A-Za-z_.])(\d{1,7})(?![0-9A-Za-z_])')
_RANGE = re.compile(r'(?<![0-9A-Za-z_.])(\d{1,7})\s*(?:-|–|\.\.)\s*(\d{1,7})(?![0-9A-Za-z_])')
_GO_FIELDS = {'kind', 'version', 'stage', 'protocol_sha256', 'granted_by', 'granted_at'}
_ROOT_FIELDS = {'directory': {'name', 'kind', 'path', 'exclude', 'held_out_payloads'},
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

def _load_declaration(path):
    raw = _read_small(path, 'comparison set')
    document = _strict_json(raw, 'comparison set')
    if (type(document) is not dict or set(document) != {'kind', 'version', 'roots'}
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
            for row in root['exclude']:
                if (type(row) is not dict or set(row) != {'path', 'reason'}
                        or type(row['reason']) is not str or not row['reason'].strip()):
                    raise AdmissionRefused('exclusions need path and nonempty reason')
                if not _under(_canonical_path(row['path'], 'exclusion'), root['path']) \
                        or row['path'] == root['path']:
                    raise AdmissionRefused('exclusions must lie strictly below their root')
            directories.append(root['path'])
        elif root['advertisement'] is not None:
            _canonical_path(root['advertisement'], 'advertisement')
    for index, path in enumerate(directories):
        if any(_under(path, other) or _under(other, path) for other in directories[:index]):
            raise AdmissionRefused('directory roots overlap')
    return raw, document


def _load_go(path, stage, label):
    if path is None:
        raise AdmissionRefused(f'{label} required: stage {stage!r} GO record is missing')
    raw = _read_small(path, label)
    record = _strict_json(raw, label)
    if type(record) is not dict or set(record) != _GO_FIELDS:
        raise AdmissionRefused(f'{label} requires exactly fields {sorted(_GO_FIELDS)}')
    if record['kind'] != GO_KIND or record['version'] != 1:
        raise AdmissionRefused(f'{label} kind/version differs')
    if record['stage'] != stage:
        raise AdmissionRefused(f'{label} names stage {record["stage"]!r}, not {stage!r}')
    if record['protocol_sha256'] != PROTOCOL_SHA256:
        raise AdmissionRefused(f'{label} protocol_sha256 differs from {PROTOCOL_SHA256}')
    if any(type(record[key]) is not str or not record[key].strip()
           for key in ('granted_by', 'granted_at')):
        raise AdmissionRefused(f'{label} needs granted_by and granted_at text')
    return raw, record


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
    return set(re.split(r'[^a-z0-9]+', key.lower())) - {''}


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


def _escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def _walk(value, pointer, typed, occurrences, held_out_payloads):
    if type(value) is dict:
        ids = [value[key] for key in value if key in _ID_KEYS]
        if (_GEOMETRY_KEYS & set(value)
                and any(type(item) is int and item in HELD_OUT_SCENE_IDS for item in ids)):
            held_out_payloads.append((pointer, next(
                item for item in ids if type(item) is int and item in HELD_OUT_SCENE_IDS)))
        for key, child in value.items():
            if typed and re.fullmatch(r'\d{1,7}', key):
                occurrences.append((pointer + '/' + key, int(key)))
            child_typed = (typed or _key_is_scene(key)) and not _key_is_non_scene(key)
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


def _raw_new_ids(raw):
    text = raw.decode('utf-8', errors='replace')
    return {int(match[1]) for match in _TOKEN.finditer(text)} & set(NEW_SCENE_IDS)


# Root scanning -------------------------------------------------------------------

def _walk_directory(root):
    base = root['path']
    excluded = sorted(row['path'] for row in root['exclude'])
    files, symlinks, skipped, git_dirs = [], [], 0, []
    for directory, dirnames, filenames in os.walk(base, followlinks=False):
        keep = []
        for name in sorted(dirnames):
            full = os.path.join(directory, name)
            if name == '.git':
                git_dirs.append(os.path.relpath(full, base))
            elif any(_under(full, path) for path in excluded):
                continue
            elif os.path.islink(full):
                symlinks.append(os.path.relpath(full, base))
            else:
                keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            full = os.path.join(directory, name)
            relative = os.path.relpath(full, base)
            info = os.lstat(full)
            if name == '.git':
                git_dirs.append(relative)
            elif stat.S_ISLNK(info.st_mode):
                symlinks.append(relative)
            elif not stat.S_ISREG(info.st_mode):
                continue
            elif name.endswith(SCANNED_SUFFIXES):
                files.append((relative, info.st_size, info.st_mtime_ns, info.st_ino))
            else:
                skipped += 1
    return sorted(files), sorted(symlinks), skipped, sorted(git_dirs)


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
        if header[0] != oid or header[1] != 'blob':
            offset = end + 1  # tree named like a document: no payload follows usable
            if header[1] != 'missing':
                offset += int(header[2]) + 1
            continue
        size = int(header[2])
        if size > MAX_FILE_BYTES:
            raise AdmissionRefused(f'git blob {oid} exceeds {MAX_FILE_BYTES} bytes')
        blobs.append((wanted[oid], oid, batch[end + 1:end + 1 + size]))
        offset = end + 1 + size + 1
    return blobs


class _Scan:
    def __init__(self, lost_root):
        self.lost_root = lost_root
        self.collisions, self.ambiguous, self.untyped = [], [], []
        self.reuse, self.held_out_ids, self.held_out_payloads = {}, {}, []
        self.lineage, self.unparsed, self.max_puck = [], [], None

    def document(self, root, relative, raw, oid=None, *, git=False):
        where = {'root': root, 'path': relative}
        if oid is not None:
            where['oid'] = oid
        lineage = (relative == COMPANION_RELATIVE_PATH or relative == PROTOCOL_RELATIVE_PATH
                   and (git or _sha(raw) == PROTOCOL_SHA256))
        if lineage:
            self.lineage.append({**where, 'sha256': _sha(raw)})
            return
        raw_new = _raw_new_ids(raw)
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
            if PUCK_NAMESPACE[0] <= scene_id <= PUCK_NAMESPACE[1] \
                    and scene_id not in NEW_SCENE_IDS:
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

    def scan_directory(self, root):
        before = _walk_directory(root)
        files, symlinks, skipped, git_dirs = before
        digest_rows = []
        for relative, size, _, _ in files:
            if size > MAX_FILE_BYTES:
                raise AdmissionRefused(f'{root["name"]}:{relative} exceeds {MAX_FILE_BYTES} bytes')
            raw = Path(root['path'], relative).read_bytes()
            digest_rows.append([relative, _sha(raw), len(raw)])
            self.document(root['name'], relative, raw)
        if _walk_directory(root) != before:
            raise AdmissionRefused(f'root {root["name"]} changed during inventory')
        return {'name': root['name'], 'kind': 'directory', 'path': root['path'],
                'held_out_payloads': root['held_out_payloads'],
                'excluded': sorted(root['exclude'], key=lambda row: row['path']),
                'files_scanned': len(files), 'files_skipped_by_suffix': skipped,
                'unfollowed_symlinks': symlinks, 'git_storage_skipped': git_dirs,
                'content_digest': _sha(canonical_bytes(digest_rows))}

    def scan_git(self, root, directory_roots):
        repo = root['path']
        refs = _git_refs(repo)
        tips = set(refs.values())
        worktrees, lost = [], []
        for row in _git_worktrees(repo):
            path = row['worktree']
            if _under(path, self.lost_root):
                lost.append(path)
                continue
            if not os.path.isdir(path):
                raise AdmissionRefused(f'git worktree is missing: {path}')
            if not any(_under(path, d['path']) and not any(
                    _under(path, e['path']) for e in d['exclude']) for d in directory_roots):
                raise AdmissionRefused(f'git worktree not covered by a directory root: {path}')
            if 'HEAD' in row:
                tips.add(row['HEAD'])
            worktrees.append(path)
        remotes = _git(repo, 'remote').decode().split()
        advert_sha = None
        if remotes and root['advertisement'] is None:
            raise AdmissionRefused(f'git root {root["name"]} has remotes {remotes} but no fresh '
                                   'remote advertisement')
        if root['advertisement'] is not None:
            advert = _read_small(root['advertisement'], 'remote advertisement')
            advert_sha = _sha(advert)
            for line in advert.decode().splitlines():
                oid = line.split('\t')[0].strip()
                if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', oid):
                    raise AdmissionRefused('remote advertisement line is malformed')
                check = subprocess.run([GIT, '-C', repo, 'cat-file', '-e', oid + '^{object}'],
                                       capture_output=True, env={'PATH': '/usr/bin:/bin'})
                if check.returncode != 0:
                    raise AdmissionRefused(f'remote advertisement names {oid} absent locally: '
                                           'stale inventory')
                tips.add(oid)
        blobs = _git_blobs(repo, sorted(tips))
        for path, oid, raw in blobs:
            self.document(root['name'], path, raw, oid, git=True)
        if _git_refs(repo) != refs:
            raise AdmissionRefused(f'git root {root["name"]} refs changed during inventory')
        return {'name': root['name'], 'kind': 'git', 'path': repo,
                'held_out_payloads': root['held_out_payloads'], 'refs': refs,
                'scanned_tips': sorted(tips), 'worktrees_covered': sorted(worktrees),
                'remotes': sorted(remotes), 'advertisement_sha256': advert_sha,
                'blobs_scanned': len(blobs),
                'content_digest': _sha(canonical_bytes(sorted(oid for _, oid, _ in blobs)))}, lost


# Publication ---------------------------------------------------------------------

def _publish(output, raw):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / f'.{output.name}.{os.getpid()}.tmp'
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, output)  # never replaces an existing report
    finally:
        os.unlink(temporary)
    directory = os.open(output.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


# Entry points --------------------------------------------------------------------

def admit(*, protocol_path, comparison_set_path, output_path, execute=False,
          go_record_path=None, held_out_go_record_path=None, lost_root=None):
    """Plan (default) or execute S1. Returns the plan or a verdict summary."""
    protocol_raw, protocol, roster = _load_protocol(protocol_path)
    declaration_raw, declaration = _load_declaration(comparison_set_path)
    derived = lost_root is None
    lost_root = lost_root_from_protocol(protocol) if derived else _canonical_path(
        lost_root, 'lost root')
    lost = _lost_root_record(protocol, lost_root, derived)
    roots = declaration['roots']
    blockers = [problem for root in roots for problem in _root_problems(root, lost_root)]
    if lost['status'] == 'present-refused':
        blockers.append(f'frozen lost root {lost_root} is present; its exception premise fails')
    needs_held_out_go = any(root['held_out_payloads'] for root in roots)
    if not execute:
        plan = {'mode': 'plan-only', 'stage': S1_GO_STAGE, 'writes': [], 'contents_read': False,
                'protocol_sha256': PROTOCOL_SHA256, 'comparison_set_sha256': _sha(declaration_raw),
                'roster': roster, 'roots': [{key: root[key] for key in ('name', 'kind', 'path')}
                                            for root in roots],
                'lost_root': lost, 'blockers': blockers,
                'required_go': {'stage': S1_GO_STAGE, 'protocol_sha256': PROTOCOL_SHA256},
                'required_held_out_go': ({'stage': HELD_OUT_GO_STAGE,
                                          'protocol_sha256': PROTOCOL_SHA256}
                                         if needs_held_out_go else None),
                'would_write_on_execute': str(output_path)}
        return plan
    go_raw, _ = _load_go(go_record_path, S1_GO_STAGE, 'S1 GO record')
    held_raw = None
    if held_out_go_record_path is not None:
        held_raw, _ = _load_go(held_out_go_record_path, HELD_OUT_GO_STAGE, 'D2 held-out GO record')
    if needs_held_out_go and held_raw is None:
        raise AdmissionRefused('a root declares held-out payloads; D2 requires a separate '
                               f'{HELD_OUT_GO_STAGE!r} GO record')
    output = Path(_canonical_path(os.path.abspath(output_path), 'output'))
    if os.path.lexists(output):
        raise AdmissionRefused(f'output must be a fresh path: {output}')
    if any(_under(str(output), root['path']) for root in roots) or _under(str(output), lost_root):
        raise AdmissionRefused('output lies inside a comparison root')
    if blockers:
        raise AdmissionRefused('; '.join(blockers))

    scan = _Scan(lost_root)
    directories = [root for root in roots if root['kind'] == 'directory']
    root_reports, lost_worktrees = [], []
    for root in roots:
        if root['kind'] == 'directory':
            root_reports.append(scan.scan_directory(root))
        else:
            record, lost_paths = scan.scan_git(root, directories)
            root_reports.append(record)
            lost_worktrees.extend(lost_paths)

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
    lost.update({'git_worktrees_excluded': sorted(lost_worktrees),
                 'max_observed_prior_puck_id': scan.max_puck, 'mitigation_holds': mitigation})

    def key(row):
        return (row['root'], row['path'], row.get('pointer', ''), row.get('scene_id', 0))

    report = {
        'kind': REPORT_KIND, 'version': 1, 'stage': S1_GO_STAGE, 'protocol_id': PROTOCOL_ID,
        'verdict': verdict, 'refusal_reasons': reasons,
        'inputs': {
            'protocol': {'path': str(protocol_path), 'sha256': _sha(protocol_raw)},
            'comparison_set': {'path': str(comparison_set_path), 'sha256': _sha(declaration_raw)},
            'go_record': {'path': str(go_record_path), 'sha256': _sha(go_raw)},
            'held_out_go_record': None if held_raw is None else {
                'path': str(held_out_go_record_path), 'sha256': _sha(held_raw)},
        },
        'roster': roster,
        'reservation': None if reasons else {
            'scene_ids': list(NEW_SCENE_IDS), 'collection': list(COLLECTION_SCENE_IDS),
            'development': list(DEVELOPMENT_SCENE_IDS), 'lineage_protocol_sha256': PROTOCOL_SHA256},
        'roots': root_reports,
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
            'scanned_suffixes': list(SCANNED_SUFFIXES), 'puck_namespace': list(PUCK_NAMESPACE),
            'typed_fields': 'JSON keys with scene/layout/seed tokens (not model/training/rng '
                            'seeds, not counts/bytes/hashes) and their descendants; Markdown via '
                            'puck_scene_markdown explicit-label grammar',
            'untyped_mentions': 'diagnostic only, never collisions (v3 semantic parsing rule)',
        },
        'claims': {'held_out_payloads_compared': False, 'held_out_read': False,
                   'scenes_minted': False, 'simulator_executed': False,
                   'models_loaded': False, 'qualification_claims': []},
    }
    for path, raw in ((protocol_path, protocol_raw), (comparison_set_path, declaration_raw),
                      (go_record_path, go_raw), (held_out_go_record_path, held_raw)):
        if raw is not None and Path(path).read_bytes() != raw:
            raise AdmissionRefused(f'input changed during admission: {path}')
    raw = canonical_bytes(report)
    _publish(output, raw)
    return {'verdict': verdict, 'output': str(output), 'report_sha256': _sha(raw),
            'refusal_reasons': reasons}


def main(argv=None):
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
                       held_out_go_record_path=args.held_out_go_record)
    except AdmissionRefused as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return 2
    sys.stdout.write(canonical_bytes(result).decode())
    if not args.execute:
        return 1 if result['blockers'] else 0
    return 0 if result['verdict'] == 'admitted' else 1
