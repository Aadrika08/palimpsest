"""Fixed conditional source workload. Trusted-parent authentication remains external.

No launcher, provider, CLI, accepted Q, resource accounting or execution grant.
"""
from __future__ import annotations
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import threading
import time
from scripts import memory_family_source_records_vnext as wire
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles, _identity
from scripts.memory_source_runtime_closure_v1 import RuntimeHandle, hold_runtime_manifest

_ACTUAL_TOKEN=object(); _AUTHORED_TOKEN=object(); _DIRECTORY_TOKEN=object(); _REGISTRY_TOKEN=object()
_LEASE_SLOTS=('_state','_domain','_thread_id','_attempt_id','_job_bytes','_authorization_bytes',
    '_readset','_roots','_runtime','_input_files','_directory_closure','_registry','_policy_refs',
    '_stage_stacks','_provenance','_load','_deadline_ns','_source_deadline_ns','_phase','_closed_source','_failures')


@dataclass
class _Binding:
    descriptor: dict
    owner: object | None
    fd: int | None
    identity: tuple | None
    roles: set


class _SourcePathRegistry:
    def __init__(self,token,deadline_ns):
        if token is not _REGISTRY_TOKEN: raise ValueError('Private source registry')
        self._thread_id=threading.get_ident(); self._deadline_ns=deadline_ns
        self._active=True; self._paths={}; self._inodes={}; self._directory_inodes={}; self._runtime_registered=False

    def _check(self):
        if not self._active or self._thread_id!=threading.get_ident(): raise RuntimeError('Inactive/cross-thread source registry')
        if time.monotonic_ns()>=self._deadline_ns: raise TimeoutError('Source registry deadline')

    def claim(self,descriptor,role):
        self._check(); descriptor=wire.descriptor(descriptor,True); wire.text(role,96)
        path=descriptor['path']; current=self._paths.get(path)
        if current is not None:
            if wire.encode(current.descriptor)!=wire.encode(descriptor): raise ValueError('Conflicting source descriptors')
            current.roles.add(role); return 'reuse'
        if len(self._paths)>=60000: raise ValueError('Source registry leaf cap')
        self._paths[path]=_Binding(descriptor,None,None,None,{role}); return 'new'

    def _register(self,holder):
        for relative,entry in holder._entries.items():
            path='/'+relative; descriptor=dict(path=path,size_bytes=entry.size,sha256=entry.sha256)
            self.claim(descriptor,'held')
            binding=self._paths[path]; fd,_,_,expected=holder._files[relative]
            actual=_identity(os.fstat(fd))
            if actual!=expected or not stat.S_ISREG(actual[2]) or actual[6]!=1: raise ValueError('Held source leaf identity')
            inode=actual[:2]
            if inode in self._inodes and self._inodes[inode]!=path: raise ValueError('Global source inode alias')
            if binding.owner is not None and (binding.owner is not holder or binding.fd!=fd): raise ValueError('Duplicate source FD owner')
            binding.owner=holder; binding.fd=fd; binding.identity=actual; self._inodes[inode]=path

    def register_runtime(self,handle):
        self._check()
        if type(handle) is not RuntimeHandle or self._runtime_registered or any(b.owner is not None for b in self._paths.values()):
            raise TypeError('Genuine runtime must be registered first once')
        handle.recheck()
        for holder in handle._holders: self._register(holder)
        handle.recheck(); self._runtime_registered=True

    def register_batch(self,holder):
        self._check()
        if type(holder) is not HeldReplayFiles: raise TypeError('Genuine replay batch required')
        holder.recheck(); self._register(holder); holder.recheck()

    def binding(self,path):
        self._check(); wire.path(path,True)
        binding=self._paths.get(path)
        if binding is None or binding.owner is None: raise ValueError('Source path is not held')
        return binding

    def recheck(self):
        self._check()
        try:
            for path,binding in self._paths.items():
                if binding.owner is None: raise RuntimeError('Unbound source claim')
                if binding.owner._state!='active' or _identity(os.fstat(binding.fd))!=binding.identity:
                    raise RuntimeError('Source owner/FD no longer active')
            self._check()
        except BaseException:
            self._active=False; raise

    def invalidate(self):
        if self._thread_id!=threading.get_ident(): raise RuntimeError('Cross-thread registry invalidate')
        self._active=False


class _HeldDirectoryClosure:
    def __init__(self,token,*,trees,ancestor_targets,deadline_ns,registry):
        if token is not _DIRECTORY_TOKEN or type(registry) is not _SourcePathRegistry: raise ValueError('Private directory closure')
        if type(trees) is not tuple or type(ancestor_targets) is not tuple: raise ValueError('Immutable directory inputs')
        self._state='new'; self._thread_id=threading.get_ident(); self._deadline_ns=deadline_ns
        self._registry=registry; self._dirs={}; self._fds=[]; self._children={}; self._directory_inodes=registry._directory_inodes
        targets=set(ancestor_targets)
        for tree in trees:
            wire.fields(tree,('root','directories','files')); root=wire.path(tree['root'],True)
            directories=tree['directories']
            if type(directories) is not list or directories!=sorted(set(directories)) or len(directories)>60000: raise ValueError('Directory roster')
            local={root:{}}
            for relative in directories: wire.path(relative); local[root+'/'+relative]={}
            for directory in list(local):
                if directory==root: continue
                parent,name=directory.rsplit('/',1)
                if parent not in local: raise ValueError('Directory parent closure missing')
                local[parent][name]='directory'
            for desc in tree['files']:
                wire.descriptor(desc,True); p=desc['path']; parent,name=p.rsplit('/',1)
                if not p.startswith(root+'/') or parent not in local or name in local[parent]: raise ValueError('File/dir closure conflict')
                local[parent][name]='file'
            for directory,children in local.items():
                if directory in self._children and self._children[directory]!=children: raise ValueError('Contradictory closed trees')
                self._children[directory]=children; targets.add(directory)
        if len(self._children)>60000: raise ValueError('Directory closure cap')
        for target in targets: wire.path(target,True)
        self._targets=tuple(sorted(targets))

    def _check(self,active=True):
        if self._thread_id!=threading.get_ident() or (active and self._state!='active'): raise RuntimeError('Inactive/cross-thread directory custody')
        if time.monotonic_ns()>=self._deadline_ns: raise TimeoutError('Directory custody deadline')

    def _open_directory(self,path):
        self._check(False); wire.path(path,True)
        if path in self._dirs: return self._dirs[path][0]
        parent_path,name=path.rsplit('/',1) if path!='/' else ('','/')
        parent=self._open_directory(parent_path or '/') if path!='/' else None
        # Check the named edge before AND after opening with no-follow.
        before=_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
        if not stat.S_ISDIR(before[2]): raise ValueError('Non-directory ancestor')
        fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent); self._fds.append(fd)
        if _identity(os.fstat(fd))!=before or _identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=before:
            raise RuntimeError('Directory changed while opening')
        inode=before[:2]
        if inode in self._directory_inodes and self._directory_inodes[inode]!=path: raise ValueError('Directory inode alias')
        self._directory_inodes[inode]=path; self._dirs[path]=(fd,parent,name,before)
        return fd

    def _edges(self):
        for directory,(fd,parent,name,identity) in self._dirs.items():
            self._check()
            if _identity(os.fstat(fd))!=identity or _identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=identity:
                raise RuntimeError('Full-stat source ancestor changed: '+directory)

    def _census(self):
        for directory,expected in self._children.items():
            fd=self._dirs[directory][0]; names=set()
            # A fresh open description avoids shared scandir offsets.
            scan=os.open('.',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try:
                with os.scandir(scan) as entries:
                    for entry in entries:
                        self._check()
                        if len(names)>=len(expected) or entry.name not in expected or entry.name in names:
                            raise ValueError('Unexpected closed directory child')
                        names.add(entry.name); state=entry.stat(follow_symlinks=False)
                        if expected[entry.name]=='directory': good=stat.S_ISDIR(state.st_mode)
                        else: good=stat.S_ISREG(state.st_mode) and state.st_nlink==1
                        if not good: raise ValueError('Closed directory child kind/link differs')
            finally: os.close(scan)
            if names!=set(expected): raise ValueError('Missing closed directory child')

    def _drain(self,primary=None):
        failures=[primary] if primary is not None else []
        while self._fds:
            try: os.close(self._fds.pop())
            except BaseException as error: failures.append(error)
        self._state='closed' if not failures else 'poisoned'
        if failures and (primary is None or len(failures)>1): raise wire.errors('Source directory teardown',failures)

    def __enter__(self):
        self._check(False)
        if self._state!='new': raise RuntimeError('Directory closure one-shot')
        try:
            for target in self._targets:
                # Targets name directories; callers pass leaf parents explicitly.
                self._open_directory(target)
            self._state='active'; self.recheck(); return self
        except BaseException as error:
            self._state='poisoned'; self._drain(error); raise

    def recheck(self):
        self._check()
        try:
            self._edges(); self._census(); self._edges(); self._check()
        except BaseException as error:
            self._state='poisoned'; self._drain(error); raise

    def require_children(self,directory):
        self.recheck()
        if directory not in self._children: raise ValueError('Not a closed directory')
        return tuple(sorted(self._children[directory].items()))

    def __exit__(self,kind,error,traceback):
        failures=[error] if error is not None else []
        if self._state=='active':
            try: self.recheck()
            except BaseException as failure: failures.append(failure)
        self._state='closing'
        try: self._drain()
        except BaseException as failure: failures.append(failure)
        if failures and (error is None or len(failures)>1): raise wire.errors('Source directory exit',failures)
        return False


def _batches(descriptors):
    batch=[]; size=0
    for row in sorted(descriptors,key=lambda r:r['path']):
        wire.descriptor(row,True,1024*wire.MiB)
        if batch and (len(batch)==512 or size+row['size_bytes']>2048*wire.MiB):
            yield batch; batch=[]; size=0
        batch.append(dict(row,path=row['path'][1:])); size+=row['size_bytes']
    if batch: yield batch


class _SourceLeaseCore:
    __slots__=_LEASE_SLOTS
    def __init__(self,token,*,job=None,authorization=None,job_bytes=None,authorization_bytes=None):
        if type(self) is _LiveInputLease and token is _ACTUAL_TOKEN: domain='actual'
        elif type(self) is _AuthoredLiveInputLease and token is _AUTHORED_TOKEN: domain='authored'
        else: raise ValueError('Private exact source lease constructor')
        self._state='new'; self._domain=domain; self._thread_id=threading.get_ident()
        self._job_bytes=job_bytes; self._authorization_bytes=authorization_bytes
        self._attempt_id=job['attempt_id']; self._readset=job['readset']; self._roots={}
        self._runtime=None; self._input_files=[]; self._directory_closure=None
        self._registry=_SourcePathRegistry(_REGISTRY_TOKEN,authorization['deadline_monotonic_ns'])
        self._policy_refs=None; self._stage_stacks=[]; self._provenance=None; self._load=None
        self._deadline_ns=authorization['deadline_monotonic_ns']; self._source_deadline_ns=None
        self._phase='producer'; self._closed_source=None; self._failures=[]

    def __setattr__(self,name,value):
        if name=='_domain' and hasattr(self,'_domain'): raise AttributeError('Read-only lease domain')
        object.__setattr__(self,name,value)

    def _check(self,job=None,phase=None):
        _lease_kind(self)
        if self._thread_id!=threading.get_ident() or self._state!='active': raise RuntimeError('Inactive/cross-thread source lease')
        if job is not None and wire.encode(job,262144)!=self._job_bytes: raise ValueError('Lease job identity differs')
        if phase is not None and self._phase!=phase: raise RuntimeError('Wrong source phase')
        if time.monotonic_ns()>=self._deadline_ns: raise TimeoutError('Original source outer deadline')

    def recheck(self):
        self._check()
        try:
            if self._directory_closure is not None: self._directory_closure.recheck()
            for stack in self._stage_stacks:
                for directory in getattr(stack,'_source_directories',()): directory.recheck()
            if self._runtime is not None: self._runtime.recheck()
            for holder in self._input_files: holder.recheck()
            self._registry.recheck()
            if self._directory_closure is not None: self._directory_closure.recheck()
            self._check()
        except BaseException:
            self._state='poisoned'; raise

    def _read(self,descriptor,maximum):
        self.recheck(); descriptor=wire.descriptor(descriptor,True,maximum)
        binding=self._registry.binding(descriptor['path'])
        if binding.descriptor!=descriptor: raise ValueError('Read descriptor differs')
        payload=bytearray(); os.lseek(binding.fd,0,os.SEEK_SET)
        while True:
            self._check(); block=os.read(binding.fd,min(wire.MiB,maximum+1-len(payload)))
            if not block: break
            payload.extend(block)
            if len(payload)>maximum: raise ValueError('Bounded source read grew')
            self._check()
        self.recheck()
        if len(payload)!=descriptor['size_bytes'] or hashlib.sha256(payload).hexdigest()!=descriptor['sha256']: raise ValueError('Source read bytes differ')
        return bytes(payload)

    def _hold_stage(self,descriptors,exact=()):
        self.recheck(); job=wire.decode(self._job_bytes,262144); root=job['workspace_root']
        absolute=[]
        for d in descriptors:
            row=dict(d,path=root+'/'+d['path'])
            if self._registry.claim(row,'stage')=='new': absolute.append(row)
        known={path for stack in self._stage_stacks for path in getattr(stack,'_source_roots',())}
        selected=[path for path in exact if path not in known]
        if not absolute and not selected: self.recheck(); return
        stack=ExitStack(); stack._source_directories=[]; stack._source_roots=tuple(selected)
        self._stage_stacks.append(stack)
        if selected:
            trees=[]
            for relative in selected:
                wire.path(relative); prefix=root+'/'+relative; leaves=[dict(d,path=root+'/'+d['path']) for d in descriptors if d['path'].startswith(relative+'/')]
                directories=set()
                for leaf in leaves:
                    parent=str(Path(leaf['path']).parent)
                    while parent!=prefix:
                        if not parent.startswith(prefix+'/'): raise ValueError('Closed-stage parent closure')
                        directories.add(parent[len(prefix)+1:]); parent=str(Path(parent).parent)
                trees.append(dict(root=prefix,directories=sorted(directories),files=sorted(leaves,key=lambda d:d['path'])))
            directory=stack.enter_context(_HeldDirectoryClosure(_DIRECTORY_TOKEN,trees=tuple(trees),ancestor_targets=(),deadline_ns=self._deadline_ns,registry=self._registry))
            stack._source_directories.append(directory)
        for rows in _batches(absolute):
            holder=stack.enter_context(HeldReplayFiles('/',rows,self._deadline_ns/1e9,structured_teardown=True))
            self._input_files.append(holder); self._registry.register_batch(holder)
        self.recheck()

    def _raw(self,descriptor,maximum):
        job=wire.decode(self._job_bytes,262144)
        return self._read(dict(descriptor,path=job['workspace_root']+'/'+descriptor['path']),maximum)

    def _publish(self,path,value,maximum):
        self.recheck(); raw=wire.encode(value,maximum); job=wire.decode(self._job_bytes,262144)
        roster={row['path']:row for row in wire.output_roster(job['case']['case_id'],job['source_run_id'])}
        if path not in roster or maximum>roster[path]['max_bytes']: raise ValueError('Unreserved output')
        result=_publish_bytes(job,path,raw,roster,minimum_free_bytes=_publication_floor(self)); self.recheck(); return result


class _LiveInputLease(_SourceLeaseCore): __slots__=()
class _AuthoredLiveInputLease(_SourceLeaseCore): __slots__=()


def _lease_kind(lease):
    if type(lease) is _LiveInputLease: return 'actual'
    if type(lease) is _AuthoredLiveInputLease: return 'authored'
    raise TypeError('Exact source lease required')


def _require_role(job,lease,phase,authored=False):
    if _lease_kind(lease)!=('authored' if authored else 'actual'): raise TypeError('Sibling source lease is not accepted')
    wire._job(job,authored); lease._check(job,phase); lease.recheck()


def _publication_floor(lease):
    _lease_kind(lease); lease._check()
    job=wire.decode(lease._job_bytes,262144)
    resources=wire.decode(lease._raw(lease._readset['resources'],65536),65536)
    return resources['capacity']['required_free_bytes'] if _lease_kind(lease)=='authored' else job['limits']['min_free_bytes']


def _check_output_budget(job, prospective=None):
    """Conservative fixed-slot physical occupancy, never provider accounting.

    Producer controls remain externally mutable until their final marker. Their
    whole 640KiB reservation is charged without inspecting that branch early.
    """
    root=job['workspace_root']; roster=wire.output_roster(job['case']['case_id'],job['source_run_id'])
    marker=root+f"/output/controls/{job['source_run_id']}/producer/supervisor.json"
    producer_closed=os.path.lexists(marker)
    totals=dict(raw=0,snapshot=0,candidate=0,controls=0,atomic=0,metadata=0)
    pending=dict(raw=0,numeric=0,metadata=0)
    if not producer_closed: totals['controls']=640*1024
    metadata_names={'raw-manifest','worker-report','owner','numeric-manifest','base-manifest','legacy-manifest','base-index','numeric-index','audit','registration','conversion','commit','candidate','outcome'}
    for row in roster:
        role=row['role']; relative=row['path']
        if '/producer/' in relative and not producer_closed: continue
        try: state=os.stat(root+'/'+relative,follow_symlinks=False)
        except FileNotFoundError: continue
        if not stat.S_ISREG(state.st_mode) or state.st_size>row['max_bytes']: raise ValueError('Output slot type/physical cap')
        size=state.st_size
        if role.startswith('pending-'):
            kind='raw' if relative.endswith('.tmp') else 'numeric' if '/source/numeric/' in relative else 'metadata'
            pending[kind]+=1; totals['atomic']+=size
        elif '/source/numeric/' in relative: totals['candidate']+=size
        elif role=='snapshot': totals['snapshot']+=size
        elif '/controls/' in relative: totals['controls']+=size
        else: totals['raw']+=size
        if role in metadata_names: totals['metadata']+=size
    if prospective is not None:
        relative,size=prospective
        if '/source/numeric/' in relative:
            if size>768*1024: raise ValueError('Numeric atomic occupancy cap')
            totals['candidate']+=size; pending['numeric']+=1
        else:
            if size>256*1024: raise ValueError('Metadata/control atomic occupancy cap')
            if '/controls/' in relative:
                if producer_closed or '/producer/' not in relative: totals['controls']+=size
            else: totals['raw']+=size
            pending['metadata']+=1
        totals['atomic']+=size
        role=next(row['role'] for row in roster if row['path']==relative)
        if role in metadata_names: totals['metadata']+=size
    for kind,cap in [('raw',512),('snapshot',16),('candidate',32),('controls',8),('atomic',8),('metadata',1)]:
        if totals[kind]>cap*wire.MiB: raise ValueError('Source component physical cap: '+kind)
    if any(count>1 for count in pending.values()): raise ValueError('Multiple live atomic slots')
    if sum(totals[key] for key in ('raw','snapshot','candidate','controls','atomic'))+64*wire.MiB>640*wire.MiB: raise ValueError('Total source new-byte/headroom cap')
    return totals


def _publish_bytes(job,relative,raw,roster,*,minimum_free_bytes=None):
    wire.path(relative); row=roster.get(relative)
    if row is None or type(raw) is not bytes or len(raw)>row['max_bytes']: raise ValueError('Output byte/slot cap')
    root=job['workspace_root']; target=Path(root)/relative; pending=Path(str(target)+'.pending')
    if target.exists() or pending.exists(): raise FileExistsError('Source target/pending already exists')
    floor=job['limits']['min_free_bytes'] if job['schema']=='memory-source-job-vnext-v1' else 0
    if minimum_free_bytes is not None: floor=max(floor,wire.integer(minimum_free_bytes,0,2**63-1))
    report=Path(root)/f"output/.pending/{job['case']['case_id']}/.raw/{job['source_run_id']}/worker-report.json"
    report_reserve=32768 if relative.endswith('/source/owner.json') and not report.exists() else 0
    free=os.statvfs(root)
    if free.f_bavail*free.f_frsize-len(raw)-report_reserve<floor: raise ValueError('Source min-free reservation lost before write')
    _check_output_budget(job,(relative,len(raw)))
    fd=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    failures=[]
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view[:wire.MiB])
            if count<=0: raise OSError('Source write made no progress')
            view=view[count:]
        os.fsync(fd)
    except BaseException as error: failures.append(error)
    finally:
        try: os.close(fd)
        except BaseException as error: failures.append(error)
    if failures:
        if len(failures)==1: raise failures[0]
        raise wire.errors('Source publication write/close',failures)
    # Exclusive no-replace publication; only a successful publication consumes pending.
    import ctypes
    libc=ctypes.CDLL(None,use_errno=True)
    rename=libc.renameat2
    rename.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
    rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(pending),-100,os.fsencode(target),1)!=0:
        code=ctypes.get_errno()
        raise OSError(code,os.strerror(code),str(target))
    parent=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    failures=[]
    try: os.fsync(parent)
    except BaseException as error: failures.append(error)
    finally:
        try: os.close(parent)
        except BaseException as error: failures.append(error)
    if failures:
        if len(failures)==1: raise failures[0]
        raise wire.errors('Source publication directory fsync/close',failures)
    _check_output_budget(job)
    free=os.statvfs(root)
    if free.f_bavail*free.f_frsize<floor: raise ValueError('Source min-free reservation lost after write')
    return wire.describe(relative,raw)


def _await_producer_controls(job,live_inputs):
    _lease_kind(live_inputs); live_inputs._check(job,'producer')
    run=job['source_run_id']; base=f'output/controls/{run}/producer/'
    marker=Path(job['workspace_root'])/(base+'supervisor.json')
    while True:
        live_inputs.recheck()
        try: os.lstat(marker); break
        except FileNotFoundError: pass
        remaining=(live_inputs._deadline_ns-time.monotonic_ns())/1e9
        if remaining<=0: raise TimeoutError('Producer control rendezvous deadline')
        time.sleep(min(.01,remaining)); live_inputs.recheck()
    # Single final validation attempt: invalid/partial markers are never retried.
    descriptors=[]; values={}
    for name,cap in [('supervisor.json',65536),('stdout',262144),('stderr',262144),('cleanup.json',65536)]:
        relative=base+name; value=_initial_bytes(job['workspace_root']+'/'+relative,cap)
        descriptors.append(wire.describe(relative,value)); values[name]=value
        if os.path.lexists(job['workspace_root']+'/'+relative+'.pending'): raise ValueError('Producer control pending companion remains')
    live_inputs._hold_stage(descriptors,exact=(base.rstrip('/'),))
    for descriptor in descriptors:
        if live_inputs._raw(descriptor,262144)!=values[descriptor['path'].rsplit('/',1)[1]]: raise ValueError('Producer marker changed')
    authored=_lease_kind(live_inputs)=='authored'; supervisor=wire.decode(values['supervisor.json'],65536); cleanup=wire.decode(values['cleanup.json'],65536)
    wire.schema(supervisor,'producer-supervision',authored); wire.schema(cleanup,'producer-cleanup',authored)
    wire.fields(cleanup,('schema','job','engine_closed','writer_closed','environment_closed','source_deadline_met','cleanup_deadline_met','claims'))
    if any(cleanup[name] is not True for name in ('engine_closed','writer_closed','environment_closed','source_deadline_met','cleanup_deadline_met')): raise ValueError('Producer cleanup is incomplete')
    wire.fields(supervisor,('schema','attempt_id','job','authorization_sha256','resource_contract','process_role','segment','scope','owner_intent','worker_report','cleanup','stdout','stderr','started_monotonic_ns','ended_monotonic_ns','status','claims'))
    held={desc['path'].rsplit('/',1)[1]:desc for desc in descriptors}; closed=live_inputs._closed_source
    job_d=wire.describe('freeze/metadata/job.json',live_inputs._job_bytes)
    equalities=dict(attempt_id=job['attempt_id'],job=job_d,authorization_sha256=hashlib.sha256(live_inputs._authorization_bytes).hexdigest(),resource_contract=job['readset']['resources'],process_role='workload',segment='producer-only',scope='observed-owner-intent-to-closed-worker-report',owner_intent=closed.owner,worker_report=closed.worker_report,cleanup=held['cleanup.json'],stdout=held['stdout'],stderr=held['stderr'],status='closed')
    if any(wire.encode(supervisor[key])!=wire.encode(value) for key,value in equalities.items()) or cleanup['job']!=job_d: raise ValueError('Producer control identity differs')
    start=wire.integer(supervisor['started_monotonic_ns'],0,2**63-1); end=wire.integer(supervisor['ended_monotonic_ns'],start,time.monotonic_ns())
    live_inputs.recheck()
    return tuple(held[name] for name in ('supervisor.json','stdout','stderr','cleanup.json'))


def _initial_bytes(path,maximum,deadline_ns=None):
    wire.path(path,True); wire.integer(maximum,0,1024*wire.MiB)
    fds=[]; directories=[]; failures=[]; raw=bytearray()
    def clock():
        if deadline_ns is not None and time.monotonic_ns()>=deadline_ns: raise TimeoutError('Bounded source read deadline')
    try:
        clock(); parent=None
        components=path.split('/')[1:]
        for name in ['/',*components[:-1]]:
            clock(); before=_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
            if not stat.S_ISDIR(before[2]): raise ValueError('Metadata ancestor is not a real directory')
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent); fds.append(fd)
            if _identity(os.fstat(fd))!=before or _identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=before: raise ValueError('Metadata ancestor changed during open')
            directories.append((fd,parent,name,before)); parent=fd
        name=components[-1]; fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent); fds.append(fd)
        before=_identity(os.fstat(fd))
        if not stat.S_ISREG(before[2]) or before[6]!=1 or before[3]>maximum or _identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=before: raise ValueError('Metadata leaf type/link/size/edge')
        while len(raw)<=maximum:
            clock(); block=os.read(fd,min(wire.MiB,maximum+1-len(raw))); clock()
            if not block: break
            raw.extend(block)
        if len(raw)>maximum or _identity(os.fstat(fd))!=before or _identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=before: raise ValueError('Metadata changed/oversized')
        for directory,ancestor,component,identity in directories:
            if _identity(os.fstat(directory))!=identity or _identity(os.stat(component,dir_fd=ancestor,follow_symlinks=False))!=identity: raise ValueError('Metadata ancestor changed while reading')
        clock()
    except BaseException as error: failures.append(error)
    finally:
        while fds:
            try: os.close(fds.pop())
            except BaseException as error: failures.append(error)
    if failures:
        if len(failures)==1: raise failures[0]
        raise wire.errors('Bounded source read teardown',failures)
    return bytes(raw)


def run_attempt(job_bytes,authorization_bytes):
    return _run_attempt_core(job_bytes,authorization_bytes,_ACTUAL_TOKEN)


def _run_authored_attempt(job_bytes,authorization_bytes):
    return _run_attempt_core(job_bytes,authorization_bytes,_AUTHORED_TOKEN)


def _run_attempt_core(job_bytes,authorization_bytes,token):
    # Parsing/whole contract validation occurs before imports, runtime/model opens or output.
    authored=token is _AUTHORED_TOKEN
    job,authorization,metadata=wire.validate_attempt(job_bytes,authorization_bytes,authored,_initial_bytes)
    lease=(_AuthoredLiveInputLease(_AUTHORED_TOKEN,job=job,authorization=authorization,job_bytes=job_bytes,authorization_bytes=authorization_bytes)
        if authored else _LiveInputLease(_ACTUAL_TOKEN,job=job,authorization=authorization,job_bytes=job_bytes,authorization_bytes=authorization_bytes))
    return _execute(job,authorization,metadata,lease)


def _execute(job,authorization,metadata,lease):
    from scripts import memory_family_source_runtime_vnext as owner
    from scripts import memory_family_source_raw_audit_vnext as raw
    from scripts import memory_family_source_numeric_vnext as numeric
    from scripts import memory_family_source_qualifier_vnext as qualifier
    from palimpsest.held_provenance import held_provenance
    authored=_lease_kind(lease)=='authored'; source=job['case']['case_id']; run=job['source_run_id']
    k=f'output/controls/{run}'; failures=[]; result=None; outer=ExitStack()
    try:
        load=metadata['load_environment']; lease._load=load
        requirements=load['runtime_requirements']; roots=tuple(requirements['roots'])
        runtime=outer.enter_context(hold_runtime_manifest(load['runtime_reference'],required_roots=roots,
            required_pins=requirements['pins'],output_root=job['workspace_root']+'/output',
            deadline=lease._deadline_ns/1e9,check=lambda: _deadline(lease),structured_teardown=True))
        lease._runtime=runtime; lease._registry.register_runtime(runtime)
        descriptors,trees=wire.input_closure(job,authorization,metadata,authored)
        targets=tuple(sorted({str(Path(row['path']).parent) for row in descriptors} | {str(Path(path).parent) for path in lease._registry._paths} | set(roots) | {str(Path(requirements['pins']['python_alias']).parent)}))
        directory=_HeldDirectoryClosure(_DIRECTORY_TOKEN,trees=tuple(trees),ancestor_targets=targets,deadline_ns=lease._deadline_ns,registry=lease._registry)
        # Directory FDs must outlive byte-holder teardown, so drain separately last.
        directory.__enter__(); lease._directory_closure=directory
        extra=[]
        for row in descriptors:
            if lease._registry.claim(row,'frozen')=='new': extra.append(row)
        for rows in _batches(extra):
            holder=outer.enter_context(HeldReplayFiles('/',rows,lease._deadline_ns/1e9,structured_teardown=True))
            lease._input_files.append(holder); lease._registry.register_batch(holder)
        lease._state='active'; lease.recheck()
        _check_entry_source_bindings(lease)
        _check_capacity(metadata['resources'],lease)
        wire.validate_held_namespaces(job,authorization,metadata,lease)
        _check_provenance_bindings(lease)
        lease._provenance=held_provenance(**load['provenance']); lease._roots={row['role']:row['path'] for row in load['roots']}
        producer=owner._produce_authored_source if authored else owner.produce_source
        auditor=raw._audit_authored_source if authored else raw.audit_source
        converter=numeric._convert_authored_source if authored else numeric.convert_source
        qualify=qualifier._qualify_authored_source if authored else qualifier.qualify_source
        closed=producer(job,lease); lease._closed_source=closed
        controls=_await_producer_controls(job,lease)
        lease._phase='raw-audit'; A=auditor(job,closed,lease)
        lease._phase='registration'
        A_d=wire.describe(k+'/raw-audit/audit.json',wire.encode(A,131072))
        E=dict(schema=wire.record_schema('producer-registration',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],case=job['case'],source_run_id=run,job=closed.job,owner_record=closed.owner,snapshot=closed.snapshot,raw_audit=A_d,controls=dict(zip(('supervisor','stdout','stderr','cleanup'),controls),job=closed.job,audit=A_d),claims=wire.CLAIMS.copy())
        E_d=lease._publish(k+'/registration/registration.json',E,65536)
        lease._hold_stage([E_d],exact=(k+'/registration',)); lease._phase='conversion'; V,C=converter(job,closed,A,E,lease)
        lease._phase='qualifier'; Q=qualify(job,closed,lease)
        result=dict(schema=wire.record_schema('attempt-outcome',authored),attempt_id=job['attempt_id'],source_run_id=run,job=closed.job,authorization_sha256=hashlib.sha256(lease._authorization_bytes).hexdigest(),producer_registration=E_d,numeric_conversion=wire.describe(k+'/conversion/conversion.json',wire.encode(V,131072)),numeric_commit=wire.describe(k+'/conversion/commit.json',wire.encode(C,16384)),qualification_candidate=wire.describe(k+'/qualifier/candidate.json',wire.encode(Q,131072)),status='candidate-unaccepted',consistency_checked=True,external_parent_precondition='required-not-established-by-this-code',claims=wire.CLAIMS.copy())
        lease.recheck()
    except BaseException as error:
        failures.append(error); lease._state='poisoned'
    finally:
        lease._state='closing'; lease._registry.invalidate()
        # ExitStack itself may replace errors; callbacks already aggregate primitives.
        while lease._stage_stacks:
            stack=lease._stage_stacks.pop()
            try: _drain_stack(stack)
            except BaseException as error: failures.append(error)
        try: _drain_stack(outer)
        except BaseException as error: failures.append(error)
        if lease._directory_closure is not None:
            try: lease._directory_closure.__exit__(None,None,None)
            except BaseException as error: failures.append(error)
        lease._state='closed' if not failures else 'poisoned'
    if failures:
        _failure(job,lease,failures,metadata['resources'])
        raise wire.errors('Source attempt failed',failures)
    # Detached publication only after every source input has drained successfully.
    _publish_bytes(job,k+'/final-accounting/outcome.json',wire.encode(result,32768),{row['path']:row for row in wire.output_roster(source,run)},minimum_free_bytes=metadata['resources']['capacity']['required_free_bytes'] if authored else job['limits']['min_free_bytes'])
    return wire.decode(wire.encode(result,32768),32768)


def _drain_stack(stack):
    failures=[]
    while stack._exit_callbacks:
        synchronous,callback=stack._exit_callbacks.pop()
        try:
            if not synchronous: raise TypeError('Unexpected async source teardown')
            callback(None,None,None)
        except BaseException as error: failures.append(error)
    if failures: raise wire.errors('Source owned context drain',failures)


def _check_entry_source_bindings(lease):
    import sys
    required=lease._load['runtime_requirements']['pins']['required_sources']
    expected={row['path']:row for row in required}
    for name in ('memory_source_parent_entry_vnext','memory_family_source_records_vnext',
            'memory_family_source_runtime_vnext','memory_family_source_raw_audit_vnext',
            'memory_family_source_numeric_vnext','memory_family_source_qualifier_vnext'):
        module=sys.modules['scripts.'+name]; path=str(Path(module.__file__).absolute())
        if path not in expected: raise ValueError('Actual loaded source is not independently pinned')
        wire._literal(lease._registry.binding(path).descriptor,expected[path])
    owner=str(Path(sys.modules['scripts.memory_family_source_runtime_vnext'].__file__).absolute())
    wire._literal(lease._load['runtime_requirements']['pins']['owner_source'],expected[owner])
    lease.recheck()


def _check_capacity(resources,lease):
    capacity=resources['capacity']
    actual=dict(frozen_input_bytes=sum(binding.descriptor['size_bytes'] for binding in lease._registry._paths.values()),
        frozen_input_files=len(lease._registry._paths),frozen_input_directories=len(lease._directory_closure._dirs))
    for name,value in actual.items(): wire._literal(capacity[name],value)
    workspace=wire.decode(lease._job_bytes,262144)['workspace_root']; info=os.statvfs(workspace)
    if info.f_bavail*info.f_frsize<capacity['required_free_bytes']: raise ValueError('Frozen capacity/free-space reservation unavailable')


def _check_provenance_bindings(lease):
    provenance=lease._load['provenance']; pins=lease._load['runtime_requirements']['pins']
    wire._literal({key:provenance['interpreter'][key] for key in ('path','size_bytes','sha256')},pins['python_elf'])
    roots=lease._load['runtime_requirements']['roots']
    from palimpsest.held_provenance import _normalized
    for row in provenance['upstream']['files']:
        absolute=dict(row,path=provenance['upstream']['path']+'/'+row['path'])
        wire._literal(lease._registry.binding(absolute['path']).descriptor,absolute)
    for row in provenance['distributions']:
        lease.recheck(); index=wire.integer(row['root_index'],0,len(roots)-1)
        path=roots[index]+'/'+row['metadata_path']; binding=lease._registry.binding(path)
        os.lseek(binding.fd,0,os.SEEK_SET); header=bytearray()
        # Read metadata headers only from a genuinely owned FD. Whole bytes are
        # separately rehashed by the runtime before/after this bounded decode.
        while b'\n\n' not in header and b'\r\n\r\n' not in header:
            _deadline(lease); block=os.read(binding.fd,4096)
            if not block: break
            header.extend(block)
            if len(header)>wire.MiB: raise ValueError('Distribution metadata header bound')
        names={b'Name':[],b'Version':[]}
        for line in bytes(header).splitlines():
            if not line: break
            key,separator,value=line.partition(b':')
            if separator and key in names: names[key].append(value.strip().decode('utf-8'))
        if len(names[b'Name'])!=1 or len(names[b'Version'])!=1 or _normalized(names[b'Name'][0])!=_normalized(row['name']) or names[b'Version'][0]!=row['version']:
            raise ValueError('Held distribution metadata differs from frozen provenance')
        lease.recheck()


def _deadline(lease):
    if lease._thread_id!=threading.get_ident() or time.monotonic_ns()>=lease._deadline_ns: raise TimeoutError('Source outer deadline')


def _failure(job,lease,failures,resources):
    try: _failure_core(job,lease,failures,resources)
    except BaseException as error: failures.append(error)


def _failure_core(job,lease,failures,resources):
    # Bounded diagnostics never replace full original exception objects, and
    # never quote model/native payload excerpts from an exception message.
    phase=lease._phase
    flattened=list(wire.errors('Source failure diagnostics',failures).exceptions)
    primary=flattened[0]
    def item(error): return dict(type=type(error).__name__,message='Source operation failed during '+phase+'; original exception retained')
    retained=[]
    for row in wire.output_roster(job['case']['case_id'],job['source_run_id']):
        try: state=os.stat(job['workspace_root']+'/'+row['path'],follow_symlinks=False)
        except FileNotFoundError: continue
        if not stat.S_ISREG(state.st_mode): continue
        pending=row['role'].startswith('pending-')
        disposition='pending' if pending else 'incomplete' if row['role']=='snapshot' and lease._closed_source is None else 'closed'
        retained.append(dict(path=row['path'],disposition=disposition,size_bytes=state.st_size))
    if len(flattened)>33 or len(retained)>256:
        primary.add_note('Bounded failure JSON omitted: full ordered errors/retained prefix exceed diagnostic cap'); return
    value=dict(schema=wire.record_schema('failure',_lease_kind(lease)=='authored'),attempt_id=job['attempt_id'],source_run_id=job['source_run_id'],phase=phase,job=wire.describe('freeze/metadata/job.json',lease._job_bytes),primary=item(primary),teardown=[item(error) for error in flattened[1:]],retained=sorted(retained,key=lambda row:row['path']),status='failed-unqualified',claims=wire.CLAIMS.copy())
    try:
        roster={row['path']:row for row in wire.output_roster(job['case']['case_id'],job['source_run_id'])}
        _publish_bytes(job,f"output/controls/{job['source_run_id']}/failures/{phase}/failure.json",wire.encode(value,32768),roster,minimum_free_bytes=resources['capacity']['required_free_bytes'] if _lease_kind(lease)=='authored' else job['limits']['min_free_bytes'])
    except BaseException as error: failures.append(error); primary.add_note('Bounded failure diagnostics could not be published')
