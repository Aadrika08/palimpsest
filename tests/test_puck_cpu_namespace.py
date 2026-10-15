"""A fixed namespace seam, with two inert authored bwrap passes."""
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
NATIVE = json.loads((ROOT/'docs/plans/puck-cpu-characterization-native-metadata-05.json').read_bytes())
PYTHON = BASELINE['python_prefix']+'/bin/python3.11'
QUALIFICATION_LAUNCHER='import os,sys;os.setsid();os.execv(sys.argv[1],sys.argv[1:])'
BASE_PATHS = sorted(['/etc/ld.so.cache', PYTHON] + ['/usr/lib/'+name for name in (
    'ld-linux-x86-64.so.2', 'libc.so.6', 'libdl.so.2', 'libm.so.6',
    'libpthread.so.0', 'librt.so.1', 'libutil.so.1')])


PARENT_ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')


def api():
    return importlib.import_module('palimpsest.puck_cpu_namespace')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


@pytest.fixture
def arguments(tmp_path):
    paths = {}
    for key in ('stage_parent','source_root','control_root','output_root','site_root','generated_root'):
        path = tmp_path/key
        path.mkdir(mode=0o700)
        paths[key] = str(path)
    return dict(phase='prepare',command=[PYTHON,'-I','-S','-B','-c','pass'],
                environment={'HOME':'/scratch/home','TMPDIR':'/scratch/tmp'},**paths)


def build(arguments, baseline=BASELINE, native=NATIVE, baseline_paths=BASE_PATHS):
    return api().sandbox_command(baseline,native,baseline_paths,**arguments)


def binds(command, option):
    return [(command[i+1],command[i+2]) for i,value in enumerate(command) if value==option]


def qualify(arguments):
    result = dict(arguments,phase='qualify',site_root=None,generated_root=None)
    (Path(result['stage_parent'])/'inputs').mkdir(mode=0o700)
    return result


def test_prepare_exact_mounts_and_private_scratch(arguments):
    command = build(arguments)
    readonly = binds(command,'--ro-bind')
    assert (BASELINE['python_prefix'],BASELINE['python_prefix']) in readonly
    assert (arguments['source_root'],'/puck/source') in readonly
    assert (arguments['control_root'],'/puck/control') in readonly
    for key in ('site_root','generated_root'):
        assert (arguments[key],arguments[key]) in readonly
    for row in NATIVE['native_files']:
        assert (row['path'],row['path']) in readonly
    assert binds(command,'--bind')==[(arguments['stage_parent'],'/puck/staged'),
                                   (arguments['output_root'],'/output')]
    assert '--clearenv' in command and '--unshare-all' in command
    assert '--as-pid-1' in command
    assert command[command.index('--size')+1:command.index('--size')+4]==['67108864','--tmpfs','/scratch']
    for name in ('home','tmp','pycache'):
        assert ['--chmod','0700','/scratch/'+name] == command[command.index('/scratch/'+name)+1:command.index('/scratch/'+name)+4]
    assert ('scratch/tmp','/tmp') in binds(command,'--symlink')
    assert command[-len(arguments['command']):]==arguments['command']
    assert command[-len(arguments['command'])-2:-len(arguments['command'])]==['--chdir','/puck/source']
    assert command.count('--remount-ro')==3


def test_exact_cpu_parent_environment_retains_empty_cuda_value(arguments):
    arguments['environment']=PARENT_ENVIRONMENT
    command=build(arguments)
    assert dict(binds(command,'--setenv'))==PARENT_ENVIRONMENT
    assert ('CUDA_VISIBLE_DEVICES','') in binds(command,'--setenv')


def test_exact_seeded_cpu_parent_worker_command_accepts_python_whitespace(arguments):
    path=ROOT/'scripts/qualify_puck_cpu_held_runtime.py'
    spec=importlib.util.spec_from_file_location('cpu_namespace_parent_command_test',path)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    files=[]
    for relative in parent.WORKER_SOURCES:
        raw=(ROOT/relative).read_bytes()
        files.append(dict(path=relative,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    worker,command=parent.worker_registration(files,b'{"authored":"inert dependencies"}',negative_imports=['org'])
    assert command[:5]==[PYTHON,'-I','-B','-S','-c']
    assert command[5].startswith('import os,sys,stat,hashlib\n') and '\n' in command[5]
    assert worker['argv_prefix']==command[:-1]
    assert all(0<len(arg.encode())<=4096 for arg in command)
    arguments['command']=command
    built=build(arguments)
    assert built[-len(command):]==command


def test_qualify_only_input_tree_and_selective_original_baseline(arguments):
    args = qualify(arguments)
    command = build(args)
    assert '--as-pid-1' not in command
    assert '--new-session' not in command
    readonly = binds(command,'--ro-bind')
    assert (args['stage_parent']+'/inputs','/puck/staged/inputs') in readonly
    assert not any(source==args['stage_parent'] for source,target in readonly+binds(command,'--bind'))
    assert binds(command,'--bind')==[(args['output_root'],'/output')]
    for row in NATIVE['native_files']:
        path = row['path']
        expected = path if path in BASE_PATHS else args['stage_parent']+'/inputs/root-0001/'+path.removeprefix('/usr/')
        assert (expected,path) in readonly
    assert ('/usr/lib/libgcc_s.so.1','/usr/lib/libgcc_s.so.1') not in readonly
    assert ('/usr/lib/libcap.so.2.78','/usr/lib/libcap.so.2.78') not in readonly
    assert not any(source in (arguments['site_root'],arguments['generated_root']) for source,target in readonly)


def test_qualify_maps_nonbaseline_etc_to_root_two(arguments):
    native = copy.deepcopy(NATIVE)
    native['native_files'].append({'path':'/etc/authored.conf'})
    command = build(qualify(arguments),native=native)
    assert (arguments['stage_parent']+'/inputs/root-0002/authored.conf','/etc/authored.conf') in binds(command,'--ro-bind')


@pytest.mark.parametrize('changed',[
    lambda rows: rows[:-1],
    lambda rows: rows+[rows[0]],
    lambda rows: rows+['/usr/lib/libgcc_s.so.1'],
    lambda rows: list(reversed(rows)),
    lambda rows: rows[:-1]+['/usr/lib/../lib/libutil.so.1'],
])
def test_only_exact_sorted_authenticated_nine_baseline_paths(arguments,changed):
    with pytest.raises(ValueError,match='baseline'):
        build(arguments,baseline_paths=changed(BASE_PATHS))


@pytest.mark.parametrize('field,value',[
    ('phase','observe'),('scratch_bytes',0),('scratch_bytes',True),('scratch_bytes',64*1024**2+1),
    ('source_root','/'),('source_root','/proc'),('source_root','/dev'),
    ('source_root','/sys'),('control_root','/etc'),('control_root','relative'),('output_root','/tmp/../output'),
    ('site_root','/usr'),('generated_root','/scratch/generated'),
    ('command',[]),('command',['/bin/true','bad\x00arg']),
    ('command',[PYTHON,'-c','']),('command',[PYTHON,'-c','x'*4097]),
    ('command',[PYTHON,'-c','é'*2049]),
    ('environment',{'BAD=KEY':'x'}),('environment',{'HOME':'bad\x00value'}),
])
def test_reject_unsafe_namespace_arguments(arguments,field,value):
    arguments[field]=value
    with pytest.raises(ValueError): build(arguments)


def test_reject_overlapping_host_inputs_and_nonprivate_stage(arguments):
    arguments['source_root']=arguments['control_root']
    with pytest.raises(ValueError,match='overlap'): build(arguments)
    arguments['source_root']=str(Path(arguments['control_root']).parent/'source_root')
    os.chmod(arguments['stage_parent'],0o755)
    with pytest.raises(ValueError,match='0700'): build(arguments)


def test_reject_preexisting_prepare_input_and_qualify_source_exposure(arguments):
    (Path(arguments['stage_parent'])/'inputs').mkdir(mode=0o700)
    with pytest.raises(ValueError,match='exist'): build(arguments)
    arguments['phase']='qualify'
    with pytest.raises(ValueError,match='prepare'): build(arguments)


@pytest.mark.parametrize('mutation',[
    lambda native: native['native_files'].append(native['native_files'][0]),
    lambda native: native['native_files'].append({'path':'/tmp/untrusted.so'}),
    lambda native: native['aliases'].append(['/lib','different']),
    lambda native: native['aliases'].append(['/scratch','usr/lib']),
    lambda native: native['aliases'].append(['/usr/lib/escape.so','../escape']),
    lambda native: native['aliases'].append(['/usr/lib/libc.so.6','other.so']),
])
def test_reject_duplicate_conflicting_or_unsafe_native_mounts(arguments,mutation):
    native=copy.deepcopy(NATIVE);mutation(native)
    with pytest.raises(ValueError):build(arguments,native=native)


def test_identical_cross_manifest_aliases_are_merged_once(arguments):
    command=build(arguments)
    assert binds(command,'--symlink').count(('usr/lib','/lib'))==1


RUNNER = r'''
import errno, hashlib, json, os, sys, time
from pathlib import Path
sys.path.insert(0,'/puck/source/src')
from palimpsest.puck_dependency_files import HeldDependencyNamespace
from palimpsest.puck_native_identity import require_tmpfs_descriptor
from palimpsest.puck_runtime_staging import stage_tmpfs_registration

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def receipt(path):
    with path.open('rb') as stream:
        identity=require_tmpfs_descriptor(stream.fileno())
        return dict(identity=list(identity),sha256=hashlib.sha256(stream.read()).hexdigest())

phase=sys.argv[1]
assert sys.pycache_prefix=='/scratch/pycache'
assert Path('/scratch/home').stat().st_mode&0o777==0o700
assert not Path(sys.argv[2]).exists(), 'host stage path exposed'
if phase=='prepare':
    raw=Path('/puck/control/source.json').read_bytes()
    reg=stage_tmpfs_registration(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),
        staging_root='/puck/staged/inputs',deadline=time.monotonic()+15)
    Path('/output/registration.json').write_bytes(canonical(reg))
    leaf=Path(reg['roots'][0]['root'])/'demo/__init__.py'
    result=receipt(leaf)
    assert Path('/puck/staged').stat().st_mode&0o777==0o700
    Path('/puck/staged/normal-write').write_text('authored writable tmpfs parent')
    Path('/puck/staged/normal-write').unlink()
else:
    raw=Path('/puck/control/held.json').read_bytes()
    reg=json.loads(raw)
    assert not Path('/puck/staged/host-sibling').exists()
    native=Path('/usr/lib/puck_cpu_namespace_authored.bin')
    assert native.read_bytes()==b'authored inert native-path data'
    assert receipt(native)==receipt(Path(reg['roots'][1]['root'])/'lib/puck_cpu_namespace_authored.bin')
    assert not Path(sys.argv[3]).exists(), 'authored source host path exposed in qualification'
    held=HeldDependencyNamespace(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),
        deadline=time.monotonic()+15,registration_path='/puck/control/held.json')
    with held:
        leaf=Path(reg['roots'][0]['root'])/'demo/__init__.py'
        assert held.read(0,'demo/__init__.py')==b'raise AssertionError("authored bytes stay inert")\n'
        result=receipt(leaf)
        for path in (leaf,leaf.parent/'new-file'):
            try:
                path.write_bytes(b'must not write')
            except OSError as error:
                assert error.errno==errno.EROFS
            else:raise AssertionError('qualification input writable')
        held.recheck()
        assert held.snapshot()['runtime_qualified'] is False
        result['held_consumer']=True
        result['readonly']=True
        result['process']=dict(pid=os.getpid(),ppid=os.getppid(),pgid=os.getpgrp(),sid=os.getsid(0))
        assert result['process']==dict(pid=2,ppid=1,pgid=2,sid=2)
        result['parent_stat_readable']=Path('/proc/1/stat').read_bytes().startswith(b'1 (')
        assert result['parent_stat_readable']
        result['argv']=sys.orig_argv
Path('/output/'+phase+'.json').write_bytes(canonical(result))
if phase=='qualify':time.sleep(0.3)
'''


def host_process_tree(pid):
    rows={};pending=[pid]
    while pending:
        current=pending.pop()
        if current in rows:continue
        path=Path('/proc')/str(current)
        values=(path/'stat').read_bytes().rsplit(b')',1)[1].split()
        nspid=next(line.split()[1:] for line in (path/'status').read_text().splitlines()
                   if line.startswith('NSpid:'))
        rows[current]=dict(pid=current,ppid=int(values[1]),pgid=int(values[2]),sid=int(values[3]),
                           start_tick=int(values[19]),nspid=[int(value) for value in nspid])
        pending.extend(int(value) for value in (path/'task'/str(current)/'children').read_text().split())
    return rows


def test_real_two_bwrap_passes_preserve_raw_tmpfs_inode_and_held_custody(tmp_path):
    source=tmp_path/'capsule';source.mkdir(mode=0o700)
    package=source/'src/palimpsest';package.mkdir(parents=True)
    for name in ('__init__.py','bounded_qualification.py','puck_dependency_bindings.py',
                 'puck_dependency_files.py','puck_execution_files.py','puck_native_identity.py',
                 'puck_runtime_registration.py','puck_runtime_staging.py'):
        shutil.copyfile(ROOT/'src/palimpsest'/name,package/name)
    (source/'runner.py').write_text(RUNNER)
    control=tmp_path/'control';control.mkdir(mode=0o700)
    output=tmp_path/'output';output.mkdir(mode=0o700)
    site=tmp_path/'authored-site';(site/'demo').mkdir(parents=True)
    payload=b'raise AssertionError("authored bytes stay inert")\n'
    (site/'demo/__init__.py').write_bytes(payload)
    reg=dict(kind='puck-worker-dependencies-v3',version=3,native_identity='tmpfs-raw-dev-inode-v1',
        roots=[dict(root=str(site),kind='package',files=[dict(path='demo/__init__.py',
            size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())])],
        modules=[dict(name='demo',root_index=0,path='demo/__init__.py',kind='python',is_package=True)],
        namespaces=[],distributions=[],import_profile=dict(exports=[],module_changes=[],native_origins=[]))
    generated=tmp_path/'authored-generated';(generated/'lib').mkdir(parents=True)
    native_data=b'authored inert native-path data'
    (generated/'lib/puck_cpu_namespace_authored.bin').write_bytes(native_data)
    reg['roots'].append(dict(root=str(generated),kind='package',files=[dict(
        path='lib/puck_cpu_namespace_authored.bin',size_bytes=len(native_data),
        sha256=hashlib.sha256(native_data).hexdigest())]))
    (control/'source.json').write_bytes(canonical(reg))
    native={'native_files':[row for row in NATIVE['native_files'] if row['path'] in BASE_PATHS],
            'aliases':BASELINE['host_path_aliases']}
    with tempfile.TemporaryDirectory(prefix='puck-authored-two-pass-',dir='/tmp') as temporary:
        ancestor=Path(temporary);stage=ancestor/'private-stage';stage.mkdir(mode=0o700)
        args=dict(stage_parent=str(stage),source_root=str(source),control_root=str(control),
            output_root=str(output),environment=PARENT_ENVIRONMENT,
            command=[PYTHON,'-I','-S','-B','-X','pycache_prefix=/scratch/pycache',
                     '/puck/source/runner.py','prepare',str(stage)])
        first=build(dict(args,phase='prepare',site_root=str(site),generated_root=str(generated)),native=native)
        result=subprocess.run(first,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        (output/'prepare.stdout').write_bytes(result.stdout);(output/'prepare.stderr').write_bytes(result.stderr)
        assert result.returncode==0,result.stderr.decode(errors='replace')
        assert (stage/'inputs/root-0000/demo/__init__.py').read_bytes()==payload
        shutil.copyfile(output/'registration.json',control/'held.json')
        (ancestor/'ancestor-sibling').mkdir()
        (stage/'host-sibling').write_bytes(b'host mutation between private namespaces')
        args['command']=args['command'][:-2]+['qualify',str(stage),str(site)]
        native['native_files'].append({'path':'/usr/lib/puck_cpu_namespace_authored.bin'})
        worker_command=args['command']
        args['command']=[PYTHON,'-I','-S','-B','-c',QUALIFICATION_LAUNCHER]+worker_command
        second=build(dict(args,phase='qualify'),native=native)
        process=subprocess.Popen(second,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            ready=output/'qualify.json';until=time.monotonic()+3
            while not ready.exists() and process.poll() is None and time.monotonic()<until:
                time.sleep(.005)
            assert ready.is_file(), 'authored qualification topology receipt missing'
            tree=host_process_tree(process.pid)
            assert len(tree)==3
            worker=next(row for row in tree.values() if row['nspid'][-1]==2)
            init=next(row for row in tree.values() if row['nspid'][-1]==1)
            assert worker['ppid']==init['pid']
            assert worker['pid']==worker['pgid']==worker['sid']
            assert worker['pgid']!=process.pid and init['pgid']==process.pid
            topology=dict(outer_popen_pid=process.pid,host_tree=list(tree.values()),
                          worker_in_outer_group=False,descendant_supervision_required=True)
            (output/'topology.json').write_bytes(canonical(topology))
            stdout,stderr=process.communicate(timeout=3)
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=1)
        (output/'qualify.stdout').write_bytes(stdout);(output/'qualify.stderr').write_bytes(stderr)
        assert process.returncode==0,stderr.decode(errors='replace')
        before=json.loads((output/'prepare.json').read_bytes())
        after=json.loads((output/'qualify.json').read_bytes())
        assert before['identity']==after['identity']
        assert before['sha256']==after['sha256']==hashlib.sha256(payload).hexdigest()
        assert after['held_consumer'] is True and after['readonly'] is True
        assert after['process']==dict(pid=2,ppid=1,pgid=2,sid=2)
        assert after['parent_stat_readable'] is True and after['argv']==worker_command
        assert (stage/'inputs/root-0000/demo/__init__.py').read_bytes()==payload
