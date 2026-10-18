"""Registration v4: the closed held public-episode worker; authored entries only.

Real isolated bootstrap children with tiny authored dependency forests. No
mujoco, EGL, upstream, model or episode runs: the fixed entry module here is
authored, so these cases specify dispatch, the closed descriptor, policy-v5
rosters, the 600 s clock (user decision after rehearsal 6), the single stdlib-name exception and the
process-creation refusal. Registration v1-v3 keep their behavior.
"""
import copy
import json
from pathlib import Path
import textwrap

import pytest

from test_puck_tmpfs_dependencies import authored, v3
from test_puck_worker_bootstrap import descriptor, sha
from test_puck_worker_dependencies import dependency_fixture


ENTRY='src/palimpsest/puck_held_episode.py'
SYSCONFIG='_sysconfigdata__linux_x86_64-linux-gnu'
NEGATIVES=['cffi','charset_normalizer','org']
HIDDEN=['networkx']
EXPECTED=dict(numpy='authored-numpy',torch='authored-torch',mujoco='authored-mujoco',gymnasium='authored-gymnasium')
SOURCE_ID='a'*32;REPLAY_ID='b'*32


def stdlib_row(runtime_root):
    path=Path(runtime_root).parent/'lib/python3.11'/(SYSCONFIG+'.py')
    return dict(name=SYSCONFIG,path=str(path),size_bytes=path.stat().st_size,sha256=sha(path.read_bytes()))


def episode(runtime_root,phase='source'):
    return dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=dict(EXPECTED),
        stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=list(NEGATIVES),hidden_imports=list(HIDDEN),
        stdlib_exception=stdlib_row(runtime_root),
        profile=dict(scenario='reproduction',texture='checker',controller='manual',device='cpu',seed=7),
        schedule=dict(ticks=48,actions=[[0,.5,0.],[24,.5,.25]]),
        run_ids=dict(source=SOURCE_ID,replay=REPLAY_ID),
        paths=dict(output_root='/authored/output',source_root='/authored/output' if phase=='source' else '/authored/source-run',
                   asset_root='/authored/assets'),
        upstream_commit='8d964599119b420de67ee259434d273651a1a76d')


ENTRY_PRELUDE='''\
import os, sys, time
def run(admission):
    owner = admission
    owner.recheck()
    sys.stderr.write('EPISODE_ENTRY_RAN\\n')
'''


def run_v4(body='return {"kind": "authored-episode"}',*,phase='source',change=None,preflight='raise AssertionError("PREFLIGHT_RAN")'):
    def source_change(reg,source):
        path=source/ENTRY;path.write_text(ENTRY_PRELUDE+textwrap.indent(textwrap.dedent(body),'    ')+'\n')
        reg['source_files'].append(descriptor(path,ENTRY))
        reg['source_files'].sort(key=lambda row:row['path'])
        reg['modules'].append({'name':'palimpsest.puck_held_episode','path':ENTRY})
        reg.update(kind='puck-worker-source-bootstrap-v4',version=4,deadline_seconds=600,
                   episode=episode(reg['runtime']['root'],phase))
        if change:change(reg)
    with authored() as base:
        result,_=dependency_fixture(base,preflight,mutate=lambda deps,root:v3(deps),source_change=source_change)
    print(json.dumps({'kind':'authored-v4-episode-worker-v1','returncode':result.returncode,
                      'stdout':result.stdout,'stderr':result.stderr},sort_keys=True))
    return result


def succeeded(result):
    assert result.returncode==0,result.stderr
    assert 'EPISODE_ENTRY_RAN\n' in result.stderr and 'PREFLIGHT_RAN' not in result.stderr
    receipt=json.loads(result.stdout)
    for key in ('runtime_qualified','native_authorized','collection_authorized','executable','dependencies_qualified'):
        assert receipt[key] is False
    assert receipt['qualification_claims']==[]
    return receipt


def refused(result,reason,*,entry_ran=False):
    assert result.returncode!=0 and result.stdout=='',result.stderr
    assert reason in result.stderr,result.stderr
    assert ('EPISODE_ENTRY_RAN\n' in result.stderr) is entry_ran
    assert 'PREFLIGHT_RAN' not in result.stderr


@pytest.mark.parametrize('phase',['source','replay'])
def test_v4_runs_only_the_fixed_episode_entry_on_a_600s_clock(phase):
    receipt=succeeded(run_v4('''
        remaining = owner._deadline - time.monotonic()
        assert 540 < remaining <= 600, remaining
        assert owner._dependencies.provider._deadline == owner._deadline
        assert owner._missing_policy_version == 5 and owner._stdlib_names is sys.stdlib_module_names
        return {"kind": "authored-episode", "phase": owner._reg["episode"]["phase"]}
    ''',phase=phase))
    assert receipt['entry_result']=={'kind':'authored-episode','phase':phase}
    assert receipt['episode_phase']==phase
    assert receipt['expected_missing_imports']==NEGATIVES and receipt['expected_hidden_imports']==HIDDEN
    assert receipt['denied_imports']==[] and receipt['stdlib_cache_aliases'] in ({},{'__mp_main__':'__main__'})
    assert receipt['process_creation_attempts']=={'count':0,'events':[]}
    assert 'qualification' not in receipt


@pytest.mark.parametrize('defect,reason',[
    ('phase','Exact held public episode descriptor required'),
    ('kind','Exact held public episode descriptor required'),
    ('version','Exact held public episode descriptor required'),
    ('extra','Exact held public episode descriptor required'),
    ('torchvision','Exact held public episode descriptor required'),
    ('version-value','Exact held public episode descriptor required'),
    ('aliases','Exact held public episode descriptor required'),
    ('scenario','Exact held public episode profile required'),
    ('controller','Exact held public episode profile required'),
    ('seed-bool','Exact held public episode profile required'),
    ('ticks','Exact held public episode schedule required'),
    ('action-tick','Exact held public episode schedule required'),
    ('action-range','Exact held public episode schedule required'),
    ('action-bool','Exact held public episode schedule required'),
    ('run-ids-equal','Exact held public episode run identities required'),
    ('run-id-upper','Exact held public episode run identities required'),
    ('paths-relative','Canonical path without traversal required'),
    ('paths-source-mixed','Exact held public episode paths required'),
    ('commit','Exact held public episode descriptor required'),
    ('negatives-empty','Bounded expected missing import declaration required'),
    ('hidden-overlap','Expected hidden imports must be disjoint from expected missing imports'),
    ('local-negative','Expected missing import overlaps authenticated local source'),
    ('exception-name','Exact pinned stdlib-name exception required'),
    ('exception-path','Exact pinned stdlib-name exception required'),
    ('exception-sha','Exact lowercase SHA256 required'),
    ('no-deadline','Exact source-only bootstrap registration required'),
    ('deadline-180','Exact extended worker deadline'),
    ('deadline-360','Exact extended worker deadline required for the held episode'),
    ('qualification-key','Exact source-only bootstrap registration required'),
    ('no-entry','Complete Python module mapping required'),
])
def test_v4_descriptor_is_closed_before_any_initializer(defect,reason):
    def change(reg):
        e=reg['episode']
        if defect=='phase':e['phase']='record'
        elif defect=='kind':e['kind']='puck-held-public-episode-v2'
        elif defect=='version':e['version']=True
        elif defect=='extra':e['entry']='palimpsest.other'
        elif defect=='torchvision':e['expected_versions']['torchvision']='authored'
        elif defect=='version-value':e['expected_versions']['numpy']=''
        elif defect=='aliases':e['stdlib_cache_aliases']={}
        elif defect=='scenario':e['profile']['scenario']='sparse-navigation'
        elif defect=='controller':e['profile']['controller']='flynn'
        elif defect=='seed-bool':e['profile']['seed']=True
        elif defect=='ticks':e['schedule']['ticks']=1
        elif defect=='action-tick':e['schedule']['actions'][1][0]=23
        elif defect=='action-range':e['schedule']['actions'][0][1]=3.5
        elif defect=='action-bool':e['schedule']['actions'][0][2]=False
        elif defect=='run-ids-equal':e['run_ids']['replay']=SOURCE_ID
        elif defect=='run-id-upper':e['run_ids']['source']='A'*32
        elif defect=='paths-relative':e['paths']['asset_root']='authored/assets'
        elif defect=='paths-source-mixed':e['paths']['source_root']='/authored/elsewhere'
        elif defect=='commit':e['upstream_commit']='8d96459'
        elif defect=='negatives-empty':e['negative_imports']=[]
        elif defect=='hidden-overlap':e['hidden_imports']=['cffi']
        elif defect=='local-negative':e['negative_imports']=sorted(NEGATIVES+['palimpsest.optional'])
        elif defect=='exception-name':e['stdlib_exception']['name']='_sysconfigdata_other'
        elif defect=='exception-path':e['stdlib_exception']['path']='/authored/'+SYSCONFIG+'.py'
        elif defect=='exception-sha':e['stdlib_exception']['sha256']='A'*64
        elif defect=='no-deadline':del reg['deadline_seconds']
        elif defect=='deadline-180':reg['deadline_seconds']=180
        elif defect=='deadline-360':reg['deadline_seconds']=360
        elif defect=='qualification-key':reg['qualification']={}
        else:
            reg['modules']=[row for row in reg['modules'] if row['name']!='palimpsest.puck_held_episode']
    refused(run_v4(change=change),reason)


def test_v4_loads_only_the_pinned_sysconfigdata_bytes_as_its_one_stdlib_exception():
    receipt=succeeded(run_v4('''
        import sysconfig
        values = sysconfig.get_config_vars()
        assert values['VERSION'] == '3.11', values.get('VERSION')
        module = sys.modules[%r]
        assert module.__file__ == owner._reg['episode']['stdlib_exception']['path']
        owner.recheck()
        return {"kind": "authored-episode", "sysconfig": True}
    ''' % SYSCONFIG))
    rows=[row for row in receipt['loaded_modules'] if row['name']==SYSCONFIG]
    assert len(rows)==1 and rows[0]['path'].endswith('/lib/python3.11/'+SYSCONFIG+'.py')
    assert rows[0]['sha256']==stdlib_row(Path(rows[0]['path']).parents[2]/'bin')['sha256']


def test_v4_sysconfigdata_bytes_that_differ_from_the_pin_poison():
    def change(reg):
        reg['episode']['stdlib_exception']['sha256']='0'*64
    refused(run_v4('''
        import sysconfig
        try:
            sysconfig.get_config_vars()
        except ValueError:
            pass
        return {"kind": "authored-episode"}
    ''',change=change),'Initial authenticated bytes differ',entry_ran=True)


def test_v4_other_unlisted_stdlib_directory_modules_still_refuse():
    refused(run_v4('''
        try:
            import _sysconfigdata_authored_other
        except ImportError:
            pass
        return {"kind": "authored-episode"}
    '''),'Unregistered local or external dependency import: _sysconfigdata_authored_other',entry_ran=True)


def test_v3_qualification_does_not_gain_the_stdlib_exception():
    from test_puck_cpu_optional_import_contract_v2 import poisoned, run
    poisoned(run('''
        import sysconfig
        try:
            sysconfig.get_config_vars()
        except ImportError:
            pass
    '''),'Unregistered local or external dependency import: '+SYSCONFIG)


def test_v4_refuses_and_records_every_process_creation_attempt():
    receipt=succeeded(run_v4('''
        import subprocess
        refused = []
        for attempt in (lambda: subprocess.run(['/usr/bin/true']), lambda: os.system('true'),
                        lambda: os.posix_spawn('/usr/bin/true', ['true'], {})):
            try:
                attempt()
            except RuntimeError as error:
                refused.append(str(error))
        owner.recheck()
        return {"kind": "authored-episode", "refused": refused}
    '''))
    assert receipt['entry_result']['refused']==[
        'Held episode refuses process creation: subprocess.Popen',
        'Held episode refuses process creation: os.system',
        'Held episode refuses process creation: os.posix_spawn']
    assert receipt['process_creation_attempts']=={'count':3,'events':['subprocess.Popen','os.system','os.posix_spawn']}


def test_v4_applies_policy_v5_stock_absence_rosters():
    receipt=succeeded(run_v4('''
        import importlib.util
        assert importlib.util.find_spec('cffi') is None and importlib.util.find_spec('networkx') is None
        try:
            import charset_normalizer
        except ModuleNotFoundError:
            pass
        assert owner._state == 'active'
        return {"kind": "authored-episode"}
    '''))
    assert receipt['denied_imports']==['cffi','charset_normalizer','networkx']


def test_v4_undeclared_request_still_poisons_when_caught():
    refused(run_v4('''
        try:
            import foreign_episode_optional
        except ImportError:
            pass
        return {"kind": "authored-episode"}
    '''),'Unregistered local or external dependency import: foreign_episode_optional',entry_ran=True)


def test_v4_episode_rosters_are_bound_for_the_worker_lifetime():
    refused(run_v4('''
        owner._reg['episode']['negative_imports'].append('zz_unreviewed')
        owner.recheck()
        return {"kind": "authored-episode"}
    '''),'Expected missing import declaration changed',entry_ran=True)


def test_v4_bounds_the_entry_result():
    refused(run_v4('return {"kind": "authored-episode", "padding": "x" * 70000}'),
            'Bounded source-preflight result required',entry_ran=True)


def test_v1_preflight_keeps_process_creation_and_its_original_entry(tmp_path):
    from test_puck_worker_bootstrap import launch
    result,_=launch(tmp_path,body=(
        'import subprocess\nsubprocess.run(["/usr/bin/true"], check=True)\nreturn {"answer": 42}'))
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':42} and 'process_creation_attempts' not in receipt


def test_only_the_v4_episode_worker_may_hold_dependencies_for_600_seconds():
    import time
    from palimpsest.puck_dependency_files import HeldDependencyNamespace
    with pytest.raises(ValueError,match='at most 600 seconds'):
        HeldDependencyNamespace(b'{}',expected_sha256='0'*64,deadline=time.monotonic()+500,registration_path='/authored/r.json',
                                deadline_seconds=600)
    with pytest.raises(ValueError) as error:
        HeldDependencyNamespace(b'{}',expected_sha256='0'*64,deadline=time.monotonic()+500,registration_path='/authored/r.json',
                                deadline_seconds=600,episode=True)
    assert 'deadline' not in str(error.value)
    with pytest.raises(ValueError,match='at most 360 seconds'):
        HeldDependencyNamespace(b'{}',expected_sha256='0'*64,deadline=time.monotonic()+361,registration_path='/authored/r.json',
                                deadline_seconds=360,episode=True)
