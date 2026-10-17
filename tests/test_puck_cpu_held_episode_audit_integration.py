"""AUTHORED end to end: characterization-04 -> candidate 02 -> preparation04 -> allocation 16 -> episode audit.

The independent episode auditor must PASS the normal authored chain and refuse
snapshot, record, replay-report and registration drift, an emptied episode, a
failed worker, a tampered outcome and a different transport pin. Three
authored defects the parents cannot see (a constant camera frame, a replay that
diverges while reporting success, and an unlisted bundle member) must also fail
the audit.
"""
import json
import os
from pathlib import Path
import secrets
import shutil

import pytest

from puck_episode_authored import (PYTHON, allocation16, authored_scale, characterize, derive_candidate, episode_project,
                                   prepare04, run, sha)

AUDITOR='scripts/audit_puck_cpu_held_episode.py'
OUTPUT='runs/puck-cpu-held-episode-16'


def build_chain(base,defect=None):
    assert base.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'runs'),'Use persistent runs/ basetemp'
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-04-authored-'+secrets.token_hex(8))
    project=episode_project(base,defect=defect);authored_scale(project)
    return allocation16(prepare04(derive_candidate(characterize(project)),stage)),stage


def remove(stage):
    if os.path.lexists(stage):
        for parent,directories,_ in os.walk(stage):
            for name in directories:os.chmod(os.path.join(parent,name),0o700)
        shutil.rmtree(stage)


def audit(chain,label,transport_sha=None):
    root=chain['root'];configuration=chain['episode_configuration'];transport=root/'authored-episode16-transport.json'
    output=root/('docs/authored/episode-audit-'+label+'.json')
    code,stdout,stderr=run([PYTHON,'-I','-S','-B',str(root/AUDITOR),'--configuration',str(configuration),
        '--sha256',sha(configuration.read_bytes()),'--transport',str(transport),
        '--transport-sha256',transport_sha or sha(transport.read_bytes()),'--output',str(output)],root,330)
    return code,json.loads(output.read_bytes()) if output.exists() else None,stderr


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    value,stage=build_chain(tmp_path_factory.mktemp('episode-audit'))
    try:yield value
    finally:remove(stage)


def test_the_independent_episode_audit_passes_the_authored_chain(chain):
    assert chain['episode'][0]==0,chain['result']
    code,value,stderr=audit(chain,'pass')
    assert code==0,(value,stderr)
    verified=value['verified'];root=chain['root']
    assert value['kind']=='puck-cpu-held-episode-independent-audit-v1' and value['status']=='PASS'
    assert value['target_code_executed_by_auditor'] is False and verified['evidence_scope']=='AUTHORED fixture only'
    assert verified['result_sha256']==sha((root/OUTPUT/'result.json').read_bytes()) and verified['compared_ticks']==48
    assert verified['frames_checked']==2*4*48
    assert verified['validator_sha256']==sha((root/'scripts/validate_palimpsest_bundle.py').read_bytes())
    assert all(value[k] is False for k in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))


def flip(path):
    raw=bytearray(path.read_bytes());raw[len(raw)//2]^=1;path.write_bytes(bytes(raw))


def empty(path):
    lines=path.read_bytes().splitlines(keepends=True);path.write_bytes(lines[0])


@pytest.mark.parametrize('label',['snapshot','record','replay-report','registration','empty-episode','failed-worker','outcome','bundle'])
def test_the_episode_audit_refuses_retained_drift(chain,label):
    output=chain['root']/OUTPUT;ids=chain['allocation']['run_ids']
    source=output/'payload-source'/ids['source'];replay=output/'payload-replay'/ids['replay']
    path,mutate={'snapshot':(source/'snapshots/initial.snp',flip),'record':(source/'recording/chunks/000001.npz',flip),
        'replay-report':(replay/'replay-report.json',lambda p:p.write_bytes(p.read_bytes().replace(b'"compared_ticks":48',b'"compared_ticks":47'))),
        'registration':(output/'control/worker-registration-replay.json',flip),'empty-episode':(source/'recording/events.jsonl',empty),
        'failed-worker':(output/'source-supervision.json',lambda p:p.write_bytes(p.read_bytes().replace(b'"returncode":0',b'"returncode":1'))),
        'outcome':(output/'result.json',lambda p:p.write_bytes(p.read_bytes().replace(b'"ticks_completed":48',b'"ticks_completed":47'))),
        'bundle':(output/'payload-replay/replay-bundle.zip',flip)}[label]
    original=path.read_bytes()
    try:
        mutate(path);assert path.read_bytes()!=original
        code,value,_=audit(chain,'tamper-'+label)
    finally:path.write_bytes(original)
    assert code!=0 and value['status']=='FAIL' and 'verified' not in value


def test_the_episode_audit_refuses_a_different_transport_pin(chain):
    code,value,_=audit(chain,'transport-pin','0'*64)
    assert code!=0 and value['status']=='FAIL'


@pytest.mark.parametrize('defect,reason',[('constant-frame','Constant cam_left frame'),('diverge','Replay diverged'),
                                          ('unlisted-member','Bundle members differ')])
def test_defects_the_parents_cannot_see_fail_the_episode_audit(tmp_path,defect,reason):
    value,stage=build_chain(tmp_path,defect)
    try:
        assert value['episode'][0]==0 and value['result']['status']=='episode_completed'
        code,verdict,_=audit(value,'defect-'+defect)
        assert code!=0 and verdict['status']=='FAIL' and reason in verdict['error']
    finally:remove(stage)
