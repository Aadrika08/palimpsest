#!/usr/bin/env python3
"""Run one separately accounted same-host offline check with frozen supervision.

This operational follow-up never changes the 111-unit scientific campaign.
Native/cache output uses inventory monitoring, not a strict prewrite quota.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

FROZEN_COMMIT = 'cc57edf9f70323926237d887d766627d8c9cdd42'
PROTOCOL_SHA256 = '570a4afe8179425bb2b25b86364470af34052ecc4929b74f207c279076728860'
ORIGINAL_DEADLINE = 1793860506.2223496
GiB, MiB = 1024**3, 1024**2
TOTAL_CAP, REPORT_RESERVE = 16 * GiB, 64 * MiB
SCRIPT = Path(__file__).resolve()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def deadline(now, requested):
    require(math.isfinite(requested), 'deadline must be finite')
    result = min(now + 900, requested, ORIGINAL_DEADLINE)
    require(result > now, 'follow-up deadline already expired')
    return result


def pins(repo, protocol):
    require(protocol.resolve() == (repo / 'paper/studies/authority_replay_v1/protocol.json').resolve(),
            'protocol must be the frozen runtime protocol')
    require(git(repo, 'rev-parse', 'HEAD') == FROZEN_COMMIT, 'frozen commit differs')
    require(digest(protocol) == PROTOCOL_SHA256, 'frozen protocol hash differs')


def required_roots(repo):
    return {(repo.parent / name / 'runs/paper-authority-replay-v1').resolve()
            for name in ('paper-systems', 'authority-study-recovery', repo.name)}


def locations(repo, retained, output):
    require(len(retained) == 3 and set(retained) == required_roots(repo),
            'all three distinct retained campaign roots are required')
    require(all(path.is_dir() for path in retained), 'retained root missing')
    require(not output.exists() and not output.is_symlink(), 'fresh nonexistent output required')
    require(all(not output.is_relative_to(path) and not path.is_relative_to(output) for path in retained),
            'follow-up output must not overlap a retained root')


def load_frozen(repo):
    # A fresh CLI interpreter imports only the frozen package. Refuse module
    # cache contamination rather than silently reusing another worktree's code.
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / 'src'))
    module = importlib.import_module('paper.studies.authority_replay_v1.campaign')
    for name in ('campaign', 'common', 'analyze'):
        loaded = sys.modules['paper.studies.authority_replay_v1.' + name]
        require(Path(loaded.__file__).resolve().is_relative_to(repo), 'nonfrozen module import refused')
    return module


def retained_metadata(retained):
    return {str(root): {str(path.relative_to(root)): digest(path)
                       for path in (root / 'identity.json', root / 'analysis/summary.json',
                                    root / 'analysis/campaign-manifest.json') if path.is_file()}
            for root in retained}


class CumulativeGuard:
    def __init__(self, base, campaign, retained, root, end, script_hash):
        self.base, self.campaign, self.retained = base, campaign, retained
        self.root, self.end, self.script_hash = root, end, script_hash

    def check_identity(self):
        self.base.check_identity()
        require(digest(SCRIPT) == self.script_hash, 'launcher script bytes changed')

    def check(self):
        self.base.check()
        require(time.time() < self.end, 'follow-up deadline reached')
        total = sum(self.campaign.tree_size(path) for path in (*self.retained, self.root))
        require(total <= TOTAL_CAP - REPORT_RESERVE, 'cumulative original16GiB cap/report reserve crossed')
        require(self.campaign.tree_size(self.root / 'offline_reproduction') <= 10 * GiB,
                'follow-up offline unit cap crossed')


def run(args):
    repo, protocol, assets = (path.resolve() for path in (args.frozen_repo, args.protocol, args.assets))
    retained = [path.resolve() for path in args.retained_root]
    require(not args.output.is_symlink(), 'fresh nonsymlink output required')
    output = args.output.resolve()
    locations(repo, retained, output)
    pins(repo, protocol)
    started = time.time()
    end = deadline(started, args.deadline)
    script_hash = digest(SCRIPT)
    campaign = load_frozen(repo)
    identity = campaign.campaign_identity(repo, protocol, assets)
    phase = campaign.plan(protocol, assets, output, end)[-1]
    require(phase.kind == 'offline_reproduction', 'frozen offline phase missing')
    retained_before = retained_metadata(retained)
    initial_bytes = {str(path): campaign.tree_size(path) for path in retained}
    require(sum(initial_bytes.values()) < TOTAL_CAP - REPORT_RESERVE, 'no cumulative output budget remains')
    require(shutil.disk_usage(output.parent).free >= 6 * GiB + 512 * MiB,
            'free reserve insufficient for follow-up admission')
    launcher_repo = SCRIPT.parents[2]
    admission = {'runtime_identity': identity, 'launcher_commit': git(launcher_repo, 'rev-parse', 'HEAD'),
                 'launcher_script_sha256': script_hash, 'started_unix': started, 'deadline_unix': end,
                 'requested_deadline_unix': args.deadline, 'original_deadline_unix': ORIGINAL_DEADLINE,
                 'retained_roots_bytes': initial_bytes, 'retained_metadata_sha256': retained_before,
                 'original_aggregate_cap_bytes': TOTAL_CAP, 'report_reserve_bytes': REPORT_RESERVE,
                 'offline_unit_cap_bytes': 10 * GiB, 'minimum_free_bytes': 6 * GiB,
                 'admission_headroom_bytes': 512 * MiB, 'command': phase.command,
                 'environment': {key: os.environ.get(key) for key in
                                 ('UV_LINK_MODE', 'UV_CACHE_DIR', 'PATH', 'PYTHONDONTWRITEBYTECODE')},
                 'interpreter': {'executable': sys.executable, 'version': sys.version},
                 'frozen_phase_environment': {'PYTHONPATH': os.pathsep.join(map(str, (repo, repo / 'src', repo / 'scripts'))),
                                              'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg',
                                              'OMP_NUM_THREADS': '2', 'CUDA_VISIBLE_DEVICES': ''},
                 'policy': 'Actual cumulative inventory monitored; no full10GiB aggregate reservation or strict native prewrite quota.',
                 'scope': 'Separate operational same-host clean-checkout; scientific campaign rows unchanged.',
                 'replaces_scientific_row': False}
    if args.plan_only:
        print(json.dumps(admission, sort_keys=True, indent=2))
        return 0
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'admission.json', admission)
    base = campaign.Guard(output, protocol, assets, identity, end)
    guard = CumulativeGuard(base, campaign, retained, output, end, script_hash)
    report = {'status': 'failed', 'scope': admission['scope'], 'replaces_scientific_row': False,
              'runtime_identity': identity, 'launcher_script_sha256': script_hash,
              'scientific_campaign_unit_id': None}
    try:
        guard.check_identity()
        guard.check()
        process = campaign.run_phase(phase, root=output, deadline=end, guard=guard)
        report['process'] = process
        pins(repo, protocol)
        guard.check_identity()
        report['runtime_identity_at_end'] = campaign.campaign_identity(repo, protocol, assets)
        require(report['runtime_identity_at_end'] == identity, 'frozen runtime identity changed')
        guard.check()
        require(process.get('status') == 'exited' and process.get('returncode') == 0
                and not process.get('cleanup_error') and not process.get('cleanup_errors'),
                'offline process or owned-process cleanup did not succeed')
        row = campaign.offline_row(phase.output, identity)
        report['offline_validation'] = row
        require(row['status'] == 'completed', row.get('reason', 'offline validation failed'))
        require(retained_metadata(retained) == retained_before, 'retained campaign metadata changed')
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        report['ended_unix'] = time.time()
        report['cumulative_output_bytes'] = sum(campaign.tree_size(path) for path in (*retained, output))
        report['retained_metadata_unchanged'] = retained_metadata(retained) == retained_before
        report['launcher_script_unchanged'] = digest(SCRIPT) == script_hash
        report['report_sha256'] = {str(path.relative_to(output)): digest(path) for path in
                                  (output / 'admission.json', output / 'commands/offline_reproduction/command.json',
                                   output / 'commands/offline_reproduction/process.json',
                                   output / 'commands/offline_reproduction/supervisor.json',
                                   phase.output / 'report.json', phase.output / 'setup.json',
                                   phase.output / 'full-flynn/verification.json') if path.is_file()}
        if not report['retained_metadata_unchanged'] or not report['launcher_script_unchanged']:
            report['status'] = 'failed'
        write_json(output / 'operational-result.json', report)
    return int(report['status'] != 'passed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frozen-repo', 'protocol', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--retained-root', type=Path, action='append', required=True)
    parser.add_argument('--deadline', type=float, default=ORIGINAL_DEADLINE)
    parser.add_argument('--plan-only', action='store_true')
    return run(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
