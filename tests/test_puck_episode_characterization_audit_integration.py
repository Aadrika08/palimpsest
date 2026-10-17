"""Characterization-04 observer, independent outcome auditor and archive over an AUTHORED project.

The real characterization-04 parent runs through the real observer on an authored
clone (authored site, accepted receipts, native v6 from host rows and the
stdlib episode stand-in). The independent auditor must PASS the exact contract
preparation04 binds and refuse tampered bytes; the archive tool writes the
evidence index preparation04 reads.
"""
import json
import os
from pathlib import Path
import shutil

import pytest

from puck_episode_authored import PYTHON, audit_characterization, characterize, episode_project, load, run, sha

AUDIT_KIND='cpu-episode-characterization-outcome-audit-v1'
OUTPUT='runs/puck-cpu-runtime-characterization-04'
ROLE_PATHS={'frozen-configuration.json','raw/payload/source/characterization.json','raw/payload/replay/characterization.json',
            'raw/result.json','outcome-audit-04.json'}


@pytest.fixture(scope='module')
def characterized(tmp_path_factory):
    return characterize(episode_project(tmp_path_factory.mktemp('characterization04')))


def test_observer_records_one_normal_transport(characterized):
    code,stdout,stderr=characterized['observer']
    root=characterized['root'];transport=json.loads(characterized['transport'].read_bytes())
    result=json.loads((root/OUTPUT/'result.json').read_bytes())
    assert code==0,(stderr,result.get('error'))
    assert transport['kind']=='puck-cpu-episode-characterization-cli-transport-v1' and transport['observed_returncode']==0
    assert transport['timed_out'] is False and transport['configuration_sha256']==sha(characterized['configuration_raw'])
    assert json.loads((root/transport['stdout']['path']).read_bytes())==result and result['status']=='observed'
    for name in ('stdout','stderr'):assert ((root/transport[name]['path']).stat().st_mode&0o777)==0o600
    assert result['process_creation_attempts']==0 and result['ticks_completed']==48
    assert result['replay']==dict(status='passed',compared_ticks=48,compared_events=result['replay']['compared_events'],first_divergence=None)
    again=run([PYTHON,'-I','-S','-B',str(root/'scripts/observe_puck_cpu_episode_characterization.py'),'--configuration',
               str(characterized['configuration']),'--sha256',sha(characterized['configuration_raw'])],root)
    assert again[0]!=0 and b'already reserved' in again[2]


def test_independent_audit_passes_with_the_bound_contract(characterized):
    code,value,stdout,stderr,output=audit_characterization(characterized)
    assert code==0,(value,stderr)
    root=characterized['root'];verified=value['verified']
    assert value['kind']==AUDIT_KIND and value['status']=='PASS' and value['target_code_executed_by_auditor'] is False
    assert all(value[k] is False for k in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))
    assert verified['configuration_sha256']==sha(characterized['configuration_raw'])
    assert verified['result_sha256']==sha((root/OUTPUT/'result.json').read_bytes())
    for phase in ('source','replay'):
        assert verified[phase+'_report_sha256']==sha((root/OUTPUT/('payload-'+phase)/'characterization.json').read_bytes())
    assert verified['transport_sha256']==sha(characterized['transport'].read_bytes())
    assert json.loads(stdout)==value and output.read_bytes()==stdout


def tampered(characterized,label,path,mutate):
    original=path.read_bytes()
    try:
        mutate(path)
        return audit_characterization(characterized,'docs/authored/tamper-'+label+'.json')
    finally:
        if path.exists() and path.is_file():path.unlink()
        elif path.exists():shutil.rmtree(path)
        path.write_bytes(original)


@pytest.mark.parametrize('label',['report','bundle','result','extra-member','request','supervision','vendor'])
def test_independent_audit_refuses_tampered_retained_bytes(characterized,label):
    root=characterized['root'];output=root/OUTPUT
    def flip(path):raw=bytearray(path.read_bytes());raw[len(raw)//2]^=1;path.write_bytes(bytes(raw))
    if label=='extra-member':
        extra=output/'unexpected.json'
        try:
            extra.write_bytes(b'{}\n');code,value,*_=audit_characterization(characterized,'docs/authored/tamper-extra.json')
        finally:extra.unlink()
    else:
        path={'report':output/'payload-source/characterization.json','bundle':output/'payload-replay/replay-bundle.zip',
              'result':output/'result.json','request':output/'request-replay.json','supervision':output/'source-supervision.json',
              'vendor':output/'egl-vendor.json'}[label]
        code,value,*_=tampered(characterized,label,path,flip)
    assert code!=0 and value['status']=='FAIL' and 'verified' not in value


def test_audit_refuses_a_different_transport_pin(characterized):
    root=characterized['root'];output=root/'docs/authored/tamper-transport-pin.json'
    code,_,_=run([PYTHON,'-I','-S','-B',str(root/'scripts/audit_puck_cpu_episode_characterization.py'),'--configuration',
        str(characterized['configuration']),'--sha256',sha(characterized['configuration_raw']),'--transport',str(characterized['transport']),
        '--transport-sha256','0'*64,'--output',str(output)],root)
    assert code!=0 and json.loads(output.read_bytes())['status']=='FAIL'


def test_archive_writes_the_index_preparation04_binds(characterized):
    root=characterized['root'];code,value,*_,output=audit_characterization(characterized,'docs/authored/archive-audit.json')
    assert code==0
    tool=load(root/'scripts/archive_puck_episode_characterization.py','authored_archive04')
    receipt=tool.archive(characterized['configuration'],output,'docs/authored/characterization-04-archive')
    archive=root/'docs/authored/characterization-04-archive';index=json.loads((archive/'evidence-index.json').read_bytes())
    assert index['kind']=='cpu-episode-characterization-evidence-index-v1' and receipt['sha256']==sha((archive/'evidence-index.json').read_bytes())
    rows={r['path']:r for r in index['entries']}
    assert ROLE_PATHS<=set(rows) and index['file_count']==len(rows)
    for path,row in rows.items():assert row==dict(path=path,size_bytes=(archive/path).stat().st_size,sha256=sha((archive/path).read_bytes()))
    assert (archive/'frozen-configuration.json').read_bytes()==characterized['configuration_raw']
    assert (archive/'raw/payload/source/characterization.json').read_bytes()==(root/OUTPUT/'payload-source/characterization.json').read_bytes()
    with pytest.raises(FileExistsError):tool.archive(characterized['configuration'],output,'docs/authored/characterization-04-archive')
    failed=root/'docs/authored/failed-audit.json';failed.write_bytes(json.dumps(dict(value,status='FAIL')).encode())
    with pytest.raises(ValueError):tool.archive(characterized['configuration'],failed,'docs/authored/other-archive')


def test_observer_refuses_another_identity_before_launch(tmp_path):
    project=episode_project(tmp_path);root=project['root']
    config=root/'docs/authored/not-characterization04.json';raw=json.dumps(dict(kind='puck-cpu-runtime-characterization-v2',version=2,
        output=OUTPUT)).encode();config.parent.mkdir(parents=True,exist_ok=True);config.write_bytes(raw)
    code,_,stderr=run([PYTHON,'-I','-S','-B',str(root/'scripts/observe_puck_cpu_episode_characterization.py'),'--configuration',
        str(config),'--sha256',sha(raw)],root)
    assert code!=0 and b'Exact characterization-04 identity' in stderr and not (root/'runs/puck-cpu-runtime-characterization-04').exists()


def test_a_refused_process_creation_fails_the_observation_and_its_audit(tmp_path):
    characterized=characterize(episode_project(tmp_path,defect='spawn'))
    root=characterized['root'];result=json.loads((root/OUTPUT/'result.json').read_bytes())
    report=json.loads((root/OUTPUT/'payload-source/characterization.json').read_bytes())
    assert characterized['observer'][0]!=0 and result['status']=='FAIL'
    assert report['process_creation_attempts']==dict(count=1,events=['subprocess.Popen'])
    code,value,*_=audit_characterization(characterized)
    assert code!=0 and value['status']=='FAIL'
