"""Build and verify the MaleCNS v4 port branches (Amendment 1) from the checked-in hunk manifest.

A port tree is its producing commit plus ONLY the hunks listed in
``docs/plans/m7-navigation-v4-pins/ports.json``. This script never checks out, imports or
runs a producer and opens no data: it reads producing-commit blobs, applies each hunk only
if its ``old`` lines match the base bytes exactly at ``start``, writes blobs and trees with
git plumbing into a private index, and creates one commit per tree with a fixed identity
and date, so the port commit is a deterministic function of the manifest and the base.

``--verify`` (default) checks every ``port/male-v4-<tree>`` branch; ``--build`` creates
missing branches (an existing branch must already be the expected commit); ``--record``
also writes the built commits into the manifest. Any hunk that fails to apply exactly,
any unlisted file or byte difference, a parent other than the producing commit or a
branch at another commit is a refusal (exit 2) and no ref is moved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT/'docs/plans/m7-navigation-v4-pins/ports.json'
SCHEMA = 'm7-navigation-v4-ports-1'
PROTOCOL_SHA256 = '238bc160d26c70273765eb1d51f8280383f99a88bc8f26ec4a829048552594f8'
HUNK_HEADER = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
TRAILER = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'


class PortRefusal(Exception):
    """The port manifest, a base blob or a port branch differs from the listed hunks."""


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def git(repo, *args, data=None, env=None, check=True):
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    done = subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=repo, input=data, capture_output=True,
                          env={**clean, **(env or {})}, timeout=60)
    if check and done.returncode != 0:
        raise PortRefusal(f'git {" ".join(args[:3])} failed: {done.stderr.decode(errors="replace").strip()[:300]}')
    return done


def load_spec(path=SPEC_PATH):
    spec = json.loads(Path(path).read_bytes())
    if spec.get('schema') != SCHEMA or spec.get('protocol_sha256') != PROTOCOL_SHA256:
        raise PortRefusal('Port manifest does not bind the v4 protocol')
    return spec


# --------------------------------------------------------------------------- hunks

def apply_hunks(base, hunks, *, name='file'):
    """Base bytes with exactly the listed hunks applied; refuses any inexact hunk."""
    text = base.decode()
    if not text.endswith('\n') or '\r' in text: raise PortRefusal(f'{name}: LF-terminated base bytes required')
    lines = text[:-1].split('\n')
    spans = sorted((h['start'], h['start'] + max(len(h['old']), 1)) for h in hunks)
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])): raise PortRefusal(f'{name}: overlapping hunks')
    for hunk in sorted(hunks, key=lambda h: h['start'], reverse=True):
        where, start = f'{name}:{hunk["spec_lines"]}', hunk['start']
        if not 1 <= start <= len(lines): raise PortRefusal(f'{where}: start line {start} is outside the base')
        if hunk.get('empty'):
            if hunk['old'] or hunk['new'] or hunk['unchanged_line_contains'] not in lines[start-1]:
                raise PortRefusal(f'{where}: empty hunk site differs from the base')
            continue
        if not hunk['old'] or lines[start-1:start-1+len(hunk['old'])] != hunk['old']:
            raise PortRefusal(f'{where}: hunk does not apply exactly at line {start}')
        lines[start-1:start-1+len(hunk['old'])] = hunk['new']
    return ('\n'.join(lines) + '\n').encode()


def expected_files(repo, spec, tree_id):
    """{path: port bytes} for one tree; each base blob must have its pinned sha256."""
    tree, files = spec['trees'][tree_id], {}
    for path in tree['files']:
        item = spec['files'][path]
        base = git(repo, 'show', f'{tree["base"]}:{path}').stdout
        if sha256(base) != item['base_sha256']: raise PortRefusal(f'{tree_id} {path}: base bytes differ from the pin')
        files[path] = apply_hunks(base, item['hunks'], name=path)
    return files


def diff_ranges(repo, base, commit, path):
    """Old-side ranges [(first, count)] of a zero-context diff of one file."""
    out = git(repo, 'diff', '--no-color', '--no-ext-diff', '-U0', base, commit, '--', path).stdout.decode()
    ranges = []
    for line in out.splitlines():
        if match := HUNK_HEADER.match(line):
            ranges.append((int(match[1]), 1 if match[2] is None else int(match[2])))
    return ranges


def contained(first, count, hunks):
    for hunk in hunks:
        if hunk.get('empty'): continue
        lo, hi = hunk['start'], hunk['start'] + len(hunk['old']) - 1
        if (count == 0 and lo - 1 <= first <= hi) or (count and lo <= first and first + count - 1 <= hi): return True
    return False


# --------------------------------------------------------------------------- commits

def message(spec, tree_id):
    tree = spec['trees'][tree_id]
    hunks = ', '.join(f'{Path(p).name}:{h["spec_lines"]}' for p in tree['files'] for h in spec['files'][p]['hunks']
                      if not h.get('empty'))
    return (f'port({tree_id}): MaleCNS v4 Amendment 1 port of {tree["base"][:7]} for {tree["stage"]}\n\n'
            f'Only the hunks listed in docs/plans/m7-navigation-v4-pins/ports.json: {hunks}.\n\n{TRAILER}\n')


def build_commit(repo, spec, tree_id):
    """The deterministic port commit for one tree (objects written; no ref moved)."""
    tree = spec['trees'][tree_id]
    files = expected_files(repo, spec, tree_id)
    identity = spec['commit_identity']
    with tempfile.TemporaryDirectory() as scratch:
        index = {'GIT_INDEX_FILE': str(Path(scratch)/'index')}
        git(repo, 'read-tree', tree['base'], env=index)
        for path, payload in files.items():
            mode = git(repo, 'ls-tree', tree['base'], '--', path).stdout.decode().split()[0]
            blob = git(repo, 'hash-object', '-w', '--stdin', data=payload).stdout.decode().strip()
            git(repo, 'update-index', '--cacheinfo', f'{mode},{blob},{path}', env=index)
        written = git(repo, 'write-tree', env=index).stdout.decode().strip()
    env = {'GIT_AUTHOR_NAME': identity['name'], 'GIT_AUTHOR_EMAIL': identity['email'], 'GIT_AUTHOR_DATE': identity['date'],
           'GIT_COMMITTER_NAME': identity['name'], 'GIT_COMMITTER_EMAIL': identity['email'],
           'GIT_COMMITTER_DATE': identity['date']}
    return git(repo, 'commit-tree', '--no-gpg-sign', written, '-p', tree['base'], data=message(spec, tree_id).encode(),
               env=env).stdout.decode().strip()


def verify_port(repo, spec, tree_id, commit):
    """Diff-restricted review: base..commit must be exactly the listed hunks, nothing else."""
    tree = spec['trees'][tree_id]
    parents = git(repo, 'rev-list', '--parents', '-n', '1', commit).stdout.decode().split()[1:]
    if parents != [tree['base']]: raise PortRefusal(f'{tree_id}: port parent is not the producing commit {tree["base"]}')
    changed = git(repo, 'diff', '--no-renames', '--name-only', tree['base'], commit).stdout.decode().split()
    if sorted(changed) != sorted(tree['files']):
        raise PortRefusal(f'{tree_id}: changed files {sorted(changed)} differ from the listed {sorted(tree["files"])}')
    expected = expected_files(repo, spec, tree_id)
    for path, payload in expected.items():
        actual = git(repo, 'show', f'{commit}:{path}').stdout
        if actual != payload: raise PortRefusal(f'{tree_id} {path}: port bytes differ from base + listed hunks')
        hunks = spec['files'][path]['hunks']
        for first, count in diff_ranges(repo, tree['base'], commit, path):
            if not contained(first, count, hunks):
                raise PortRefusal(f'{tree_id} {path}: unlisted change at base line {first}')
    return {'tree': tree_id, 'commit': commit, 'base': tree['base'],
            'files': {p: sha256(b) for p, b in expected.items()}}


def branch_commit(repo, branch):
    done = git(repo, 'rev-parse', '--verify', '-q', f'refs/heads/{branch}^{{commit}}', check=False)
    return done.stdout.decode().strip() if done.returncode == 0 else None


def build(repo, spec, *, update_refs=True):
    """Build (or confirm) every port branch; refuses before moving any ref."""
    planned = {}
    for tree_id, tree in spec['trees'].items():
        commit = build_commit(repo, spec, tree_id)
        verify_port(repo, spec, tree_id, commit)
        if tree.get('port_commit') not in (None, commit):
            raise PortRefusal(f'{tree_id}: built {commit} but the manifest records {tree["port_commit"]}')
        existing = branch_commit(repo, tree['branch'])
        if existing not in (None, commit):
            raise PortRefusal(f'{tree_id}: branch {tree["branch"]} exists at {existing}, not the port commit {commit}')
        planned[tree_id] = (commit, existing)
    if update_refs:
        for tree_id, (commit, existing) in planned.items():
            if existing is None:
                git(repo, 'update-ref', f'refs/heads/{spec["trees"][tree_id]["branch"]}', commit, '0'*40)
    return {tree_id: commit for tree_id, (commit, _) in planned.items()}


def verify(repo, spec):
    """Every port branch exists at its recorded commit and passes the diff-restricted review."""
    reports = {}
    for tree_id, tree in spec['trees'].items():
        commit = branch_commit(repo, tree['branch'])
        if commit is None: raise PortRefusal(f'{tree_id}: branch {tree["branch"]} is missing')
        if commit != tree.get('port_commit'):
            raise PortRefusal(f'{tree_id}: branch {tree["branch"]} is at {commit}, not the recorded {tree.get("port_commit")}')
        reports[tree_id] = verify_port(repo, spec, tree_id, commit)
    return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true', help='Verify every port branch (default)')
    mode.add_argument('--build', action='store_true', help='Create missing port branches')
    mode.add_argument('--record', action='store_true', help='Build, then record port commits in the manifest')
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--spec', type=Path, default=SPEC_PATH)
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        if args.record:
            for tree in spec['trees'].values(): tree['port_commit'] = None
            commits = build(args.repo, spec)
            for tree_id, commit in commits.items(): spec['trees'][tree_id]['port_commit'] = commit
            args.spec.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + '\n')
            result = {'status': 'recorded', 'commits': commits}
        elif args.build:
            result = {'status': 'built', 'commits': build(args.repo, spec)}
        else:
            result = {'status': 'verified', 'ports': verify(args.repo, spec)}
    except (PortRefusal, OSError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'refused', 'reason': f'{type(error).__name__}: {error}'})); return 2
    print(json.dumps(result, indent=1, sort_keys=True)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
