"""Authored software fixtures; no native/model/source qualification authority."""
import copy
import importlib
import json
from unittest.mock import patch

import pytest

from palimpsest import memory, memory_decision as legacy, memory_decision_world as world
from palimpsest import memory_experiment


def api():
    return importlib.import_module('palimpsest.memory_transition_vnext')


def packet(state, tick, token=0, *, missing=False, fresh=False, arrivals=()):
    case_ids=state['graph']['landmark_ids']
    subjects=[f['subject_id'] for f in state['m']['facts']]
    cue=state['m']['facts'][0]['associations'][0]['cue_id']
    return {'version':2,'id':legacy.memory_task._sensor_id('episode-0',tick,'packet'),
        'episode_id':'episode-0','tick':tick,'common_goal_id':state['graph']['common_goal_id'],
        'cues':[{'id':cue,'state':token,'bearing_rad':0.}],
        'landmarks':[] if missing else [{'id':i,'bearing_rad':0.} for i in case_ids],
        'passages':[{'id':legacy.memory_task._sensor_id('episode-0',tick,'passage',s),
            'episode_id':'episode-0','tick':tick,'subject_id':s,
            'passability':'open' if fresh else 'unobserved'} for s in subjects],
        'arrivals':list(arrivals)}


def fixture(condition='oracle', kind='change'):
    """One deterministic development geometry, with explicitly authored packets."""
    v=api()
    case=world.make_case(0,'local_cue',kind)
    source=legacy.initialize(case)
    for tick in range(30):
        if legacy.acquired_boundary(source):
            break
        target=source['supervisor']['waypoint_ids'][source['supervisor']['waypoint_index']]
        source,_,_=legacy.advance_memory(source,packet(source,tick,fresh=True,arrivals=[target]))
    assert legacy.acquired_boundary(source)
    boundary=source['cursor']['tick']+1
    source_world=world.initial_state(case)
    source_world['last_tick']=boundary-1
    descriptor={'path':'authored/profile.json','size_bytes':100,'sha256':'a'*64}
    context={'schema':'memory-terminal-context-vnext-v1',
        **{k:copy.deepcopy(descriptor) for k in ('profile','source_closure','source_registration','source_commit','source_raw_audit','source_snapshot')},
        'source_application_sha256':'b'*64,'source_m_sha256':memory.sha256(source['m']),
        'source_world_sha256':memory.sha256(source_world),'source_run_id':'00000000-0000-0000-0000-000000000001',
        'case_id':case['case_id'],'case_sha256':memory.sha256(case),'kind':kind,
        'run_id':'00000000-0000-0000-0000-000000000002','condition':condition,
        'condition_resources_sha256':'c'*64,'source_invariant_sha256':'d'*64,
        'schedule':{'boundary_tick':boundary,'event_tick':None if kind=='no-event' else boundary+1,'decision_tick':boundary+2}}
    cfg={'version':1,'condition':condition,'limit':1,'resource':[] if condition=='oracle' else {'version':1,'episodes':[]} if condition=='retrieval' else None,
        'resource_sha256':memory.sha256([] if condition=='oracle' else {'version':1,'episodes':[]} if condition=='retrieval' else None),
        'provenance_sha256':v.pending_provenance_vnext(context) if condition=='oracle' else 'e'*64}
    u=memory.artifact('local_cue') if condition=='hand-authored' else memory.artifact()
    context['condition_resources_sha256']=memory.sha256({'selector':cfg,'u':u})
    state=v.configure_terminal_condition_vnext(source,cfg,u,context=context)
    state=v.arm_terminal_state_vnext(state,boundary_tick=boundary,context=context)
    binding=v.OracleBinding(source['m'],case,source_world) if condition=='oracle' else None
    return v,source,state,context,binding,case


def reach_for(case, *, event=False, maps=False):
    v=api()
    circles=[[*xy,.4] for xy in world.PROFILE['obstacles']]
    if event and case['closure_subject_id'] is not None:
        side=case['subjects_by_side'].index(case['closure_subject_id'])
        circles[len(world.POSTS)+side][:2]=world.CLOSED_GATES[side]
    ref=lambda n:{'sequence':n,'sha256':str(n)*64}
    return {'cue_event':ref(1) if event else None,
        'gate_event':ref(2) if event and case['kind']=='change' else None,
        'intervention_event':ref(3) if event and case['kind']=='change' else None,
        'sensed_event':ref(4),'before_occupancy':None,'after_occupancy':None,'actual_circles':circles}


def step(v,state,context,binding,case, *, token=0, missing=False, chain=None, fresh=False):
    tick=state['cursor']['tick']+1
    p=packet(state,tick,token,missing=missing,fresh=fresh)
    r=v.advance_transition_vnext(state,p,context=context,oracle_binding=binding,
        reach=reach_for(case,event=context['schedule']['event_tick'] is not None and tick>=context['schedule']['event_tick']),
        job_sha256='f'*64,chain=(0,memory.sha256(context)) if chain is None else chain)
    return r,p


def at_trigger(**kw):
    v,source,state,context,binding,case=fixture(**kw)
    r,_=step(v,state,context,binding,case)
    assert r.status=='ordinary-return'
    return v,source,r.proposed_state,context,binding,case


def test_local_selection_then_cue_failure_preserves_detached_witness():
    v,_,state,c,b,case=at_trigger()
    original=copy.deepcopy(state)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        r,p=step(v,state,c,b,case,token=1,missing=True)
    assert select.call_count==1
    assert state==original
    assert r.status=='raised' and isinstance(r.error.original_exception,legacy.CueUnavailable)
    assert r.proposed_state is None and r.bearing is None and r.decisions==[]
    assert r.input_lifecycle['status']=='pending' and r.local_lifecycle['status']=='selected'
    assert r.witness['result']=='raised' and r.witness['selection']['target_ids']==[case['facts'][0]['id']]
    trigger=r.witness['trigger']; selection=r.witness['selection']
    m,revisions,_=memory.revise(state['m'],trigger,selection,[],episode_id='episode-0',tick=p['tick'])
    audit=[{'kind':'memory_trigger','tick':p['tick'],'trigger':trigger},
           {'kind':'memory_selection','tick':p['tick'],'selection':selection}]
    audit += [{'kind':'memory_revision','tick':p['tick'],'revision':x} for x in revisions]
    assert r.witness['local_decisions_sha256']==memory.sha256(audit)
    assert r.witness['local_memory_sha256']!=memory.sha256(state)
    with pytest.raises(legacy.CueUnavailable,match='selected_waypoint_unavailable'):
        v.rethrow_transition_error_vnext(r)
    r.error.original_exception.args=('changed',)
    with pytest.raises(RuntimeError,match='changed'):
        v.rethrow_transition_error_vnext(r)


def test_input_and_all_nested_aliases_unchanged_on_success_and_exception():
    for missing in (False,True):
        v,_,state,c,b,case=at_trigger()
        originals=copy.deepcopy((state,c,b.source_m,b.case,b.source_world))
        r,p=step(v,state,c,b,case,token=1,missing=missing)
        assert (state,c,b.source_m,b.case,b.source_world)==originals
        assert r.status==('raised' if missing else 'witnessed-return')
        if r.proposed_state:
            r.proposed_state['m']['facts'][0]['associations'][0]['cue_id']='changed'
        assert (state,c,b.source_m,b.case,b.source_world)==originals
        detached=b.source_m; detached['facts'].clear()
        assert b.source_m==originals[2]


def test_mutating_each_result_projection_cannot_change_other_projections_or_witness():
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1)
    before=copy.deepcopy(r.witness)
    r.proposed_state['selector']['resource'].clear()
    r.proposed_state['terminal_lifecycle']['selection_sha256']='0'*64
    r.local_lifecycle['resource_sha256']='1'*64
    r.input_lifecycle['status']='changed'
    r.decisions[0]['trigger']['cue_id']='changed'
    assert r.witness==before
    r.witness['selection']['target_ids'].clear()
    assert r.witness['gold'] and r.decisions[1]['selection']['target_ids']


def test_every_stage_preimage_and_result_variant_is_exact():
    v,_,state,c,b,case=at_trigger()
    r,p=step(v,state,c,b,case,token=1)
    w=r.witness; h=memory.sha256(c); t=w['trigger']; selection=w['selection']
    stages={x['stage']:x for x in w['stages']}
    assert list(stages)==['trigger','resolved','installed','selected']
    before=state['detector']['cues'][0]; current=p['cues'][0]
    assert stages['trigger']['input_sha256']==memory.sha256({'context_sha256':h,'packet_sha256':memory.sha256(p),
        'detector_sha256':memory.sha256(state['detector']),'cue_id':current['id'],
        'previous_cue_sha256':memory.sha256(before),'current_cue_sha256':memory.sha256(current)})
    assert stages['trigger']['output_sha256']==memory.sha256({'trigger':t})
    ri={'context_sha256':h,'packet_sha256':memory.sha256(p),'trigger_sha256':memory.sha256(t),
        'source_m_sha256':c['source_m_sha256'],'source_world_sha256':c['source_world_sha256'],
        'case_sha256':c['case_sha256'],'event_evidence_sha256':memory.sha256(w['reach']),
        'before_occupancy':w['reach']['before_occupancy'],'after_occupancy':w['reach']['after_occupancy']}
    assert stages['resolved']['input_sha256']==memory.sha256(ri)
    assert stages['resolved']['output_sha256']==memory.sha256({'gold_target_ids':w['gold'],'resource_sha256':memory.sha256(w['gold'])})
    provenance=memory.sha256({'schema':'memory-oracle-resolution-provenance-vnext-v1','context_sha256':h,
        'input_sha256':stages['resolved']['input_sha256'],'output_sha256':stages['resolved']['output_sha256']})
    cfg=copy.deepcopy(state['selector']); cfg.update(resource=w['gold'],resource_sha256=memory.sha256(w['gold']),provenance_sha256=provenance)
    assert stages['installed']['input_sha256']==memory.sha256({'context_sha256':h,'selector_before_sha256':memory.sha256(state['selector']),
        'input_lifecycle':state['terminal_lifecycle'],'resource_sha256':memory.sha256(w['gold']),'resolution_provenance_sha256':provenance})
    assert stages['installed']['output_sha256']==memory.sha256({'selector_after':cfg})
    assert stages['selected']['input_sha256']==memory.sha256({'context_sha256':h,'packet_sha256':memory.sha256(p),
        'trigger_sha256':memory.sha256(t),'live_m_sha256':memory.sha256(state['m']),'selector_sha256':memory.sha256(cfg),
        'u_sha256':memory.sha256(state['u']),'resources_sha256':memory.sha256({'gold_target_ids':w['gold']})})
    assert stages['selected']['output_sha256']==memory.sha256({'selection':selection})
    assert w['local_memory_sha256']==memory.sha256(r.proposed_state)
    assert w['local_decisions_sha256']==memory.sha256(r.decisions)
    assert r.error is None and r.bearing==[1.,0.] and not r.idempotent
    assert set(vars(r))==set('status proposed_state bearing decisions input_lifecycle local_lifecycle witness error idempotent'.split())


def test_later_terminal_binds_prior_selection_without_new_gold_or_call():
    v,_,state,c,b,case=at_trigger()
    first,_=step(v,state,c,b,case,token=1)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        later,_=step(v,first.proposed_state,c,b,case,token=1,missing=True,chain=(1,memory.sha256(first.witness)))
    assert select.call_count==0 and later.status=='raised'
    assert later.witness['gold'] is None and later.witness['selection'] is None and later.witness['stages']==[]
    assert later.input_lifecycle==later.local_lifecycle==first.local_lifecycle
    assert later.witness['previous_sha256']==memory.sha256(first.witness) and later.witness['index']==1


def test_state4_rejects_direct_legacy_api_and_missing_or_mismatched_markers():
    v,_,state,c,b,case=fixture()
    for fn,args in ((legacy.validate_state,()),(legacy.advance_memory,(packet(state,state['cursor']['tick']+1),)),
                    (legacy.configure_selector,(state['selector'],)),(legacy.arm,(state['cursor']['tick']+1,)),
                    (legacy.inspect,()),(legacy.goal_allowed,()),(legacy.mark_goal,()),(legacy.acquired_boundary,())):
        with pytest.raises(ValueError): fn(state,*args)
    for key in ('terminal_context_sha256','terminal_lifecycle'):
        bad=copy.deepcopy(state); bad.pop(key)
        with pytest.raises(ValueError): v.validate_terminal_state_vnext(bad,context=c)
    bad=copy.deepcopy(state); bad['terminal_context_sha256']='0'*64
    with pytest.raises(ValueError): v.validate_terminal_state_vnext(bad,context=c)
    bad=copy.deepcopy(state); bad['version']=3
    with pytest.raises(ValueError): legacy.validate_state(bad)
    with pytest.raises(TypeError):
        v.advance_transition_vnext(state,packet(state,10),context=c,oracle_binding=b,reach=reach_for(case),job_sha256='f'*64,chain=(0,memory.sha256(c)),hook=lambda:None)


def test_promote_configure_arm_preserve_exact_source_view_and_declared_changes():
    v,source,state,c,b,case=fixture()
    cfg=copy.deepcopy(state['selector'])
    configured=v.configure_terminal_condition_vnext(source,cfg,state['u'],context=c)
    assert v.terminal_source_view_vnext(source)==v.terminal_source_view_vnext(configured,context=c)
    assert v.terminal_acquired_boundary_vnext(configured,context=c)
    expected=copy.deepcopy(configured)
    expected['supervisor'].update(continuation_start_tick=c['schedule']['boundary_tick'],decision_tick=c['schedule']['decision_tick'])
    assert expected==state
    inspected=v.inspect_terminal_state_vnext(state,context=c)
    inspected['facts'].clear(); inspected['terminal_lifecycle']['status']='changed'
    assert v.validate_terminal_state_vnext(state,context=c)==state
    app={'memory':source,'source_run_id':'a','event_prefix':'b','world':{'unchanged':1}}
    fork={**copy.deepcopy(app),'memory':configured,'source_run_id':'c','event_prefix':'d'}
    assert v.terminal_condition_invariant_vnext(app)==v.terminal_condition_invariant_vnext(fork,context=c)
    fork['world']['unchanged']=2
    assert v.terminal_condition_invariant_vnext(app)!=v.terminal_condition_invariant_vnext(fork,context=c)
    assert not v.terminal_goal_allowed_vnext(state,context=c)
    with pytest.raises(ValueError): v.mark_terminal_goal_vnext(state,context=c)


def test_source_m_gold_ignores_changed_live_m_but_selector_still_uses_live_m():
    v,_,state,c,b,case=at_trigger()
    state['m']['facts'][0].update(status='uncertain')
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        r,_=step(v,state,c,b,case,token=1)
    assert r.status=='witnessed-return' and r.witness['gold']==[case['facts'][0]['id']]
    assert select.call_count==1 and select.call_args.args[1]==state['m']


def test_null_empty_is_distinct_from_pending_noevent():
    v,_,state,c,b,case=at_trigger(kind='null')
    r,_=step(v,state,c,b,case,token=1)
    assert r.status=='witnessed-return' and r.witness['gold']==[] and r.local_lifecycle['status']=='selected'
    v,_,state,c,b,case=at_trigger(kind='no-event')
    r,_=step(v,state,c,b,case)
    assert r.status=='ordinary-return' and r.witness is None and r.local_lifecycle['status']=='pending'
    r,_=step(v,state,c,b,case,token=1)
    assert r.status=='rejected' and r.error is not None


def test_repeated_consumed_packet_has_no_second_calls_or_witness():
    v,_,state,c,b,case=at_trigger()
    r,p=step(v,state,c,b,case,token=1)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        repeat=v.advance_transition_vnext(r.proposed_state,p,context=c,oracle_binding=b,reach=reach_for(case,event=True),
            job_sha256='f'*64,chain=(1,memory.sha256(r.witness)))
    assert repeat.status=='idempotent' and repeat.idempotent and repeat.witness is None
    assert repeat.decisions==[] and select.call_count==0
    assert repeat.proposed_state==r.proposed_state and repeat.proposed_state is not r.proposed_state


def test_wrong_packet_digest_or_second_trigger_refuses():
    v,_,state,c,b,case=at_trigger()
    first,p=step(v,state,c,b,case,token=1)
    p['landmarks'][0]['bearing_rad']=.1
    r=v.advance_transition_vnext(first.proposed_state,p,context=c,oracle_binding=b,reach=reach_for(case,event=True),job_sha256='f'*64,chain=(1,memory.sha256(first.witness)))
    assert r.status=='rejected' and r.witness is None
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        r,_=step(v,first.proposed_state,c,b,case,token=0,chain=(1,memory.sha256(first.witness)))
    assert r.status=='rejected' and select.call_count==0


def test_witness_predicate_index_and_commit_candidates_never_contradict():
    v,_,state,c,b,case=at_trigger(condition='no-U')
    r,_=step(v,state,c,b,case,token=1)
    assert r.status=='ordinary-return' and r.witness is None and r.local_lifecycle['status']=='not-oracle'
    r,_=step(v,state,c,b,case,token=1,missing=True)
    assert r.status=='raised' and r.witness['stages']==[] and r.witness['selection'] is not None
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1,chain=(2,'0'*64))
    assert r.status=='rejected' and r.witness is None
    r,_=step(v,state,c,b,case,token=1,fresh=True)
    assert r.status=='rejected' and r.witness is not None
    # These are proposed local results, never claims that Engine assigned/committed.
    assert 'commit' not in vars(r)


@pytest.mark.parametrize('path',['quote".json','back\\slash','white space','control\x01','/absolute','a//b','a/../b','a/./b','a/','é'])
def test_descriptor_quotes_backslash_control_and_noncanonical_path_refuse(path):
    v,_,_,c,_,_=fixture()
    c['profile']['path']=path
    with pytest.raises(ValueError): v.validate_context_vnext(c)


def test_canonical_worst_case_witness_and_context_fit_subcaps(tmp_path):
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1,missing=True)
    # Max byte-domain exception: ASCII controls expand 6x in the complete writer.
    w=copy.deepcopy(r.witness); w['exception']={'type':'\x01'*512,'message':'\x00'*512}
    w['reach']['actual_circles']=[[-1.7976931348623157e308,-1.7976931348623157e308,1.7976931348623157e308] for _ in range(20)]
    for i,k in enumerate(('cue_event','gate_event','intervention_event','sensed_event')): w['reach'][k]['sequence']=49995+i
    w['tick']=2100; w['trigger']['tick']=2100
    long='x'*128
    w['reach']['before_occupancy']={long:'blocked','y'*128:'blocked'}
    w['reach']['after_occupancy']=copy.deepcopy(w['reach']['before_occupancy'])
    for i,k in enumerate(('id','episode_id','cue_id','before_observation_id','observation_id')): w['trigger'][k]=str(i)*128
    w['selection']['event_id']=w['trigger']['id']; w['selection']['target_ids']=[long]; w['gold']=[long]
    w['local_lifecycle']['resource_sha256']=memory.sha256(w['gold'])
    w['local_lifecycle']['selection_sha256']=memory.sha256(w['selection'])
    w['stages'][0]['output_sha256']=memory.sha256({'trigger':w['trigger']})
    w['stages'][1]['output_sha256']=memory.sha256({'gold_target_ids':w['gold'],'resource_sha256':memory.sha256(w['gold'])})
    w['stages'][3]['output_sha256']=memory.sha256({'selection':w['selection']})
    w['local_lifecycle']['provenance_sha256']=memory.sha256({'schema':'memory-oracle-resolution-provenance-vnext-v1',
        'context_sha256':w['context_sha256'],'input_sha256':w['stages'][1]['input_sha256'],'output_sha256':w['stages'][1]['output_sha256']})
    encoded=v.terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])
    decoded=json.loads(encoded)
    assert encoded.endswith(b'\n') and b'\\u0001' in encoded and decoded['witness']==w
    assert len(encoded)<=14336<16384
    import re
    def hashes(value):
        if type(value) is str: return int(re.fullmatch('[0-9a-f]{64}',value) is not None)
        if type(value) is dict: return sum(hashes(x) for x in value.values())
        if type(value) is list: return sum(hashes(x) for x in value)
        return 0
    hash_bytes=hashes(w)*66
    id_bytes=sum(len(k) for occupancy in (w['reach']['before_occupancy'],w['reach']['after_occupancy']) for k in occupancy)
    id_bytes+=sum(len(w['trigger'][k]) for k in ('id','episode_id','cue_id','before_observation_id','observation_id'))
    id_bytes+=len(w['selection']['event_id'])+sum(map(len,w['selection']['target_ids']))+sum(map(len,w['gold']))+len(c['run_id'])
    circle_bytes=len(json.dumps(w['reach']['actual_circles']))
    error_bytes=sum(len(json.dumps(x))-2 for x in w['exception'].values())
    fixed_bytes=len(encoded)-hash_bytes-id_bytes-circle_bytes-error_bytes
    assert hash_bytes<=2048 and id_bytes<=2048 and circle_bytes<=2048 and fixed_bytes<=2048
    assert error_bytes==6144
    # Exercise the actual unchanged writer's exact spaced/ASCII escaped envelope.
    from palimpsest.records import RunWriter
    writer=RunWriter(tmp_path/'authored-record',{'run_id':c['run_id']})
    writer._sequence=49999
    writer.event('memory_transition_witness_vnext',witness=w,run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])
    writer.close()
    assert (tmp_path/'authored-record'/'events.jsonl').read_bytes()==encoded
    for d in ('profile','source_closure','source_registration','source_commit','source_raw_audit','source_snapshot'):
        c[d]['path']='p'*512; c[d]['size_bytes']=16777216 if d=='source_snapshot' else 1048576
    c['case_id']=long; c['condition']='history-independent'; c['kind']='no-event'
    c['schedule']={'boundary_tick':2098,'event_tick':None,'decision_tick':2100}
    context_bytes=len(memory.canonical_bytes(v.validate_context_vnext(c)))
    assert context_bytes<=8192
    maximum_commit={'schema':'memory-transition-commit-vnext-v1','context_sha256':'a'*64,'witness_sha256':'b'*64,
        'tick':2100,'memory_sha256':'c'*64,'lifecycle':{'status':'selected','resource_sha256':'d'*64,'provenance_sha256':'e'*64,'selection_sha256':'f'*64}}
    commit_bytes=len(v.terminal_event_bytes_vnext('memory_transition_commit_vnext',maximum_commit,
        sequence=49999,run_id=c['run_id'],episode=0,tick=2100,episode_step=2100))
    assert commit_bytes<=2048
    print('Authored complete size proof:',{'witness':len(encoded),'context':context_bytes,'commit':commit_bytes,'fixed':fixed_bytes,'hashes':hash_bytes,'IDs':id_bytes,'circles':circle_bytes,'errors':error_bytes})
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',{**w,'exception':{'type':'x','message':'x'*513}},sequence=0,run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])


@pytest.mark.parametrize('mutation',[
    lambda w:w.update(extra=1),
    lambda w:w.update(index=True),
    lambda w:w.update(tick=2101),
    lambda w:w['reach']['sensed_event'].update(sequence=True),
    lambda w:w['stages'][0].update(extra=1),
    lambda w:w['stages'].append(copy.deepcopy(w['stages'][0])),
    lambda w:w.update(gold=['x','y']),
    lambda w:w['selection'].update(target_ids=['x','y']),
    lambda w:w['selection'].update(reason='arbitrary'),
    lambda w:w.update(result='returned'),  # exception still present
    lambda w:w['trigger'].update(cue_id='é'),
    lambda w:w['local_lifecycle'].update(status='pending'),
    lambda w:w['stages'][3].update(output_sha256='0'*64),
    lambda w:w['local_lifecycle'].update(provenance_sha256='0'*64),
])
def test_complete_event_encoder_refuses_malformed_nested_witness(mutation):
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1,missing=True)
    w=copy.deepcopy(r.witness); mutation(w)
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])


def test_bad_chain_resource_binding_ref_and_wire_ids_refuse_before_selector():
    v,_,state,c,b,case=at_trigger()
    p=packet(state,state['cursor']['tick']+1,1)
    kwargs=dict(context=c,oracle_binding=b,reach=reach_for(case,event=True),job_sha256='f'*64,chain=(0,memory.sha256(c)))
    candidates=[]
    bad=copy.deepcopy(kwargs); bad['reach']['gate_event']['sequence']=bad['reach']['sensed_event']['sequence']; candidates.append((state,p,bad))
    bad=copy.deepcopy(kwargs); bad['chain']=(0,'0'*64); candidates.append((state,p,bad))
    altered=copy.deepcopy(state); altered['selector']['resource_sha256']='0'*64; candidates.append((altered,p,kwargs))
    altered=copy.deepcopy(p); altered['cues'][0]['id']='é'; candidates.append((state,altered,kwargs))
    altered=copy.deepcopy(p); altered['id']='x'*129; candidates.append((state,altered,kwargs))
    for s,p,args in candidates:
        with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
            r=v.advance_transition_vnext(s,p,**args)
        assert r.status=='rejected' and r.witness is None and select.call_count==0
    # Bounded reached geometry refusal has the actual stage prefix, never 900.
    kwargs['reach']['actual_circles'][0][0]+=.1
    r=v.advance_transition_vnext(state,packet(state,state['cursor']['tick']+1,1),**kwargs)
    assert r.status=='rejected' and r.witness['result']=='rejected'
    assert [s['stage'] for s in r.witness['stages']]==['trigger']
    assert r.witness['gold'] is None and r.witness['selection'] is None


def test_successor_id_and_exception_one_byte_over_bounds_refuse():
    v,_,state,c,b,case=at_trigger()
    for path in ('p'*513,):
        bad=copy.deepcopy(c); bad['profile']['path']=path
        with pytest.raises(ValueError): v.validate_context_vnext(bad)
    bad=copy.deepcopy(c); bad['case_id']='x'*129
    with pytest.raises(ValueError): v.validate_context_vnext(bad)
    # Old ID admission remains deliberately broader.
    memory._id('é')


def test_returned_supervisor_failure_is_witnessed_without_fabricating_exception():
    v,_,state,c,b,case=fixture(condition='no-U',kind='no-event')
    # Authored travel/inspection sequence uses the real worker to reach its
    # frozen waypoint deadline without inventing a supervisor/model callback.
    for tick in range(c['schedule']['boundary_tick'],c['schedule']['boundary_tick']+400):
        r,p=step(v,state,c,b,case)
        assert r.error is None
        state=r.proposed_state
        if state['supervisor']['phase']=='failure': break
    assert r.status=='witnessed-return' and r.witness['result']=='returned'
    assert r.witness['exception'] is None and r.error is None and r.bearing==[1.,0.]
    assert r.decisions and r.witness['local_decisions_sha256']==memory.sha256(r.decisions)
    commit={'schema':'memory-transition-commit-vnext-v1','context_sha256':memory.sha256(c),
        'witness_sha256':memory.sha256(r.witness),'tick':state['cursor']['tick'],
        'memory_sha256':memory.sha256(state),'lifecycle':r.local_lifecycle}
    encoded=v.terminal_event_bytes_vnext('memory_transition_commit_vnext',commit,sequence=49999,run_id=c['run_id'],episode=0,tick=commit['tick'],episode_step=commit['tick'])
    assert len(encoded)<=2048
    bad=copy.deepcopy(commit); bad['lifecycle']['resource_sha256']='a'*64
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_commit_vnext',bad,sequence=1,run_id=c['run_id'],episode=0,tick=bad['tick'],episode_step=bad['tick'])


def test_mutated_error_and_aligned_witness_cannot_bypass_captured_projection():
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1,missing=True)
    # Witness is intentionally a detached mutable projection. The immutable
    # token projection must still catch a matching mutation to both objects.
    original=r.error.original_exception
    assert r.error.captured_type is type(original)
    original.args=('changed',)
    r.witness['exception']['message']='changed'
    with pytest.raises(RuntimeError,match='changed'):
        v.rethrow_transition_error_vnext(r)
    r,_=step(v,state,c,b,case,token=1,missing=True)
    original=r.error.original_exception
    with pytest.raises(legacy.CueUnavailable) as raised:
        v.rethrow_transition_error_vnext(r)
    assert raised.value is original
    r.witness['exception']['message']='changed'
    with pytest.raises(RuntimeError,match='changed'):
        v.rethrow_transition_error_vnext(r)


def test_delayed_trigger_at_decision_is_valid_but_later_install_refuses():
    v,_,state,c,b,case=at_trigger()
    pre,_=step(v,state,c,b,case,token=0)
    assert pre.status=='ordinary-return' and pre.witness is None
    r,_=step(v,pre.proposed_state,c,b,case,token=1)
    assert r.status=='witnessed-return' and r.witness['tick']==c['schedule']['decision_tick']
    pre,_=step(v,pre.proposed_state,c,b,case,token=0)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        late,_=step(v,pre.proposed_state,c,b,case,token=1)
    assert late.status=='rejected' and late.witness['result']=='rejected' and select.call_count==0


@pytest.mark.parametrize('mutation',[
    lambda m:m['facts'][0].update(status='uncertain'),
    lambda m:m['facts'][0].update(estimate='blocked'),
    lambda m:m['facts'][0]['evidence'].update(tick=2100),
    lambda m:m['facts'][0]['associations'][0].update(relation='paired_cue'),
])
def test_source_binding_refuses_nonacquired_or_changed_factual_identity(mutation):
    v,source,state,c,b,case=fixture()
    m=copy.deepcopy(source['m']); mutation(m)
    with pytest.raises(ValueError): v.OracleBinding(m,case,b.source_world)


def test_event_references_must_precede_complete_writer_event():
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1)
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',r.witness,sequence=4,run_id=c['run_id'],episode=0,tick=r.witness['tick'],episode_step=r.witness['tick'])
    assert v.terminal_event_bytes_vnext('memory_transition_witness_vnext',r.witness,sequence=5,run_id=c['run_id'],episode=0,tick=r.witness['tick'],episode_step=r.witness['tick'])


def test_every_arm_noevent_is_nonuse_and_has_equal_ordinary_source_view():
    baseline=None
    for condition in memory_experiment.CONDITIONS:
        v,_,state,c,b,case=fixture(condition=condition,kind='no-event')
        with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
            for _ in range(3):
                r,p=step(v,state,c,b,case)
                assert r.status=='ordinary-return' and r.witness is None and r.error is None
                state=r.proposed_state
        assert select.call_count==0
        assert r.local_lifecycle['status']==('pending' if condition=='oracle' else 'not-oracle')
        view=v.terminal_source_view_vnext(state,context=c)
        if baseline is None: baseline=view
        else: assert view==baseline


def test_terminal_sensed_packet_at_decision_keeps_fresh_passage_guard():
    v,_,state,c,b,case=at_trigger()
    first,_=step(v,state,c,b,case,token=1)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        terminal,p=step(v,first.proposed_state,c,b,case,token=1,missing=True,fresh=True,chain=(1,memory.sha256(first.witness)))
    assert p['tick']==c['schedule']['decision_tick'] and select.call_count==0
    assert terminal.status=='rejected' and terminal.witness['result']=='rejected'
    assert terminal.witness['stages']==[] and terminal.witness['gold'] is None and terminal.witness['selection'] is None
    assert terminal.witness['reach']['before_occupancy'] is None


@pytest.mark.parametrize('circle',[[10**308,0.,.4],(0.,0.,.4),[0,0.,.4],[float('inf'),0.,.4],[0.,0.,False]])
def test_successor_circles_require_plain_finite_float64_triples(circle):
    v,_,state,c,b,case=fixture(condition='no-U',kind='no-event')
    reach=reach_for(case); reach['actual_circles'][0]=circle
    p=packet(state,state['cursor']['tick']+1)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        r=v.advance_transition_vnext(state,p,context=c,oracle_binding=None,reach=reach,job_sha256='f'*64,chain=(0,memory.sha256(c)))
    assert r.status=='rejected' and r.witness is None and select.call_count==0


def test_terminal_encoder_uses_exact_engine_envelope(tmp_path):
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1,missing=True)
    tick=r.witness['tick']
    encoded=v.terminal_event_bytes_vnext('memory_transition_witness_vnext',r.witness,
        sequence=49999,run_id=c['run_id'],episode=0,tick=tick,episode_step=tick)
    assert set(json.loads(encoded))=={'run_id','episode','tick','episode_step','sequence','kind','witness'}
    from palimpsest.records import RunWriter
    writer=RunWriter(tmp_path/'exact-engine-envelope',{'run_id':c['run_id']})
    writer._sequence=49999
    writer.event('memory_transition_witness_vnext',run_id=c['run_id'],episode=0,tick=tick,episode_step=tick,witness=r.witness)
    writer.close()
    assert (tmp_path/'exact-engine-envelope'/'events.jsonl').read_bytes()==encoded


@pytest.mark.parametrize('field,value',[('episode',True),('episode',1),('tick',True),('tick',2101),('episode_step',True),('episode_step',2101)])
def test_exact_engine_envelope_refuses_bad_counters(field,value):
    v,_,state,c,b,case=at_trigger()
    r,_=step(v,state,c,b,case,token=1)
    fields={'sequence':49999,'run_id':c['run_id'],'episode':0,'tick':r.witness['tick'],'episode_step':r.witness['tick']}
    fields[field]=value
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',r.witness,**fields)
    fields={'sequence':49999,'run_id':c['run_id'],'episode':0,'tick':r.witness['tick'],'episode_step':r.witness['tick']+1}
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',r.witness,**fields)


def test_round1_selected_duplicate_requires_persisted_selection_count():
    v,_,state,c,b,case=at_trigger()
    first,p=step(v,state,c,b,case,token=1)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        valid=v.advance_transition_vnext(first.proposed_state,p,context=c,oracle_binding=b,reach=reach_for(case,event=True),
            job_sha256='f'*64,chain=(1,memory.sha256(first.witness)))
        contradictory=v.advance_transition_vnext(first.proposed_state,p,context=c,oracle_binding=b,reach=reach_for(case,event=True),
            job_sha256='f'*64,chain=(0,memory.sha256(c)))
    assert select.call_count==0
    assert valid.status=='idempotent' and valid.idempotent and valid.witness is None and valid.decisions==[]
    assert contradictory.status=='rejected' and not contradictory.idempotent and contradictory.witness is None
    assert contradictory.proposed_state is None and contradictory.bearing is None and contradictory.decisions==[]


def test_round1_witness_input_selected_requires_index_one_bidirectionally():
    v,_,state,c,b,case=at_trigger()
    first,_=step(v,state,c,b,case,token=1)
    assert first.witness['index']==0 and first.witness['input_lifecycle']['status']=='pending'
    assert first.witness['local_lifecycle']['status']=='selected'
    later,_=step(v,first.proposed_state,c,b,case,token=1,missing=True,chain=(1,memory.sha256(first.witness)))
    w=copy.deepcopy(later.witness)
    assert w['input_lifecycle']['status']=='selected'
    assert v.terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,
        run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])
    w.update(index=0,previous_sha256=memory.sha256(c))
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,
            run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])


@pytest.mark.parametrize('mutation',[
    lambda r:r.update(gate_event=None),
    lambda r:r.update(intervention_event=None),
    lambda r:r.update(cue_event=None),
    lambda r:r['gate_event'].update(sequence=r['intervention_event']['sequence']),
    lambda r:r['gate_event'].update(sha256=r['intervention_event']['sha256']),
    lambda r:r['gate_event'].update(sequence=r['sensed_event']['sequence']+1),
])
def test_round1_reach_ref_invariants_match_admission_and_encoding(mutation):
    v,_,state,c,b,case=at_trigger()
    first,_=step(v,state,c,b,case,token=1)
    w=copy.deepcopy(first.witness); mutation(w['reach'])
    with pytest.raises(ValueError):
        v.validate_reach_vnext(w['reach'],context=c,subjects=case['subjects_by_side'])
    with pytest.raises(ValueError):
        v.terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,
            run_id=c['run_id'],episode=0,tick=w['tick'],episode_step=w['tick'])


def test_round1_valid_input_output_decision_cap_is_rejected_without_witness():
    v,source,state,c,b,case=fixture(condition='no-U',kind='no-event')
    state['last_decisions']=['x'*65520]
    original=copy.deepcopy(state)
    assert len(memory.canonical_bytes(state['last_decisions']))==65524
    assert v.validate_terminal_state_vnext(state,context=c)==state
    legacy_input=legacy.configure_selector(source,state['selector'],state['u'])
    legacy_input=legacy.arm(legacy_input,c['schedule']['boundary_tick'])
    legacy_input['last_decisions']=copy.deepcopy(state['last_decisions'])
    legacy_original=copy.deepcopy(legacy_input)
    assert legacy.validate_state(legacy_input)==legacy_input
    p=packet(state,state['cursor']['tick']+1)
    with pytest.raises(ValueError) as old_error:
        legacy.advance_memory(legacy_input,p)
    with patch.object(memory_experiment,'selection_for_condition',wraps=memory_experiment.selection_for_condition) as select:
        r,_=step(v,state,c,b,case)
    assert select.call_count==0 and state==original and legacy_input==legacy_original
    assert r.status=='rejected' and r.witness is None and not r.idempotent
    assert r.proposed_state is None and r.bearing is None and r.decisions==[]
    assert r.input_lifecycle==r.local_lifecycle==state['terminal_lifecycle']
    assert r.input_lifecycle is not r.local_lifecycle and r.input_lifecycle is not state['terminal_lifecycle']
    assert type(r.error.original_exception) is type(old_error.value) is ValueError
    assert str(r.error.original_exception)==str(old_error.value)=='Memory JSON exceeds byte limit'
    with pytest.raises(ValueError) as rethrown:
        v.rethrow_transition_error_vnext(r)
    assert rethrown.value is r.error.original_exception
