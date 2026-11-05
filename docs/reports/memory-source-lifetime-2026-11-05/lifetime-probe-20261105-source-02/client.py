import json, os, pathlib, resource, sys

root = pathlib.Path(__file__).parent
role = sys.argv[1]
assert role in ('01-occupied', '02-launch', '03-properties', '04-stop-empty')
assert resource.getrlimit(resource.RLIMIT_CPU) == (2, 2)
assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
assert sys.argv[2] in ('/usr/bin/systemctl', '/usr/bin/systemd-run')
status = pathlib.Path('/proc/self/status').read_text()
fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
assert os.getuid() == os.geteuid() == 1000
assert all(int(fields[key].strip(), 16) == 0
           for key in ('CapInh', 'CapPrm', 'CapEff', 'CapAmb'))
assert fields['NoNewPrivs'].strip() == '1'
with (root / (role + '-pre-exec.json')).open('x') as stream:
    json.dump({'pid': os.getpid(), 'argv': sys.argv[2:], 'uid': os.getuid(),
               'cpu_limit': resource.getrlimit(resource.RLIMIT_CPU),
               'core_limit': resource.getrlimit(resource.RLIMIT_CORE),
               'status': status}, stream, sort_keys=True)
    stream.flush()
    os.fsync(stream.fileno())
os.execv(sys.argv[2], sys.argv[2:])
