"""Held provenance: doctor-schema diagnostics derived only from authenticated pins.

No subprocess, importlib.metadata, platform, ambient sys/os value or filesystem
discovery may contribute. The record keeps every doctor check name and shape
used by recording admission and run comparison, plus one explicit pin check.
"""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import pytest

from palimpsest import doctor
from palimpsest.artifacts import _provenance
from palimpsest.held_provenance import HeldProvenance, held_provenance


SOURCE=Path(__file__).resolve().parents[1]/'src/palimpsest/held_provenance.py'
REFUSED=[False]
PROCESS_EVENTS={'subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty','os.spawn'}
DISCOVERY_EVENTS={'open','os.listdir','os.scandir','glob.glob','os.walk'}


def _hook(event,args):
    if REFUSED[0] and (event in PROCESS_EVENTS|DISCOVERY_EVENTS or event.startswith('os.exec')):
        raise RuntimeError('Held provenance performed an ambient operation: '+event)


sys.addaudithook(_hook)


def inputs(**changes):
    value=dict(
        interpreter=dict(path='/puck/runtime/python3.11',size_bytes=21662864,sha256='57'*32,python_version='3.11.15'),
        upstream=dict(path='/puck/source/upstream/fly-gym',commit=doctor.UPSTREAM_PIN,files=[
            dict(path='environment/__init__.py',size_bytes=10,sha256='1'*64),
            dict(path='environment/mujoco_two_cam_env_random_obstacles.py',size_bytes=20,sha256='2'*64)]),
        distributions=[dict(name=name,version='9.'+str(index),root_index=0,
                            metadata_path=name.replace('-','_')+'-9.'+str(index)+'.dist-info/METADATA')
                       for index,name in enumerate(doctor.SIMULATION_DISTRIBUTIONS)],
        palimpsest_version='0.1.0',lock_sha256='3'*64,
        environment=dict(MUJOCO_GL='egl',PATH='/nonexistent',LANG='C.UTF-8'))
    value.update(changes)
    return value


def doctor_report():
    root=Path(tempfile.mkdtemp())
    def run(args,**kwargs):
        if args[0]=='git':
            output=str(root/'upstream/fly-gym')+'\n' if '--show-toplevel' in args else (
                doctor.UPSTREAM_PIN+'\n' if 'rev-parse' in args else '')
        else:output='CPU fixture, 0, 1, 1\n'
        return subprocess.CompletedProcess(args,0,output,'')
    with patch('palimpsest.doctor.metadata.version',return_value='1.0'),patch('palimpsest.doctor.subprocess.run',side_effect=run):
        return doctor.diagnose(root,root/'assets')


def check(report,name):
    return next(row for row in report['checks'] if row['name']==name)


def test_record_is_deterministic_detached_and_canonical():
    first,second=held_provenance(**inputs()),held_provenance(**inputs())
    assert type(first) is HeldProvenance and first.report()==second.report() and first.sha256==second.sha256
    report=first.report();report['checks'].clear();report['ready']=False
    assert first.report()==second.report() and first.report()['ready'] is True
    raw=json.dumps(first.report(),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    import hashlib
    assert first.sha256==hashlib.sha256(raw).hexdigest()
    shuffled=inputs();shuffled['distributions']=list(reversed(shuffled['distributions']))
    shuffled['environment']=dict(reversed(list(shuffled['environment'].items())))
    assert held_provenance(**shuffled).report()==first.report()


def test_report_keeps_every_doctor_check_name_and_shape():
    held,ambient=held_provenance(**inputs()).report(),doctor_report()
    assert set(held)==set(ambient)=={'schema_version','checks','ready'} and held['schema_version']==ambient['schema_version']==1
    assert [row['name'] for row in held['checks']]==[row['name'] for row in ambient['checks']]+['held-provenance']
    for row in held['checks']:
        assert set(row)=={'name','status','detail'} and row['status'] in {'ok','missing','error','info'}
    for name in ('python','upstream','renderer'):
        assert set(check(held,name)['detail'])==set(check(ambient,name)['detail']),name
    for name in ['dependency:palimpsest']+['dependency:'+d for d in doctor.SIMULATION_DISTRIBUTIONS]:
        assert type(check(held,name)['detail']) is str and check(held,name)['status']=='ok'
    assert type(check(held,'gpu')['detail']['devices']) is list
    assert check(held,'hardware')==check(ambient,'hardware')
    json.dumps(held,allow_nan=False)


def test_values_come_only_from_the_supplied_pins():
    report=held_provenance(**inputs()).report()
    python=check(report,'python')['detail']
    assert python['version']=='3.11.15' and python['executable']=='/puck/runtime/python3.11'
    assert python['required']==check(doctor_report(),'python')['detail']['required']
    upstream=check(report,'upstream')
    assert upstream['status']=='ok' and upstream['detail']==dict(path='/puck/source/upstream/fly-gym',
        commit=doctor.UPSTREAM_PIN,expected_commit=doctor.UPSTREAM_PIN,dirty=False,changes=[])
    assert [check(report,'dependency:'+d)['detail'] for d in doctor.SIMULATION_DISTRIBUTIONS]==[
        '9.'+str(i) for i in range(len(doctor.SIMULATION_DISTRIBUTIONS))]
    assert check(report,'dependency:palimpsest')['detail']=='0.1.0'
    renderer=check(report,'renderer')['detail']
    assert renderer['requested_backend']=='egl' and renderer['backend_selection']=='explicit MUJOCO_GL' and renderer['probed'] is False
    pins=check(report,'held-provenance')
    assert pins['status']=='info' and pins['detail']['kind']=='puck-held-provenance-v1'
    assert pins['detail']['interpreter']==inputs()['interpreter'] and pins['detail']['lock_sha256']=='3'*64
    assert pins['detail']['upstream']['file_count']==2 and len(pins['detail']['upstream']['files_sha256'])==64
    assert len(pins['detail']['distributions_sha256'])==64 and len(pins['detail']['environment_sha256'])==64
    for name in ('platform','ram','disk','gpu','assets'):
        assert check(report,name)['status']=='info' and 'held' in json.dumps(check(report,name)['detail'])


def test_recording_admission_and_run_comparison_accept_the_record():
    report=held_provenance(**inputs()).report()
    required=[row for row in report['checks'] if row['name'] in {'python','upstream'} or row['name'].startswith('dependency:')]
    assert required and all(row['status']=='ok' for row in required) and report['ready'] is True
    runtime=_provenance({'manifest':{},'events':[{'kind':'diagnostics','report':report}]})['runtime']
    assert [row['name'] for row in runtime]==['python','platform','dependency:palimpsest']+[
        'dependency:'+d for d in doctor.SIMULATION_DISTRIBUTIONS]+['gpu','renderer']


@pytest.mark.parametrize('change,name,status',[
    ('missing-distribution','dependency:scipy','missing'),('wrong-commit','upstream','error'),
    ('python312','python','error'),('no-backend','renderer','info')])
def test_statuses_follow_the_pins_like_doctor(change,name,status):
    value=inputs()
    if change=='missing-distribution':value['distributions']=[r for r in value['distributions'] if r['name']!='scipy']
    elif change=='wrong-commit':value['upstream']=dict(value['upstream'],commit='0'*40)
    elif change=='python312':value['interpreter']=dict(value['interpreter'],python_version='3.12.1')
    else:value['environment']={k:v for k,v in value['environment'].items() if k!='MUJOCO_GL'}
    report=held_provenance(**value).report()
    assert check(report,name)['status']==status
    assert report['ready'] is (change=='no-backend')
    if change=='no-backend':
        assert check(report,'renderer')['detail']['requested_backend']=='platform default'


def test_distribution_names_match_like_metadata_normalization():
    value=inputs()
    for row in value['distributions']:
        if row['name']=='opencv-python':row['name']='OpenCV_Python'
        if row['name']=='scikit-learn':row['name']='scikit.learn'
    report=held_provenance(**value).report()
    assert check(report,'dependency:opencv-python')['status']==check(report,'dependency:scikit-learn')['status']=='ok'


def test_building_performs_no_process_import_or_filesystem_discovery():
    tree=ast.parse(SOURCE.read_text())
    imported={alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names}
    imported|={node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.level==0}
    assert imported<={'copy','hashlib','json','re'},imported
    value=inputs()
    def refuse(*args,**kwargs):raise AssertionError('ambient inspection')
    with patch('importlib.metadata.version',refuse),patch('platform.platform',refuse),patch('platform.python_version',refuse):
        REFUSED[0]=True
        try:record=held_provenance(**value);record.report()
        finally:REFUSED[0]=False
    assert record.report()['ready'] is True


def test_constants_mirror_the_ambient_doctor():
    import palimpsest.held_provenance as module
    assert module.SIMULATION_DISTRIBUTIONS==doctor.SIMULATION_DISTRIBUTIONS
    assert module.UPSTREAM_PIN==doctor.UPSTREAM_PIN


@pytest.mark.parametrize('defect',['interpreter-relative','interpreter-sha','interpreter-size-bool','interpreter-extra',
    'interpreter-version','upstream-relative','upstream-commit','upstream-unsorted','upstream-duplicate','upstream-traversal',
    'upstream-empty','distribution-duplicate','distribution-extra','distribution-version','distribution-name','lock',
    'palimpsest-version','environment-type','environment-nul','not-dict'])
def test_inputs_are_strict(defect):
    value=copy.deepcopy(inputs())
    if defect=='interpreter-relative':value['interpreter']['path']='python3.11'
    elif defect=='interpreter-sha':value['interpreter']['sha256']='A'*64
    elif defect=='interpreter-size-bool':value['interpreter']['size_bytes']=True
    elif defect=='interpreter-extra':value['interpreter']['ambient']=True
    elif defect=='interpreter-version':value['interpreter']['python_version']='3.11'
    elif defect=='upstream-relative':value['upstream']['path']='upstream/fly-gym'
    elif defect=='upstream-commit':value['upstream']['commit']='abc'
    elif defect=='upstream-unsorted':value['upstream']['files'].reverse()
    elif defect=='upstream-duplicate':value['upstream']['files'].append(copy.deepcopy(value['upstream']['files'][-1]))
    elif defect=='upstream-traversal':value['upstream']['files'][0]['path']='../escape.py'
    elif defect=='upstream-empty':value['upstream']['files']=[]
    elif defect=='distribution-duplicate':value['distributions'].append(dict(value['distributions'][0],name=value['distributions'][0]['name'].upper()))
    elif defect=='distribution-extra':value['distributions'][0]['ambient']=True
    elif defect=='distribution-version':value['distributions'][0]['version']=''
    elif defect=='distribution-name':value['distributions'][0]['name']='bad name'
    elif defect=='lock':value['lock_sha256']='3'*63
    elif defect=='palimpsest-version':value['palimpsest_version']=1
    elif defect=='environment-type':value['environment']['MUJOCO_GL']=1
    elif defect=='environment-nul':value['environment']['MUJOCO_GL']='egl\x00'
    else:value['upstream']=[value['upstream']]
    with pytest.raises(ValueError):held_provenance(**value)


def test_record_cannot_be_constructed_outside_the_builder():
    with pytest.raises(TypeError):HeldProvenance(b'{}')
