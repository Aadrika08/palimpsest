"""The sole source Engine owner. Outputs are consistency evidence, never admission."""
from __future__ import annotations
import copy
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import time
from scripts import memory_family_source_records_vnext as wire


@dataclass(frozen=True)
class ClosedSource:
    job: dict
    owner: dict
    worker_report: dict
    raw_manifest: dict
    raw_events: dict
    raw_chunks: tuple
    snapshot: dict
    prefix: dict
    boundary: int


class _OwnedPolicyReferences:
    __slots__=('engine','policy','teacher','agent','audit_act_had_instance_value',
        'audit_act_original_value','custody_check','replay_rows','decoded_snapshot','replay_result')
    def __init__(self):
        for name in self.__slots__: setattr(self,name,False if name=='audit_act_had_instance_value' else None)


def _release_source_owned_policy_refs(refs):
    if type(refs) is not _OwnedPolicyReferences: raise TypeError('Exact source-owned references required')
    failures=[]; policy=refs.policy; engine=refs.engine; agent=refs.agent
    def attempt(operation):
        try: operation()
        except BaseException as error: failures.append(error)
    try:
        if policy is not None:
            if refs.audit_act_had_instance_value:
                attempt(lambda:setattr(policy,'act',refs.audit_act_original_value))
            elif 'act' in vars(policy): attempt(lambda:delattr(policy,'act'))
            for name in ('failure_diagnostics','_current_raw_output','_encoded','_raw'):
                if hasattr(policy,name): attempt(lambda name=name:setattr(policy,name,{} if name=='failure_diagnostics' else None))
            if agent is None: agent=getattr(policy,'agent',None)
            cell=getattr(agent,'cell',None)
            if cell is not None:
                attempt(lambda:setattr(cell,'_cached_alphas',None)); attempt(lambda:setattr(cell,'_alphas_dirty',True))
            cell=None
        if engine is not None:
            attempt(lambda:setattr(engine,'policy',None)); attempt(lambda:setattr(engine,'teacher',None))
    finally:
        policy=engine=agent=None
        for name in refs.__slots__:
            try: setattr(refs,name,False if name=='audit_act_had_instance_value' else None)
            except BaseException as error: failures.append(error)
    if failures: raise wire.errors('Source-owned policy reference release',failures)


class _LoadedPolicyIdentity:
    """Fixed source-owned checker; immutable identity excludes hidden/cache state."""
    __slots__=('_job','_lease','_refs','_tensors','_runtime','_provenance','_policy_id','_agent_id','_cell_id')
    def __init__(self,job,lease,refs):
        from palimpsest import snapshots
        from scripts.memory_family_source_qualifier_vnext import _guard_policy
        from scripts.memory_family_cell_replay_v4 import _runtime
        if type(refs) is not _OwnedPolicyReferences: raise TypeError('Exact source-owned references required')
        self._job=job; self._lease=lease; self._refs=refs
        policy=refs.policy
        try:
            _guard_policy(job,lease,policy)
            self._runtime=copy.deepcopy(snapshots._torch_profile())
            _runtime(policy,{'identity':{'torch':self._runtime}})
            self._tensors=snapshots.state_digest(snapshots.controller_hashes(policy))
            self._provenance=snapshots.state_digest(policy.provenance)
            self._policy_id=id(policy); self._agent_id=id(policy.agent); self._cell_id=id(policy.agent.cell)
        finally: policy=None

    def __call__(self):
        from palimpsest import snapshots
        from scripts.memory_family_source_qualifier_vnext import _guard_policy
        from scripts.memory_family_cell_replay_v4 import _runtime
        self._lease.recheck(); policy=self._refs.policy
        try:
            if policy is None or (id(policy),id(policy.agent),id(policy.agent.cell))!=(self._policy_id,self._agent_id,self._cell_id):
                raise ValueError('Loaded source-owned policy identity changed')
            _guard_policy(self._job,self._lease,policy)
            _runtime(policy,{'identity':{'torch':self._runtime}})
            if snapshots.state_digest(snapshots.controller_hashes(policy))!=self._tensors or snapshots.state_digest(policy.provenance)!=self._provenance:
                raise ValueError('Loaded source immutable tensor/provenance identity changed')
            self._lease.recheck()
        finally: policy=None


def _checked_source_step(engine,refs):
    if type(refs) is not _OwnedPolicyReferences or type(refs.custody_check) is not _LoadedPolicyIdentity:
        raise TypeError('Fixed source-owned loaded identity checker required')
    refs.custody_check()
    command={'id':f'neural-{engine.episode_step}','kind':'step',
        'expected_state':'paused','expected_episode':engine.episode}
    if engine.controller!='flynn' or engine.policy is None or engine.phase!='paused':
        raise ValueError('Only paused CPU FLYNN stepping is admitted')
    if engine.submit(command).get('status')!='queued': raise ValueError('Policy step refused')
    refs.custody_check()
    result=engine.advance()
    refs.custody_check()
    return result


def _admit_source_write(job,totals,incoming,kind,free_bytes,floor,report_remaining=32768):
    """Fixed conservative value arithmetic used immediately before actual I/O."""
    wire.integer(incoming,0,16*wire.MiB); wire.integer(floor,0,2**63-1)
    if free_bytes-incoming-report_remaining<floor: raise ValueError('Source free-space floor before write')
    physical=sum(totals[name] for name in ('raw','snapshot','candidate','controls','atomic'))
    if kind=='raw':
        if incoming>7*wire.MiB or totals['raw']+incoming+report_remaining>512*wire.MiB or totals['atomic']+incoming>8*wire.MiB: raise ValueError('Source raw/report/atomic cap before write')
        addition=2*incoming+report_remaining
    elif kind=='snapshot':
        if totals['snapshot']+incoming>16*wire.MiB: raise ValueError('Source SNP cap before write')
        addition=incoming+report_remaining
    else: raise ValueError('Unknown fixed source write kind')
    if physical+addition+64*wire.MiB>640*wire.MiB: raise ValueError('Source total/headroom before write')


def _validate_raw_write_target(recording,path,incoming):
    import re,stat
    recording=Path(recording); path=Path(path); wire.integer(incoming,0,7*wire.MiB)
    if path==recording/'events.jsonl':
        state=path.stat(follow_symlinks=False)
        if not stat.S_ISREG(state.st_mode) or state.st_nlink!=1 or state.st_size+incoming>7*wire.MiB:
            raise ValueError('Raw events append exceeds reserved leaf cap')
    elif path==recording/'manifest.json':
        if incoming>65536: raise ValueError('Raw manifest exceeds reserved leaf cap')
        if path.with_suffix('.tmp').exists(): raise FileExistsError('Retained raw manifest pending')
    elif path.parent==recording/'chunks' and re.fullmatch(r'0000(?:[0-2][0-9]|3[0-7])\.npz',path.name):
        if path.exists() or path.with_suffix('.tmp').exists(): raise FileExistsError('Raw chunk target/pending exists')
    else: raise ValueError('Unreserved raw write target')


class _SourceStorageBudget:
    __slots__=('_lease','_job','_floor')
    def __init__(self,lease):
        from scripts.memory_source_parent_entry_vnext import _publication_floor
        self._lease=lease; self._job=wire.decode(lease._job_bytes,262144); self._floor=_publication_floor(lease)

    def check(self,size,*,path):
        try: self._check_write(size,path=path)
        except BaseException:
            self._lease._state='poisoned'
            raise

    def _check_write(self,size,*,path):
        from scripts.memory_source_parent_entry_vnext import _check_output_budget
        self._lease.recheck(); job=self._job; root=Path(job['workspace_root'])
        b=f"output/.pending/{job['case']['case_id']}"; raw=root/f"{b}/.raw/{job['source_run_id']}/recording"; snapshot=root/(b+'/source/snapshots/initial.snp')
        if Path(path)==raw: kind='raw'
        elif Path(path).is_relative_to(raw):
            _validate_raw_write_target(raw,path,size); kind='raw'
        elif Path(path)==snapshot: kind='snapshot'
        else: raise ValueError('Source write outside fixed recording/SNP slots')
        totals=_check_output_budget(job)
        report=root/f"{b}/.raw/{job['source_run_id']}/worker-report.json"
        report_remaining=max(0,32768-(report.stat().st_size if report.exists() else 0))
        info=os.statvfs(root)
        _admit_source_write(job,totals,size,kind,info.f_bavail*info.f_frsize,self._floor,report_remaining)
        if kind=='raw':
            if (raw/'manifest.tmp').exists() or any((raw/f'chunks/{i:06}.tmp').exists() for i in range(38)):
                raise ValueError('Retained raw pending prevents a new write')
        self._lease.recheck()


def produce_source(job,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'producer'); return _produce_source_core(job,live_inputs)


def _produce_authored_source(job,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'producer',True); return _produce_source_core(job,live_inputs)


def _produce_source_core(job,lease):
    entered=time.monotonic_ns(); lease._source_deadline_ns=min(entered+360_000_000_000,lease._deadline_ns-10_000_000_000)
    from palimpsest import memory, memory_decision, memory_decision_world as world, snapshots
    from palimpsest.engine import Engine
    from scripts.memory_decision_pilot import audit_policy
    from scripts.memory_source_parent_entry_vnext import _lease_kind,_initial_bytes
    from scripts.memory_family_source_qualifier_vnext import _guard_policy
    authored=_lease_kind(lease)=='authored'; run=job['source_run_id']; case=job['case']; root=Path(job['workspace_root'])
    b=f"output/.pending/{case['case_id']}"; r=f'{b}/.raw/{run}'; s=b+'/source'; k=f'output/controls/{run}'
    job_d=wire.describe('freeze/metadata/job.json',lease._job_bytes)
    owner=dict(schema=wire.record_schema('owner',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],job=job_d,case_id=case['case_id'],case_sha256=memory.sha256(case),source_run_id=run,owner_source=lease._load['runtime_requirements']['pins']['owner_source'],operation='source',condition=None,status='owner-intent-unqualified',claims=wire.CLAIMS.copy())
    owner_d=lease._publish(s+'/owner.json',owner,16384)
    storage=_SourceStorageBudget(lease)
    refs=_OwnedPolicyReferences(); lease._policy_refs=refs; engine=policy=agent=None; errors=[]; report=None
    def check_source():
        storage.check(0,path=root/(r+'/recording'))
        lease.recheck()
        if refs.custody_check is not None: refs.custody_check()
        if time.monotonic_ns()>=lease._source_deadline_ns: raise TimeoutError('Source production deadline')
    try:
        check_source()
        engine=Engine.open(lease._roots['repo'],lease._roots['assets'],root/(r+'/recording'),
            source_bootstrap_mode='canonical-prepared-vnext-v1',diagnostics=lease._provenance,
            run_id=run,scenario='memory-decision-v2',controller='flynn',device='cpu',texture='checker',seed=case['seed'],memory_case=case,
            restore_snapshot=None,replace_controller=False,memory_u=None,research_binding=None,expected_policy_identity=None,max_bytes=512*wire.MiB,storage_budget=storage)
        refs.engine=engine; policy=refs.policy=engine.policy; refs.teacher=engine.teacher; agent=refs.agent=policy.agent
        check_source(); _guard_policy(job,lease,policy)
        refs.custody_check=_LoadedPolicyIdentity(job,lease,refs)
        check_source()
        if engine.writer._background is not None or engine.memory['version']!=3 or engine.total_tick!=0 or engine.episode_step!=0 or engine.phase!='paused': raise ValueError('Source bootstrap epoch differs')
        engine.writer.manifest['memory_source_registration_vnext']=dict(schema=wire.record_schema('raw-registration',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],job=job_d,case=copy.deepcopy(case),source_run_id=run,operation='source',condition=None)
        refs.audit_act_had_instance_value='act' in vars(policy); refs.audit_act_original_value=vars(policy).get('act')
        audit_policy(engine)
        for step in range(1200):
            check_source()
            if (engine.phase!='paused' or engine.controller!='flynn' or str(policy.device)!='cpu' or engine.eyes!={'left':True,'right':True} or engine.episode!=0 or engine.total_tick!=engine.episode_step): raise ValueError('Source live cursor/controller/eyes differs')
            if memory_decision.acquired_boundary(engine.memory): break
            _checked_source_step(engine,refs); check_source()
            if engine.memory['cursor']['tick']!=engine.episode_step-1 or engine.world_task_state['last_tick']!=engine.episode_step-1: raise ValueError('Source memory/world cursor differs')
            if memory_decision.acquired_boundary(engine.memory): break
        if not memory_decision.acquired_boundary(engine.memory) or not 1<=engine.episode_step<=1200 or engine.phase!='paused': raise ValueError('No genuine acquired source boundary')
        snapshot=snapshots.capture(engine.env,engine.observation,policy=policy,teacher=engine.teacher,application=engine.application_state()); refs.decoded_snapshot=snapshot
        check_source()
        snapshots.validate_decision_snapshot(snapshot)
        from scripts.memory_family_raw_audit_v4 import _source_application
        state=world.validate_state(copy.deepcopy(engine.world_task_state)); boundary=engine.episode_step
        _source_application(snapshot['application'],case,run,dict(total_ticks=boundary,world_state=state)); check_source()
        prefix=copy.deepcopy(snapshot['application']['event_prefix'])
        snapshots.save_snapshot(snapshot,root/(s+'/snapshots/initial.snp'),preserve_failed=True,storage_budget=storage)
        storage.check(0,path=root/(s+'/snapshots/initial.snp')); check_source(); snp_raw=_initial_bytes(str(root/(s+'/snapshots/initial.snp')),16*wire.MiB,lease._deadline_ns); snp_d=wire.describe(s+'/snapshots/initial.snp',snp_raw)
        engine._event('snapshot_registered',snapshot_id=job['attempt_id'],filename='initial.snp',initial=True,sha256=snp_d['sha256'])
        engine.writer.manifest['world_state']=copy.deepcopy(state)
        report=dict(schema=wire.record_schema('worker-report',authored),job=job_d,source_run_id=run,case_id=case['case_id'],case_sha256=memory.sha256(case),operation='source',condition=None,status='recorded-unqualified',snapshot=snp_d,total_ticks=boundary,final_phase='paused',world_state=state,event_prefix=prefix,claims=wire.CLAIMS.copy())
        check_source(); snapshot=snp_raw=None
    except BaseException as error:
        lease._state='poisoned'; errors.append(error)
    finally:
        cleanup_start=time.monotonic_ns()
        if refs.custody_check is not None:
            try: refs.custody_check()
            except BaseException as error: errors.append(error)
        if engine is not None:
            try: engine.close()
            except BaseException as error:
                lease._state='poisoned'; errors.append(error)
        if refs.custody_check is not None:
            try: refs.custody_check()
            except BaseException as error: errors.append(error)
        try: _release_source_owned_policy_refs(refs)
        except BaseException as error: errors.append(error)
        engine=policy=agent=None; lease._policy_refs=None
        try:
            lease.recheck()
            if time.monotonic_ns()>=lease._deadline_ns or time.monotonic_ns()-cleanup_start>10_000_000_000: raise TimeoutError('Source cleanup deadline')
        except BaseException as error: errors.append(error)
    if errors: raise wire.errors('Source owner failed',errors)
    report_d=lease._publish(r+'/worker-report.json',report,32768)
    lease._publish(k+'/producer/cleanup.json',dict(schema=wire.record_schema('producer-cleanup',authored),job=job_d,engine_closed=True,writer_closed=True,environment_closed=True,source_deadline_met=True,cleanup_deadline_met=True,claims=wire.CLAIMS.copy()),65536)
    manifest_raw=_initial_bytes(str(root/(r+'/recording/manifest.json')),65536,lease._deadline_ns); manifest=__import__('json').loads(manifest_raw)
    if manifest.get('status')!='completed': raise ValueError('Source writer did not complete')
    manifest_d=wire.describe(r+'/recording/manifest.json',manifest_raw)
    events_d=wire.describe(r+'/recording/events.jsonl',_initial_bytes(str(root/(r+'/recording/events.jsonl')),7*wire.MiB,lease._deadline_ns))
    chunks=tuple(wire.describe(f'{r}/recording/chunks/{i:06}.npz',_initial_bytes(str(root/f'{r}/recording/chunks/{i:06}.npz'),7*wire.MiB,lease._deadline_ns)) for i in range((boundary+31)//32))
    closed=ClosedSource(job_d,owner_d,report_d,manifest_d,events_d,chunks,snp_d,prefix,boundary)
    lease._closed_source=closed
    return closed
