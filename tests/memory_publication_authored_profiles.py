"""Explicit test-only current-profile fixtures; never an accepted qualification.

Opted-in test modules bind authored profiles to current source bytes without
editing historical JSON or real trust anchors. Actual raw-auditor subprocesses
receive exactly that authored profile. The fixture does not populate execution
or qualification pins and cannot authorize research or protected execution.
"""
import copy
import hashlib
import pytest
from palimpsest import memory
from scripts import memory_family_compact_v4 as compact

def _install_authored_profile(patch, profile_path, extension_path):
    """Test-only prospective identities; never change historical profile bytes."""
    from scripts import memory_family_raw_audit_v4 as audit
    from scripts import memory_family_oracle_admission_v4 as pair
    from scripts import memory_family_producer_v4 as source
    from scripts import memory_family_condition_seal_v4 as seal
    from pathlib import Path
    payload=Path(profile_path).read_bytes(); value=__import__('json').loads(payload)
    digest=hashlib.sha256(payload).hexdigest()
    for mod in (compact,audit,pair,source):
        patch.setattr(mod,'PROTOCOL',value)
        if hasattr(mod,'PROTOCOL_SHA256'):patch.setattr(mod,'PROTOCOL_SHA256',digest)
        if hasattr(mod,'PROTOCOL_BYTES'):patch.setattr(mod,'PROTOCOL_BYTES',payload)
    patch.setattr(compact,'PROTOCOL_PATH',Path(profile_path))
    patch.setattr(seal,'EXTENSION_PATH',extension_path)


def _authored_current_profile(tmp_path, patch, request):
    import subprocess,sys
    from pathlib import Path
    from scripts import memory_family_condition_seal_v4 as seal
    root=Path(__file__).resolve().parents[1]
    import tempfile
    profile_directory=tempfile.TemporaryDirectory(prefix='memory-publication-authored-',dir=root/'tests')
    request.addfinalizer(profile_directory.cleanup)
    tmp_path=Path(profile_directory.name)
    profile=copy.deepcopy(compact.PROTOCOL)
    for d in profile['behavior_sources']:
        payload=(root/d['path']).read_bytes()
        d.update(size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    profile_path=tmp_path/'authored-prospective-compact.json'
    payload=memory.canonical_bytes(profile);profile_path.write_bytes(payload)
    extension=__import__('json').loads((root/seal.EXTENSION_PATH).read_bytes())
    extension['base_protocol_sha256']=hashlib.sha256(payload).hexdigest()
    for d in extension['source_pins']:
        payload=(root/d['path']).read_bytes();d.update(size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    extension_path=tmp_path/'authored-prospective-seal.json'
    extension_path.write_bytes(memory.canonical_bytes(extension))
    relative_extension=extension_path.relative_to(root).as_posix()
    _install_authored_profile(patch,profile_path,relative_extension)
    original=subprocess.run
    def run(command,*args,**kwargs):
        if len(command)>1 and command[1]==str(root/'scripts/memory_family_raw_audit_v4.py'):
            code=('import sys;sys.path[:0]=["tests","src","."];import pytest;'
                  'from test_memory_family_case_publication_v1 import _install_authored_profile;'
                  'from scripts import memory_family_raw_audit_v4 as audit;'
                  'p=pytest.MonkeyPatch();_install_authored_profile(p,sys.argv[1],sys.argv[2]);'
                  'audit.main(sys.argv[3:])')
            command=[command[0],'-B','-c',code,str(profile_path),relative_extension,*command[2:]]
        return original(command,*args,**kwargs)
    patch.setattr(subprocess,'run',run)


@pytest.fixture(scope='module',autouse=True)
def authored_current_profile(request,tmp_path_factory):
    """Explicit module opt-in for current-semantic authored evidence only."""
    patch=pytest.MonkeyPatch()
    request.addfinalizer(patch.undo)
    _authored_current_profile(tmp_path_factory.mktemp('authored-profile'),patch,request)
    if hasattr(request.module,'PROTOCOL_PATH'):
        patch.setattr(request.module,'PROTOCOL_PATH',compact.PROTOCOL_PATH)
