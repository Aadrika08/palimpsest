"""Deterministically build the puck v4 S1 comparison-set declaration for this machine.

Lists directory names only (no file contents, registries, or payloads are read)
and writes a fresh canonical JSON declaration for scripts/admit_puck_v4_scene_ids.py.
Unknown siblings of the palimpsest checkout are refused rather than silently dropped.
"""
import argparse
import json
import os
import sys

SHRADDHA = '/home/utkarsh/Work/shraddha'
MAIN = SHRADDHA + '/palimpsest'
CODEX_WORKTREES = '/home/utkarsh/.codex/worktrees'
EVIDENCE = 'palimpsest-authored-test-evidence'
WORKTREE_CONTAINERS = ('.worktrees', 'worktrees', '.claude/worktrees')
SUBMODULE = 'upstream/fly-gym'
ENV_DIRS = {'.venv': 'Python virtual environment (installed third-party packages)',
            'venv': 'Python virtual environment (installed third-party packages)',
            'node_modules': 'JavaScript dependencies (third-party packages)',
            '.tox': 'tox environments (third-party packages)',
            '.mypy_cache': 'type-checker cache', '.ruff_cache': 'linter cache',
            '.pytest_cache': 'pytest cache (test-run bookkeeping)'}
UNRELATED_PROJECTS = {
    'aadrikas-archiv': 'unrelated project (archive); not part of the puck lineage',
    'checks': 'unrelated project (checks tooling); not part of the puck lineage',
    'decision-aware-tsfm': 'unrelated project (time-series forecasting); no puck scenes',
    'decision-aware-tsfm-aadrika3': 'unrelated project (time-series forecasting copy); '
                                    'no puck scenes',
    'posthumus': 'unrelated project; not part of the puck lineage',
}
HELD_OUT_RUNS = ('.worktrees', 'authority-study-final')
LOST_ROOT_NAME = 'brain'


def _raise(error):
    raise ValueError(f'directory listing failed: {error}')


def _env_excludes(tree, skip=()):
    """Bounded name-only walk that finds environment directories to exclude."""
    rows = []
    for directory, dirnames, _ in os.walk(tree, followlinks=False, onerror=_raise):
        keep = []
        for name in sorted(dirnames):
            full = os.path.join(directory, name)
            if name == '.git' or full in skip or os.path.islink(full):
                continue
            if name in ENV_DIRS:
                rows.append({'path': full, 'reason': ENV_DIRS[name]})
            else:
                keep.append(name)
        dirnames[:] = keep
    return rows


def _directory(name, path, *, exclude=(), held_out=True, lost_root_clone=False):
    return {'name': name, 'kind': 'directory', 'path': path,
            'exclude': sorted(exclude, key=lambda row: row['path']),
            'held_out_payloads': held_out, 'lost_root_clone': lost_root_clone}


def _git_root(name, path, advertisement, *, held_out):
    return {'name': name, 'kind': 'git', 'path': path, 'advertisement': advertisement,
            'held_out_payloads': held_out}


def _children(path):
    if not os.path.isdir(path):
        return []
    names = sorted(os.listdir(path))
    for name in names:
        full = os.path.join(path, name)
        if os.path.islink(full) or not os.path.isdir(full):
            raise ValueError(f'unexpected non-directory entry {full}; declare it explicitly')
    return names


def build(*, shraddha=SHRADDHA, main=MAIN, codex_worktrees=CODEX_WORKTREES, advertisement,
          submodule_advertisement=None):
    roots, unscanned = [], []
    trees = [('palimpsest', main)]
    containers = [os.path.join(main, c) for c in WORKTREE_CONTAINERS
                  if os.path.isdir(os.path.join(main, c))]
    worktrees = []
    for container in WORKTREE_CONTAINERS:
        for child in _children(os.path.join(main, container)):
            name = 'worktree-' + container.replace('/', '-') + '-' + child
            worktrees.append((name, os.path.join(main, container, child), container, child))
            trees.append((name, os.path.join(main, container, child)))

    roots.append(_git_root('palimpsest-git', main, advertisement, held_out=True))
    for name, tree in trees:
        if os.path.lexists(os.path.join(tree, SUBMODULE, '.git')):
            git_name = ('palimpsest-git' if tree == main else name + '-git') \
                + '-' + SUBMODULE.replace('/', '-')
            roots.append(_git_root(git_name, os.path.join(tree, SUBMODULE),
                                   submodule_advertisement, held_out=False))

    main_excludes = [{'path': path, 'reason': 'worktree container; each worktree is declared '
                      'as its own directory root'} for path in containers]
    roots.append(_directory('palimpsest-main', main,
                            exclude=_env_excludes(main, skip=set(containers)) + main_excludes))
    for name, tree, container, child in worktrees:
        excludes = []
        if (container, child) == HELD_OUT_RUNS and os.path.isdir(os.path.join(tree, 'runs')):
            runs = os.path.join(tree, 'runs')
            excludes.append({'path': runs, 'reason': 'declared separately as a held-out-'
                             'payload root'})
            roots.append(_directory(name, tree, exclude=_env_excludes(tree, {runs}) + excludes))
            roots.append(_directory(name + '-runs', runs, exclude=_env_excludes(runs)))
        else:
            roots.append(_directory(name, tree, exclude=_env_excludes(tree)))

    for child in _children(codex_worktrees):
        brain = os.path.join(codex_worktrees, child, 'brain')
        if os.path.isdir(brain) and not os.path.islink(brain):
            roots.append(_directory(f'codex-{child}-brain', brain, lost_root_clone=True))

    known = {os.path.basename(main), EVIDENCE, LOST_ROOT_NAME}
    for child in sorted(os.listdir(shraddha)):
        full = os.path.join(shraddha, child)
        if child.startswith('.palimpsest-'):
            roots.append(_directory('fixture-' + child, full, exclude=_env_excludes(full),
                                    held_out=False))
        elif child in UNRELATED_PROJECTS:
            unscanned.append({'path': full, 'reason': UNRELATED_PROJECTS[child]})
        elif child not in known:
            raise ValueError(f'unclassified sibling {full}: add it as a root or an '
                             'unscanned project with a reason')
    evidence = os.path.join(shraddha, EVIDENCE)
    if os.path.isdir(evidence):
        own = [{'path': os.path.join(evidence, child), 'reason': 'puck v4 S1 output or '
                'attempt ledger (written by this stage)'}
               for child in sorted(os.listdir(evidence)) if child.startswith('puck-v4-s1-')]
        roots.append(_directory(EVIDENCE, evidence, exclude=_env_excludes(
            evidence, {row['path'] for row in own}) + own))
    return {'kind': 'puck-v4-s1-comparison-set-v1', 'version': 1, 'roots': roots,
            'unscanned': unscanned}


def render(declaration):
    return json.dumps(declaration, sort_keys=True, indent=1, ensure_ascii=False).encode() + b'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--shraddha', default=SHRADDHA)
    parser.add_argument('--main', default=MAIN)
    parser.add_argument('--codex-worktrees', default=CODEX_WORKTREES)
    parser.add_argument('--advertisement', required=True,
                        help='fresh `ls-remote` output for the palimpsest origin')
    parser.add_argument('--submodule-advertisement',
                        help='fresh `ls-remote` output for the upstream/fly-gym origin')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    if os.path.lexists(args.output):
        parser.error(f'output must be a fresh path: {args.output}')
    raw = render(build(shraddha=args.shraddha, main=args.main,
                       codex_worktrees=args.codex_worktrees, advertisement=args.advertisement,
                       submodule_advertisement=args.submodule_advertisement))
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return 0


if __name__ == '__main__':
    sys.exit(main())
