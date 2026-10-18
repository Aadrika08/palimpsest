"""Independent-auditor control failures, with no repository validator imports."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/audit_puck_cpu_held_runtime.py'


def api():
    assert SCRIPT.is_file(),'Independent CPU held auditor is missing'
    spec=importlib.util.spec_from_file_location('independent_cpu_audit_test',SCRIPT)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def sha(raw):return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('raw',[b'{"kind":1,"kind":2}',b'{"x":NaN}',b'{"x":1e999}',
    b'['*34+b'0'+b']'*34,b'{}',b'[]',b'not json'])
def test_malformed_authenticated_configuration_rejects_without_leaking_fds(tmp_path,raw):
    m=api();config=tmp_path/'config.json';config.write_bytes(raw)
    transport=tmp_path/'transport.json';transport.write_bytes(b'{}')
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError):
        m.audit(config,sha(raw),transport,sha(b'{}'),deadline=time.monotonic()+30)
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('deadline',[True,float('nan'),float('inf'),0,-1])
def test_invalid_deadline_is_not_an_audit(tmp_path,deadline):
    m=api()
    with pytest.raises(ValueError):m.audit(tmp_path/'absent','0'*64,tmp_path/'absent2','0'*64,deadline=deadline)


def test_external_hashes_are_required_before_decoding(tmp_path):
    m=api();config=tmp_path/'config.json';config.write_bytes(b'not json')
    transport=tmp_path/'transport.json';transport.write_bytes(b'{}')
    with pytest.raises(ValueError,match='hash|SHA|pin'):
        m.audit(config,'0'*64,transport,sha(b'{}'),deadline=time.monotonic()+30)


def test_cli_publishes_failed_audit_exclusively(tmp_path):
    api();config=tmp_path/'config.json';config.write_bytes(b'{}')
    transport=tmp_path/'transport.json';transport.write_bytes(b'{}');output=tmp_path/'audit.json'
    command=[sys.executable,'-I','-S','-B',str(SCRIPT),'--configuration',str(config),'--sha256',sha(b'{}'),
             '--transport',str(transport),'--transport-sha256',sha(b'{}'),'--output',str(output)]
    first=subprocess.run(command,capture_output=True,timeout=10)
    assert first.returncode!=0
    raw=output.read_bytes();result=json.loads(raw)
    assert result['status']=='FAIL' and result['runtime_qualified'] is False
    assert result['auditor_source_sha256']==sha(SCRIPT.read_bytes())
    second=subprocess.run(command,capture_output=True,timeout=10)
    assert second.returncode!=0 and output.read_bytes()==raw


def binding_fixture():
    modules=[dict(name=n,path=n+'.py') for n in ('mujoco','numpy','torch','torchvision')]
    profile=dict(exports=[dict(name='torch.created',producer='torch')],
        native_origins=[dict(name='numpy',policy='held-directory-observed-v1')],
        module_changes=[dict(name='torch',kind='replace')],
        native_cache=[dict(name='authored_cache',producer='numpy',phase='module_exec',delegate_attributes=['delegate'])])
    dependency=dict(modules=modules,namespaces=[],import_profile=profile)
    receipt=dict(loaded_modules=modules,exported_modules=[dict(name='torch.created',producer='torch')],
        native_origin_policies={'numpy':'held-directory-observed-v1'},native_cache_modules=profile['native_cache'],
        module_dispatch_bindings=[dict(name=r['name'],original_metadata_bound=r['name']=='torch',
            delegate_attributes=['method'] if r['name']=='torch' else []) for r in modules])
    return dependency,receipt


def test_nonempty_producer_origin_and_cache_receipt_is_complete():
    m=api();dependency,receipt=binding_fixture();m.binding_receipt(receipt,dependency)


@pytest.mark.parametrize('key',['loaded_modules','exported_modules','native_origin_policies','native_cache_modules'])
def test_nonempty_binding_receipt_cannot_omit_required_proof(key):
    m=api();dependency,receipt=binding_fixture();receipt[key]={} if key=='native_origin_policies' else []
    with pytest.raises(ValueError):m.binding_receipt(receipt,dependency)


@pytest.mark.parametrize('extra',['stage','inputs'])
def test_private_mount_wrappers_have_only_the_four_declared_roots(extra):
    import tempfile
    m=api()
    with tempfile.TemporaryDirectory(prefix='palimpsest-puck-cpu-held-audit-wrapper-') as directory:
        stage=Path(directory);inputs=stage/'inputs';inputs.mkdir(mode=0o700)
        roots=[];identities=[]
        for i in range(4):
            path=inputs/('root-'+str(i).zfill(4));path.mkdir(mode=0o700);state=path.stat()
            identities.append(dict(root_index=i,device=state.st_dev,inode=state.st_ino));roots.append(dict(files=[]))
        (stage if extra=='stage' else inputs).joinpath('undeclared.py').write_bytes(b'INERT = True\n')
        held=m.Held(time.monotonic()+30)
        try:
            with pytest.raises(ValueError,match='(?i)(wrapper|namespace|staged)'):
                m.forest(held,dict(stage_parent=str(stage)),dict(roots=roots,distributions=[]),[[]]*4,identities)
        finally:held.close()


def test_cli_kernel_alarm_terminates_without_entering_failure_publication(tmp_path):
    api();published=tmp_path/'unexpected-publication'
    # Shorten only the authored child's timer; retain main's actual signal
    # disposition. A stalled audit must terminate, without attempting a second
    # potentially stalled publication after a catchable Python timeout.
    seed='''import importlib.util,pathlib,signal,sys,time
spec=importlib.util.spec_from_file_location('authored_audit_alarm',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.signal.setitimer
m.signal.setitimer=lambda kind,seconds:original(kind,0.1 if seconds else 0)
m.audit=lambda *args,**kwargs:time.sleep(10)
publication=pathlib.Path(sys.argv[2])
m.publish=lambda *args:publication.write_bytes(b'publication was attempted')
sys.argv=[sys.argv[1],'--configuration','/unused','--sha256','0'*64,'--transport','/unused','--transport-sha256','0'*64,'--output','/unused']
raise SystemExit(m.main())
'''
    process=subprocess.run([sys.executable,'-I','-S','-B','-c',seed,str(SCRIPT),str(published)],capture_output=True,timeout=5)
    import signal
    assert process.returncode==-signal.SIGALRM and not published.exists(),(process.returncode,process.stdout,process.stderr)
