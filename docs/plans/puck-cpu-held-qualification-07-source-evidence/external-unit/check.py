"""AST-isolated runner unit checks; fake process/clock/in-memory FS only."""
import ast
import hashlib
import io
import json
from pathlib import Path as ActualPath
import subprocess as std_subprocess
from types import SimpleNamespace

SOURCE = ActualPath('/tmp/palimpsest-held07-external.py')
SOURCE_SHA = '3eb0c77ad3d7ba6ea3f7f00fcba650db364262c1a57b81be37f73cd80d2f898a'
FREEZE_SOURCE = ActualPath('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-07-freeze.json')
FREEZE_SHA = '6230a4072b3606efd41efc694f0da15671d248f2cd39203f4eb2ca39ead22d17'
OUTPUT = ActualPath('/tmp/palimpsest-held07-external-unit-check.json')
raw = SOURCE.read_bytes()
assert len(raw) == 4194 and hashlib.sha256(raw).hexdigest() == SOURCE_SHA
freeze_raw = FREEZE_SOURCE.read_bytes()  # Authenticated metadata only; never a control invocation.
assert len(freeze_raw) == 124995 and hashlib.sha256(freeze_raw).hexdigest() == FREEZE_SHA
freeze = json.loads(freeze_raw)
tree = ast.parse(raw, str(SOURCE))
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('stream_pin', 'main')]
assert len(functions) == 2 and {n.name for n in functions} == {'stream_pin', 'main'}
isolated = compile(ast.Module(body=functions, type_ignores=[]), '<isolated-external07-functions>', 'exec')
checks = [dict(name='source_and_metadata_pins_exactly_two_function_AST_nodes', status='PASS')]
PAYLOAD = b'RAW_PAYLOAD_MUST_NOT_APPEAR_IN_SUMMARY_' * 300


def setup(phase='admission', outcome=0, freeze_delay=7.5, hash_delay=0,
          fsync_delay=0, print_delay=0):
    state = SimpleNamespace(now=0.0, files={'/unit/freeze.json': freeze_raw}, opens=[], reads=[],
        calls=[], summaries=[], freeze_delay=freeze_delay, freeze_read=False,
        hash_delay=hash_delay, hash_delayed=False, fsync_delay=fsync_delay,
        print_delay=print_delay, outcome=outcome, race_receipt=False)

    class FakeFile:
        def __init__(self, name, mode):
            self.name, self.mode = name, mode
            self.buffer = io.BytesIO(state.files[name] if mode == 'rb' else b'')
        def __enter__(self): return self
        def __exit__(self, *args):
            if self.mode != 'rb': state.files[self.name] = self.buffer.getvalue()
            self.buffer.close()
        def read(self, size):
            assert size > 0
            state.reads.append((self.name, size))
            if self.name == '/unit/freeze.json' and not state.freeze_read:
                state.now += state.freeze_delay
                state.freeze_read = True
            data = self.buffer.read(size)
            if self.name.endswith('.stdout') and data and not state.hash_delayed:
                state.now += state.hash_delay
                state.hash_delayed = True
            return data
        def write(self, data):
            if self.mode == 'x': assert isinstance(data, str); data = data.encode()
            else: assert self.mode == 'xb' and isinstance(data, bytes)
            count = self.buffer.write(data)
            state.files[self.name] = self.buffer.getvalue()
            return count
        def flush(self): state.files[self.name] = self.buffer.getvalue()
        def fileno(self): return 99

    class FakePath:
        def __init__(self, value):
            value = str(value)
            if value.startswith('/tmp/palimpsest-held07-'):
                value = '/unit/output/' + value.rsplit('/', 1)[1]
            assert value.startswith('/unit/'), value
            self.name = value
        def __str__(self): return self.name
        def __truediv__(self, suffix): return FakePath(self.name + '/' + str(suffix))
        def __eq__(self, other): return self.name == str(other)
        def resolve(self): return self
        def open(self, mode):
            assert mode in ('rb', 'x', 'xb')
            state.opens.append((self.name, mode))
            if mode in ('x', 'xb'):
                if mode == 'x' and state.race_receipt:
                    state.files[self.name] = b'authored race occupant'
                    raise FileExistsError(self.name)
                if self.name in state.files: raise FileExistsError(self.name)
                state.files[self.name] = b''
            else: assert self.name in state.files, self.name
            return FakeFile(self.name, mode)

    stem = '/unit/output/palimpsest-held07-' + phase + '-external'
    receipt = stem + '.json'
    audit_input = '/unit/output/palimpsest-held07-concrete-audit-command.json'
    audit_command = freeze['commands']['auditor_prefix'] + ['a' * 64, '--output', freeze['commands']['auditor_output']]
    state.files[audit_input] = json.dumps(dict(command=audit_command)).encode()

    def fake_run(command, **kwargs):
        # Exclusive receipt and both streams exist before any fake child launch.
        assert receipt in state.files and stem + '.stdout' in state.files and stem + '.stderr' in state.files
        assert str(kwargs['cwd']) == '/unit/root'
        assert kwargs['env'] == freeze['outer_environment']
        assert kwargs['stdin'] == -3 and kwargs['close_fds'] is True
        assert kwargs['timeout'] > 0
        state.calls.append(dict(command=command, timeout=kwargs['timeout'], launched_at=state.now))
        kwargs['stdout'].write(PAYLOAD)
        kwargs['stderr'].write(b'authored stderr\n')
        state.now += 2.0
        if state.outcome == 'timeout': raise std_subprocess.TimeoutExpired(command, kwargs['timeout'])
        if state.outcome == 'oserror': raise OSError('authored OS error ' * 100)
        return SimpleNamespace(returncode=state.outcome)

    def fake_fsync(fd):
        assert fd == 99
        state.now += state.fsync_delay

    def fake_print(value, *, flush):
        assert flush is True and isinstance(value, str)
        state.summaries.append(value)
        state.now += state.print_delay

    namespace = dict(Path=FakePath, hashlib=hashlib, json=json,
        time=SimpleNamespace(monotonic=lambda: state.now),
        os=SimpleNamespace(environ={}, path=SimpleNamespace(lexists=lambda p: str(p) in state.files), fsync=fake_fsync),
        subprocess=SimpleNamespace(run=fake_run, TimeoutExpired=std_subprocess.TimeoutExpired, DEVNULL=-3),
        sys=SimpleNamespace(argv=['isolated-unit', phase], flags=SimpleNamespace(isolated=True, no_site=True),
                            dont_write_bytecode=True, executable='/unit/python3.11'),
        ROOT=FakePath('/unit/root'), FREEZE=FakePath('/unit/freeze.json'), FREEZE_SHA=FREEZE_SHA,
        PYTHON='/unit/python3.11', print=fake_print)
    # No imports, module assignments or __main__ statement from the coordinator execute.
    exec(isolated, namespace)
    state.namespace, state.FakePath = namespace, FakePath
    state.stem, state.receipt, state.audit_input = stem, receipt, audit_input
    return state


def passed(name, **details): checks.append(dict(name=name, status='PASS', **details))


def inspect_result(state):
    value = json.loads(state.files[state.receipt])
    assert len(state.files[state.receipt]) <= 64 * 1024
    assert len(state.summaries) == 1 and len(state.summaries[0].encode()) <= 4096
    assert 'RAW_PAYLOAD_MUST_NOT_APPEAR' not in state.summaries[0]
    summary = json.loads(state.summaries[0])
    for channel in ('stdout', 'stderr'):
        path = state.stem + '.' + channel
        data = state.files[path]
        assert value[channel] == dict(path=path, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        assert summary[channel] == value[channel]
    assert all(path.startswith('/unit/') for path, mode in state.opens)
    return value, summary


for phase, budget in [('admission', 145), ('observer', 240), ('audit', 145)]:
    s = setup(phase)
    assert s.namespace['main']() == 0
    value, summary = inspect_result(s)
    assert len(s.calls) == 1 and s.calls[0]['timeout'] == budget - 7.5
    assert value['external_deadline_seconds'] == budget and value['elapsed_seconds'] == 9.5
    assert value['normal_exit'] is True and value['timed_out'] is False and summary['accepted'] is True
    expected = (freeze['commands']['auditor_prefix'] + ['a' * 64, '--output', freeze['commands']['auditor_output']]
                if phase == 'audit' else freeze['commands'][phase])
    assert s.calls[0]['command'] == value['command'] == expected
    passed(phase + '_whole_budget_remaining_after_freeze_and_exact_receipt_digests',
           budget=budget, remaining_child_seconds=budget - 7.5)

for outcome, normal, timed_out in [(7, True, False), (-9, False, False), ('timeout', False, True), ('oserror', False, False)]:
    s = setup(outcome=outcome)
    assert s.namespace['main']() == 1
    value, summary = inspect_result(s)
    assert value['normal_exit'] is normal and value['timed_out'] is timed_out and summary['accepted'] is False
    assert value['returncode'] == (None if isinstance(outcome, str) else outcome)
    if outcome == 'oserror': assert value['error_type'] == 'OSError' and len(value['error']) == 1024
    passed('outcome_' + str(outcome) + '_retains_transport_status_and_refuses_acceptance')

late_observations = []
for stage in ['hash', 'fsync', 'print']:
    s = setup(**{stage + '_delay': 145})
    assert s.namespace['main']() == 1
    value, summary = inspect_result(s)
    assert value['returncode'] == 0 and s.now >= 145
    if stage == 'hash': assert value['timed_out'] is True and summary['accepted'] is False
    if stage == 'fsync': assert summary['accepted'] is False
    if stage == 'print': assert summary['accepted'] is True  # Emitted before print completion; final gate still refuses.
    late_observations.append(dict(stage=stage, child_returncode=0, wrapper_returncode=1,
                                  receipt_timed_out=value['timed_out'], summary_accepted=summary['accepted']))
    passed('late_' + stage + '_zero_child_cannot_produce_wrapper_zero')

for extra in [0, 1]:
    s = setup()
    path = '/unit/stream-bound'
    data = b'z' * (16 * 1024**2 + extra)
    s.files[path] = data
    if extra:
        try: s.namespace['stream_pin'](s.FakePath(path))
        except AssertionError: pass
        else: raise AssertionError('oversize stream accepted')
    else:
        assert s.namespace['stream_pin'](s.FakePath(path)) == dict(path=path, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert s.reads and all(n == 1024**2 for p, n in s.reads if p == path)
    assert s.calls == []
    passed('stream_exact_16MiB_allowed' if not extra else 'stream_16MiB_plus_one_refused_with_bounded_reads')

for suffix in ['.json', '.stdout', '.stderr']:
    s = setup()
    occupied = s.stem + suffix
    s.files[occupied] = b'preserved occupant'
    before = dict(s.files)
    try: s.namespace['main']()
    except AssertionError: pass
    else: raise AssertionError('existing output accepted')
    assert s.calls == [] and s.files == before
    passed('existing_' + suffix[1:] + '_refused_before_launch_without_mutation')

s = setup(); s.race_receipt = True
try: s.namespace['main']()
except FileExistsError: pass
else: raise AssertionError('exclusive receipt race accepted')
assert s.calls == [] and s.files[s.receipt] == b'authored race occupant'
assert s.stem + '.stdout' not in s.files and s.stem + '.stderr' not in s.files
passed('receipt_exclusive_open_race_refuses_before_child_or_stream_creation')

s = setup(); assert s.namespace['main']() == 0
before = dict(s.files)
try: s.namespace['main']()
except AssertionError: pass
else: raise AssertionError('reentry accepted')
assert len(s.calls) == 1 and s.files == before
passed('reentry_refuses_second_launch_and_preserves_first_files')

for phase, budget in [('admission', 145), ('observer', 240), ('audit', 145)]:
    s = setup(phase, freeze_delay=budget)
    try: s.namespace['main']()
    except AssertionError: pass
    else: raise AssertionError('exhausted prelaunch budget accepted')
    assert s.calls == []
    passed(phase + '_freeze_consumed_budget_refuses_before_child')

for argv in [['unit', 'foreign'], ['unit', 'admission', 'extra']]:
    s = setup(); s.namespace['sys'].argv = argv
    try: s.namespace['main']()
    except AssertionError: pass
    else: raise AssertionError('foreign CLI accepted')
    assert s.calls == [] and s.opens == []
    passed('unknown_phase_refused' if len(argv) == 2 else 'extra_cli_option_refused')

s = setup('audit')
command = json.loads(s.files[s.audit_input])['command']; command[0] = 'foreign'
s.files[s.audit_input] = json.dumps(dict(command=command)).encode()
try: s.namespace['main']()
except AssertionError: pass
else: raise AssertionError('foreign audit command accepted')
assert s.calls == [] and s.receipt not in s.files
passed('audit_concrete_command_must_match_frozen_prefix_and_shape')

assert len(checks) == 24 and len({x['name'] for x in checks}) == 24
assert SOURCE.read_bytes() == raw
result = dict(kind='held07-external-isolated-unit-check-v1', status='PASS', meaningful_check_count=24,
    source=dict(path=str(SOURCE), size_bytes=len(raw), sha256=SOURCE_SHA),
    freeze_metadata=dict(path=str(FREEZE_SOURCE), size_bytes=len(freeze_raw), sha256=FREEZE_SHA),
    checks=checks, late_completion_observations=late_observations,
    extracted_functions=['stream_pin', 'main'], full_coordinator_imported_or_executed=False,
    extracted_main_executed_with_fakes=True, all_extracted_FS_paths_in_memory_under_unit=True,
    real_subprocess_target_launched=False, actual07_output_paths_opened_or_written=False,
    actual07_admission_observer_auditor_invoked=False, census_or_payload_probe_performed=False,
    limitations=['These are authored fake-clock/process/in-memory-FS unit cases, not coordinator/admission execution.',
        'Real freeze bytes were read only as authenticated metadata for the fake fixture.',
        'Late print can leave pre-print summary accepted=true, but the final post-print return gate is1; callers must require wrapper zero in addition to child/summary data.',
        'No OS process-kill, filesystem durability, real wall-clock deadline or native/runtime behavior is qualified.'])
encoded = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
OUTPUT.write_bytes(encoded)
print(encoded.decode(), end='')
