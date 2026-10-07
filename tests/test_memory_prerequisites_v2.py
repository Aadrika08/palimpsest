"""Campaign gates on fresh completed-owner doubles; no native/retained decode."""
import importlib
import importlib.util
import copy
import json
import os
from pathlib import Path
import sys
import time
from contextlib import nullcontext

import numpy as np
import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_restore_offline_readout as o
from palimpsest import memory_decision_world as world
from palimpsest.snapshots import save_snapshot
from palimpsest.storage import StorageBudget, StorageLimits


def campaign():
    assert importlib.util.find_spec('scripts.memory_prerequisites_v2'), 'Eight-cell campaign missing'
    return importlib.import_module('scripts.memory_prerequisites_v2')


def test_unknown_registration_cannot_allocate():
    with pytest.raises(ValueError, match='registration'):
        campaign().validate_registration({'mode':'qualify'})


def setup_campaign(tmp_path, monkeypatch):
    m = campaign(); repo = tmp_path/'repo'; (repo/'scripts').mkdir(parents=True)
    module = repo/'scripts/memory_prerequisites_v2.py'; module.write_text('fixture campaign\n')
    monkeypatch.setattr(m, '__file__', str(module))
    worker = repo/'scripts/memory_decision_pilot.py'; worker.write_text('fixture unchanged worker\n')
    monkeypatch.setattr(p, '__file__', str(worker))
    legacy = repo/'scripts/memory_restore_diagnostic.py'; legacy.write_text('fixture unchanged legacy\n')
    monkeypatch.setattr(d, '__file__', str(legacy))
    evidence = repo/'docs/reports/memory-prerequisites-v2-evidence'; evidence.mkdir(parents=True)
    shared = repo/'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py'
    shared.parent.mkdir(parents=True); shared.write_text('fixture shared launcher\n')
    contract = repo/'docs/plans/memory-prerequisites-v2.md'; contract.parent.mkdir(parents=True)
    contract.write_text('fixture reviewed scope\n')
    old = repo/'old'; old.mkdir(); (old/'immutable').write_text('historical bytes\n')
    reg = {'schema':'memory-prerequisites-registration-v2', 'mode':'prerequisites-v2',
        'repo':str(repo), 'assets':str(repo/'assets'), 'history_root':str(repo/'histories'),
        'output':str(repo/'runs/memory-prerequisites-v2-fixture'), 'source_identity':{},
        'seconds_caps':[4300,600], 'state_contract':'restore-reproducibility-v2-candidate',
        'profile_sha256':d.PROFILE, 'protocol_sha256':p.TRAVEL_PROTOCOL_SHA256,
        'expected_specs':p.travel_specs('travel-feasibility',d.PROFILE),
        'source_derivation':{'job_id':'south-prefix','operation':'prefix','repeat_job_ids':['restore-1','restore-2']},
        'native_invocations':1, 'native_owners_max':8, 'corrective_studies':0,
        'preparation_seconds_cap':180, 'implementation_commit':'0'*40,
        'control_root':str(repo/'.superpowers/sdd/memory-prerequisites-v2'),
        'publication_root':str(evidence), 'python':sys.executable, 'runtime':d.runtime_v2_identity(),
        'contract':str(contract), 'contract_sha256':p.file_hash(contract),
        'diagnostic_driver_sha256':p.file_hash(legacy), 'history_inputs':{},
        'prior_output':str(old), 'prior_inventory':p.hash_ledger(old),
        'preserved_sets':[{'root':str(old),'files':p.hash_ledger(old)}], 'protected_roots':[str(old)]}
    reg['expected_cases'] = [world.make_case(s['seed'],s['regime'],s['kind'],s['mirrored'],
        profile_sha256=d.PROFILE) for s in reg['expected_specs']]
    for name, path in {'driver':module, 'auditor':module,
            'comparator':repo/'scripts/memory_restore_offline_readout.py',
            'launcher':evidence/'execute-campaign.py', 'registration_preparer':evidence/'register.py',
            'shared_launcher':shared}.items():
        if not path.exists(): path.write_text('fixture '+name+'\n')
        reg[name+'_path'] = str(path); reg[name+'_sha256'] = p.file_hash(path)
    path = evidence/'registration.json'; path.write_text(json.dumps(reg))
    control = Path(reg['control_root']); control.mkdir(parents=True)
    (control/'launched.json').write_text(json.dumps({'started_monotonic':time.monotonic(),
        'registration_sha256':p.file_hash(path)}))
    monkeypatch.setattr(p, 'source_identity', lambda *args: {})
    monkeypatch.setattr(m.subprocess, 'check_output', lambda command, **kw:
        '0'*40+'\n' if 'rev-parse' in command else b'')
    monkeypatch.setattr(StorageBudget, 'lock', lambda self:nullcontext())
    root = Path(reg['output'])
    # /tmp is a small tmpfs: only fixture free-space admission is relaxed.
    monkeypatch.setattr(m, 'budget', lambda reg:StorageBudget(
        [reg[key] for key in ('output','control_root','publication_root')],
        StorageLimits(max_bytes=8*p.GiB,min_free_bytes=0,max_runs=38,max_snapshots=1),
        headroom_bytes=64*p.MiB))
    def preflight(*args, **kw):
        return {**{key:reg[key] for key in ('repo','assets','history_root','source_identity')},
            'output':str(root/'stage'), 'phase_root':str(root), 'geometry_valid':True}
    monkeypatch.setattr(p, 'preflight', preflight)
    native = b'\0'*120+b'non-timing native fields'
    initial = {'integration':np.array([1.,2.]), 'native_data':native,
        'native_sha256':p.hashlib.sha256(native).hexdigest(), 'application':{
            'source_run_id':'source', 'event_prefix':{}, 'memory':{'u':{}, 'selector':{},
                'm':{'facts':[]}, 'supervisor':{'phase':'await_decision'}},
            'receipts':{'old':{'received_run_id':'source','applied_tick':1}}}}
    launched = []; raw_rows = {}
    def launch(stage, spec, plan, storage, deadline, *, source, retain_repeat_state):
        assert stage == 'travel-feasibility' and spec['id'] not in launched
        assert retain_repeat_state is (spec['operation']=='repeat')
        job = p.make_job(stage,spec,plan,spec['operation'],source=source)
        job = p.validate_job(job)
        run = Path(job['output']); (run/'snapshots').mkdir(parents=True)
        state = copy.deepcopy(initial)
        if source is not None:
            state = d.read_snapshot(source['snapshot_path'])
        save_snapshot(state,run/'snapshots/initial.snp')
        owner = {'run_id':job['run_id'],'pid':9000+len(launched),'pgid':9000+len(launched),'starttime':1}
        (run/'owner.json').write_text(json.dumps(owner))
        (root/'stage/jobs').mkdir(exist_ok=True)
        (root/'stage/jobs'/(job['run_id']+'.json')).write_text(json.dumps(job))
        supervision = root/'stage/supervision'/job['run_id']; supervision.mkdir(parents=True)
        _, outer = p.owner_allocation(stage,spec['operation'],p.TRAVEL_PROTOCOL_SHA256)
        supervised = {'status':'completed','returncode':0,'timeout_seconds':outer,
            'output':str(supervision),'elapsed_seconds':1.}
        (supervision/'supervisor.json').write_text(json.dumps(supervised))
        rows = [{'tick':i,'action':np.array([.1,0.],dtype=np.float32)} for i in range(5)]
        raw_rows[str(run)] = rows
        report = {'job_id':spec['id'],'run_id':job['run_id'],'run':str(run),'status':'recorded',
            'raw_audit_pass':True,'invariants_preserved':True,'acquired':True,'goal':True,
            'retreat_completed':True,'first_commitment_blocked':True,'replans':1,
            'continuation_ticks':5,'trace_digest':p.trace_digest(rows),'wall_seconds':1.,
            'snapshot_path':str(run/'snapshots/initial.snp'),
            'snapshot_sha256':p.file_hash(run/'snapshots/initial.snp'),
            'invariant':p.condition_digest(state),'supervision':supervised}
        if retain_repeat_state:
            post = copy.deepcopy(state)
            post['native_data'] = bytes([len(launched)])*120+native[120:]
            post['native_sha256'] = p.hashlib.sha256(post['native_data']).hexdigest()
            report.update(p.publish_repeat_state(post,{'old'},run,storage))
        (run/'worker-report.json').write_text(json.dumps(report)); launched.append(spec['id'])
        return report
    monkeypatch.setattr(p, 'launch_owner', launch)
    monkeypatch.setattr(p, 'audit_run', lambda job,*args:p.read_json(Path(job['output'])/'worker-report.json'))
    monkeypatch.setattr(p, 'read_raw', lambda run,*args:{'rows':raw_rows[str(run)]})
    monkeypatch.setattr(d, 'owner_exited', lambda owner:True)
    monkeypatch.setattr(d, 'cleanup_owners', lambda root:[{'path':str(path),'owner':p.read_json(path),
        'status':'already-exited'} for path in sorted(root.rglob('owner.json'))])
    # Only trusted-native duration probing is doubled. The real candidate reader
    # verifies raw SHA, projects 120 bytes and compares all other typed state.
    monkeypatch.setattr(o, 'attribute_native_pair', lambda *args:{'sides':[
        {'timer_fields':[{'start_offset':i*8,'end_offset_exclusive':i*8+8,'duration':float(i)}
                         for i in range(15)]} for _ in range(2)]})
    return m,path,root,reg,launched,raw_rows


def test_all_eight_fresh_cells_close_only_after_independent_recomputation(tmp_path,monkeypatch):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    assert m.run(path) == 0
    assert launched == ['south-no-event','south-change','north-no-event','north-change',
                        'south-prefix','north-prefix','restore-1','restore-2']
    before = p.read_json(root/'execution.json')
    assert before['native_prerequisites_passed'] is False
    assert before['restore_pair_matches'] is False
    assert before['candidate_restore_pair_matches'] is True
    assert not (root/'scientific-close.json').exists()
    assert m.audit(path) == 0
    close = p.read_json(root/'scientific-close.json')
    assert close['native_prerequisites_passed'] is True
    assert close['qualification_claims'] == [] and close['r2_complete'] is False
    assert close['paired_pilot'] == 'unattempted-by-scope' and close['held_out_used'] is False
    assert len(close['owners']) == len(close['allocated_jobs']) == len(close['started_owners']) == 8
    assert p.read_json(root/'execution.json') == before
    with pytest.raises(FileExistsError): m.audit(path)


def test_first_failed_mandatory_cell_stops_later_owners_and_retains_started(tmp_path,monkeypatch):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    launch = p.launch_owner
    def failed(*args,**kwargs):
        report = launch(*args,**kwargs)
        report['goal'] = False
        Path(report['run'],'worker-report.json').write_text(json.dumps(report))
        return report
    monkeypatch.setattr(p,'launch_owner',failed)
    assert m.run(path) == 1 and launched == ['south-no-event']
    receipt = p.read_json(root/'execution.json')
    assert len(receipt['owners']) == 1 and len(receipt['unattempted']) == 7
    assert m.audit(path) == 1
    close = p.read_json(root/'scientific-close.json')
    assert close['native_prerequisites_passed'] is False
    assert len(close['allocated_jobs']) == len(close['started_owners']) == 1


@pytest.mark.parametrize('component',['python','numpy','mujoco','torch'])
def test_self_consistent_unapproved_runtime_refuses_before_allocation(tmp_path,monkeypatch,component):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    actual = copy.deepcopy(reg['runtime'])
    if component == 'python': actual['python_version'][:2] = [3,12]
    else: actual['versions'][component] = {'numpy':'2.2.6','mujoco':'3.3.7','torch':'2.9.1'}[component]
    reg['runtime'] = actual
    path.write_text(json.dumps(reg))
    monkeypatch.setattr(d,'runtime_v2_identity',lambda:copy.deepcopy(actual))
    with pytest.raises(ValueError,match='runtime'): m.run(path)
    assert launched == [] and not root.exists()


@pytest.mark.parametrize('failure',['missing-post','corrupt-post','invariant','tick-count'])
def test_first_restore_failure_prohibits_second_restore_owner(tmp_path,monkeypatch,failure):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    launch = p.launch_owner
    def fail_first_restore(*args,**kwargs):
        result = launch(*args,**kwargs)
        if result['job_id'] == 'restore-1':
            if failure == 'missing-post': Path(result['post_snapshot_path']).unlink()
            elif failure == 'corrupt-post': Path(result['post_snapshot_path']).write_bytes(b'corrupt')
            elif failure == 'invariant': result['invariants_preserved'] = False
            else: result['continuation_ticks'] = 4
            Path(result['run'],'worker-report.json').write_text(json.dumps(result))
        return result
    monkeypatch.setattr(p,'launch_owner',fail_first_restore)
    assert m.run(path) == 1
    assert launched == ['south-no-event','south-change','north-no-event','north-change',
                        'south-prefix','north-prefix','restore-1']
    receipt = p.read_json(root/'execution.json')
    assert receipt['unattempted'] == ['restore-2']
    assert receipt['native_prerequisites_passed'] is False
    assert receipt['error']
    assert len(list((root/'stage/jobs').glob('*.json'))) == 7


@pytest.mark.parametrize('change',['schema','spec-order','case','output-overlap','pin','runtime'])
def test_changed_campaign_contract_refuses_before_output_or_owner(tmp_path,monkeypatch,change):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    if change == 'schema': reg['schema'] = 'memory-restore-registration-v2'
    elif change == 'spec-order': reg['expected_specs'][0],reg['expected_specs'][1] = reg['expected_specs'][1],reg['expected_specs'][0]
    elif change == 'case': reg['expected_cases'][0]['seed'] += 1
    elif change == 'output-overlap': reg['protected_roots'].append(str(root))
    elif change == 'pin': Path(reg['comparator_path']).write_text('changed comparator\n')
    else: reg['runtime']['environment']['OMP_NUM_THREADS'] = '2'
    path.write_text(json.dumps(reg))
    with pytest.raises(ValueError): m.run(path)
    assert launched == [] and not root.exists()


def test_aggregate_owner_reservation_refusal_prevents_third_allocation(tmp_path,monkeypatch):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    storage = m.budget(reg); check = storage.check; reserved = []
    def admit(additional,*,path):
        if additional == 548*p.MiB:
            reserved.append(True)
            if len(reserved) == 3: raise OSError('aggregate reservation refusal fixture')
        return check(additional,path=path)
    monkeypatch.setattr(storage,'check',admit)
    monkeypatch.setattr(m,'budget',lambda reg:storage)
    assert m.run(path) == 1 and launched == ['south-no-event','south-change']
    assert len(p.read_json(root/'execution.json')['owners']) == 2
    assert len(list((root/'stage/jobs').glob('*.json'))) == 2


@pytest.mark.parametrize('failure',['namespace','extra-job','active-owner','raw-count','trace','invariant',
    'non-timing-state','fresh-source','supervision','internal-cap','initial-checksum','post-checksum',
    'changed-history','changed-raw','expired-readout','late-close','storage-close','failed-invalidation'])
def test_independent_failure_never_leaves_campaign_authority(tmp_path,monkeypatch,failure):
    m,path,root,reg,launched,rows = setup_campaign(tmp_path,monkeypatch)
    assert m.run(path) == 0
    receipt = p.read_json(root/'execution.json')
    second = receipt['attempted'][-1]
    if failure == 'namespace':
        receipt['process_namespace'] = 'pid:[different]'
        monkeypatch.setattr(d,'owner_exited',lambda owner:pytest.fail('PID observation in another namespace'))
    elif failure == 'extra-job':
        job = next((root/'stage/jobs').glob('*.json')); (job.parent/('f'*32+'.json')).write_bytes(job.read_bytes())
    elif failure == 'active-owner': monkeypatch.setattr(d,'owner_exited',lambda owner:False)
    elif failure == 'raw-count': rows[second['run']].pop()
    elif failure == 'trace': rows[second['run']][0]['action'][0] = .25
    elif failure in ('invariant','internal-cap'):
        report = Path(second['run'])/'worker-report.json'; value = p.read_json(report)
        value['invariants_preserved' if failure == 'invariant' else 'wall_seconds'] = False if failure == 'invariant' else 151.
        report.write_text(json.dumps(value))
    elif failure == 'non-timing-state':
        post = d.read_snapshot(second['post_snapshot_path']); post['integration'][0] += 1
        # Regenerate fixture checksums and components coherently: the candidate
        # must still reject a genuine non-timing state difference.
        Path(second['post_snapshot_path']).unlink()
        retained = p.publish_repeat_state(post,{'old'},Path(second['run']),m.budget(reg))
        second.update(retained)
        report = Path(second['run'])/'worker-report.json'; report.write_text(json.dumps(second))
        comparison = d.compare_states(d.read_snapshot(receipt['attempted'][-2]['post_snapshot_path']),post,{'old'},{'old'})
        receipt['comparison'] = comparison
        receipt['candidate_comparison'] = o.compare_reproducibility_states(
            d.read_snapshot(receipt['attempted'][-2]['post_snapshot_path']),post,{'old'},{'old'})
    elif failure == 'fresh-source':
        source = p.read_json(root/'fresh-source.json'); source['source_job_id'] = 'historical-prefix'
        (root/'fresh-source.json').write_text(json.dumps(source))
    elif failure == 'supervision':
        supervision = root/'stage/supervision'/second['run_id']/'supervisor.json'
        value = p.read_json(supervision); value['returncode'] = 1; supervision.write_text(json.dumps(value))
    elif failure == 'initial-checksum': (Path(second['run'])/'snapshots/initial.snp').write_bytes(b'corrupt')
    elif failure == 'post-checksum': Path(second['post_snapshot_path']).write_bytes(b'corrupt')
    elif failure == 'changed-history': (Path(reg['prior_output'])/'immutable').write_text('changed historical bytes\n')
    elif failure == 'changed-raw':
        compare = o.compare_reproducibility_states
        def mutate(*args):
            report = Path(second['run'])/'worker-report.json'; report.write_text(report.read_text()+'\n')
            return compare(*args)
        monkeypatch.setattr(o,'compare_reproducibility_states',mutate)
    elif failure == 'expired-readout':
        now = time.monotonic()
        receipt.update(started_monotonic=now-4902,owner_deadline_monotonic=now-602,
            global_deadline_monotonic=now-2,readout_started_monotonic=now-601,readout_deadline_monotonic=now-2)
    elif failure in ('late-close','storage-close','failed-invalidation'):
        replace = d.replace_control; published = []
        def publish(path,value,storage):
            if failure == 'failed-invalidation' and published and value.get('native_prerequisites_passed') is False:
                raise OSError('false close write refused fixture')
            replace(path,value,storage)
            if value.get('native_prerequisites_passed') is True: published.append(True)
        monkeypatch.setattr(d,'replace_control',publish)
        if failure in ('late-close','failed-invalidation'):
            original_time = time.monotonic
            monkeypatch.setattr(m.time,'monotonic',lambda:original_time()+(10000 if published else 0))
        else:
            check = StorageBudget.check
            def recount(self,size,*,path):
                if published and size == 0: raise OSError('final storage recount refused fixture')
                return check(self,size,path=path)
            monkeypatch.setattr(StorageBudget,'check',recount)
    # Refresh the software fixture ledger for coherent corruptions, so independent
    # raw/state checks rather than the index alone have to reject them.
    if failure not in ('changed-raw','expired-readout'):
        receipt['artifact_index'] = [row for row in p.hash_ledger(root) if row['path'] != 'execution.json']
    (root/'execution.json').write_text(json.dumps(receipt))
    assert m.audit(path) == 1
    if failure == 'failed-invalidation':
        assert not (root/'scientific-close.json').exists()
        assert p.read_json(root/'scientific-close.invalidated.json')['native_prerequisites_passed'] is True
    else:
        close = p.read_json(root/'scientific-close.json')
        assert close['native_prerequisites_passed'] is False and close['qualification_claims'] == []
        assert close['error']
