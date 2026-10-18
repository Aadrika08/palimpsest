"""Three tiny authored process-topology observations; no package imports."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE=Path('/tmp/palimpsest-puck-cpu-topology-probe-01')
REPORT=Path('/tmp/palimpsest-cpu-namespace-topology-probe-01.json')
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(15)
sys.path.insert(0,str(ROOT/'src'))
from palimpsest.puck_cpu_namespace import sandbox_command
baseline=json.loads((ROOT/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
metadata=json.loads((ROOT/'docs/plans/puck-cpu-characterization-native-metadata-05.json').read_bytes())
python=baseline['python_prefix']+'/bin/python3.11'
paths=sorted(['/etc/ld.so.cache',python]+['/usr/lib/'+name for name in (
    'ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6','libpthread.so.0','librt.so.1','libutil.so.1')])
native={'native_files':[row for row in metadata['native_files'] if row['path'] in paths],
        'aliases':baseline['host_path_aliases']}
BASE.mkdir(mode=0o700)
for name in ('stage','source','control','output'):(BASE/name).mkdir(mode=0o700)
(BASE/'stage/inputs').mkdir(mode=0o700)
help_text=subprocess.run(['/usr/bin/bwrap','--help'],capture_output=True,text=True,timeout=2,check=True).stdout
assert '--new-session' in help_text
PROBE='''import json,os,time,sys
from pathlib import Path
def proc(pid):
 try:
  raw=Path('/proc/'+str(pid)+'/stat').read_bytes()
  values=raw.rsplit(b')',1)[1].split()
  return dict(pid=pid,ppid=int(values[1]),pgid=int(values[2]),sid=int(values[3]),start_tick=int(values[19]))
 except OSError as error:return dict(error=type(error).__name__,errno=error.errno,pid=pid)
row=dict(pid=os.getpid(),ppid=os.getppid(),pgid=os.getpgrp(),sid=os.getsid(0),
 parent=proc(os.getppid()),self_stat=proc(os.getpid()),
 pid_namespace=os.readlink('/proc/self/ns/pid'),network_namespace=os.readlink('/proc/self/ns/net'),
 network_isolated=os.readlink('/proc/self/ns/net')!=sys.argv[2],project_hidden=not Path(sys.argv[3]).exists())
Path('/output/'+sys.argv[1]+'.json').write_text(json.dumps(row,sort_keys=True))
print(json.dumps(row,sort_keys=True),flush=True)
time.sleep(0.8)
'''

def host_row(pid):
    path=Path('/proc')/str(pid)
    values=(path/'stat').read_bytes().rsplit(b')',1)[1].split()
    status=(path/'status').read_text()
    return dict(pid=pid,ppid=int(values[1]),pgid=int(values[2]),sid=int(values[3]),start_tick=int(values[19]),
        nspid=[int(value) for line in status.splitlines() if line.startswith('NSpid:') for value in line.split()[1:]],
        rss_bytes=int((path/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE'),
        pid_namespace=os.readlink(path/'ns/pid'))


def owned_tree(pid):
    rows={};pending=[pid]
    while pending:
        current=pending.pop()
        if current in rows:continue
        try:
            rows[current]=host_row(current)
            child=Path('/proc')/str(current)/'task'/str(current)/'children'
            pending.extend(int(value) for value in child.read_text().split())
        except (OSError,IndexError,ValueError):continue
    return rows

results=[]
for mode in ('as-pid-1','default-init','default-init-new-session'):
    command=sandbox_command(baseline,native,paths,phase='qualify',stage_parent=str(BASE/'stage'),
        source_root=str(BASE/'source'),control_root=str(BASE/'control'),output_root=str(BASE/'output'),
        command=[python,'-I','-S','-B','-c',PROBE,mode,os.readlink('/proc/self/ns/net'),str(ROOT)],
        environment={'HOME':'/scratch/home','TMPDIR':'/scratch/tmp','LC_ALL':'C.UTF-8'})
    if mode!='as-pid-1':command.remove('--as-pid-1')
    if mode=='default-init-new-session':command.insert(1,'--new-session')
    output=BASE/'output';rows={};peak_processes=0;peak_rss=0;sample=None;inside=None
    with (output/(mode+'.stdout')).open('xb') as stdout,(output/(mode+'.stderr')).open('xb') as stderr:
        process=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
        until=time.monotonic()+3
        try:
            while process.poll() is None:
                rows=owned_tree(process.pid);peak_processes=max(peak_processes,len(rows))
                peak_rss=max(peak_rss,sum(row['rss_bytes'] for row in rows.values()))
                if peak_processes>3:raise RuntimeError('authored child process ceiling exceeded')
                ready=output/(mode+'.json')
                if ready.is_file() and sample is None:
                    inside=json.loads(ready.read_bytes());sample=rows
                if time.monotonic()>=until:raise TimeoutError('tiny topology probe exceeded 3 seconds')
                time.sleep(.01)
            code=process.wait(timeout=.2)
        finally:
            if process.poll() is None:
                for pid in reversed(list(owned_tree(process.pid))):
                    try:os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                process.wait(timeout=1)
    assert code==0,(mode,(output/(mode+'.stderr')).read_text())
    assert sample is not None and inside['network_isolated'] and inside['project_hidden']
    candidates=[row for row in sample.values() if row['pid_namespace']==inside['pid_namespace'] and row['nspid'][-1]==inside['pid']]
    assert len(candidates)==1
    worker=candidates[0]
    results.append(dict(mode=mode,returncode=code,outer_popen_pid=process.pid,inside=inside,
        host_tree=list(sample.values()),outer_owned_group_members=sorted(pid for pid,row in sample.items() if row['pgid']==process.pid),
        worker_host=worker,worker_in_outer_owned_group=worker['pgid']==process.pid,
        worker_identity_contract=inside['pid']==inside['pgid']==inside['sid'] and inside['ppid']>0 and 'error' not in inside['parent'],
        peak_descendant_processes=peak_processes,peak_descendant_rss_bytes=peak_rss,
        no_owned_descendant_survivors=not owned_tree(process.pid)))
report=dict(kind='puck-authored-namespace-topology-probe-v1',results=results,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    namespace_source_sha256=hashlib.sha256((ROOT/'src/palimpsest/puck_cpu_namespace.py').read_bytes()).hexdigest(),
    original_interpreter=python,max_processes=3,probe_sleep_seconds=.8,
    vendor_imports=False,installed_site_staged=False,runtime_qualified=False)
with REPORT.open('xb') as stream:
    stream.write((json.dumps(report,sort_keys=True,indent=2)+'\n').encode());stream.flush();os.fsync(stream.fileno())
print(json.dumps(report,sort_keys=True),flush=True)
signal.alarm(0)
