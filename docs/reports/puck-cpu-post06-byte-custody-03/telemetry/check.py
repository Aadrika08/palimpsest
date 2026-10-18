"""Unit-check only AST-extracted03 telemetry helpers with fake OS/Path state."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path('/tmp/palimpsest-held06-post-byte-custody-03.py')
EXPECTED_SHA256 = '96e496cef4ba2b1c2250e8a2a45737cb930b18cb019c8cc2b32d565830c522ff'
OUTPUT = Path('/tmp/palimpsest-held06-post-byte-custody-03-telemetry-check.json')
raw = SOURCE.read_bytes()
assert len(raw) == 19086 and hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256
parsed = ast.parse(raw, str(SOURCE))
function_names = {'_stderr_record', '_phase', '_failure'}
assignment_names = {'_MARKER_COUNT', '_MARKER_BYTES'}
selected = []
for node in parsed.body:
    if isinstance(node, ast.FunctionDef) and node.name in function_names:
        selected.append(node)
    elif (isinstance(node, ast.Assign) and len(node.targets) == 1
          and isinstance(node.targets[0], ast.Name)
          and node.targets[0].id in assignment_names):
        assert isinstance(node.value, ast.Constant) and node.value.value == 0
        selected.append(node)
assert len(selected) == 5
assert {n.name for n in selected if isinstance(n, ast.FunctionDef)} == function_names
assert {n.targets[0].id for n in selected if isinstance(n, ast.Assign)} == assignment_names
isolated = ast.Module(body=selected, type_ignores=[])
checks = [{'name': 'source_pin_and_only_three_helpers_two_zero_assignments', 'status': 'PASS'}]

# Every OS/Path operation reached by the extracted functions is a fake.
writes = []
queries = []
clock = [20.25]
write_mode = ['normal']
query_failure = [None]
write_error = OSError('authored stderr write failure')
fd_names = ['0', '1', '2']
children_text = ['200 201\n']
thread_names = ['100', '101', '102']

def fake_write(fd, payload):
    assert fd == 2 and isinstance(payload, bytes)
    writes.append(payload)
    if write_mode[0] == 'raise':
        raise write_error
    return len(payload) - 1 if write_mode[0] == 'partial' else len(payload)

def fake_listdir(path):
    queries.append(path)
    if path == '/proc/self/fd':
        if query_failure[0] == 'fd':
            raise RuntimeError('authored fd query refusal')
        return list(fd_names)
    assert path == '/proc/self/task'
    if query_failure[0] == 'threads':
        raise RuntimeError('authored thread query refusal')
    return list(thread_names)

def fake_path(path):
    assert path == '/proc/self/task/100/children'
    def read_text():
        queries.append(path)
        if query_failure[0] == 'children':
            raise RuntimeError('authored children query refusal')
        return children_text[0]
    return SimpleNamespace(read_text=read_text)

namespace = {'json': json, 'time': SimpleNamespace(monotonic=lambda: clock[0]),
             'os': SimpleNamespace(write=fake_write, listdir=fake_listdir, getpid=lambda: 100),
             'Path': fake_path}
# This compile/exec contains only the five selected AST nodes, never the source module.
exec(compile(isolated, '<isolated-held06-03-telemetry>', 'exec'), namespace)
assert '_phase' in namespace and 'main' not in namespace and 'Held' not in namespace

def reset():
    writes.clear()
    queries.clear()
    namespace['_MARKER_COUNT'] = namespace['_MARKER_BYTES'] = 0
    clock[0] = 20.25
    write_mode[0] = 'normal'
    query_failure[0] = None
    children_text[0] = '200 201\n'

def passed(name):
    checks.append({'name': name, 'status': 'PASS'})

reset()
namespace['_phase']('forest', 10.0, SimpleNamespace(files={'a': 1, 'b': 2}, total=77))
assert len(writes) == 1 and queries == []
assert json.loads(writes[0]) == dict(kind='held06-post-byte-custody-phase-v1', check_id=3,
    status='phase_completed', phase='forest', elapsed_seconds=10.25, held=dict(files=2, total=77))
assert namespace['_MARKER_COUNT'] == 1 and namespace['_MARKER_BYTES'] == len(writes[0])
passed('phase_exact_fields_count_and_byte_counters')

for name, before, closed in [
    ('initial_failure_omits_closure_and_all_queries', None, False),
    ('normal_close_without_before_omits_closure_and_queries', None, True),
    ('before_without_normal_close_omits_closure_and_queries', 8, False),
]:
    reset()
    error = ValueError('authored original')
    namespace['_failure'](error, 10.0, before=before, held_closed=closed)
    value = json.loads(writes[0])
    assert 'closure' not in value and queries == []
    assert value == dict(kind='held06-post-byte-custody-failure-v1', check_id=3,
        status='FAIL', error_type='ValueError', error='authored original', elapsed_seconds=10.25)
    passed(name)

reset()
normal_close = []
held = SimpleNamespace(close=lambda: normal_close.append(True))
held.close()
namespace['_failure'](ValueError('authored original'), 10.0, before=8,
                      held_closed=normal_close == [True])
value = json.loads(writes[0])
assert value['status'] == 'FAIL'
assert value['closure'] == dict(fd_count_before=8, fd_count_after=3,
    active_children=['200', '201'], active_non_main_threads=['101', '102'],
    held_close_completed=True, scope='current process observations only')
assert not any('pass' in key.lower() or 'qualified' in key for key in value['closure'])
passed('normal_close_then_unequal_fds_children_threads_are_observations_not_pass')

for mode in ['fd', 'children', 'threads']:
    reset()
    query_failure[0] = mode
    namespace['_failure'](ValueError('authored original'), 10.0, before=8, held_closed=True)
    value = json.loads(writes[0])
    assert 'closure' not in value and value['error'] == 'authored original'
    assert value['status'] == 'FAIL' and namespace['_MARKER_COUNT'] == 1
    passed('closure_' + mode + '_query_failure_omits_whole_closure')

reset()
namespace['_failure'](RuntimeError('\u00e9' * 1400), 10.0)
value = json.loads(writes[0])
assert len(value['error']) == 1024 and value['error'] == '\u00e9' * 1024
assert value['error_type'] == 'RuntimeError' and len(writes[0]) <= 8192
passed('error_text_cap_is_1024_characters')

reset()
children_text[0] = '9' * 9000
namespace['_failure'](ValueError('authored original'), 10.0, before=8, held_closed=True)
value = json.loads(writes[0])
assert 'closure' not in value and value['error'] == 'authored original' and len(writes[0]) <= 8192
passed('oversized_closure_is_omitted_before_record')

reset()
for index in range(12):
    namespace['_stderr_record']({'index': index})
assert len(writes) == namespace['_MARKER_COUNT'] == 12
before = (namespace['_MARKER_COUNT'], namespace['_MARKER_BYTES'])
try:
    namespace['_stderr_record']({'index': 12})
except AssertionError:
    pass
else:
    raise AssertionError('thirteenth telemetry record accepted')
assert len(writes) == 12 and before == (namespace['_MARKER_COUNT'], namespace['_MARKER_BYTES'])
passed('twelfth_record_allowed_thirteenth_refused_before_write')

payload = {'x': 'small'}
encoded = (json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
reset()
namespace['_MARKER_BYTES'] = 64 * 1024 - len(encoded)
namespace['_stderr_record'](payload)
assert namespace['_MARKER_BYTES'] == 64 * 1024 and len(writes) == 1
passed('exact_64KiB_aggregate_boundary_allowed')
reset()
namespace['_MARKER_BYTES'] = 64 * 1024 - len(encoded) + 1
try:
    namespace['_stderr_record'](payload)
except AssertionError:
    pass
else:
    raise AssertionError('aggregate cap exceeded')
assert writes == [] and namespace['_MARKER_COUNT'] == 0
assert namespace['_MARKER_BYTES'] == 64 * 1024 - len(encoded) + 1
passed('aggregate_64KiB_excess_refused_before_write')

reset()
exact = {'x': 'z' * (8192 - len(b'{"x":""}\n'))}
namespace['_stderr_record'](exact)
assert len(writes) == 1 and len(writes[0]) == namespace['_MARKER_BYTES'] == 8192
passed('exact_8192B_record_boundary_allowed')
reset()
try:
    namespace['_stderr_record']({'x': exact['x'] + 'z'})
except AssertionError:
    pass
else:
    raise AssertionError('single-record cap exceeded')
assert writes == [] and namespace['_MARKER_COUNT'] == namespace['_MARKER_BYTES'] == 0
passed('single_record_8192B_excess_refused_before_write')

for mode in ['partial', 'raise']:
    reset()
    write_mode[0] = mode
    try:
        namespace['_phase']('forest', 10.0, SimpleNamespace(files={}, total=0))
    except (AssertionError, OSError) as error:
        assert (mode == 'partial' and isinstance(error, AssertionError)) or error is write_error
    else:
        raise AssertionError('phase swallowed stderr failure')
    assert len(writes) == 1 and namespace['_MARKER_COUNT'] == namespace['_MARKER_BYTES'] == 0
    passed(mode + '_stderr_write_propagates_phase_failure_without_counter_increment')

for mode in ['partial', 'raise']:
    reset()
    write_mode[0] = mode
    original = ValueError('authored caller exception must survive')
    try:
        try:
            raise original
        except ValueError:
            assert namespace['_failure'](original, 10.0) is None
            raise
    except ValueError as observed:
        assert observed is original
    else:
        raise AssertionError('caller original exception lost')
    assert len(writes) == 1 and namespace['_MARKER_COUNT'] == namespace['_MARKER_BYTES'] == 0
    passed(mode + '_failure_telemetry_error_suppressed_preserving_caller_exception')

assert len(checks) == 20 and len({row['name'] for row in checks}) == 20
assert SOURCE.read_bytes() == raw
result = dict(kind='held06-post03-telemetry-isolated-unit-check-v1', status='PASS',
    meaningful_check_count=len(checks), checks=checks,
    source=dict(path=str(SOURCE), size_bytes=len(raw), sha256=EXPECTED_SHA256),
    extracted_assignments=sorted(assignment_names), extracted_functions=sorted(function_names),
    extracted_node_count=5, all_os_and_path_operations_faked=True,
    full03_module_imported_or_executed=False, main_invoked=False,
    auditor_or_other_helpers_imported_or_executed=False, target_runtime_invoked=False,
    census_performed=False, actual_admission_performed=False,
    scope='Unit helper tests with authored observations only; no03 admission or real resource/closure inference.')
encoded = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
OUTPUT.write_bytes(encoded)
print(encoded.decode(), end='')
