import json, os, pathlib, resource, sys, time

root = pathlib.Path(__file__).parent
def save(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
def spin(seconds):
    start = time.process_time()
    while time.process_time() - start < seconds:
        pass
def usage(kind):
    value = resource.getrusage(kind)
    return value.ru_utime + value.ru_stime

assert resource.getrlimit(resource.RLIMIT_CPU) == (6, 6)
assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
save('worker-start.json', {
    'pid': os.getpid(), 'uid': os.getuid(),
    'cpu_limit': resource.getrlimit(resource.RLIMIT_CPU),
    'core_limit': resource.getrlimit(resource.RLIMIT_CORE),
    'cgroup': pathlib.Path('/proc/self/cgroup').read_text(),
    'status': pathlib.Path('/proc/self/status').read_text(),
    'stat': pathlib.Path('/proc/self/stat').read_text(),
    'cpu_start': usage(resource.RUSAGE_SELF),
})
spin(2.2)
child = os.fork()
if child == 0:
    spin(.05)
    os._exit(0)
pid, status, child_usage = os.wait4(child, 0)
assert pid == child and status == 0
save('authored-terminal.json', {
    'kind': 'authored-software-probe-only',
    'parent_cpu_before_terminal': usage(resource.RUSAGE_SELF),
    'child_cpu': child_usage.ru_utime + child_usage.ru_stime,
    'parent_pid': os.getpid(), 'child_pid': child,
    'scientific_qualification': False,
    'unmeasured_here': 'this file publication, fsync and interpreter exit',
})
