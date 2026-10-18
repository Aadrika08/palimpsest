"""AUTHORED chain: characterization-04 -> candidate 02 -> preparation04 -> allocation 16.

Every stage is the real parent CLI over the authored project; allocation 16 runs
the real held v4 bootstrap twice (source, then replay over the read-only source
output) on preparation04's staged roots. The episode entry is the stdlib
stand-in, so no vendor package, renderer or simulation runs.
"""
import json
import os
from pathlib import Path
import secrets
import shutil

import pytest

from puck_episode_authored import (allocation16, authored_scale, characterize, derive_candidate, episode_project,
                                   prepare04, sha)


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    base=tmp_path_factory.mktemp('episode16')
    assert base.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'runs'),'Use persistent runs/ basetemp'
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-04-authored-'+secrets.token_hex(8))
    try:
        project=episode_project(base);authored_scale(project)
        yield allocation16(prepare04(derive_candidate(characterize(project)),stage))
    finally:
        if os.path.lexists(stage):
            for parent,directories,_ in os.walk(stage):
                for name in directories:os.chmod(os.path.join(parent,name),0o700)
            shutil.rmtree(stage)


def test_allocation16_completes_one_held_episode(chain):
    code,stdout,stderr=chain['episode'];result=chain['result']
    assert code==0,(stderr.decode()[-4000:],result and result.get('error'))
    root=chain['root'];output=root/'runs/puck-cpu-held-episode-16'
    assert json.loads(stdout)==result and result['status']=='episode_completed' and result['held_episode_observed'] is True
    assert (result['kind'],result['version'],result['allocation_id'])==('puck-cpu-held-episode-outcome-v16',16,16)
    assert result['ticks_completed']==48 and result['process_creation_attempts']==0
    assert result['replay']==dict(status='passed',compared_ticks=48,compared_events=result['replay']['compared_events'],first_divergence=None)
    assert all(result[k] is False for k in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))
    for phase in ('source','replay'):
        run=result['runs'][phase];payload=output/('payload-'+phase)
        assert run['run_id']==chain['allocation']['run_ids'][phase]
        assert sha((payload/run['bundle']['path']).read_bytes())==run['bundle']['sha256']
        for row in run['files']:assert sha((payload/run['run_id']/row['path']).read_bytes())==row['sha256']
        receipt=json.loads((output/('logs-'+phase)/'stdout.log').read_bytes())
        assert receipt['episode_phase']==phase and receipt['process_creation_attempts']==dict(count=0,events=[])
        assert receipt['registration_sha256']==result['registration_sha256'][phase]
    assert result['replay_report']['path']=='replay-report.json'
    late=[dict(attribute='fused_cython_function',producers=[dict(producer='authoredcy._fused',phase='module_exec')])]
    candidate=json.loads((root/chain['candidate']['path']).read_bytes())
    assert candidate['import_profile']['native_cache']==[dict(name='_cython_authored',producer='authoredcy._creator',phase='module_exec',
        delegate_attributes=['cython_function_or_method'],late_delegates=late)]
    for phase in ('source','replay'):
        receipt=json.loads((output/('logs-'+phase)/'stdout.log').read_bytes())
        assert receipt['dependencies']['native_cache_modules']==candidate['import_profile']['native_cache']


def test_allocation16_is_reserved_once(chain):
    from puck_episode_authored import EPISODE_PARENT,PYTHON,run
    root=chain['root'];configuration=chain['episode_configuration']
    code,_,stderr=run([PYTHON,'-I','-S','-B',str(root/EPISODE_PARENT),'--configuration',str(configuration),
                       '--sha256',sha(configuration.read_bytes())],root)
    assert code!=0 and b'Allocation 16 already reserved' in stderr
