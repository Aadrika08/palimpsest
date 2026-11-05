"""Sequential, fresh-output campaign coordinator; --plan-only never runs a unit.

Driver storage guards cover cooperative output. Polling native output is monitoring,
not a strict filesystem quota. Results remain under output/analysis for review.
"""
import argparse
import csv
import ctypes
import hashlib
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from paper.studies.authority_replay_v1.common import (
    append_row, campaign_identity, declared_units, load_protocol, parse_json,
    read_rows, require, sha256_file)
from paper.studies.authority_replay_v1.analyze import load_complete_rows, summarize

REPO = Path(__file__).resolve().parents[3]
STUDY = REPO / 'paper/studies/authority_replay_v1'
GiB = 1024**3
MiB = 1024**2


@dataclass(frozen=True)
class Phase:
    name: str
    kind: str
    output: Path
    command: list[str]


def plan(protocol, assets, output, deadline):
    protocol, assets, output = map(lambda p: Path(p).absolute(), (protocol, assets, output))
    phases = []
    for name, kind, driver, extra in (
        ('fault_matrix', 'fault', 'fault_matrix.py', []),
        ('continuation', 'continuation', 'repeatability.py', ['--kind', 'continuation']),
        ('replay', 'replay', 'repeatability.py', ['--kind', 'replay']),
        ('execution_overhead', 'execution_overhead', 'overhead.py', ['--kind', 'execution']),
        ('operation_cost', 'operation_cost', 'overhead.py', ['--kind', 'operations', '--replay-root', str(output / 'replay')]),
    ):
        command = [sys.executable, str(STUDY / driver), '--protocol', str(protocol), '--assets', str(assets),
                   '--output', str(output / name), '--campaign-root', str(output),
                   '--campaign-deadline-epoch', str(float(deadline)), *extra]
        phases.append(Phase(name, kind, output / name, command))
    phases.append(Phase('offline_reproduction', 'offline_reproduction', output / 'offline_reproduction',
                        [sys.executable, str(REPO / 'scripts/verify_offline.py'), '--repo', str(REPO),
                         '--assets', str(assets), '--output', str(output / 'offline_reproduction'),
                         '--setup', '--full-flynn', '--duration', '55']))
    return phases


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def files(root):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def tree_size(root):
    return sum(p.stat().st_size for p in files(root))


def boundary(row):
    if row.get('status') in ('timeout', 'refused', 'incomplete'):
        return f"unit {row['unit_id']}: {row.get('reason', row['status'])}"
    if (row.get('resource_boundary') or row.get('verifier_report', {}).get('resource_boundary')
            or row.get('process', {}).get('stop_reason') or row.get('error', {}).get('resource_limit')):
        return f"unit resource boundary: {row['unit_id']}"
    error = row.get('error', {})
    if error.get('type') in ('SourceMutation', 'IdentityDrift', 'OutputCap', 'CampaignOutputCap'):
        return f"unit identity/resource boundary: {row['unit_id']}"
    return None


class Guard:
    def __init__(self, root, protocol, assets, identity, deadline):
        self.root, self.protocol, self.assets = root, protocol, assets
        self.identity, self.deadline = identity, deadline
        self.resources = load_protocol(protocol).resources

    def check(self):
        require(time.time() < self.deadline, 'campaign deadline reached')
        require(tree_size(self.root) <= self.resources['campaign_max_output_bytes'], 'campaign output cap crossed')
        require(shutil.disk_usage(self.root).free >= self.resources['minimum_free_bytes'], 'filesystem free reserve crossed')
        require(campaign_identity(REPO, self.protocol, self.assets) == self.identity, 'campaign identity drift')
        # Unit directories are assigned by existing driver CLIs. Shared runtime-base
        # belongs to the aggregate budget, never to a single ordinary unit.
        for phase in plan(self.protocol, self.assets, self.root, self.deadline):
            if not phase.output.exists():
                continue
            if phase.kind == 'offline_reproduction':
                require(tree_size(phase.output) <= self.resources['offline_unit_max_output_bytes'], 'offline unit output cap crossed')
                continue
            for path in phase.output.iterdir():
                if path.is_dir() and not path.is_symlink() and not (phase.kind == 'fault' and path.name == 'runtime-base'):
                    require(tree_size(path) <= self.resources['ordinary_unit_max_output_bytes'], f'ordinary unit output cap crossed: {path.name}')
            rows = phase.output / 'rows.jsonl'
            if rows.exists():
                # Read only complete appends while the writer is running. Final
                # analysis reads the entire file strictly, including torn tails.
                content = rows.read_text()
                complete = content[:content.rfind('\n') + 1]
                for line in complete.splitlines():
                    row = parse_json(line)
                    require(row.get('identity') == self.identity, 'emitted row identity drift')
                    reason = boundary(row)
                    require(reason is None, reason or '')


def _processes():
    result = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                fields = (entry / 'stat').read_text().rsplit(') ', 1)[1].split()
                result[int(entry.name)] = (int(fields[1]), int(fields[19]), fields[0])
            except (OSError, ValueError, IndexError):
                continue
    return result


def _remember(child, known, baseline):
    current = _processes()
    # A Linux subreaper adopts descendants whose intermediate owner exited,
    # including descendants which called setsid before our first monitor poll.
    known.update({pid: values[1] for pid, values in current.items()
                  if values[0] == os.getpid() and pid != child.pid and pid not in baseline})
    parents = {child.pid, *known}
    while True:
        found = {pid: values[1] for pid, values in current.items() if values[0] in parents and pid not in parents}
        if not found:
            break
        known.update(found)
        parents.update(found)


def _cleanup(child, known, baseline):
    _remember(child, known, baseline)
    # The child is session leader and cannot reuse its PID until wait() reaps it.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    current = _processes()
    for pid, start in known.items():
        if pid in current and current[pid][1] == start:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    child.wait()
    # Once intermediate parents die, adopted children can be reaped by PID.
    end = time.monotonic() + 2
    pending = set(known)
    while pending and time.monotonic() < end:
        for pid in list(pending):
            try:
                reaped, _ = os.waitpid(pid, os.WNOHANG)
                if reaped:
                    pending.remove(pid)
            except ChildProcessError:
                if pid not in _processes():
                    pending.remove(pid)
        if pending:
            time.sleep(.01)
    require(not pending, f'owned descendants not reaped: {sorted(pending)}')


def run_phase(phase, *, root, deadline, guard):
    log = root / 'commands' / phase.name
    log.mkdir(parents=True, exist_ok=False)
    write_json(log / 'command.json', {'argv': phase.command, 'cwd': str(REPO), 'deadline_unix': deadline})
    record = {'command_record': str(log / 'command.json'), 'stdout': str(log / 'stdout.log'),
              'stderr': str(log / 'stderr.log'), 'status': 'failed', 'started_unix': time.time()}
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(map(str, (REPO, REPO / 'src', REPO / 'scripts'))),
           'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2', 'CUDA_VISIBLE_DEVICES': ''}
    child, known = None, {}
    baseline = set(_processes())
    libc = ctypes.CDLL(None, use_errno=True)
    prior_subreaper = ctypes.c_int()
    require(libc.prctl(37, ctypes.byref(prior_subreaper), 0, 0, 0) == 0, 'cannot read child-subreaper state')
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'cannot enable child-subreaper cleanup')
    previous = {}
    def interrupted(number, frame):
        raise InterruptedError(f'coordinator signal {number}')
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, interrupted)
        with (log / 'stdout.log').open('xb') as stdout, (log / 'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(phase.command, cwd=REPO, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            record['pid'] = child.pid
            timeout = min(deadline, record['started_unix'] + 900) if phase.kind == 'offline_reproduction' else deadline
            while child.poll() is None:
                _remember(child, known, baseline)
                guard.check()
                require(time.time() < timeout, 'offline unit timeout' if phase.kind == 'offline_reproduction' else 'campaign deadline')
                time.sleep(.1)
            # Fast native writes can finish between polls.
            guard.check()
            require(time.time() < timeout, 'phase deadline crossed at exit')
            record.update(status='exited', returncode=child.returncode)
    except Exception as exc:
        record.update(reason=str(exc), error_type=type(exc).__name__)
    finally:
        if child is not None:
            try:
                _cleanup(child, known, baseline)
            except Exception as exc:
                record.update(status='failed', cleanup_error=str(exc))
            record.setdefault('returncode', child.returncode)
        libc.prctl(36, prior_subreaper.value, 0, 0, 0)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        record['ended_unix'] = time.time()
        record['owned_descendants'] = [{'pid': pid, 'start_ticks': start} for pid, start in sorted(known.items())]
        write_json(log / 'process.json', record)
    return record


def offline_row(output, identity):
    row = dict(schema_version=1, study_id='authority_replay_v1', unit_id='offline_reproduction/0',
               kind='offline_reproduction', repetition=0, identity=identity, status='failed', metrics={},
               scope='same-host clean-checkout', independent_machine_reproduction=False)
    try:
        report = parse_json((output / 'report.json').read_text())
        row['report'] = report
        require(report.get('status') == 'passed', 'offline report did not pass')
        source = report.get('runtime_source', {})
        require(source.get('commit') == identity['commit'] and source.get('files_sha256'), 'offline source identity missing or mismatched')
        expected_source = {k: v for k, v in identity['runtime_source_sha256'].items()
                           if k in ('pyproject.toml', 'uv.lock') or Path(k).parent.as_posix() == 'src/palimpsest'}
        require(source['files_sha256'] == expected_source, 'offline source hashes incomplete or differ')
        require(report.get('runtime_source_at_end') == source and report.get('runtime_source_unchanged') is True, 'offline end source identity differs')
        setup = output / 'setup.json'
        require(setup.is_file(), 'offline fresh-checkout setup missing')
        fresh = parse_json(setup.read_text())
        require(fresh.get('status') == 'passed' and fresh.get('source') == source, 'offline fresh-checkout identity differs')
        verification = parse_json((output / 'full-flynn/verification.json').read_text())
        require(verification.get('status') == 'passed' and verification.get('controller') == 'flynn'
                and verification.get('device') == 'cpu', 'full CPU FLYNN result did not pass')
        row.update(status='completed', full_flynn_report=verification)
    except (OSError, ValueError, KeyError) as exc:
        row['reason'] = str(exc)
    return row


def _finish(protocol, output, identity, phases, records, stopped):
    analysis = output / 'analysis'
    analysis.mkdir()
    raw_rows, paths, row_errors = [], [], []
    for phase in phases:
        path = phase.output / 'rows.jsonl'
        if path.exists():
            paths.append(path)
            try:
                raw_rows.extend(read_rows(path))
            except (ValueError, OSError) as exc:
                row_errors.append(str(exc))
                # Recover descriptors for accounting only. The original strict
                # read error still prevents any successful final analysis.
                content = path.read_text()
                for line in content[:content.rfind('\n') + 1].splitlines():
                    try:
                        row = parse_json(line)
                        if isinstance(row, dict) and isinstance(row.get('unit_id'), str):
                            raw_rows.append(row)
                    except ValueError:
                        continue
    recovered = output / 'recovered-rows.jsonl'
    for phase in phases:
        for unit in declared_units(protocol):
            if unit['kind'] != phase.kind or phase.kind == 'offline_reproduction':
                continue
            if phase.kind in ('continuation', 'replay'):
                snapshot = phase.output / f"seed-{unit['seed']}" / 'row.json'
            elif phase.kind == 'fault':
                snapshot = phase.output / unit['unit_id'].replace('/', '__') / 'row.json'
            else:
                snapshot = phase.output / (unit['unit_id'].replace('/', '__') + '.json')
            if not snapshot.exists():
                continue
            try:
                row = parse_json(snapshot.read_text())
                require(isinstance(row, dict) and row.get('unit_id') == unit['unit_id'],
                        f'inconsistent unit snapshot descriptor: {snapshot}')
                matches = [r for r in raw_rows if r['unit_id'] == unit['unit_id']]
                if matches:
                    keys = (*unit, 'identity', 'status', 'metrics', 'schema_version', 'study_id')
                    require(all(row.get(k) == matches[0].get(k) for k in keys),
                            f'inconsistent emitted unit snapshot: {snapshot}')
                else:
                    append_row(recovered, row)
                    raw_rows.append(row)
            except (ValueError, OSError) as exc:
                row_errors.append(str(exc))
    if recovered.exists():
        paths.append(recovered)
    seen = {r['unit_id'] for r in raw_rows}
    missing = output / 'unexecuted.jsonl'
    for unit in declared_units(protocol):
        if unit['unit_id'] not in seen:
            append_row(missing, dict(schema_version=1, study_id=protocol.study_id, **unit, identity=identity,
                                    status='incomplete', metrics={}, reason=stopped or 'phase emitted no row; unit not completed'))
    if missing.exists():
        paths.append(missing)
    manifest = {'identity': identity, 'phases': records, 'rows': [str(p) for p in paths],
                'stopped_reason': stopped, 'analysis_status': 'failed',
                'limitations': ['Same-host clean-checkout; independent machine reproduction remains external.',
                                'Polling native output is monitoring, not a strict filesystem quota.',
                                'Offline cache/link setup reserves 512 MiB physical headroom, monitors the 6 GiB free floor, '
                                'and limits logical directory inventory to the protocol cap; uv/npm output has no strict prewrite quota.'],
                'analysis_paths': [str(analysis / n) for n in ('summary.json', 'rows.csv', 'failures.json', 'fault-traces.jsonl', 'raw-inventory.json', 'campaign-manifest.json')]}
    try:
        require(not row_errors, '; '.join(row_errors))
        summary = summarize(protocol, load_complete_rows(protocol, paths, identity))
        require(summary['declared_units'] == 111, 'expected exactly 111 descriptors')
        write_json(analysis / 'summary.json', summary)
        write_json(analysis / 'failures.json', summary['failures'])
        with (analysis / 'rows.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['unit_id', 'kind', 'status', 'row_json'])
            for row in summary['rows']:
                writer.writerow([row['unit_id'], row['kind'], row['status'], json.dumps(row, sort_keys=True, allow_nan=False)])
        with (analysis / 'fault-traces.jsonl').open('w') as stream:
            # Allowlist compact semantic evidence; raw trace strings/paths remain raw.
            keys = ('unit_id', 'case_id', 'seed', 'variant', 'condition', 'status', 'silent_acceptance',
                    'explicit_detection', 'correct_recovery', 'benign_false_rejection', 'palimpsest_outcome', 'outcome_scope')
            for row in summary['rows']:
                if row['kind'] == 'fault':
                    stream.write(json.dumps({k: row[k] for k in keys if k in row}, sort_keys=True) + '\n')
        manifest['analysis_status'] = 'passed'
        result = int(bool(stopped) or any(row['status'] != 'completed' for row in summary['rows']))
    except (ValueError, OSError) as exc:
        manifest['analysis_error'] = str(exc)
        result = 1
    write_json(analysis / 'campaign-manifest.json', manifest)
    inventory = [{'path': str(p.relative_to(output)), 'type': 'file', 'size_bytes': p.stat().st_size, 'sha256': sha256_file(p)}
                 for p in sorted(files(output)) if not p.is_relative_to(analysis)]
    for directory, dirs, names in os.walk(output, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_relative_to(analysis))
        for name in sorted([*dirs, *names]):
            path = Path(directory) / name
            if path.is_symlink():
                target = os.readlink(path)
                inventory.append({'path': str(path.relative_to(output)), 'type': 'symlink',
                                  'target': target, 'size_bytes': path.lstat().st_size,
                                  'sha256': hashlib.sha256(os.fsencode(target)).hexdigest()})
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
    write_json(analysis / 'raw-inventory.json', sorted(inventory, key=lambda item: item['path']))
    return result


def run(protocol_path, assets, output):
    require(not Path(output).is_symlink(), 'campaign requires a fresh nonsymlink output root')
    protocol_path, assets, output = map(lambda p: Path(p).resolve(), (protocol_path, assets, output))
    require(not output.exists() and not output.is_symlink(), 'campaign requires a fresh nonexistent output root')
    protocol = load_protocol(protocol_path)
    identity = campaign_identity(REPO, protocol_path, assets)
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    deadline = started + protocol.resources['campaign_timeout_seconds']
    write_json(output / 'identity.json', identity)
    write_json(output / 'preflight.json', {
        'resources': protocol.resources, 'available_free_bytes': shutil.disk_usage(output).free,
        'offline_admission_headroom_bytes': protocol.resources['ordinary_unit_max_output_bytes'],
        'cache_link_mode': {'UV_LINK_MODE': os.environ.get('UV_LINK_MODE', 'tool default; actual mode not inferred'),
                            'npm': 'existing cache required; installer output is monitored'},
        'offline_allocation_policy': 'Logical inventory cap; physical free reserve actively monitored. '
                                     'No worst-case reservation of the whole cached environment.',
    })
    write_json(output / 'campaign-clock.json', dict(identity=identity, started_unix=started, deadline_unix=deadline))
    guard = Guard(output, protocol_path, assets, identity, deadline)
    phases, records, stopped = plan(protocol_path, assets, output, deadline), [], None
    for phase in phases:
        record = {'name': phase.name, 'kind': phase.kind, 'command': phase.command, 'output': str(phase.output),
                  'rows': str(phase.output / 'rows.jsonl'),
                  'process_record': str(output / 'commands' / phase.name / 'process.json')}
        if not stopped:
            try:
                guard.check()
                allowance = protocol.resources['offline_unit_max_output_bytes'] if phase.kind == 'offline_reproduction' else protocol.resources['ordinary_unit_max_output_bytes']
                require(tree_size(output) + allowance <= protocol.resources['campaign_max_output_bytes'], 'campaign output admission cap')
                headroom = protocol.resources['ordinary_unit_max_output_bytes'] if phase.kind == 'offline_reproduction' else allowance
                require(shutil.disk_usage(output).free - headroom >= protocol.resources['minimum_free_bytes'], 'free reserve insufficient for unit admission')
                process = run_phase(phase, root=output, deadline=deadline, guard=guard)
                record['process'] = process
                if phase.kind == 'offline_reproduction':
                    phase.output.mkdir(exist_ok=True)
                    row = offline_row(phase.output, identity)
                    if process['status'] != 'exited' or process.get('returncode') != 0:
                        row.update(status='failed', reason=process.get('reason', 'offline process failed'))
                    append_row(phase.output / 'rows.jsonl', row)
                path = phase.output / 'rows.jsonl'
                emitted = read_rows(path) if path.exists() else []
                expected = [u for u in declared_units(protocol) if u['kind'] == phase.kind]
                if {r['unit_id'] for r in emitted} != {u['unit_id'] for u in expected}:
                    stopped = f'{phase.name}: phase failed before all declared rows were emitted'
                if process['status'] != 'exited':
                    stopped = process.get('reason', 'phase monitoring failure')
                for row in emitted:
                    stopped = boundary(row) or stopped
                guard.check()
            except Exception as exc:
                stopped = str(exc)
                record['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        else:
            record['not_executed_reason'] = stopped
        records.append(record)
    return _finish(protocol, output, identity, phases, records, stopped)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args(argv)
    if args.plan_only:
        protocol = load_protocol(args.protocol)
        print('# resources ' + json.dumps(protocol.resources, sort_keys=True))
        deadline = time.time() + 14400
        for phase in plan(args.protocol, args.assets, args.output, deadline):
            print(shlex.join(phase.command))
        return 0
    return run(args.protocol, args.assets, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
