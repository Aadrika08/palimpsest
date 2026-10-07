"""One restore-v2 invocation: driver, independent auditor, and timely close."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from palimpsest.evaluate import bounded_logs


def admission(path, *, recheck=True):
    evidence = Path(__file__).resolve().parent
    repo = evidence.parents[2]
    registration = p.read_json(path)
    if path != evidence/'registration.json' or Path(registration['repo']) != repo:
        raise ValueError('Registered checkout and registration path must be exact')
    if registration.get('mode') != 'restore-v2':
        raise ValueError('This launcher accepts only restore-v2')
    d.validate_v2_registration(registration)
    if Path(registration['output']).exists():
        raise ValueError('Registered output must be absent; no retry')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Native invocation requires a clean committed checkout')
    if recheck:
        d.recheck_v2_inputs(registration)
    return registration


def pipeline(path):
    """Child admission and both scientific stages share the outer watchdog."""
    registration = admission(path)
    driver_code = 1
    try:
        driver_code = d.main(['--registration', str(path)])
    except BaseException as error:
        print(json.dumps({'driver_error':type(error).__name__, 'message':str(error)}), flush=True)
    root = Path(registration['output'])
    audit_code = 1
    if root.exists():
        from scripts import memory_restore_v2_audit as a
        audit_code = a.audit(path)
    close = p.read_json(root/'scientific-close.json') if (root/'scientific-close.json').exists() else {}
    return 0 if driver_code == audit_code == 0 and close.get('narrow_restore_passed') is True else 1


def invalidate(root, storage, error):
    path = root/'scientific-close.json'
    if path.exists():
        close = p.read_json(path)
        close.update(status='scientific-close-stop', narrow_restore_passed=False,
                     qualification_claims=[], launcher_error=str(error))
        try:
            d.replace_control(path, close, storage)
        except BaseException:
            # Keep the original bytes, but remove authority if failure cannot publish.
            if path.exists() and p.read_json(path).get('narrow_restore_passed') is True:
                path.rename(root/'scientific-close.invalidated.json')


def execute():
    evidence = Path(__file__).resolve().parent
    path = evidence/'registration.json'
    registration = admission(path)
    repo = Path(registration['repo']); root = Path(registration['output'])
    storage = d.restore_v2_budget(registration)
    marker = Path(registration['control_root'])/'launched.json'
    storage.check(2*p.MiB, path=marker)
    if shutil.disk_usage(repo).free < 10*p.GiB:
        raise ValueError('Admission requires 10 GiB free')
    marker.parent.mkdir(parents=True, exist_ok=True)
    command = [registration['python'],
               str(Path(__file__).resolve()), '--pipeline', str(path)]
    p.write_control(marker, {'command':command, 'started_monotonic':time.monotonic(),
        'watchdog_command': ['timeout', '--signal=TERM', '--kill-after=5', '890s',
            registration['python'], str(Path(__file__).resolve()), '--supervised'],
        'registration_sha256':p.file_hash(path), 'implementation_head':subprocess.check_output(
            ['git','rev-parse','HEAD'], cwd=repo, text=True).strip()}, storage)
    env = dict(os.environ, PYTHONPATH='.:src:scripts', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    process = timer = None
    failures = []; cleanup = []
    def fail_log(reason):
        nonlocal timer
        failures.append(reason)
        if process is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            if timer is None:
                def kill():
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                timer = threading.Timer(5, kill)
                timer.daemon = True; timer.start()
    print(json.dumps({'restore_v2_invocation':'starting', 'output':str(root)}), flush=True)
    code = 1
    try:
        # Live files remain ignored until clean child admission and both stages exit.
        with bounded_logs(marker.parent, p.MiB, fail_log) as (stdout, stderr):
            process = subprocess.Popen(command, cwd=repo, env=env, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            if failures:
                fail_log(failures[0])
            code = process.wait()
        if code != 0 or failures:
            raise ValueError('Scientific pipeline failed: '+str(code)+'; '+str(failures))
        deadline = p.read_json(root/'execution.json')['readout_deadline_monotonic']
        p.deadline_check(deadline)
        d.recheck_v2_inputs(registration, deadline)
        if p.read_json(root/'scientific-close.json').get('narrow_restore_passed') is not True:
            raise ValueError('Independent scientific close did not pass')
    except BaseException as error:
        code = 1
        failures.append(str(error))
        if process is not None and process.poll() is None:
            fail_log(str(error))
            process.wait()  # The log-failure cleanup has its existing five-second kill.
        invalidate(root, storage, error)
    finally:
        if timer is not None:
            timer.cancel()
        if process is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        try:
            # Native bounded_process owners have their own PGIDs: pipeline exit
            # cannot substitute for exact recorded owner cleanup and absence.
            cleanup = d.cleanup_owners(root)
            for row in cleanup:
                row['matching_owner_exited'] = d.owner_exited(row['owner'])
            if any(not row['matching_owner_exited'] for row in cleanup):
                raise ValueError('Matching native owner survives parent cleanup')
        except BaseException as error:
            code = 1; failures.append(str(error))
            invalidate(root, storage, error)
    try:
        if failures:
            code = 1
        for name in ('stdout.log', 'stderr.log'):
            source = marker.parent/name
            payload = source.read_bytes()
            storage.check(len(payload), path=evidence/('native-'+name))
            with (evidence/('native-'+name)).open('xb') as stream:
                stream.write(payload)
        if code == 0:
            p.deadline_check(deadline)
        result = {'native_exit_code':code, 'pipeline_exit_code':process.returncode if process else None,
                  'qualification_claims':[], 'failures':failures,
                  'cleanup':cleanup,
                  'registration_sha256':p.file_hash(path), 'storage':storage.usage()}
        p.write_control(evidence/'invocation-result.json', result, storage)
        storage.check(0, path=evidence/'invocation-result.json')
        if code == 0:
            p.deadline_check(deadline)
    except BaseException as error:
        invalidate(root, storage, error)
        result = {'native_exit_code':1, 'pipeline_exit_code':process.returncode if process else None,
                  'qualification_claims':[], 'failures':failures+[str(error)],
                  'cleanup':cleanup,
                  'registration_sha256':p.file_hash(path)}
        with contextlib.suppress(Exception):
            d.replace_control(evidence/'invocation-result.json', result, storage)
        print(json.dumps({'publication_error':str(error)}), flush=True)
        return 1
    print(json.dumps(result), flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline', type=Path)
    parser.add_argument('--supervised', action='store_true')
    args = parser.parse_args(argv)
    if args.pipeline is not None:
        return pipeline(args.pipeline)
    def interrupted(signum, frame):
        raise RuntimeError('Launcher interrupted: '+str(signum))
    if args.supervised:
        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            return execute()
        finally:
            signal.signal(signal.SIGTERM, previous)
    evidence = Path(__file__).resolve().parent
    registration = admission(evidence/'registration.json', recheck=False)
    if registration['python'] != d.sys.executable:
        raise ValueError('Registered launcher Python differs')
    command = ['timeout', '--signal=TERM', '--kill-after=5', '890s', registration['python'],
               str(Path(__file__).resolve()), '--supervised']
    env = dict(os.environ, PYTHONPATH='.:src:scripts', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    previous = signal.signal(signal.SIGTERM, interrupted)
    process = None
    code = 1
    try:
        process = subprocess.Popen(command, cwd=registration['repo'], env=env, start_new_session=True)
        code = process.wait()
    except BaseException:
        code = 1
        if process is not None and process.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    finally:
        signal.signal(signal.SIGTERM, previous)
    if code != 0:
        root = Path(registration['output']); storage = d.restore_v2_budget(registration)
        invalidate(root, storage, 'Whole-invocation watchdog or interruption: '+str(code))
        cleanup = d.cleanup_owners(root) if root.exists() else []
        result_path = evidence/'invocation-result.json'
        if root.exists():
            result = p.read_json(result_path) if result_path.exists() else {}
            result.update(native_exit_code=1, watchdog_exit_code=code, cleanup=cleanup,
                qualification_claims=[], registration_sha256=p.file_hash(evidence/'registration.json'))
            d.replace_control(result_path, result, storage)
    return 0 if code == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
