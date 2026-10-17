"""Explicit held diagnostics for Engine.open and replay_run; authored seams only.

The default (diagnostics=None) keeps the ambient doctor exactly. A supplied
record must be the exact held-provenance type from the same palimpsest package;
it replaces doctor without any process creation, and replay hands the same
record to its fresh owner after binding it to the source diagnostics event.
"""
import importlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import uuid

import pytest

from test_held_provenance import inputs
from test_public_manual_episode_constructor import route  # noqa: F401 - authored Engine.open fixture


PROCESS=[False]


def _hook(event,args):
    if PROCESS[0] and (event in {'subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty','os.spawn'}
                       or event.startswith('os.exec')):
        raise RuntimeError('Process creation refused: '+event)


sys.addaudithook(_hook)


def authored_record(**changes):
    module=importlib.import_module('_authored_public_manual_constructor.held_provenance')
    return module,module.held_provenance(**inputs(**changes))


def events(route):
    return [json.loads(line) for line in (route.output/'events.jsonl').read_text().splitlines()]


def test_engine_uses_the_supplied_record_without_doctor_or_process_creation(route):
    module,record=authored_record()
    PROCESS[0]=True
    try:engine=route.open(diagnostics=record)
    finally:PROCESS[0]=False
    try:
        assert ('diagnose',) not in route.trace
        recorded=events(route)
        assert [e['kind'] for e in recorded]==['diagnostics','environment','engine_opened','episode_started']
        assert recorded[0]['report']==record.report()
        assert route.constructed and engine.phase=='paused'
    finally:engine.close()


def test_default_engine_open_still_runs_the_ambient_doctor(route):
    engine=route.open()
    try:
        assert ('diagnose',) in route.trace
        assert events(route)[0]['report']=={'checks':[{'name':'upstream','status':'ok'}]}
    finally:engine.close()


@pytest.mark.parametrize('kind',['dict','doctor-like','duck','foreign-class','subclass','none-string'])
def test_engine_refuses_any_other_diagnostics_before_allocation(route,kind):
    module,record=authored_record()
    if kind=='dict':value=record.report()
    elif kind=='doctor-like':value={'schema_version':1,'checks':[],'ready':True}
    elif kind=='duck':value=type('Duck',(),{'report':lambda self:record.report(),'sha256':record.sha256})()
    elif kind=='foreign-class':
        from palimpsest.held_provenance import held_provenance
        value=held_provenance(**inputs())
    elif kind=='subclass':
        value=object.__new__(type('Sub',(module.HeldProvenance,),{}))
    else:value='None'
    with pytest.raises(ValueError,match='exact held provenance'):route.open(diagnostics=value)
    assert not route.output.exists() and route.constructed==[] and ('diagnose',) not in route.trace


def test_failed_held_requirements_refuse_before_environment_construction(route):
    module,record=authored_record(distributions=[])
    with pytest.raises(RuntimeError,match='runtime diagnostics failed'):route.open(diagnostics=record)
    assert route.constructed==[] and ('diagnose',) not in route.trace
    assert json.loads((route.output/'manifest.json').read_text())['status']=='failed'
    assert events(route)[0]['report']==record.report()


def replay_case(source_report,**kwargs):
    from palimpsest.replay import replay_run
    root=Path(tempfile.mkdtemp());source=root/uuid.uuid4().hex;source.mkdir()
    destination=root/uuid.uuid4().hex;destination.mkdir()
    manifest={'controller':'manual','scenario':{'id':'reproduction'},'requested_device':'cpu','seed':7,'texture':'checker','run_id':source.name}
    data={'manifest':manifest,'events':[{'kind':'diagnostics','report':source_report}]}
    with patch('palimpsest.replay._load',return_value=data), \
         patch('palimpsest.replay._initial_snapshot',return_value=({'application':{}},{'snapshot_id':'fixture','sha256':'a'*64},[])), \
         patch('palimpsest.engine.Engine.open',side_effect=RuntimeError('fixture stop before allocation')) as opened:
        report=replay_run(source,destination,mode='actions',repo_root=root,asset_root=root,**kwargs)
    return report,opened,destination


def test_replay_hands_the_same_record_to_the_fresh_owner():
    from palimpsest.held_provenance import held_provenance
    record=held_provenance(**inputs())
    report,opened,_=replay_case(record.report(),diagnostics=record)
    assert report['status']=='failed' and opened.call_count==1
    assert opened.call_args.kwargs['diagnostics'] is record


def test_replay_default_call_is_unchanged():
    report,opened,_=replay_case({'schema_version':1,'checks':[],'ready':True})
    assert opened.call_count==1 and 'diagnostics' not in opened.call_args.kwargs


def test_replay_refuses_a_record_that_differs_from_the_source_diagnostics():
    from palimpsest.held_provenance import held_provenance
    record=held_provenance(**inputs())
    other=held_provenance(**inputs(lock_sha256='4'*64)).report()
    report,opened,destination=replay_case(other,diagnostics=record)
    assert report['status']=='failed' and opened.call_count==0
    assert any('held provenance' in str(error) for error in report['errors'])
    assert json.loads((destination/'replay-report.json').read_text())==report


@pytest.mark.parametrize('value',[{'schema_version':1,'checks':[],'ready':True},'record',object()])
def test_replay_refuses_other_diagnostics_before_loading(value):
    from palimpsest.replay import replay_run
    root=Path(tempfile.mkdtemp());source=root/uuid.uuid4().hex;source.mkdir()
    destination=root/uuid.uuid4().hex;destination.mkdir()
    with patch('palimpsest.replay._load',side_effect=AssertionError('loaded')):
        with pytest.raises(ValueError,match='exact held provenance'):
            replay_run(source,destination,mode='actions',repo_root=root,asset_root=root,diagnostics=value)
    assert not (destination/'replay-report.json').exists()
