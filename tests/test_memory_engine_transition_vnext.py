"""Private authored Engine persistence only; no source/native/model authority.

The environment and policy refuse every access in helper/guard tests. Existing
SmallEnv/SmallPolicy are used only to prove the unchanged legacy default path.
"""
import copy
from dataclasses import replace
import json
import os
import threading
from unittest.mock import patch

import pytest

from palimpsest import memory, memory_decision as legacy, memory_decision_world as world
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
from test_memory_transition_vnext import at_trigger, fixture, packet, reach_for, step


class Untouchable:
    def __getattribute__(self, name):
        raise AssertionError('private helper/guard touched environment or policy: '+name)


def events(engine):
    return [json.loads(line) for line in (engine.writer.path/'events.jsonl').read_text().splitlines()]


def authored_engine(tmp_path, state, context, *, bound=True):
    engine=Engine.__new__(Engine)
    engine._owner=threading.get_ident()
    engine._closed=False
    engine._recording_failed=False
    engine.env=engine.policy=Untouchable()
    engine.scenario='memory-decision-v2'
    engine.memory=copy.deepcopy(state)
    engine.observation={}
    engine.task_state=None
    engine.world_task_state={}
    engine.run_id=context['run_id']
    engine.episode=0
    engine.total_tick=engine.episode_step=state['cursor']['tick']+1
    engine.writer=RunWriter(tmp_path/'recording',{'run_id':context['run_id']})
    if bound:
        engine.writer.manifest.update(memory_terminal_vnext_context_sha256=memory.sha256(context),
            memory_terminal_vnext_mode='memory-terminal-vnext-v1')
        engine._memory_terminal_vnext_mode='memory-terminal-vnext-v1'
        engine._memory_terminal_vnext_context=copy.deepcopy(context)
        engine._memory_terminal_vnext_job_sha256='f'*64
        engine._memory_terminal_vnext_chain=(0,memory.sha256(context))
        engine._memory_terminal_vnext_failed=False
        engine._memory_terminal_vnext_route_anchor={'tick':engine.total_tick,'stage':'pre-control','xy':[1.,2.]}
    return engine


def transition(engine, v, context, binding, case, *, token=1, missing=False, fresh=False):
    """Bind actual earlier authored event refs, rather than invented event hashes."""
    reach=reach_for(case,event=case['kind']!='no-event')
    for field in ('cue_event','gate_event','intervention_event','sensed_event'):
        if reach[field] is not None:
            engine._event('authored_'+field)
            event=events(engine)[-1]
            reach[field]={'sequence':event['sequence'],'sha256':memory.sha256(event)}
    p=packet(engine.memory,engine.total_tick,token,missing=missing,fresh=fresh)
    return v.advance_transition_vnext(engine.memory,p,context=context,oracle_binding=binding,
        reach=reach,job_sha256='f'*64,chain=engine._memory_terminal_vnext_chain)


@pytest.fixture
def authored(tmp_path):
    v,_,state,c,b,case=at_trigger()
    engine=authored_engine(tmp_path,state,c)
    try:
        yield engine,v,c,b,case
    finally:
        engine.writer.close()


def persist(engine, result, given_context, **overrides):
    args={'context':given_context,'job_sha256':'f'*64,'chain':engine._memory_terminal_vnext_chain}
    args.update(overrides)
    engine._persist_terminal_transition_vnext(result,**args)


def test_default_engine_path_emits_no_vnext_events(tmp_path):
    from test_memory_decision_engine import DecisionEngineTests
    fixture=DecisionEngineTests()
    fixture.setUp()
    try:
        engine=fixture.engine()
        engine._step()
        kinds=[event['kind'] for event in events(engine)]
        assert 'memory_sensed' in kinds and 'memory_decision' in kinds
        assert not any('vnext' in kind for kind in kinds)
        assert engine.total_tick==1 and engine.env.calls==1
    finally:
        fixture.doCleanups()


@pytest.mark.parametrize('indication',[
    'state4','context-marker','lifecycle-marker','demoted-bound-mode',
    'missing-context','missing-lifecycle','missing-mode',
    'manifest-context','manifest-mode','null-bound-context','route-anchor',
])
def test_default_refuses_state4_or_lost_context_lifecycle_mode_before_selection(tmp_path,indication):
    v,source,state,c,_,_=fixture()
    engine=authored_engine(tmp_path,source,c,bound=False)
    if indication in ('state4','missing-context','missing-lifecycle','missing-mode'):
        engine.memory=state
        if indication=='missing-context': del engine.memory['terminal_context_sha256']
        if indication=='missing-lifecycle': del engine.memory['terminal_lifecycle']
    elif indication in ('context-marker','lifecycle-marker'):
        key='terminal_context_sha256' if indication=='context-marker' else 'terminal_lifecycle'
        engine.memory[key]=None
    elif indication=='demoted-bound-mode': engine._memory_terminal_vnext_mode='memory-terminal-vnext-v1'
    elif indication=='null-bound-context': engine._memory_terminal_vnext_context=None
    elif indication=='route-anchor': engine._memory_terminal_vnext_route_anchor=None
    else: engine.writer.manifest['memory_terminal_vnext_'+indication.split('-')[1]+('_sha256' if indication=='manifest-context' else '')]=None
    try:
        with patch.object(world,'advance_world',side_effect=AssertionError('sensing reached')), \
                patch.object(legacy,'advance_memory',side_effect=AssertionError('selection reached')):
            with pytest.raises((ValueError,RuntimeError),match='[Tt]erminal|vnext|integrated'):
                engine._step()
        assert events(engine)==[]
        assert engine._memory_terminal_vnext_failed is True
    finally:
        engine.writer.close()


def test_guard_validates_strict3_before_sensing_and_other_scenarios_only_refuse_indications(tmp_path):
    _,source,_,c,_,_=fixture()
    engine=authored_engine(tmp_path,source,c,bound=False)
    try:
        engine._require_memory_transition_mode()
        engine.memory['version']=True
        with pytest.raises(ValueError): engine._step()
        assert events(engine)==[]
        engine.scenario='reproduction'
        engine.memory=None
        engine._require_memory_transition_mode()
        engine.writer.manifest['memory_terminal_vnext_mode']=None
        with pytest.raises((ValueError,RuntimeError),match='[Tt]erminal|vnext|integrated'):
            engine._require_memory_transition_mode()
    finally:
        engine.writer.close()


@pytest.mark.parametrize('missing',[False,True])
def test_witness_fsync_precedes_assignment_and_natural_rethrow(authored,missing):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case,missing=missing)
    before=copy.deepcopy(engine.memory)
    chain=engine._memory_terminal_vnext_chain
    observed=[]
    real_fsync=os.fsync
    def fsync(fd):
        real_fsync(fd)
        event=events(engine)[-1]
        observed.append(event['kind'])
        if event['kind']=='memory_transition_witness_vnext':
            assert engine.memory==before
            assert engine._memory_terminal_vnext_chain==chain
        elif event['kind']=='memory_transition_commit_vnext':
            assert engine.memory==result.proposed_state
            assert engine._memory_terminal_vnext_chain==(1,memory.sha256(result.witness))
    with patch('palimpsest.records.os.fsync',side_effect=fsync):
        if missing:
            with pytest.raises(legacy.CueUnavailable) as raised: persist(engine,result,c)
            assert raised.value is result.error.original_exception
            assert engine.memory==before
            assert engine._memory_terminal_vnext_failed is True
        else:
            persist(engine,result,c)
    terminal=[e for e in events(engine) if 'vnext' in e['kind']]
    assert observed[0]=='memory_transition_witness_vnext'
    assert len(terminal)==(1 if missing else 2)
    assert terminal[0]['witness']==result.witness
    assert set(terminal[0])=={'run_id','episode','tick','episode_step','sequence','kind','witness'}
    if not missing:
        assert set(terminal[1])=={'run_id','episode','tick','episode_step','sequence','kind','commit'}
        assert terminal[1]['commit']['memory_sha256']==memory.sha256(engine.memory)
        assert terminal[1]['commit']['witness_sha256']==memory.sha256(result.witness)
        tail=events(engine)[terminal[-1]['sequence']+1:]
        assert [e['detail'] for e in tail]==result.decisions
        assert all(e['kind']=='memory_decision' and e['route_anchor']=={'stage':'pre-control','xy':[1.,2.]} for e in tail)
        lines=(engine.writer.path/'events.jsonl').read_bytes().splitlines(keepends=True)
        for event in terminal:
            body=event['witness'] if 'witness' in event else event['commit']
            assert lines[event['sequence']]==v.terminal_event_bytes_vnext(event['kind'],body,
                **{k:event[k] for k in ('sequence','run_id','episode','tick','episode_step')})


@pytest.mark.parametrize('fail_at',[1,2,3])
def test_failed_write_keeps_actual_assignment_and_blocks_continuation(authored,fail_at):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    before=copy.deepcopy(engine.memory)
    original_chain=engine._memory_terminal_vnext_chain
    real_fsync=os.fsync
    calls=0
    failure=OSError('authored fsync failure')
    def fsync(fd):
        nonlocal calls
        calls+=1
        if calls==fail_at: raise failure
        real_fsync(fd)
    with patch('palimpsest.records.os.fsync',side_effect=fsync):
        with pytest.raises(OSError) as raised: persist(engine,result,c)
    assert raised.value is failure
    assert engine.memory==(before if fail_at==1 else result.proposed_state)
    assert engine._memory_terminal_vnext_chain==(original_chain if fail_at==1 else (1,memory.sha256(result.witness)))
    assert engine._memory_terminal_vnext_failed is True
    retained=(engine.writer.path/'events.jsonl').read_bytes()
    with pytest.raises((ValueError,RuntimeError)): persist(engine,result,c)
    with pytest.raises((ValueError,RuntimeError)): engine._step()
    assert (engine.writer.path/'events.jsonl').read_bytes()==retained


def test_assignment_cannot_mutate_detached_hashed_witness(authored):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    witness=memory.canonical_bytes(result.witness)
    proposed=copy.deepcopy(result.proposed_state)
    persist(engine,result,c)
    engine.memory['selector']['resource'].clear()
    engine.memory['terminal_lifecycle']['resource_sha256']='0'*64
    engine._memory_terminal_vnext_route_anchor['xy'][0]=99.
    assert result.proposed_state==proposed
    assert memory.canonical_bytes(result.witness)==witness
    actual=[e for e in events(engine) if e['kind']=='memory_transition_witness_vnext'][0]
    assert memory.canonical_bytes(actual['witness'])==witness
    assert all(e['route_anchor']['xy']==[1.,2.] for e in events(engine) if e['kind']=='memory_decision')


def test_trigger_plus_failure_single_transaction_and_later_terminal_bound(authored):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    persist(engine,result,c)
    engine.total_tick+=1
    engine.episode_step+=1
    result=transition(engine,v,c,b,case,missing=True)
    assert result.witness['gold'] is None and result.witness['stages']==[]
    with pytest.raises(legacy.CueUnavailable): persist(engine,result,c)
    assert engine._memory_terminal_vnext_chain==(2,memory.sha256(result.witness))
    kinds=[e['kind'] for e in events(engine)]
    assert kinds.count('memory_transition_witness_vnext')==2
    assert kinds.count('memory_transition_commit_vnext')==1
    retained=(engine.writer.path/'events.jsonl').read_bytes()
    with pytest.raises((ValueError,RuntimeError)): persist(engine,result,c)
    assert (engine.writer.path/'events.jsonl').read_bytes()==retained


def test_background_writer_refused_for_vnext(authored):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    before=copy.deepcopy(engine.memory)
    retained=(engine.writer.path/'events.jsonl').read_bytes()
    engine.writer.start_background()
    with pytest.raises((ValueError,RuntimeError),match='synchronous|background'): persist(engine,result,c)
    assert engine.memory==before and engine._memory_terminal_vnext_failed is True
    assert (engine.writer.path/'events.jsonl').read_bytes()==retained


def test_ordinary_and_idempotent_return_have_no_new_transaction(tmp_path):
    v,_,state,c,b,case=fixture()
    engine=authored_engine(tmp_path,state,c)
    try:
        result,p=step(v,state,c,b,case)
        assert result.status=='ordinary-return'
        persist(engine,result,c)
        assert not any('vnext' in e['kind'] for e in events(engine))
        retained=(engine.writer.path/'events.jsonl').read_bytes()
        result=v.advance_transition_vnext(engine.memory,p,context=c,oracle_binding=b,
            reach=reach_for(case),job_sha256='f'*64,chain=engine._memory_terminal_vnext_chain)
        assert result.status=='idempotent'
        persist(engine,result,c)
        assert (engine.writer.path/'events.jsonl').read_bytes()==retained
        assert engine.memory is not result.proposed_state
    finally:
        engine.writer.close()


@pytest.mark.parametrize('defect',[
    'context','job','chain','run','episode','counter','input','local','decisions',
    'result-status','witness-input','witness-chain','witness-context','witness-job',
    'witness-tick','witness-packet','witness-local','witness-decisions','witness-cap',
    'missing-mode','missing-context','bound-context','bound-job','bound-chain',
    'anchor-missing','anchor-tick','anchor-stage','anchor-xy',
])
def test_identity_result_and_cap_failures_refuse_before_writes_and_latch(authored,defect):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    args={}
    if defect=='context': args['context']={**c,'run_id':c['source_run_id']}
    elif defect=='job': args['job_sha256']='0'*64
    elif defect=='chain': args['chain']=(1,'0'*64)
    elif defect=='run': engine.run_id=c['source_run_id']
    elif defect=='episode': engine.episode=True
    elif defect=='counter': engine.episode_step+=1
    elif defect=='input': result=replace(result,input_lifecycle={'status':'not-oracle'})
    elif defect=='local': result.local_lifecycle['selection_sha256']='0'*64
    elif defect=='decisions': result.decisions.clear()
    elif defect=='result-status': result=replace(result,status='ordinary-return')
    elif defect.startswith('witness-'):
        key={'input':'input_memory_sha256','chain':'previous_sha256','context':'context_sha256',
             'job':'job_sha256','packet':'packet_sha256','local':'local_memory_sha256',
             'decisions':'local_decisions_sha256'}.get(defect[8:])
        if key: result.witness[key]='0'*64
        elif defect=='witness-tick': result.witness['tick']+=1
        else: result.witness['reach']['actual_circles']*=100
    elif defect in ('missing-mode','missing-context'):
        delattr(engine,'_memory_terminal_vnext_'+defect.split('-')[1])
    elif defect=='bound-context': engine._memory_terminal_vnext_context['kind']='null'
    elif defect=='bound-job': engine._memory_terminal_vnext_job_sha256='0'*64
    elif defect=='bound-chain': engine._memory_terminal_vnext_chain=(1,'0'*64)
    elif defect=='anchor-missing': del engine._memory_terminal_vnext_route_anchor
    elif defect=='anchor-tick': engine._memory_terminal_vnext_route_anchor['tick']+=1
    elif defect=='anchor-stage': engine._memory_terminal_vnext_route_anchor['stage']='post-control'
    else: engine._memory_terminal_vnext_route_anchor['xy']=[True,float('nan')]
    before=copy.deepcopy(engine.memory)
    retained=(engine.writer.path/'events.jsonl').read_bytes()
    with pytest.raises((ValueError,RuntimeError,TypeError)): persist(engine,result,c,**args)
    assert engine.memory==before and engine._memory_terminal_vnext_failed is True
    assert (engine.writer.path/'events.jsonl').read_bytes()==retained


@pytest.mark.parametrize('rejected',[False,True])
def test_raised_or_rejected_never_assign_local_effects_or_fabricate_decisions(authored,rejected):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case,missing=not rejected,fresh=rejected)
    assert result.status==('rejected' if rejected else 'raised')
    before=copy.deepcopy(engine.memory)
    with pytest.raises(type(result.error.original_exception)) as raised: persist(engine,result,c)
    assert raised.value is result.error.original_exception
    assert engine.memory==before
    assert events(engine)[-1]['kind']=='memory_transition_witness_vnext'
    assert not any(e['kind'] in ('memory_transition_commit_vnext','memory_decision') for e in events(engine))


def test_rejected_without_witness_and_tampered_exception_stop_without_natural_reconstruction(authored):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case,missing=True)
    result.error.original_exception.args=('tampered',)
    before=copy.deepcopy(engine.memory)
    with pytest.raises(RuntimeError,match='changed'): persist(engine,result,c)
    assert engine.memory==before and engine._memory_terminal_vnext_failed is True
    # The bounded detached reached witness remains evidence, not a natural verdict.
    assert events(engine)[-1]['kind']=='memory_transition_witness_vnext'


@pytest.mark.parametrize('after_assignment',[False,True])
def test_assignment_cut_failure_retains_durable_witness_and_actual_state(authored,after_assignment):
    engine,v,c,b,case=authored
    result=transition(engine,v,c,b,case)
    before=copy.deepcopy(engine.memory)
    failure=RuntimeError('authored assignment cut')
    real_setattr=Engine.__setattr__
    real_event=RunWriter.event
    def assign(instance,name,value):
        if instance is engine and name=='memory': raise failure
        real_setattr(instance,name,value)
    def event(writer,kind,**data):
        if kind=='memory_transition_commit_vnext': raise failure
        return real_event(writer,kind,**data)
    target=patch.object(RunWriter,'event',event) if after_assignment else patch.object(Engine,'__setattr__',assign)
    with target:
        with pytest.raises(RuntimeError) as raised: persist(engine,result,c)
    assert raised.value is failure
    assert engine.memory==(result.proposed_state if after_assignment else before)
    assert engine._memory_terminal_vnext_chain==(1,memory.sha256(result.witness))
    assert events(engine)[-1]['kind']=='memory_transition_witness_vnext'
    retained=(engine.writer.path/'events.jsonl').read_bytes()
    with pytest.raises(RuntimeError): persist(engine,result,c)
    assert (engine.writer.path/'events.jsonl').read_bytes()==retained


def test_prevalidation_rejection_has_no_witness_or_assignment(authored):
    engine,v,c,b,case=authored
    result=v.advance_transition_vnext(engine.memory,{},context=c,oracle_binding=b,
        reach=reach_for(case),job_sha256='f'*64,chain=engine._memory_terminal_vnext_chain)
    assert result.status=='rejected' and result.witness is None
    before=copy.deepcopy(engine.memory)
    with pytest.raises(type(result.error.original_exception)) as raised: persist(engine,result,c)
    assert raised.value is result.error.original_exception
    assert engine.memory==before and events(engine)==[]
    assert engine._memory_terminal_vnext_failed is True


@pytest.mark.parametrize('stripped',[False,True])
def test_returned_supervisor_failure_requires_witness_and_stops_after_commit(tmp_path,stripped):
    v,_,state,c,b,case=fixture(condition='no-U',kind='no-event')
    for _ in range(400):
        result,_=step(v,state,c,b,case)
        if result.proposed_state['supervisor']['phase']=='failure': break
        state=result.proposed_state
    else:
        pytest.fail('authored worker did not reach its fixed waypoint timeout')
    engine=authored_engine(tmp_path,state,c)
    try:
        result=transition(engine,v,c,b,case,token=0)
        assert result.status=='witnessed-return'
        before=copy.deepcopy(engine.memory)
        retained=(engine.writer.path/'events.jsonl').read_bytes()
        if stripped:
            stripped_result=replace(result,status='ordinary-return',witness=None)
            with pytest.raises(ValueError): persist(engine,stripped_result,c)
            assert engine.memory==before
            assert (engine.writer.path/'events.jsonl').read_bytes()==retained
        else:
            persist(engine,result,c)
            assert engine.memory==result.proposed_state
            assert [e['kind'] for e in events(engine)][1:3]==[
                'memory_transition_witness_vnext','memory_transition_commit_vnext']
        assert engine._memory_terminal_vnext_failed is True
    finally:
        engine.writer.close()
