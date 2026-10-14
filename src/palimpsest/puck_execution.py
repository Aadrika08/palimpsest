"""Held collection inputs and unchanged model; no reservation or owner grant."""
from contextlib import ExitStack
import copy
from pathlib import Path, PurePosixPath
import time

from . import artifacts, puck_collection_admission as admission
from . import puck_bundle_provenance as provenance, puck_model, puck_on_policy
from .puck_execution_files import HeldCollectionFiles

MiB=1024**2
RUNTIME_PIN={'path':'python3.11','size_bytes':21662864,
    'sha256':'572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'}
REQUIRED_SOURCES={
    'src/palimpsest/__init__.py','src/palimpsest/puck_on_policy.py',
    'src/palimpsest/puck_collection_admission.py','src/palimpsest/puck_bundle_provenance.py',
    'src/palimpsest/puck_execution.py','src/palimpsest/puck_execution_files.py',
    'src/palimpsest/puck_model.py','src/palimpsest/puck_student.py',
    'src/palimpsest/puck_learning.py','src/palimpsest/puck_teacher.py',
    'scripts/verify_puck_mechanics.py',
    'upstream/fly-gym/models/connectome_rnn_model.py','upstream/fly-gym/shared_config.py',
    'pyproject.toml','uv.lock','docs/plans/m6-puck-student-models-v1.json',
    'docs/plans/m6-puck-navigation-v3-on-policy-relabeling-protocol.json'}
_ROLES={'sources','admission','projection','index','bundle','historical','runtime'}
_EXACT={'admission':{'freeze.json':MiB,'envelope.json':MiB},
    'projection':{'collection.json':64*1024},'index':{'models.json':64*1024},
    'bundle':{'report.json':4*MiB,'protocol.json':4*MiB,'checkpoint.npz':MiB},
    'historical':{path:MiB for path in provenance.HISTORICAL_SOURCES},
    'runtime':{'python3.11':32*MiB}}
_FIELDS={'version','kind','owner_ordinal','execution_freeze_sha256','roles',
         'executable','qualification_claims'}


def _parse(raw, expected, deadline, runtime_pin):
    puck_on_policy._digest(expected,'Expected custody manifest')
    if type(raw) is not bytes or not 0<len(raw)<=MiB or puck_model.sha(raw)!=expected:
        raise ValueError('Bounded custody manifest differs from reviewed digest')
    value=artifacts._json(raw)
    admission._fields(value,_FIELDS,'Custody manifest')
    if puck_on_policy._canonical_bytes(value,'Custody manifest')!=raw:
        raise ValueError('Canonical custody manifest required')
    for name,wanted in {'version':1,'kind':'puck-collection-custody-v1',
            'executable':False,'qualification_claims':[]}.items():
        admission._equal(value[name],wanted,name)
    ordinal=value['owner_ordinal']
    if type(ordinal) is not int or not 0<=ordinal<12:
        raise ValueError('Exact collection owner ordinal required')
    puck_on_policy._digest(value['execution_freeze_sha256'],'Execution freeze')
    admission._fields(value['roles'],_ROLES,'Custody roles')
    holders={};total=0
    for role,description in value['roles'].items():
        admission._fields(description,{'root','files'},role)
        root=admission._path(description['root'],role+' root',absolute=True)
        if root.startswith('//'):
            raise ValueError('Custody root requires a single leading slash')
        entries=description['files']
        if type(entries) is not list or not 1<=len(entries)<=512:
            raise ValueError('Bounded custody file roster required')
        # Validate every descriptor before any role enters or opens a path.
        holder=HeldCollectionFiles(root,entries,deadline)
        caps=_EXACT.get(role)
        if caps is not None and {row['path'] for row in entries}!=set(caps):
            raise ValueError('Exact custody role files required: '+role)
        for row in entries:
            if row['size_bytes']>(caps[row['path']] if caps else MiB):
                raise ValueError('Custody role byte cap exceeded: '+role)
            total+=row['size_bytes']
        if role=='sources':
            if not REQUIRED_SOURCES<={row['path'] for row in entries}:
                raise ValueError('Required execution source closure missing')
            fixed={path for path in REQUIRED_SOURCES if not path.endswith('.py')}
            for row in entries:
                path=row['path']
                if path not in fixed and not (path.endswith(('.py','.xml')) and
                        any(path.startswith(prefix+'/') for prefix in
                            ('src/palimpsest','scripts','upstream/fly-gym'))):
                    raise ValueError('Source closure contains an unsupported executable path')
        holders[role]=holder
    if total>80*MiB:
        raise ValueError('Aggregate collection input ceiling exceeded')
    admission._equal(value['roles']['runtime']['files'],[runtime_pin],'Original runtime')
    # Repeated objects across roles are rejected; the holder additionally checks
    # actual inode aliases/single-link identities when each role is entered.
    paths=[str(PurePosixPath(role['root'])/entry['path'])
        for role in value['roles'].values() for entry in role['files']]
    if len(paths)!=len(set(paths)):
        raise ValueError('Custody input paths alias across roles')
    return value,holders


def _unique_held_objects(holders):
    import os
    objects=set()
    for holder in holders.values():
        for fd,*_ in holder._files.values():
            value=os.fstat(fd)
            identity=(value.st_dev,value.st_ino)
            if identity in objects:
                raise ValueError('Held input objects alias across custody roles')
            objects.add(identity)


def _dispatch(module):
    return (getattr(module.forward,'__func__',None),
            getattr(module._call_impl,'__func__',None),
            getattr(module._wrapped_call_impl,'__func__',None),type(module).__call__)


class _HeldCollectionExecution:
    """Private generic core for authored fixtures; never an execution authority."""

    def __init__(self,custody_raw,expected_custody_sha256,deadline,*,
                 bundle_admitter,runtime_pin):
        self._manifest,self._holders=_parse(custody_raw,expected_custody_sha256,deadline,runtime_pin)
        self._deadline=deadline
        self._bundle_admitter=bundle_admitter
        self._stack=ExitStack()
        self._state='new'
        self._model=None
        self._model_graph=None
        self._arrays=None
        self._description=None

    def _active(self):
        if self._state!='active':
            raise RuntimeError('Collection custody is failed, closed or not entered')
        if time.monotonic()>=self._deadline:
            self._fail()
            raise TimeoutError('Collection custody deadline exhausted')

    def _fail(self):
        self._state='failed'
        # Pass exceptional close to already-poisoned holders so their refusal
        # of nominal success does not replace the original admission failure.
        import sys
        details=sys.exc_info()
        if details[0] is None:
            details=(RuntimeError,RuntimeError('Collection custody failed'),None)
        self._stack.__exit__(*details)

    def _read(self,role,name,maximum):
        return self._holders[role].read(name,maximum)

    def _inventory(self):
        # No pathname reopen: inventories use the already held root directory.
        import os
        for role,holder in self._holders.items():
            if role=='sources':
                self._source_inventory(holder)
                continue
            expected_files={row['path'] for row in self._manifest['roles'][role]['files']}
            expected_dirs=set()
            for path in expected_files:
                parent=PurePosixPath(path).parent
                while str(parent)!='.':
                    expected_dirs.add(str(parent));parent=parent.parent
            found=set()
            # Only registered child names are descended into, preserving bounded
            # work even if an attacker adds an enormous foreign subtree.
            def visit(relative):
                key=(*holder.root.parts[1:],*PurePosixPath(relative).parts) if relative else holder.root.parts[1:]
                fd=holder._dirs[key][0]
                prefix=relative+'/' if relative else ''
                allowed={path[len(prefix):].split('/')[0]
                    for path in expected_files|expected_dirs if path.startswith(prefix)}
                names=set()
                with os.scandir(fd) as iterator:
                    for entry in iterator:
                        self._active()
                        if entry.name not in allowed or entry.name in names:
                            raise ValueError('Unregistered custody input entry')
                        names.add(entry.name)
                if names!=allowed:
                    raise ValueError('Missing custody input entry')
                for name in sorted(names):
                    path=prefix+name
                    if path in expected_dirs:visit(path)
                    else:found.add(path)
            visit('')
            if found!=expected_files:
                raise ValueError('Custody root inventory differs')

    def _source_inventory(self,holder):
        """Exact Python/XML closure; non-code upstream documentation is ignored.

        Directory discovery is bounded and anchored by the holder; newly seen
        directories join its final identity checks and descriptor cleanup.
        Dependencies outside this declared source scheme require later launcher
        qualification. This does not infer an upstream Git revision from files.
        """
        import os
        import stat
        found=set();count=0
        prefixes=('src/palimpsest','scripts','upstream/fly-gym')
        def visit(relative,depth):
            nonlocal count
            self._active()
            if depth>32:raise ValueError('Execution source inventory depth exceeded')
            key=(*holder.root.parts[1:],*relative.split('/'))
            fd=holder._directory(key)
            with os.scandir(fd) as iterator:
                for entry in iterator:
                    self._active();count+=1
                    if count>4096:raise ValueError('Execution source inventory count exceeded')
                    if (entry.name=='__pycache__' or entry.name.endswith('.pyc') or
                            any(ord(c)<32 or ord(c)==127 for c in entry.name)):
                        raise ValueError('Bytecode or noncanonical source inventory entry')
                    path=relative+'/'+entry.name
                    state=os.stat(entry.name,dir_fd=fd,follow_symlinks=False)
                    if stat.S_ISDIR(state.st_mode):visit(path,depth+1)
                    elif stat.S_ISREG(state.st_mode):
                        if path.endswith(('.py','.xml')):found.add(path)
                    else:raise ValueError('Linked or nonregular execution source entry')
        for prefix in prefixes:visit(prefix,0)
        expected={row['path'] for row in self._manifest['roles']['sources']['files']
                  if any(row['path'].startswith(prefix+'/') for prefix in prefixes)}
        if found!=expected:
            raise ValueError('Complete Python/XML execution source inventory differs')

    def __enter__(self):
        if self._state!='new':
            raise RuntimeError('Collection execution custody enters once')
        try:
            for holder in self._holders.values():self._stack.enter_context(holder)
            self._state='active'
            _unique_held_objects(self._holders)
            self.recheck()
            freeze_raw=self._read('admission','freeze.json',MiB)
            envelope_raw=self._read('admission','envelope.json',MiB)
            projection=self._read('projection','collection.json',64*1024)
            index=self._read('index','models.json',64*1024)
            sources={row['path']:row['sha256'] for row in self._manifest['roles']['sources']['files']}
            freeze=artifacts._json(freeze_raw)
            description=admission.admit_collection_envelope(envelope_raw,
                execution_freeze_raw=freeze_raw,
                expected_execution_freeze_sha256=self._manifest['execution_freeze_sha256'],
                collection_projection_raw=projection,original_model_index_raw=index,
                source_before=sources,source_after=sources,
                runtime_observation={**admission.RUNTIME,'upstream_sha256':freeze['upstream_sha256']})
            admission._equal(description['puck_on_policy']['ordinal'],self._manifest['owner_ordinal'],
                             'Owner ordinal')
            for owner in freeze['owners']:
                admission._equal(owner['cwd'],str(self._holders['sources'].root),'Execution source root')
            bundle={name:self._read('bundle',name,cap) for name,cap in _EXACT['bundle'].items()}
            historical={name:self._read('historical',name,MiB) for name in provenance.HISTORICAL_SOURCES}
            arrays,identity=self._bundle_admitter(seed=description['owner']['model_seed'],
                original_model_index_raw=index,bundle_payloads=bundle,
                historical_source_payloads=historical)
            self._arrays=puck_model.validate_arrays(arrays)
            admission._equal(identity['training_seed'],description['owner']['model_seed'],'Bundle seed')
            self._description=copy.deepcopy(description)
            self._description['model_identity']=copy.deepcopy(identity)
            self.recheck()
            return self
        except BaseException:
            self._fail()
            raise

    @property
    def description(self):
        self._active()
        return copy.deepcopy(self._description)

    def _parameters(self):
        import torch
        framework=torch.nn.modules.module
        if framework._global_forward_hooks or framework._global_forward_pre_hooks:
            raise ValueError('Global model hooks differ from the uninstrumented inference profile')
        modules=list(self._model.named_modules())
        if len(modules)!=len(self._model_graph):
            raise ValueError('Live collection model topology differs')
        for (name,module),(expected_name,expected_module,expected_type,expected_dispatch) in zip(modules,self._model_graph):
            if (name!=expected_name or module is not expected_module or type(module) is not expected_type
                    or _dispatch(module)!=expected_dispatch or module._compiled_call_impl is not None
                    or module.training or module._forward_hooks or module._forward_pre_hooks
                    or module._backward_hooks or module._backward_pre_hooks):
                raise ValueError('Live collection model computation or evaluation mode differs')
        state=self._model.state_dict()
        if set(state)!=set(self._arrays):
            raise ValueError('Live model parameter names differ')
        for name,value in state.items():
            if (value.device.type!='cpu' or value.dtype!=torch.float32 or
                    tuple(value.shape)!=self._arrays[name].shape or
                    value.detach().numpy().tobytes()!=self._arrays[name].tobytes()):
                raise ValueError('Live model parameters differ from admitted arrays')

    def recheck(self):
        self._active()
        try:
            for holder in self._holders.values():holder.recheck()
            self._inventory()
            # Inventory can discover new held directory edges or race a rename.
            # Check all edges and input bytes again before returning admission.
            for holder in self._holders.values():holder.recheck()
            if self._model is not None:self._parameters()
            self._active()
        except BaseException:
            self._fail()
            raise

    def materialize_original_model(self):
        self._active()
        if self._model is not None:
            self._fail()
            raise RuntimeError('Collection model is materialized only once')
        try:
            self.recheck()
            import torch
            model=puck_model.make_model(self._description['owner']['model_seed'])
            model.load_state_dict({name:torch.from_numpy(value.copy())
                                  for name,value in self._arrays.items()},strict=True)
            model.eval()
            self._model=model
            self._model_graph=[(name,module,type(module),_dispatch(module))
                               for name,module in model.named_modules()]
            self.recheck()
            return model
        except BaseException:
            self._fail()
            raise

    def check_parameters(self):
        self._active()
        if self._model is None:
            self._fail()
            raise RuntimeError('Collection model has not been materialized')
        self.recheck()
        return copy.deepcopy(self._description['model_identity'])

    def stage_interval(self,sensors,world,teacher_mode,own,*,terminal_reason,capture_query_state):
        self._active()
        try:
            self.check_parameters()
            admission._equal(world.get('goal_xy'),self._description['scene']['layout']['goal_xy'],
                             'Collection scene goal')
            staged=puck_on_policy.stage_interval(sensors,world,teacher_mode,own,self._model,
                terminal_reason=terminal_reason,capture_query_state=capture_query_state)
            self.recheck()
            return staged
        except BaseException:
            self._fail()
            raise

    def native_interval(self,env,observation,state,world,contact,own,teacher_mode,
                        probe,writer):
        """One custodied native/publication interval; no owner allocation grant.

        The launcher must separately admit native construction, reservation,
        runtime, process ownership and final owner close. No loose model can
        bypass this context's staged inference or publication checks.
        """
        try:
            self._active()
            from scripts.verify_puck_mechanics import on_policy_interval
            return on_policy_interval(env,observation,state,world,contact,own,
                teacher_mode,None,probe,writer,execution=self)
        except BaseException:
            writer.stop()
            self._fail()
            raise

    def __exit__(self,kind,error,traceback):
        if self._state!='active':
            if kind is None:raise RuntimeError('Collection custody failed before context exit')
            return False
        try:
            self.recheck()
        finally:
            try:self._stack.close()
            finally:
                if self._state=='active':self._state='closed'
        return False


class HeldCollectionExecution(_HeldCollectionExecution):
    """Fixed original pins; caller must obtain later full execution admission.

    This binds files and staged decisions only. Runtime version/dependency and
    upstream observations, reservation, native state, process and publication
    qualification remain separate requirements. No actual owner route uses it.
    """

    def __init__(self,custody_raw,expected_custody_sha256,deadline):
        super().__init__(custody_raw,expected_custody_sha256,deadline,
            bundle_admitter=provenance.admit_original_bundle_bytes,runtime_pin=RUNTIME_PIN)
        self._check_import_origins()

    def _check_import_origins(self):
        import sys
        root=Path(__file__).absolute().parents[2]
        if str(self._holders['sources'].root)!=str(root):
            raise ValueError('Current execution source root differs from admitted root')
        registered={row['path'] for row in self._manifest['roles']['sources']['files']}
        for name,loaded in list(sys.modules.items()):
            if name=='palimpsest' or name.startswith('palimpsest.'):
                filename=getattr(loaded,'__file__',None)
                if type(filename) is not str:
                    raise ValueError('Current package import has no source origin')
                try:relative=Path(filename).absolute().relative_to(root).as_posix()
                except ValueError as error:
                    raise ValueError('Current package import comes from another source root') from error
                if relative not in registered:
                    raise ValueError('Current imported package source was not admitted')

    def recheck(self):
        self._active()
        try:
            self._check_import_origins()
            super().recheck()
        except BaseException:
            self._fail()
            raise
