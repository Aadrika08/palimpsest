"""Proposed unqualified terminal transition records; no source authority.

The fixed worker executes once. Hashes and typed references are commitments,
not custody or proof of event placement; independent held-source replay remains
required. This module opens no source/model/recording payloads and commits no
Engine state. The caller must stop an owner after an error result.
"""
import copy
from dataclasses import dataclass
import json
import math
import re
import uuid
from typing import NoReturn

from . import memory, memory_decision as decision, memory_task
from . import memory_decision_world as world, memory_experiment, memory_world

CONTEXT_SCHEMA = 'memory-terminal-context-vnext-v1'
WITNESS_SCHEMA = 'memory-transition-witness-vnext-v1'
COMMIT_SCHEMA = 'memory-transition-commit-vnext-v1'
CONTEXT_MAX_BYTES = WITNESS_EVENT_MAX_BYTES = 16384
COMMIT_EVENT_MAX_BYTES = 2048
_CONTEXT_FIELDS = ('schema profile source_closure source_registration source_commit source_raw_audit '
    'source_snapshot source_application_sha256 source_m_sha256 source_world_sha256 source_run_id '
    'case_id case_sha256 kind run_id condition condition_resources_sha256 source_invariant_sha256 schedule')
_DESCRIPTOR_ROLES = ('profile','source_closure','source_registration','source_commit','source_raw_audit','source_snapshot')
_WITNESS_FIELDS = ('schema context_sha256 job_sha256 index previous_sha256 tick packet_sha256 '
    'input_memory_sha256 input_lifecycle local_lifecycle reach trigger stages gold selection '
    'local_memory_sha256 local_decisions_sha256 result exception')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z',re.ASCII)
_PATH = re.compile(r'[A-Za-z0-9._/-]+\Z',re.ASCII)


class _Rejected(ValueError):
    """Reached infrastructure refusal; never a scientific terminal cause."""


def _id(value):
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError('Invalid proposed successor ID')


def _tick(value):
    if type(value) is not int or not 0 <= value <= 2100:
        raise ValueError('Invalid proposed successor tick')


def _uuid(value):
    if type(value) is not str or str(uuid.UUID(value)) != value:
        raise ValueError('Noncanonical run UUID')


def validate_descriptor_vnext(value, *, max_bytes=536870912):
    memory._fields(value,'path size_bytes sha256')
    p=value['path']
    if (type(p) is not str or not p or len(p.encode('utf-8'))>512 or _PATH.fullmatch(p) is None
            or any(part in ('','.','..') for part in p.split('/'))):
        raise ValueError('Noncanonical successor descriptor path')
    if type(value['size_bytes']) is not int or not 0 <= value['size_bytes'] <= max_bytes:
        raise ValueError('Invalid descriptor byte size')
    memory._digest(value['sha256'])
    return copy.deepcopy(value)


def validate_context_vnext(context):
    memory._fields(context,_CONTEXT_FIELDS)
    if context['schema'] != CONTEXT_SCHEMA:
        raise ValueError('Invalid terminal Context schema')
    # Proposed wire ceilings only: later held-source readers retain stricter
    # inherited per-role caps and the unchanged combined metadata ceiling.
    for role in _DESCRIPTOR_ROLES:
        cap=16777216 if role=='source_snapshot' else 1048576
        validate_descriptor_vnext(context[role],max_bytes=cap)
    for key in ('source_application_sha256','source_m_sha256','source_world_sha256','case_sha256',
                'condition_resources_sha256','source_invariant_sha256'):
        memory._digest(context[key])
    _uuid(context['source_run_id']); _uuid(context['run_id']); _id(context['case_id'])
    if context['source_run_id']==context['run_id']:
        raise ValueError('Source and condition owner identities must differ')
    memory._enum(context['kind'],('change','null','no-event'))
    memory._enum(context['condition'],memory_experiment.CONDITIONS)
    schedule=context['schedule']; memory._fields(schedule,'boundary_tick event_tick decision_tick')
    _tick(schedule['boundary_tick']); _tick(schedule['decision_tick'])
    if schedule['boundary_tick']==0:
        raise ValueError('Boundary must be positive')
    if schedule['event_tick'] is not None: _tick(schedule['event_tick'])
    if ((context['kind']=='no-event') != (schedule['event_tick'] is None)
            or schedule['decision_tick'] < schedule['boundary_tick']
            or schedule['event_tick'] is not None and not schedule['boundary_tick'] <= schedule['event_tick'] <= schedule['decision_tick']):
        raise ValueError('Contradictory schedule')
    memory._bounded(context,CONTEXT_MAX_BYTES)
    return copy.deepcopy(context)


def pending_provenance_vnext(context):
    """Acyclic pending-config identity; deliberately not resolved gold."""
    return memory.sha256({'schema':'memory-oracle-pending-provenance-vnext-v1',
        'profile':validate_descriptor_vnext(context['profile'],max_bytes=1048576),
        'source_application_sha256':context['source_application_sha256'],
        'case_sha256':context['case_sha256'],'run_id':context['run_id']})


def _lifecycle(value):
    memory._fields(value,'status resource_sha256 provenance_sha256 selection_sha256')
    memory._enum(value['status'],('not-oracle','pending','selected'))
    for k in ('resource_sha256','provenance_sha256','selection_sha256'):
        if value['status']=='selected': memory._digest(value[k])
        elif value[k] is not None: raise ValueError('Unselected Lifecycle contains resolved evidence')
    return copy.deepcopy(value)


def _empty_lifecycle(condition):
    return {'status':'pending' if condition=='oracle' else 'not-oracle',
            'resource_sha256':None,'provenance_sha256':None,'selection_sha256':None}


def _wire_state_ids(state):
    # Stricter successor ID domain is local to this new marked API.
    for fact in state['m']['facts']:
        for k in ('id','subject_id','inspection_landmark_id'): _id(fact[k])
        for association in fact['associations']: _id(association['cue_id'])
    for i in state['graph']['landmark_ids']: _id(i)
    for route in state['graph']['routes']: _id(route['route_id'])
    for cue in state['detector']['cues']:
        _id(cue['id']); _id(cue['observation_id'])


def validate_terminal_state_vnext(state, *, context):
    c=validate_context_vnext(context)
    s=decision._validate_state_fields(state,4)
    if s['terminal_context_sha256'] != memory.sha256(c):
        raise ValueError('Terminal state Context marker differs')
    life=_lifecycle(s['terminal_lifecycle']); cfg=s['selector']
    if cfg['condition'] != c['condition'] or (cfg['condition']=='oracle') != (life['status']!='not-oracle'):
        raise ValueError('Context/config/Lifecycle disagree')
    expected=copy.deepcopy(cfg)
    if cfg['condition']=='oracle':
        if life['status']=='selected':
            if len(cfg['resource']) != (1 if c['kind']=='change' else 0) or c['kind']=='no-event':
                raise ValueError('Selected cardinality contradicts kind')
            if cfg['resource_sha256']!=life['resource_sha256'] or cfg['provenance_sha256']!=life['provenance_sha256']:
                raise ValueError('Selected config differs from Lifecycle')
        elif cfg['resource']!=[] or cfg['provenance_sha256']!=pending_provenance_vnext(c):
            raise ValueError('Pending oracle config differs')
        expected.update(resource=[],resource_sha256=memory.sha256([]),provenance_sha256=pending_provenance_vnext(c))
    if memory.sha256({'selector':expected,'u':s['u']}) != c['condition_resources_sha256']:
        raise ValueError('Condition resource identity differs')
    profile=world.registered_profile(s['graph']['profile_sha256'])['arm_schedule']
    boundary=c['schedule']['boundary_tick']
    if c['schedule'] != {'boundary_tick':boundary,'event_tick':None if c['kind']=='no-event' else boundary+profile['event_offset'],
                         'decision_tick':boundary+profile['decision_offset']}:
        raise ValueError('Schedule differs from registered profile')
    sup=s['supervisor']
    if sup['continuation_start_tick'] is not None and (sup['continuation_start_tick']!=boundary or sup['decision_tick']!=c['schedule']['decision_tick']):
        raise ValueError('Armed state schedule differs')
    if s['cursor'] is not None: _tick(s['cursor']['tick'])
    _wire_state_ids(s)
    return copy.deepcopy(s)


def promote_terminal_state_vnext(configured_state3, *, context):
    c=validate_context_vnext(context); s=decision.validate_state(configured_state3)
    if not decision._acquired_boundary_validated(s) or s['cursor']['tick']!=c['schedule']['boundary_tick']-1:
        raise ValueError('Promotion requires unarmed acquired source boundary')
    if memory.sha256(s['m'])!=c['source_m_sha256']:
        raise ValueError('Promotion source M differs')
    s.update(version=4,terminal_context_sha256=memory.sha256(c),terminal_lifecycle=_empty_lifecycle(c['condition']))
    return validate_terminal_state_vnext(s,context=c)


def configure_terminal_condition_vnext(source_state3, config, u, *, context):
    source=decision.validate_state(source_state3)
    configured=decision.configure_selector(source,config,u)
    result=promote_terminal_state_vnext(configured,context=context)
    if terminal_source_view_vnext(source)!=terminal_source_view_vnext(result,context=context):
        raise ValueError('Declared configuration changed source view')
    return result


def arm_terminal_state_vnext(state4, *, boundary_tick, context):
    s=validate_terminal_state_vnext(state4,context=context)
    if boundary_tick!=context['schedule']['boundary_tick'] or type(boundary_tick) is not int:
        raise ValueError('Arm boundary differs from Context')
    decision._arm_validated(s,boundary_tick)
    return validate_terminal_state_vnext(s,context=context)


def inspect_terminal_state_vnext(state4, *, context):
    s=validate_terminal_state_vnext(state4,context=context)
    return copy.deepcopy({'version':4,'episode_id':s['episode_id'],'supervisor':s['supervisor'],
        'facts':s['m']['facts'],'requests':s['requests'],
        'hashes':{k:memory.sha256(s[k]) for k in ('m','e','u','selector','graph')},
        'selector':{k:v for k,v in s['selector'].items() if k!='resource'},
        'terminal_context_sha256':s['terminal_context_sha256'],'terminal_lifecycle':s['terminal_lifecycle']})


def terminal_acquired_boundary_vnext(state4, *, context):
    return decision._acquired_boundary_validated(validate_terminal_state_vnext(state4,context=context))


def terminal_goal_allowed_vnext(state4, *, context):
    return decision._goal_allowed_validated(validate_terminal_state_vnext(state4,context=context))


def mark_terminal_goal_vnext(state4, *, context):
    s=validate_terminal_state_vnext(state4,context=context)
    if not decision._goal_allowed_validated(s):
        raise ValueError('Goal requires the chosen route real open inspection and goal stage')
    s['supervisor']['phase']='goal'
    return validate_terminal_state_vnext(s,context=context)


def terminal_source_view_vnext(state, *, context=None):
    s=validate_terminal_state_vnext(state,context=context) if type(state) is dict and state.get('version')==4 else decision.validate_state(state)
    for k in ('version','u','selector','terminal_context_sha256','terminal_lifecycle'): s.pop(k,None)
    return s


def terminal_condition_invariant_vnext(application, *, context=None):
    from .snapshots import state_digest
    if type(application) is not dict or 'memory' not in application:
        raise ValueError('Incomplete application invariant')
    app=copy.deepcopy(application)
    app['memory']=terminal_source_view_vnext(app['memory'],context=context)
    for k in ('source_run_id','event_prefix'): app.pop(k,None)
    return state_digest(app)


@dataclass(frozen=True,init=False)
class OracleBinding:
    """Detached immutable data only, NOT an authenticated source capability.

    The later fixed source consumer must establish held custody and actual source
    placement equals the registered geometry; state2 validation alone cannot.
    Canonical bytes prevent mutable members from escaping through frozen fields.
    """
    _source_m_bytes: bytes
    _case_bytes: bytes
    _source_world_bytes: bytes

    def __init__(self,source_m,case,source_world):
        m=memory.validate_m(source_m); case=world.validate_case(case); sw=world.validate_state(source_world)
        if sw['case']!=case or sw['armed_boundary_tick'] is not None or sw['applied']:
            raise ValueError('Binding requires matching unarmed acquired source world')
        stable=('id','subject_id','kind','associations','inspection_landmark_id')
        if ({f['subject_id'] for f in m['facts']} != set(case['subjects_by_side'])
                or [{k:f[k] for k in stable} for f in m['facts']] !=
                   [{k:f[k] for k in stable} for f in memory.validate_m({'version':1,'facts':case['facts']})['facts']]):
            raise ValueError('Binding source factual identity differs')
        if sw['last_tick'] is None or any(f['status']!='observed' or f['estimate']!='open'
                or f['evidence']['episode_id']!='episode-0' or f['evidence']['tick']>sw['last_tick'] for f in m['facts']):
            raise ValueError('Binding source M is not the acquired observed-open boundary')
        for field,value in (('_source_m_bytes',m),('_case_bytes',case),('_source_world_bytes',sw)):
            object.__setattr__(self,field,memory.canonical_bytes(value))

    @property
    def source_m(self): return json.loads(self._source_m_bytes)
    @property
    def case(self): return json.loads(self._case_bytes)
    @property
    def source_world(self): return json.loads(self._source_world_bytes)


def _ref(value):
    memory._fields(value,'sequence sha256')
    if type(value['sequence']) is not int or not 0<=value['sequence']<50000:
        raise ValueError('Invalid event sequence')
    memory._digest(value['sha256'])


def _occupancy(value,subjects):
    if type(value) is not dict or set(value)!=set(subjects) or any(v not in ('open','blocked') or type(v) is not str for v in value.values()):
        raise ValueError('Invalid exact occupancy map')
    for s in value: _id(s)


def _circles(value):
    memory._list(value,20)
    for circle in value:
        if type(circle) is not list or len(circle)!=3 or any(type(x) is not float or not math.isfinite(x) for x in circle) or circle[2]<=0:
            raise ValueError('Reach requires plain finite float64 circle triples')


def validate_reach_vnext(reach, *, context, subjects):
    memory._fields(reach,'cue_event gate_event intervention_event sensed_event before_occupancy after_occupancy actual_circles')
    c=validate_context_vnext(context)
    refs=[]
    for key in ('cue_event','gate_event','intervention_event','sensed_event'):
        value=reach[key]
        if value is not None: _ref(value); refs.append(value)
        elif key=='sensed_event': raise ValueError('Reach requires current sensed event')
    sequences=[v['sequence'] for v in refs]
    if len(set(sequences))!=len(sequences) or refs[-1]!=reach['sensed_event'] or any(v['sequence']>=reach['sensed_event']['sequence'] for v in refs[:-1]):
        raise ValueError('Contradictory event reference order')
    if len({v['sha256'] for v in refs})!=len(refs): raise ValueError('Aliased event references')
    if c['kind'] in ('null','no-event') and (reach['gate_event'] is not None or reach['intervention_event'] is not None):
        raise ValueError('Null/no-event has no gate intervention')
    if c['kind']=='no-event' and reach['cue_event'] is not None: raise ValueError('No-event has no cue event')
    if (reach['gate_event'] is None)!=(reach['intervention_event'] is None): raise ValueError('Incomplete gate edit references')
    if reach['gate_event'] is not None and reach['cue_event'] is None: raise ValueError('Gate has no reached cue event')
    maps=(reach['before_occupancy'],reach['after_occupancy'])
    if (maps[0] is None)!=(maps[1] is None): raise ValueError('Partial occupancy maps')
    if maps[0] is not None:
        for value in maps: _occupancy(value,subjects)
    _circles(reach['actual_circles'])
    return copy.deepcopy(reach)


def _binding_matches(binding,context,state):
    if type(binding) is not OracleBinding: raise ValueError('Oracle requires fixed data binding')
    case=binding.case; sw=binding.source_world
    if (memory.sha256(binding.source_m)!=context['source_m_sha256'] or memory.sha256(sw)!=context['source_world_sha256']
            or memory.sha256(case)!=context['case_sha256'] or case['case_id']!=context['case_id']
            or case['kind']!=context['kind'] or sw['last_tick']!=context['schedule']['boundary_tick']-1
            or world.public_graph(case)!=state['graph']):
        raise ValueError('Source binding identity differs from Context/state')
    _wire_state_ids(state)


def _resolved_reach(binding,reach,trigger):
    case=binding.case
    source_world=binding.source_world
    _,_,before_circles=world.audit_inputs(source_world,[0.,0.,0.])
    actual=reach['actual_circles']
    expected=copy.deepcopy(before_circles)
    if case['kind']=='change':
        if reach['cue_event'] is None or reach['gate_event'] is None or reach['intervention_event'] is None:
            raise _Rejected('Reached change lacks actual edit references')
        side=case['subjects_by_side'].index(case['closure_subject_id'])
        expected[len(world.POSTS)+side][:2]=world.CLOSED_GATES[side].copy()
    elif case['kind']=='null':
        if reach['cue_event'] is None: raise _Rejected('Reached null lacks cue reference')
    else: raise _Rejected('No-event cannot resolve')
    if actual!=expected: raise _Rejected('Reached circles differ from sole allowed applied edit')
    before=memory_world.passage_status(before_circles); after=memory_world.passage_status(actual)
    before={s:before[old] for s,old in zip(case['subjects_by_side'],memory_world.SUBJECTS)}
    after={s:after[old] for s,old in zip(case['subjects_by_side'],memory_world.SUBJECTS)}
    result=copy.deepcopy(reach)
    if reach['before_occupancy'] is not None and (reach['before_occupancy']!=before or reach['after_occupancy']!=after):
        raise _Rejected('Caller occupancy contradicts actual geometry')
    result.update(before_occupancy=before,after_occupancy=after)
    return result


def resolve_gold_vnext(binding,reach,trigger):
    if type(binding) is not OracleBinding: raise ValueError('Invalid fixed OracleBinding')
    t=memory.validate_trigger(trigger)
    r=_resolved_reach(binding,reach,t)
    gold=memory_experiment.gold_target_ids(binding.source_m,r['before_occupancy'],r['after_occupancy'],t)
    if len(gold)!=(1 if binding.case['kind']=='change' else 0):
        raise _Rejected('Reached source-M gold cardinality differs')
    return gold


@dataclass(frozen=True)
class _ExceptionToken:
    original_exception: Exception
    captured_type: type
    captured_projection: bytes


@dataclass(frozen=True)
class TransitionResult:
    status: str
    proposed_state: dict | None
    bearing: list | None
    decisions: list
    input_lifecycle: dict | None
    local_lifecycle: dict | None
    witness: dict | None
    error: _ExceptionToken | None
    idempotent: bool


def _result(status, *, proposed_state=None,bearing=None,decisions=None,input_lifecycle=None,local_lifecycle=None,witness=None,error=None,idempotent=False):
    # Each projection has an independent deep-copy traversal, even when the
    # worker originally shared state/selection/Lifecycle objects internally.
    return TransitionResult(status,copy.deepcopy(proposed_state),copy.deepcopy(bearing),
        copy.deepcopy([] if decisions is None else decisions),copy.deepcopy(input_lifecycle),
        copy.deepcopy(local_lifecycle),copy.deepcopy(witness),
        None if error is None else _ExceptionToken(error,type(error),memory.canonical_bytes(_exception(error))),idempotent)


def _exception(error):
    value={'type':type(error).__name__,'message':str(error)}
    for text in value.values():
        if len(text.encode('utf-8'))>512: raise ValueError('Exception projection exceeds bound')
    return value


def rethrow_transition_error_vnext(result: TransitionResult) -> NoReturn:
    """Rethrow the SAME captured exception only while its projection agrees."""
    if type(result) is not TransitionResult or type(result.error) is not _ExceptionToken:
        raise RuntimeError('Transition has no captured exception token')
    token=result.error
    try:
        if type(token.original_exception) is not token.captured_type:
            raise ValueError('Captured exception type changed')
        projection=memory.canonical_bytes(_exception(token.original_exception))
        if projection!=token.captured_projection:
            raise ValueError('Captured exception projection changed')
        if result.witness is not None and memory.canonical_bytes(result.witness['exception'])!=token.captured_projection:
            raise ValueError('Captured witness exception projection changed')
    except Exception as error:
        raise RuntimeError('Captured exception token or witness changed') from error
    raise token.original_exception


class _TransitionBuilder:
    """Fixed private single-execution capture, never an externally supplied sink."""
    def __init__(self,state,packet,context,binding,reach,job_sha256,chain):
        self.context=copy.deepcopy(context); self.binding=binding; self.reach=copy.deepcopy(reach)
        self.packet=copy.deepcopy(packet); self.input_state=copy.deepcopy(state)
        self.local_state=state; self.local_decisions=[]; self.job_sha256=job_sha256; self.chain=chain
        self.stages=[]; self.trigger=None; self.gold=None; self.selection=None; self.oracle_trigger=False

    def stage(self,name,inputs,outputs):
        if len(self.stages)>=4 or name in [s['stage'] for s in self.stages]: raise _Rejected('Repeated stage')
        self.stages.append({'stage':name,'input_sha256':memory.sha256(inputs),'output_sha256':memory.sha256(outputs)})

    def witness(self,result,error):
        s=self.local_state; c=self.context
        w={'schema':WITNESS_SCHEMA,'context_sha256':memory.sha256(c),'job_sha256':self.job_sha256,
            'index':self.chain[0],'previous_sha256':self.chain[1],'tick':self.packet['tick'],
            'packet_sha256':memory.sha256(self.packet),'input_memory_sha256':memory.sha256(self.input_state),
            'input_lifecycle':copy.deepcopy(self.input_state['terminal_lifecycle']),
            'local_lifecycle':copy.deepcopy(s['terminal_lifecycle']),'reach':copy.deepcopy(self.reach),
            'trigger':copy.deepcopy(self.trigger),'stages':copy.deepcopy(self.stages),'gold':copy.deepcopy(self.gold),
            'selection':copy.deepcopy(self.selection),'local_memory_sha256':memory.sha256(s),
            'local_decisions_sha256':memory.sha256(self.local_decisions),'result':result,
            'exception':None if error is None else _exception(error)}
        terminal_event_bytes_vnext('memory_transition_witness_vnext',w,sequence=49999,run_id=c['run_id'],episode=0,tick=self.packet['tick'],episode_step=self.packet['tick'])
        return w


def _select_terminal_vnext(builder,state,packet,trigger,previous,current):
    if type(builder) is not _TransitionBuilder: raise _Rejected('Invalid fixed capture')
    c=builder.context; h=memory.sha256(c); p=memory.sha256(packet)
    trigger=memory.validate_trigger(trigger)
    for k in ('id','episode_id','cue_id','before_observation_id','observation_id'): _id(trigger[k])
    builder.trigger=copy.deepcopy(trigger)
    event=c['schedule']['event_tick']
    if (event is None or packet['tick']<event or packet['tick']>c['schedule']['decision_tick'] or trigger['cue_id']!=state['m']['facts'][0]['associations'][0]['cue_id']
            or trigger['before']!=0 or trigger['after']!=1):
        raise _Rejected('Unexpected or wrong-event trigger')
    if builder.reach['cue_event'] is None: raise _Rejected('Trigger lacks reached cue event')
    cfg=state['selector']; oracle=cfg['condition']=='oracle'
    if oracle:
        if state['terminal_lifecycle']['status']!='pending' or builder.chain[0]!=0:
            raise _Rejected('New trigger after selected resource or prior witness')
        builder.oracle_trigger=True
        builder.stage('trigger',{'context_sha256':h,'packet_sha256':p,'detector_sha256':memory.sha256(state['detector']),
            'cue_id':current['id'],'previous_cue_sha256':memory.sha256(previous),'current_cue_sha256':memory.sha256(current)}, {'trigger':trigger})
        resolved_reach=_resolved_reach(builder.binding,builder.reach,trigger)
        inputs={'context_sha256':h,'packet_sha256':p,'trigger_sha256':memory.sha256(trigger),
            'source_m_sha256':c['source_m_sha256'],'source_world_sha256':c['source_world_sha256'],'case_sha256':c['case_sha256'],
            'event_evidence_sha256':memory.sha256(resolved_reach),'before_occupancy':resolved_reach['before_occupancy'],
            'after_occupancy':resolved_reach['after_occupancy']}
        gold=resolve_gold_vnext(builder.binding,resolved_reach,trigger); resource=memory.sha256(gold)
        builder.reach=resolved_reach
        builder.gold=copy.deepcopy(gold)
        builder.stage('resolved',inputs,{'gold_target_ids':gold,'resource_sha256':resource})
        resolved=builder.stages[-1]
        provenance=memory.sha256({'schema':'memory-oracle-resolution-provenance-vnext-v1','context_sha256':h,
            'input_sha256':resolved['input_sha256'],'output_sha256':resolved['output_sha256']})
        install={'context_sha256':h,'selector_before_sha256':memory.sha256(cfg),
            'input_lifecycle':copy.deepcopy(state['terminal_lifecycle']),'resource_sha256':resource,'resolution_provenance_sha256':provenance}
        cfg.update(resource=copy.deepcopy(gold),resource_sha256=resource,provenance_sha256=provenance)
        builder.stage('installed',install,{'selector_after':cfg})
    selected={'context_sha256':h,'packet_sha256':p,'trigger_sha256':memory.sha256(trigger),'live_m_sha256':memory.sha256(state['m']),
        'selector_sha256':memory.sha256(cfg),'u_sha256':memory.sha256(state['u']),
        'resources_sha256':memory.sha256(memory_task.selector_resources(cfg,state['u']))}
    selection=memory_experiment.selection_for_condition(cfg['condition'],state['m'],trigger,limit=cfg['limit'],
        **memory_task.selector_resources(cfg,state['u']))
    selection=memory.validate_selection(selection,state['m'],trigger)
    if len(selection['target_ids'])>1: raise _Rejected('Selection exceeds fixed budget')
    builder.selection=copy.deepcopy(selection)
    if oracle:
        builder.stage('selected',selected,{'selection':selection})
        state['terminal_lifecycle']={'status':'selected','resource_sha256':cfg['resource_sha256'],
            'provenance_sha256':cfg['provenance_sha256'],'selection_sha256':memory.sha256(selection)}
    return selection


def advance_transition_vnext(state4,packet, *, context,oracle_binding,reach,job_sha256,chain):
    """One pure execution; returned local state remains a proposal, never a commit."""
    try:
        c=validate_context_vnext(context); s=validate_terminal_state_vnext(state4,context=c)
        p=copy.deepcopy(packet); decision._validate_packet(p,s); _tick(p['tick'])
        for k in ('id','episode_id','common_goal_id'): _id(p[k])
        for cue in p['cues']: _id(cue['id'])
        memory._digest(job_sha256)
        if type(chain) is not tuple or len(chain)!=2 or type(chain[0]) is not int or chain[0] not in (0,1):
            raise ValueError('Witness index exceeds bounded chain')
        memory._digest(chain[1])
        if chain[0]==0 and chain[1]!=memory.sha256(c): raise ValueError('Wrong initial witness chain')
        if chain[0]==1 and chain[1]==memory.sha256(c): raise ValueError('Missing persisted witness predecessor')
        if s['selector']['condition']=='oracle': _binding_matches(oracle_binding,c,s)
        elif oracle_binding is not None: raise ValueError('Nonoracle received evaluator binding')
        reach=validate_reach_vnext(reach,context=c,subjects=[f['subject_id'] for f in s['m']['facts']])
        cursor=s['cursor']; tick=p['tick']
        if cursor is not None and tick==cursor['tick']:
            if memory.sha256(p)!=cursor['packet_sha256']: raise ValueError('Packet boundary reused with different content')
            return _result('idempotent',proposed_state=s,bearing=cursor['bearing'],input_lifecycle=s['terminal_lifecycle'],
                local_lifecycle=s['terminal_lifecycle'],idempotent=True)
        if not c['schedule']['boundary_tick']<=tick<=c['schedule']['boundary_tick']+900:
            raise ValueError('Packet is outside bounded continuation window')
        if cursor is None or tick!=cursor['tick']+1 or s['supervisor']['continuation_start_tick'] is None:
            raise ValueError('Terminal transition requires armed consecutive continuation')
        if s['supervisor']['phase'] in ('goal','failure'): raise ValueError('Terminal cannot consume further packets')
        expected_count=1 if s['terminal_lifecycle']['status']=='selected' else 0
        if chain[0]!=expected_count:
            raise ValueError('Input Lifecycle contradicts persisted witness count')
    except Exception as error:
        return _result('rejected',error=error)
    builder=_TransitionBuilder(s,p,c,oracle_binding,reach,job_sha256,chain)
    try:
        event=c['schedule']['event_tick']
        if event is not None and event<=tick<=c['schedule']['decision_tick'] and any(x['passability']!='unobserved' for x in p['passages']):
            raise _Rejected('Fresh passage evidence in reached event-to-decision segment')
        if reach['before_occupancy'] is not None or reach['after_occupancy'] is not None:
            raise _Rejected('Input Reach occupancy must be unresolved before detector cut')
        proposed,bearing,decisions=decision._advance_memory_core(s,p,builder)
        emit=builder.oracle_trigger or proposed['supervisor']['phase']=='failure'
        witness=builder.witness('returned',None) if emit else None
        return _result('witnessed-return' if emit else 'ordinary-return',proposed_state=proposed,bearing=bearing,decisions=decisions,
            input_lifecycle=builder.input_state['terminal_lifecycle'],local_lifecycle=proposed['terminal_lifecycle'],witness=witness)
    except Exception as error:
        status='rejected' if isinstance(error,_Rejected) or builder.oracle_trigger and len(builder.stages)<4 else 'raised'
        try: witness=builder.witness('rejected' if status=='rejected' else 'raised',error)
        except Exception as bound_error:
            # No bounded local record exists: serialization/cap refusal is
            # infrastructure without a witness, never a truncated natural error.
            return _result('rejected',error=bound_error)
        return _result(status,input_lifecycle=builder.input_state['terminal_lifecycle'],
            local_lifecycle=builder.local_state['terminal_lifecycle'],witness=witness,error=error)


def _validate_witness_record(body):
    memory._fields(body,_WITNESS_FIELDS)
    if body['schema']!=WITNESS_SCHEMA: raise ValueError('Wrong Witness schema')
    for key in ('context_sha256','job_sha256','previous_sha256','packet_sha256','input_memory_sha256',
                'local_memory_sha256','local_decisions_sha256'):
        memory._digest(body[key])
    _tick(body['tick'])
    if type(body['index']) is not int or body['index'] not in (0,1): raise ValueError('Invalid Witness index')
    if (body['index']==0)!=(body['previous_sha256']==body['context_sha256']):
        raise ValueError('Witness chain identity differs')
    before=_lifecycle(body['input_lifecycle']); after=_lifecycle(body['local_lifecycle'])
    if (before['status']=='not-oracle')!=(after['status']=='not-oracle'):
        raise ValueError('Lifecycle changed condition')
    if before['status']=='selected' and after!=before: raise ValueError('Selected Lifecycle changed')
    if body['index']==1 and before['status']!='selected': raise ValueError('Second witness lacks prior oracle selection')
    memory._enum(body['result'],('returned','raised','rejected'))
    if (body['result']=='returned')!=(body['exception'] is None): raise ValueError('Witness result/exception disagree')
    if body['exception'] is not None:
        memory._fields(body['exception'],'type message')
        for text in body['exception'].values():
            if type(text) is not str or len(text.encode('utf-8'))>512: raise ValueError('Exception text exceeds bound')
    r=body['reach']
    memory._fields(r,'cue_event gate_event intervention_event sensed_event before_occupancy after_occupancy actual_circles')
    refs=[]
    for k in ('cue_event','gate_event','intervention_event','sensed_event'):
        if r[k] is not None: _ref(r[k]); refs.append(r[k])
    if r['sensed_event'] is None or len({x['sequence'] for x in refs})!=len(refs) or len({x['sha256'] for x in refs})!=len(refs):
        raise ValueError('Missing or aliased event reference')
    if any(x['sequence']>=r['sensed_event']['sequence'] for x in refs[:-1]): raise ValueError('Reference is not earlier than sensing')
    _circles(r['actual_circles'])
    memory._list(body['stages'],4)
    names=[]
    for stage in body['stages']:
        memory._fields(stage,'stage input_sha256 output_sha256')
        memory._digest(stage['input_sha256']); memory._digest(stage['output_sha256'])
        names.append(stage['stage'])
    if names!=['trigger','resolved','installed','selected'][:len(names)]: raise ValueError('Invalid ordered stage prefix')
    if names and before['status']!='pending': raise ValueError('Evaluator stages outside first pending oracle trigger')
    if names and body['trigger'] is None: raise ValueError('Stage prefix lacks actual trigger')
    if names and len(names)!=4 and body['result']!='rejected': raise ValueError('Partial evaluator transaction cannot return or raise naturally')
    if body['trigger'] is not None:
        t=memory.validate_trigger(body['trigger']); _tick(t['tick'])
        if t['tick']!=body['tick']: raise ValueError('Trigger is not from this packet tick')
        for k in ('id','episode_id','cue_id','before_observation_id','observation_id'): _id(t[k])
    if (body['gold'] is not None)!=('resolved' in names): raise ValueError('Gold lacks this-transition resolution')
    if body['gold'] is not None:
        memory._list(body['gold'],1)
        for i in body['gold']: _id(i)
        if body['gold']!=sorted(set(body['gold'])): raise ValueError('Noncanonical gold IDs')
    if body['selection'] is not None:
        selection=body['selection']; memory._fields(selection,'event_id target_ids reason')
        memory._enum(selection['reason'],('matched','no_rule','no_match','budget'))
        memory._list(selection['target_ids'],1)
        for i in selection['target_ids']: _id(i)
        if body['trigger'] is None or selection['event_id']!=body['trigger']['id']:
            raise ValueError('Selection lacks actual trigger')
        if selection['target_ids']!=sorted(set(selection['target_ids'])): raise ValueError('Noncanonical selection IDs')
        if selection['target_ids'] and selection['reason'] in ('no_rule','no_match'): raise ValueError('Selection contradicts reason')
    if names and (body['selection'] is not None)!=('selected' in names): raise ValueError('Selection/stage disagree')
    if before['status']!='not-oracle' and not names and body['selection'] is not None:
        raise ValueError('Oracle selection lacks this-transition stages')
    if names and body['stages'][0]['output_sha256']!=memory.sha256({'trigger':body['trigger']}):
        raise ValueError('Trigger output commitment differs')
    if 'resolved' in names:
        resolved=body['stages'][1]
        if resolved['output_sha256']!=memory.sha256({'gold_target_ids':body['gold'],'resource_sha256':memory.sha256(body['gold'])}):
            raise ValueError('Resolution output commitment differs')
    if 'selected' in names:
        provenance=memory.sha256({'schema':'memory-oracle-resolution-provenance-vnext-v1',
            'context_sha256':body['context_sha256'],'input_sha256':resolved['input_sha256'],'output_sha256':resolved['output_sha256']})
        if after['provenance_sha256']!=provenance or body['stages'][3]['output_sha256']!=memory.sha256({'selection':body['selection']}):
            raise ValueError('Selection/provenance commitment differs')
        if after['status']!='selected' or after['resource_sha256']!=memory.sha256(body['gold']) or after['selection_sha256']!=memory.sha256(body['selection']):
            raise ValueError('Selected Lifecycle differs from actual resolution/selection')
    elif after!=before: raise ValueError('Lifecycle changed without selected stage')
    # Occupancy is evaluator output only for an oracle resolution in this
    # transition. Nonoracle local triggers deliberately receive no evaluator.
    maps=(r['before_occupancy'],r['after_occupancy'])
    if body['gold'] is None:
        if maps!=(None,None): raise ValueError('Occupancy without oracle resolution')
    else:
        if type(maps[0]) is not dict or len(maps[0])!=2: raise ValueError('Expected two case subjects')
        for occupancy in maps: _occupancy(occupancy,maps[0])
    memory.canonical_bytes(body)


def _validate_commit_record(body):
    memory._fields(body,'schema context_sha256 witness_sha256 tick memory_sha256 lifecycle')
    if body['schema']!=COMMIT_SCHEMA: raise ValueError('Wrong Commit schema')
    for k in ('context_sha256','witness_sha256','memory_sha256'): memory._digest(body[k])
    _tick(body['tick']); _lifecycle(body['lifecycle'])


def terminal_event_bytes_vnext(kind,body, *, sequence,run_id,episode,tick,episode_step):
    """Exact complete RunWriter event bytes (spaced sorted ASCII JSON + LF).

    This is an encoding/cap check, never a persistence or commit operation.
    Rejected oversize records are not truncated. Event ref hashes use canonical
    decoded complete records separately; these bytes retain the writer format.
    """
    _uuid(run_id)
    if type(episode) is not int or episode!=0:
        raise ValueError('Terminal memory event requires episode zero')
    _tick(tick); _tick(episode_step)
    if tick!=episode_step or type(body) is not dict or body.get('tick')!=tick:
        raise ValueError('Engine counters differ from terminal body tick')
    if type(sequence) is not int or not 0<=sequence<50000: raise ValueError('Invalid event sequence')
    if kind=='memory_transition_witness_vnext':
        _validate_witness_record(body)
        if body['reach']['sensed_event']['sequence']>=sequence:
            raise ValueError('Witness reference must precede its writer event')
        field='witness'; cap=WITNESS_EVENT_MAX_BYTES
    elif kind=='memory_transition_commit_vnext':
        _validate_commit_record(body)
        field='commit'; cap=COMMIT_EVENT_MAX_BYTES
    else: raise ValueError('Unknown terminal event kind')
    memory.canonical_bytes(body)
    event={field:copy.deepcopy(body),'run_id':run_id,'episode':episode,'tick':tick,
        'episode_step':episode_step,'sequence':sequence,'kind':kind}
    data=(json.dumps(event,allow_nan=False,sort_keys=True)+'\n').encode('utf-8')
    if len(data)>cap: raise ValueError('Complete terminal writer event exceeds subcap')
    return data
