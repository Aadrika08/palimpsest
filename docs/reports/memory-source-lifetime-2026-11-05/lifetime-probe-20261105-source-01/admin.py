import json, os, pathlib, resource, subprocess, sys, time

root = pathlib.Path(__file__).parent
unit = 'palimpsest-memory-lifetime-probe-20261105-source-01.service'
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert resource.getrlimit(resource.RLIMIT_CPU) == (2, 2)
assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
assert os.getuid() == os.geteuid() == 1000
status = pathlib.Path('/proc/self/status').read_text()
fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
assert all(int(fields[key].strip(), 16) == 0
           for key in ('CapInh', 'CapPrm', 'CapEff', 'CapAmb'))

def save(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())

save('admin-start.json', {'pid': os.getpid(), 'uid': os.getuid(),
     'cpu_limit': resource.getrlimit(resource.RLIMIT_CPU),
     'core_limit': resource.getrlimit(resource.RLIMIT_CORE), 'status': status,
     'unit': unit, 'kernel': os.uname().release})
calls = []
def client(role, argv):
    assert len(calls) < 4
    calls.append(role)
    with (root / (role + '.stdout')).open('xb') as out, (root / (role + '.stderr')).open('xb') as err:
        result = subprocess.run(['/usr/bin/python3', '-I', '-B', '-S',
              str(root / 'client.py'), role, *argv], stdout=out, stderr=err,
              stdin=subprocess.DEVNULL, timeout=15, check=False)
    return result.returncode, (root / (role + '.stdout')).read_text()

base = ['/usr/bin/systemctl', '--user', '--no-pager', '--no-ask-password']
cg = None
created = False
report = {'scientific_qualification': False, 'status': 'started', 'unit': unit}
try:
    code, text = client('01-occupied', [*base, 'show', unit, '--property=LoadState', '--value'])
    if text.strip() != 'not-found':
        raise RuntimeError('Refuse occupied or unqueryable unit: ' + repr((code, text)))
    properties = {
        'Type': 'exec', 'RemainAfterExit': 'yes', 'RuntimeMaxSec': '8s',
        'TimeoutStopSec': '1s', 'MemoryMax': '67108864', 'MemorySwapMax': '0',
        'TasksMax': '8', 'LimitCPU': '6', 'LimitCORE': '0',
        'CPUAccounting': 'yes', 'MemoryAccounting': 'yes', 'TasksAccounting': 'yes',
        'NoNewPrivileges': 'yes', 'KillMode': 'control-group',
        'StandardInput': 'null', 'StandardOutput': 'append:' + str(root / 'worker.stdout'),
        'StandardError': 'append:' + str(root / 'worker.stderr'),
    }
    command = ['/usr/bin/systemd-run', '--user', '--no-ask-password', '--unit=' + unit]
    command += ['--property=' + key + '=' + value for key, value in properties.items()]
    command += ['/usr/bin/python3', '-I', '-B', '-S', str(root / 'worker.py')]
    code, text = client('02-launch', command)
    if code:
        raise RuntimeError('Single launch failed: ' + str(code))
    created = True
    until = time.monotonic() + 11
    while time.monotonic() < until:
        if (root / 'worker-start.json').exists():
            start = json.loads((root / 'worker-start.json').read_text())
            membership = start['cgroup'].strip()
            if not membership.startswith('0::/') or not membership.endswith('/' + unit):
                raise RuntimeError('Unexpected authored worker cgroup: ' + membership)
            cg = pathlib.Path('/sys/fs/cgroup' + membership[3:])
            if 'populated 0' in (cg / 'cgroup.events').read_text():
                break
        time.sleep(.05)
    else:
        raise RuntimeError('No observed empty created cgroup within probe deadline')
    wanted = ['Id', 'LoadState', 'ActiveState', 'SubState', 'MainPID', 'ControlPID',
        'ControlGroup', 'CPUUsageNSec', 'CPUAccounting', 'MemoryAccounting',
        'MemoryMax', 'MemorySwapMax', 'TasksMax', 'LimitCPU', 'LimitCPUSoft',
        'LimitCORE', 'RuntimeMaxUSec', 'TimeoutStopUSec', 'Type', 'RemainAfterExit',
        'NoNewPrivileges', 'KillMode', 'Result', 'ExecMainCode', 'ExecMainStatus',
        'InvocationID', 'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic']
    code, text = client('03-properties', [*base, 'show', unit, '--property=' + ','.join(wanted)])
    if code:
        raise RuntimeError('Property read failed')
    observed = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
    save('service-properties.json', observed)
    snapshots = []
    for i in range(3):
        snapshots.append({'monotonic_ns': time.monotonic_ns(),
            **{name: (cg / name).read_text() for name in
               ('cpu.stat', 'cgroup.events', 'cgroup.procs', 'memory.max',
                'memory.swap.max', 'memory.events', 'pids.max', 'pids.current')}})
        time.sleep(.2)
    save('empty-cgroup-samples.json', snapshots)
    terminal = json.loads((root / 'authored-terminal.json').read_text())
    assert observed['MainPID'] == observed['ControlPID'] == '0'
    assert observed['ActiveState'] == 'active' and observed['SubState'] == 'exited'
    assert observed['Result'] == 'success' and observed['ExecMainStatus'] == '0'
    assert observed['MemoryMax'] == '67108864' and observed['MemorySwapMax'] == '0'
    assert observed['TasksMax'] == '8'
    assert observed['LimitCPU'] == observed['LimitCPUSoft'] == '6'
    assert observed['LimitCORE'] == '0' and observed['RuntimeMaxUSec'] == '8s'
    assert observed['TimeoutStopUSec'] == '1s'
    assert observed['Type'] == 'exec' and observed['RemainAfterExit'] == 'yes'
    assert observed['CPUAccounting'] == observed['MemoryAccounting'] == 'yes'
    assert observed['NoNewPrivileges'] == 'yes'
    assert observed['ControlGroup'] == start['cgroup'].strip()[3:]
    assert all('populated 0' in sample['cgroup.events'] and not sample['cgroup.procs'].strip()
               and sample['pids.current'].strip() == '0' for sample in snapshots)
    usage = [dict(line.split() for line in sample['cpu.stat'].splitlines())['usage_usec']
             for sample in snapshots]
    assert len(set(usage)) == 1
    assert terminal['parent_cpu_before_terminal'] > 2.2
    assert int(usage[0]) / 1e6 >= terminal['parent_cpu_before_terminal'] + terminal['child_cpu']
    report.update(status='passed', stable_service_cpu_seconds=int(usage[0]) / 1e6,
        systemd_cpu_usage_nsec=observed['CPUUsageNSec'], parent=terminal,
        exact_whole_operation_cpu_seconds=None, charged_upper_cpu_seconds=None,
        reason='Probe verifies mechanism, not a kernel overshoot upper bound')
except BaseException as error:
    report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
finally:
    if created and cg is not None and cg.exists() and 'populated 0' in (cg / 'cgroup.events').read_text():
        code, text = client('04-stop-empty', [*base, 'stop', unit])
        report['empty_unit_stop_returncode'] = code
    else:
        report['empty_unit_stop_returncode'] = None
    report['clients'] = calls
    report['admin_self_cpu_observed_before_final_receipt'] = time.process_time()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    report['fixed_client_cpu_seconds'] = children.ru_utime + children.ru_stime
    save('probe-result.json', report)
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report['status'] == 'passed' else 1)
