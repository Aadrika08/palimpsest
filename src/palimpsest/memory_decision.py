"""One pure categorical supervisor for memory-v2, with a versioned sensor bridge.

Selectors only invalidate beliefs/create deferred requests. The route supervisor
is the single steering owner. It receives no geometry, evaluator gold or pose.
"""
import copy
import math

from . import memory, memory_task
from . import memory_decision_world as world

CueUnavailable = memory_task.CueUnavailable
MAX_LANDMARKS = 64
PHASES = ('acquire','await_decision','commit','follow_route','inspect','retreat','replan','goal','failure')


def capture_symbolic(private_world, pose, occluders, *, episode_id, tick):
    memory._id(episode_id)
    memory._int(tick)
    memory._fields(private_world,'cues landmarks passages common_goal_id')
    memory._id(private_world['common_goal_id'])
    x,y,yaw=memory_task._numbers(pose,3)
    if type(occluders) not in (list,tuple) or len(occluders)>20:
        raise ValueError('Invalid bounded v2 occluders')
    circles=[memory_task._numbers(c,3) for c in occluders]
    if any(c[2]<=0 for c in circles):
        raise ValueError('Occluder radius must be positive')
    memory_task._unique(private_world['cues'],'id',memory.MAX_FACTS)
    landmark_ids=memory_task._unique(private_world['landmarks'],'id',MAX_LANDMARKS)
    memory_task._unique(private_world['passages'],'subject_id',memory.MAX_FACTS)
    if private_world['common_goal_id'] not in landmark_ids:
        raise ValueError('Common goal has no declared landmark')

    def visible(xy):
        px,py=memory_task._numbers(xy,2)
        distance=math.hypot(px-x,py-y)
        if not math.isfinite(distance):
            raise ValueError('Nonfinite v2 displacement')
        # A coincident marker has no bearing direction. Define zero locally;
        # it still must pass the range and circular visibility checks.
        angle=0. if distance==0 else math.remainder(math.atan2(py-y,px-x)-yaw,2*math.pi)
        if distance>4. or abs(angle)>math.pi/2:
            return None
        if any(world._segment_distance([ox,oy],[x,y],[px,py])<=radius for ox,oy,radius in circles):
            return None
        return angle,distance

    packet={'version':2,'id':memory_task._sensor_id(episode_id,tick,'packet'),
            'episode_id':episode_id,'tick':tick,'common_goal_id':private_world['common_goal_id'],
            'cues':[],'landmarks':[],'passages':[],'arrivals':[]}
    for cue in sorted(private_world['cues'],key=lambda c:c['id']):
        memory._fields(cue,'id xy state')
        if type(cue['state']) is not int or cue['state'] not in (0,1):
            raise ValueError('Invalid v2 cue token')
        seen=visible(cue['xy'])
        if seen is not None:
            packet['cues'].append({'id':cue['id'],'state':cue['state'],'bearing_rad':seen[0]})
    seen_landmarks={}
    for landmark in sorted(private_world['landmarks'],key=lambda c:c['id']):
        memory._fields(landmark,'id xy')
        seen=visible(landmark['xy'])
        if seen is not None:
            seen_landmarks[landmark['id']]=seen
            packet['landmarks'].append({'id':landmark['id'],'bearing_rad':seen[0]})
            if seen[1]<=.35:
                packet['arrivals'].append(landmark['id'])
    for passage in sorted(private_world['passages'],key=lambda c:c['subject_id']):
        memory._fields(passage,'subject_id inspection_landmark_id passability')
        memory._enum(passage['passability'],('open','blocked'))
        if passage['inspection_landmark_id'] not in landmark_ids:
            raise ValueError('Passage has no declared inspection landmark')
        seen=seen_landmarks.get(passage['inspection_landmark_id'])
        packet['passages'].append({'id':memory_task._sensor_id(episode_id,tick,'passage',passage['subject_id']),
            'episode_id':episode_id,'tick':tick,'subject_id':passage['subject_id'],
            'passability':passage['passability'] if seen is not None and seen[1]<=.75 else 'unobserved'})
    return packet


def initialize(case, e=None, u=None):
    case = world.validate_case(case)
    state = memory_task.initialize(memory.seed_m(case['facts'],[]),
        {'version':1,'episodes':[]} if e is None else e,
        memory.artifact(method='empty-v1') if u is None else u, 'episode-0')
    graph = world.public_graph(case)
    state.update(version=3, graph=graph,
        selector={'version':1,'condition':'no-U','limit':1,'resource':None,
            'resource_sha256':memory.sha256(None),'provenance_sha256':world.PROFILE_SHA256},
        supervisor={'phase':'acquire','route_id':None,'waypoint_ids':graph['acquisition_ids'].copy(),
            'waypoint_index':0,'waypoint_started_tick':0,'waypoint_deadline_tick':300,
            'inspection_started_tick':None,'inspection_deadline_tick':None,'inspection_subject_id':None,
            'acquired_subject_ids':[],'acquired_evidence':{},'attempts':0,
            'commitment_tick':None,'decision_tick':None,'continuation_start_tick':None,
            'inspection_authorized':False,'failure_reason':None,
            'costs':{'inspections':0,'inspection_ticks':0,'replans':0,'waypoint_arrivals':0}})
    return validate_state(state)


def _validate_graph(graph,m):
    memory._fields(graph,'version routes acquisition_ids decision_landmark_id common_goal_id edges landmark_ids profile_sha256')
    if graph['version'] != 2 or type(graph['version']) is not int or graph['profile_sha256'] != world.PROFILE_SHA256:
        raise ValueError('Unsupported memory-v2 public graph')
    ids = graph['landmark_ids']
    memory._list(ids,MAX_LANDMARKS)
    for item in ids:
        memory._id(item)
    if ids != sorted(set(ids)) or graph['decision_landmark_id'] not in ids or graph['common_goal_id'] not in ids:
        raise ValueError('Invalid graph landmarks')
    if type(graph['routes']) is not list or len(graph['routes']) != 2:
        raise ValueError('Exactly two public routes are required')
    fact_map = {f['id']:f for f in m['facts']}
    route_ids = []
    for route in graph['routes']:
        memory._fields(route,'route_id subject_id fact_id cost inspection_landmark_id waypoint_ids retreat_ids')
        memory._id(route['route_id'])
        route_ids.append(route['route_id'])
        fact = fact_map.get(route['fact_id'])
        if fact is None or fact['subject_id'] != route['subject_id'] or fact['inspection_landmark_id'] != route['inspection_landmark_id']:
            raise ValueError('Route fact mapping differs')
        if type(route['cost']) not in (float,int) or not math.isfinite(route['cost']) or route['cost'] <= 0:
            raise ValueError('Invalid fixed authored route cost')
        for chain in ('waypoint_ids','retreat_ids'):
            memory._list(route[chain],MAX_LANDMARKS)
            if not route[chain] or any(item not in ids for item in route[chain]):
                raise ValueError('Dangling route waypoint')
        if route['waypoint_ids'][0] != route['inspection_landmark_id'] or route['waypoint_ids'][-1] != graph['common_goal_id'] or route['retreat_ids'][-1] != graph['decision_landmark_id']:
            raise ValueError('Public route misses inspection/goal/retreat boundary')
    if route_ids != sorted(set(route_ids)):
        raise ValueError('Routes must have distinct canonical IDs')
    memory._list(graph['acquisition_ids'],MAX_LANDMARKS)
    if not graph['acquisition_ids'] or graph['acquisition_ids'][-1] != graph['decision_landmark_id'] or any(i not in ids for i in graph['acquisition_ids']):
        raise ValueError('Invalid acquisition chain')
    memory._list(graph['edges'],MAX_LANDMARKS)
    seen_edges = set()
    for edge in graph['edges']:
        memory._fields(edge,'id from to direction subject_id role length_m')
        if edge['id'] in seen_edges or edge['from'] not in ids or edge['to'] not in ids or edge['direction']!='forward' or edge['role'] not in ('crossing','retreat') or edge['subject_id'] not in {f['subject_id'] for f in m['facts']}:
            raise ValueError('Invalid public graph edge')
        memory._id(edge['id'])
        seen_edges.add(edge['id'])
        if type(edge['length_m']) not in (float,int) or not math.isfinite(edge['length_m']) or edge['length_m'] <= 0:
            raise ValueError('Invalid public edge length')


def validate_state(state):
    memory._fields(state,'version m e u initial_m episode_id detector cursor requests active last_decisions selector graph supervisor')
    if type(state['version']) is not int or state['version'] != 3:
        raise ValueError('Memory-v2 requires task state version 3')
    memory._bounded(state,memory.MAX_STATE_BYTES+64*1024)
    result = copy.deepcopy(state)
    for key,validator in (('m',memory.validate_m),('initial_m',memory.validate_m),('e',memory.validate_e),('u',memory.validate_u)):
        result[key] = validator(state[key])
    memory._id(state['episode_id'])
    if state['episode_id'] != 'episode-0':
        raise ValueError('Memory-v2 has one bounded episode')
    stable = ('id','subject_id','kind','associations','inspection_landmark_id')
    if [{k:f[k] for k in stable} for f in state['m']['facts']] != [{k:f[k] for k in stable} for f in state['initial_m']['facts']] or any(f['status']!='unknown' or f['estimate'] is not None or f['evidence'] is not None for f in state['initial_m']['facts']):
        raise ValueError('Memory-v2 factual identity/unknown origin differs')
    _validate_graph(state['graph'],state['m'])
    result['selector'] = memory_task.validate_selector(state['selector'],result['m'],result['u'])
    detector,cursor,sup = state['detector'],state['cursor'],state['supervisor']
    memory._fields(detector,'tick cues')
    memory_task._unique(detector['cues'],'id',memory.MAX_FACTS)
    if cursor is None:
        if detector != {'tick':None,'cues':[]} or state['requests'] or state['last_decisions']:
            raise ValueError('Unstarted memory-v2 contains episodic state')
    else:
        memory._fields(cursor,'episode_id tick packet_sha256 common_goal_id bearing')
        memory._int(cursor['tick'])
        memory._digest(cursor['packet_sha256'])
        memory_task._bearing(cursor['bearing'])
        if cursor['episode_id'] != state['episode_id'] or cursor['common_goal_id'] != state['graph']['common_goal_id'] or detector['tick'] != cursor['tick']:
            raise ValueError('Memory-v2 detector/cursor differs')
        for f in state['m']['facts']:
            ev=f['evidence']
            if ev is not None and ev['episode_id']==state['episode_id'] and ev['tick']>cursor['tick']:
                raise ValueError('Future memory-v2 evidence')
        for cue in detector['cues']:
            memory._fields(cue,'id state observation_id')
            if type(cue['state']) is not int or cue['state'] not in (0,1) or cue['observation_id'] != memory_task._sensor_id(state['episode_id'],cursor['tick'],'cue',cue['id']):
                raise ValueError('Invalid retained cue packet')
    if state['active'] is not None:
        raise ValueError('Memory-v2 has a single supervisor, no competing active inspector')
    memory._list(state['requests'],memory.MAX_FACTS)
    requested = set()
    for request in state['requests']:
        memory._fields(request,'event_id fact_id requested_tick')
        memory._id(request['event_id'])
        memory._int(request['requested_tick'])
        if request['fact_id'] not in {f['id'] for f in state['m']['facts']} or request['fact_id'] in requested or cursor is None or request['requested_tick'] > cursor['tick']:
            raise ValueError('Invalid deferred inspection request')
        requested.add(request['fact_id'])
    if state['requests'] != sorted(state['requests'],key=lambda r:(r['requested_tick'],r['fact_id'])):
        raise ValueError('Noncanonical request queue')
    memory._fields(sup,'phase route_id waypoint_ids waypoint_index waypoint_started_tick waypoint_deadline_tick inspection_started_tick inspection_deadline_tick inspection_subject_id acquired_subject_ids acquired_evidence attempts commitment_tick decision_tick continuation_start_tick inspection_authorized failure_reason costs')
    if sup['phase'] not in PHASES or type(sup['attempts']) is not int or not 0<=sup['attempts']<=2 or type(sup['inspection_authorized']) is not bool:
        raise ValueError('Invalid supervisor phase/attempts')
    routes = {r['route_id']:r for r in state['graph']['routes']}
    if sup['route_id'] is not None and sup['route_id'] not in routes:
        raise ValueError('Unknown committed route')
    allowed = [state['graph']['acquisition_ids'],[state['graph']['decision_landmark_id']]]
    if sup['route_id'] is not None:
        allowed += [routes[sup['route_id']]['waypoint_ids'],routes[sup['route_id']]['retreat_ids']]
    if sup['waypoint_ids'] not in allowed or type(sup['waypoint_index']) is not int or not 0<=sup['waypoint_index']<len(sup['waypoint_ids']):
        raise ValueError('Invalid supervisor route cursor')
    for field in ('waypoint_started_tick','waypoint_deadline_tick','inspection_started_tick','inspection_deadline_tick','commitment_tick','decision_tick','continuation_start_tick'):
        if sup[field] is not None:
            memory._int(sup[field])
    if sup['waypoint_deadline_tick'] != sup['waypoint_started_tick']+300:
        raise ValueError('Waypoint deadline differs from frozen budget')
    if (sup['inspection_started_tick'] is None) != (sup['inspection_deadline_tick'] is None) or sup['inspection_started_tick'] is not None and sup['inspection_deadline_tick'] != sup['inspection_started_tick']+150:
        raise ValueError('Inspection deadline differs from frozen budget')
    if (sup['decision_tick'] is None) != (sup['continuation_start_tick'] is None) or sup['decision_tick'] is not None and sup['decision_tick'] != sup['continuation_start_tick']+2:
        raise ValueError('Supervisor schedule differs from acquired boundary')
    if sup['commitment_tick'] is not None and (sup['decision_tick'] is None or sup['commitment_tick'] < sup['decision_tick'] or cursor is None or sup['commitment_tick'] > cursor['tick']):
        raise ValueError('Invalid commitment timestamp')
    subjects={f['subject_id'] for f in state['m']['facts']}
    if sup['acquired_subject_ids'] != sorted(set(sup['acquired_subject_ids'])) or not set(sup['acquired_subject_ids']).issubset(subjects) or set(sup['acquired_evidence']) != set(sup['acquired_subject_ids']):
        raise ValueError('Invalid acquired evidence bank')
    for subject,sample in sup['acquired_evidence'].items():
        memory.validate_observation(sample)
        if sample['subject_id'] != subject or sample['passability']!='open' or sample['episode_id']!=state['episode_id'] or cursor is None or sample['tick']>cursor['tick']:
            raise ValueError('Acquisition requires real current-episode open samples')
    if sup['phase']!='acquire' and sup['phase']!='failure' and set(sup['acquired_subject_ids'])!=subjects:
        raise ValueError('Incomplete acquired memory-v2 prefix')
    route=routes.get(sup['route_id'])
    phase=sup['phase']
    if phase in ('acquire','await_decision') and (route is not None or sup['attempts']!=0 or sup['inspection_authorized']):
        raise ValueError('Prefix/decision boundary cannot contain a route commitment')
    if phase=='acquire' and sup['waypoint_ids']!=state['graph']['acquisition_ids'] or phase=='await_decision' and sup['waypoint_ids']!=[state['graph']['decision_landmark_id']]:
        raise ValueError('Prefix phase differs from its public chain')
    if phase in ('follow_route','retreat','goal') and (route is None or not sup['attempts'] or sup['commitment_tick'] is None):
        raise ValueError('Travel phase requires its recorded route commitment')
    if phase in ('follow_route','goal') and sup['waypoint_ids']!=route['waypoint_ids'] or phase=='retreat' and sup['waypoint_ids']!=route['retreat_ids']:
        raise ValueError('Supervisor phase and chosen public chain differ')
    if sup['inspection_authorized']:
        if route is None or sup['waypoint_ids']!=route['waypoint_ids'] or sup['waypoint_index']==0 or phase not in ('follow_route','goal','failure'):
            raise ValueError('Crossing authorization requires the chosen completed inspection')
        fact=next(f for f in state['m']['facts'] if f['id']==route['fact_id'])
        if (fact['status']!='observed' or fact['estimate']!='open' or fact['evidence']['episode_id']!=state['episode_id'] or
                fact['evidence']['tick']<sup['commitment_tick']):
            raise ValueError('Crossing authorization requires post-commit real open evidence')
    elif phase in ('follow_route','goal') and sup['waypoint_index']>0:
        raise ValueError('Crossing cannot skip the chosen route inspection')
    if phase=='inspect':
        if sup['inspection_started_tick'] is None or sup['inspection_subject_id'] is None:
            raise ValueError('Inspection phase lacks its bounded owned inspector')
        expected_subject=next((r['subject_id'] for r in state['graph']['routes'] if r['inspection_landmark_id']==sup['waypoint_ids'][sup['waypoint_index']]),None)
        if expected_subject!=sup['inspection_subject_id'] or route is not None and expected_subject!=route['subject_id']:
            raise ValueError('Inspector does not own the current selected route marker')
    elif phase!='failure' and sup['inspection_started_tick'] is not None:
        raise ValueError('Noninspection phase retains a competing inspector')
    if phase=='goal' and sup['waypoint_ids'][sup['waypoint_index']]!=state['graph']['common_goal_id']:
        raise ValueError('Goal phase requires the common-goal stage')
    if sup['inspection_subject_id'] is not None and sup['inspection_subject_id'] not in subjects:
        raise ValueError('Unknown inspection subject')
    if (sup['phase']=='failure') != (sup['failure_reason'] is not None):
        raise ValueError('Invalid terminal failure reason')
    memory._fields(sup['costs'],'inspections inspection_ticks replans waypoint_arrivals')
    for value in sup['costs'].values():
        memory._int(value)
    memory._list(state['last_decisions'],64)
    memory._bounded(state['last_decisions'],64*1024)
    return result


def acquired_boundary(state):
    state=validate_state(state)
    s=state['supervisor']
    return s['phase']=='await_decision' and s['decision_tick'] is None and all(
        f['status']=='observed' and f['estimate']=='open' and f['evidence']['episode_id']==state['episode_id'] for f in state['m']['facts'])


def configure_selector(state,config,u=None):
    state=validate_state(state)
    if not acquired_boundary(state):
        raise ValueError('Selector replacement requires the unarmed acquired boundary')
    state['u']=state['u'] if u is None else memory.validate_u(u)
    state['selector']=memory_task.validate_selector(config,state['m'],state['u'])
    return validate_state(state)


def arm(state,boundary_tick):
    state=validate_state(state)
    memory._int(boundary_tick)
    if not acquired_boundary(state) or state['cursor']['tick'] != boundary_tick-1:
        raise ValueError('Decision arm requires explicit acquired paused boundary')
    state['supervisor'].update(continuation_start_tick=boundary_tick,decision_tick=boundary_tick+2)
    return validate_state(state)


def _transition(sup,phase,tick,audit,reason=None):
    previous=sup['phase']
    sup['phase']=phase
    audit.append({'kind':'memory_transition','tick':tick,'from':previous,'to':phase,
                  'reason':reason,'route_id':sup['route_id'],'waypoint_index':sup['waypoint_index']})


def _fail(sup,reason,tick,audit):
    sup['failure_reason']=reason
    _transition(sup,'failure',tick,audit,reason)


def _chain(sup,ids,tick):
    sup.update(waypoint_ids=ids.copy(),waypoint_index=0,waypoint_started_tick=tick,waypoint_deadline_tick=tick+300)


def _choose(state,tick,audit):
    sup=state['supervisor']
    facts={f['id']:f for f in state['m']['facts']}
    inputs=[]
    candidates=[]
    for route in state['graph']['routes']:
        fact=facts[route['fact_id']]
        category='blocked' if fact['status']=='observed' and fact['estimate']=='blocked' else 'open' if fact['status']=='observed' and fact['estimate']=='open' else 'uncertain'
        inputs.append({'route_id':route['route_id'],'fact_id':fact['id'],'estimate':fact['estimate'],
                       'status':fact['status'],'evidence':copy.deepcopy(fact['evidence']), 'category':category,'cost':route['cost']})
        if category!='blocked':
            candidates.append((category!='open',route['cost'],route['route_id'],route))
    if not candidates:
        _fail(sup,'no_route',tick,audit)
        return
    if sup['attempts']>=2:
        _fail(sup,'attempt_limit',tick,audit)
        return
    route=min(candidates,key=lambda item:item[:3])[3]
    sup.update(route_id=route['route_id'],attempts=sup['attempts']+1,
        commitment_tick=tick,inspection_authorized=False,
        inspection_started_tick=None,inspection_deadline_tick=None,inspection_subject_id=None)
    _chain(sup,route['waypoint_ids'],tick)
    audit.append({'kind':'memory_commitment','tick':tick,'route_id':route['route_id'],
                  'subject_id':route['subject_id'],'inputs':inputs,'attempt':sup['attempts'],
                  'policy':'exclude-observed-blocked-prefer-observed-open-cost-lexical-v2'})
    _transition(sup,'follow_route',tick,audit)


def _validate_packet(packet,state):
    memory._fields(packet,'version id episode_id tick common_goal_id cues landmarks passages arrivals')
    if type(packet['version']) is not int or packet['version']!=2:
        raise ValueError('Memory-v2 requires packet version 2')
    old={k:v for k,v in packet.items() if k!='arrivals'}
    old['version']=1
    memory_task._validate_packet(old,state)
    if len(packet['landmarks'])>MAX_LANDMARKS:
        raise ValueError('Too many visible landmarks')
    memory._list(packet['arrivals'],MAX_LANDMARKS)
    visible={item['id'] for item in packet['landmarks']}
    graph_ids=set(state['graph']['landmark_ids'])
    if not visible.issubset(graph_ids) or packet['arrivals']!=sorted(set(packet['arrivals'])) or not set(packet['arrivals']).issubset(visible):
        raise ValueError('Arrival must identify a current visible public landmark')
    if packet['common_goal_id']!=state['graph']['common_goal_id']:
        raise ValueError('Common goal differs from public graph')


def advance_memory(state,packet):
    state=validate_state(state)
    _validate_packet(packet,state)
    tick,digest=packet['tick'],memory.sha256(packet)
    cursor=state['cursor']
    if cursor is not None and tick==cursor['tick']:
        if digest!=cursor['packet_sha256']:
            raise ValueError('Packet boundary reused with different content')
        return state,cursor['bearing'].copy(),[]
    if tick!=(0 if cursor is None else cursor['tick']+1):
        raise ValueError('Memory-v2 requires consecutive packets')
    sup=state['supervisor']
    if sup['phase'] in ('goal','failure'):
        raise ValueError('Terminal memory-v2 cannot consume further packets')
    audit=[]
    previous={c['id']:c for c in state['detector']['cues']}
    if state['detector']['tick']==tick-1:
        from .memory_experiment import selection_for_condition
        for cue in sorted(packet['cues'],key=lambda c:c['id']):
            before=previous.get(cue['id'])
            if before is not None and before['state']!=cue['state']:
                trigger={'id':memory_task._sensor_id(state['episode_id'],tick,'trigger',cue['id']),
                    'episode_id':state['episode_id'],'tick':tick,'kind':'cue_changed','cue_id':cue['id'],
                    'before':before['state'],'after':cue['state'],'before_observation_id':before['observation_id'],
                    'observation_id':memory_task._sensor_id(state['episode_id'],tick,'cue',cue['id'])}
                cfg=state['selector']
                selection=selection_for_condition(cfg['condition'],state['m'],trigger,limit=cfg['limit'],
                    **memory_task.selector_resources(cfg,state['u']))
                state['m'],revisions,requests=memory.revise(state['m'],trigger,selection,[],episode_id=state['episode_id'],tick=tick)
                audit += [{'kind':'memory_trigger','tick':tick,'trigger':trigger},{'kind':'memory_selection','tick':tick,'selection':selection}]
                audit += [{'kind':'memory_revision','tick':tick,'revision':item} for item in revisions]
                pending={r['fact_id'] for r in state['requests']}
                state['requests'] += [r for r in requests if r['fact_id'] not in pending]
    state['m'],revisions,_=memory.revise(state['m'],None,{'event_id':None,'target_ids':[],'reason':'no_rule'},packet['passages'],episode_id=state['episode_id'],tick=tick)
    audit += [{'kind':'memory_revision','tick':tick,'revision':item} for item in revisions]
    fresh={p['subject_id']:p for p in packet['passages'] if p['passability']!='unobserved'}
    facts={f['id']:f for f in state['m']['facts']}
    state['requests']=sorted([r for r in state['requests'] if facts[r['fact_id']]['subject_id'] not in fresh],key=lambda r:(r['requested_tick'],r['fact_id']))
    if sup['phase']=='acquire':
        for subject,sample in fresh.items():
            if sample['passability']=='open' and subject not in sup['acquired_evidence']:
                sup['acquired_evidence'][subject]=copy.deepcopy(sample)
        sup['acquired_subject_ids']=sorted(sup['acquired_evidence'])
    if sup['continuation_start_tick'] is not None and tick>=sup['continuation_start_tick']+900:
        _fail(sup,'continuation_timeout',tick,audit)
    elif sup['phase']=='acquire' and tick>=1200:
        _fail(sup,'acquisition_timeout',tick,audit)
    elif sup['phase'] not in ('await_decision','inspect') and tick>=sup['waypoint_deadline_tick']:
        _fail(sup,'waypoint_timeout',tick,audit)
    if sup['phase']=='await_decision' and sup['decision_tick'] is not None and tick>=sup['decision_tick']:
        _transition(sup,'commit',tick,audit)
        _choose(state,tick,audit)
    if sup['phase'] in ('acquire','follow_route','retreat'):
        target=sup['waypoint_ids'][sup['waypoint_index']]
        if target in packet['arrivals']:
            sup['costs']['waypoint_arrivals']+=1
            route=next((r for r in state['graph']['routes'] if r['route_id']==sup['route_id']),None)
            inspection=next((r for r in state['graph']['routes'] if r['inspection_landmark_id']==target),None)
            if sup['phase']=='acquire' and inspection is not None or sup['phase']=='follow_route' and route is not None and target==route['inspection_landmark_id']:
                sup.update(inspection_started_tick=tick,inspection_deadline_tick=tick+150,
                           inspection_subject_id=inspection['subject_id'])
                sup['costs']['inspections']+=1
                _transition(sup,'inspect',tick,audit,'required-passage-sample')
            elif sup['waypoint_index']+1<len(sup['waypoint_ids']):
                sup.update(waypoint_index=sup['waypoint_index']+1,waypoint_started_tick=tick,waypoint_deadline_tick=tick+300)
            elif sup['phase']=='acquire':
                if len(sup['acquired_subject_ids'])==2 and all(f['status']=='observed' and f['estimate']=='open' for f in state['m']['facts']):
                    _chain(sup,[state['graph']['decision_landmark_id']],tick)
                    _transition(sup,'await_decision',tick,audit,'both-real-open-samples-returned')
                else:
                    _fail(sup,'acquisition_incomplete',tick,audit)
            elif sup['phase']=='retreat':
                sup['costs']['replans']+=1
                _transition(sup,'replan',tick,audit)
                _choose(state,tick,audit)
    if sup['phase']=='inspect':
        sup['costs']['inspection_ticks']+=1
        sample=fresh.get(sup['inspection_subject_id'])
        if sample is not None:
            audit.append({'kind':'memory_inspection','tick':tick,'subject_id':sup['inspection_subject_id'],
                          'passability':sample['passability'],'observation_id':sample['id']})
            acquisition=sup['route_id'] is None
            if acquisition and sample['passability']!='open':
                _fail(sup,'acquisition_blocked',tick,audit)
            elif not acquisition and sample['passability']=='blocked':
                route=next(r for r in state['graph']['routes'] if r['route_id']==sup['route_id'])
                _chain(sup,route['retreat_ids'],tick)
                _transition(sup,'retreat',tick,audit,'observed-blocked')
            else:
                sup['inspection_authorized']=not acquisition
                sup.update(waypoint_index=sup['waypoint_index']+1,waypoint_started_tick=tick,waypoint_deadline_tick=tick+300)
                _transition(sup,'acquire' if acquisition else 'follow_route',tick,audit,'observed-open')
            sup.update(inspection_started_tick=None,inspection_deadline_tick=None,inspection_subject_id=None)
        elif tick>=sup['inspection_deadline_tick']:
            _fail(sup,'inspection_timeout',tick,audit)
    target=sup['waypoint_ids'][sup['waypoint_index']]
    landmarks={item['id']:item['bearing_rad'] for item in packet['landmarks']}
    # A terminal failure does not ask for a new motor cue; retain the already
    # declared cue for recording without stepping physics in the Engine.
    if sup['phase']=='failure':
        bearing=[1.,0.] if cursor is None else cursor['bearing'].copy()
    else:
        if target not in landmarks:
            raise CueUnavailable('selected_waypoint_unavailable: '+target)
        angle=landmarks[target]
        bearing=[math.cos(angle),math.sin(angle)]
        audit.append({'kind':'memory_bridge','tick':tick,'landmark_id':target,'bearing':bearing.copy(),'phase':sup['phase']})
    state['detector']={'tick':tick,'cues':[{'id':c['id'],'state':c['state'],
        'observation_id':memory_task._sensor_id(state['episode_id'],tick,'cue',c['id'])} for c in sorted(packet['cues'],key=lambda c:c['id'])]}
    state['cursor']={'episode_id':state['episode_id'],'tick':tick,'packet_sha256':digest,
        'common_goal_id':packet['common_goal_id'],'bearing':bearing.copy()}
    state['last_decisions']=(state['last_decisions']+copy.deepcopy(audit))[-64:]
    return validate_state(state),bearing,audit


def goal_allowed(state):
    state=validate_state(state)
    s=state['supervisor']
    return s['phase']=='follow_route' and s['inspection_authorized'] and s['waypoint_ids'][s['waypoint_index']]==state['graph']['common_goal_id']


def mark_goal(state):
    state=validate_state(state)
    if not goal_allowed(state):
        raise ValueError('Goal requires the chosen route real open inspection and goal stage')
    state['supervisor']['phase']='goal'
    return validate_state(state)


def inspect(state):
    state=validate_state(state)
    return {'version':3,'episode_id':state['episode_id'],'supervisor':copy.deepcopy(state['supervisor']),
        'facts':state['m']['facts'],'requests':state['requests'],
        'hashes':{k:memory.sha256(state[k]) for k in ('m','e','u','selector','graph')},
        'selector':{k:v for k,v in state['selector'].items() if k!='resource'}}


def invariant_hashes(snapshot):
    """Exclude only declared selector/U and destination recorder identities."""
    from .snapshots import SNAPSHOT_KEYS,state_digest
    if type(snapshot) is not dict or set(snapshot)!=SNAPSHOT_KEYS:
        raise ValueError('Incomplete memory-v2 snapshot')
    app=copy.deepcopy(snapshot['application'])
    state=validate_state(app['memory'])
    state.pop('u')
    state.pop('selector')
    app.pop('source_run_id')
    app.pop('event_prefix')
    app['memory']=state
    return {**{key:state_digest(value) for key,value in snapshot.items() if key!='application'},
            'application':state_digest(app)}
