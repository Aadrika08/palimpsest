"""Standalone bounded navigation audit worker, never generic replay registration.

The parent owns frozen admission, namespace/source/model pins, the writer lease,
CPU accounting and the 120s process watchdog. This worker never acquires a lease,
extracts/downloads assets, retries a condition or calls action replay. Importing
this module loads no model or native runtime. Private bindings are software-test
seams only; the CLI always uses production bindings.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

MiB = 1024**2
SNAPSHOT_BYTES = 16 * MiB
RECORDING_BYTES = 15 * MiB
SCENARIOS = {'reproduction', 'sparse-navigation', 'vision-ablation', 'texture-variation'}
GAINS = (1., .5, .75, 1.25)


class WorkerFailure(RuntimeError):
    """The retained stage report describes a failed, non-retryable job."""


class _Bindings(SimpleNamespace):
    """Private injected software-test bindings; unavailable through the CLI."""


def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _hash(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Expected an externally pinned SHA256')
    return value


def _path(value):
    if type(value) is not str or not Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('Expected an absolute path without parent traversal')
    return Path(value)


def validate_config(config):
    """Pure admission checks; do not inspect any source/model/namespace data."""
    required = {'root_id','repo_root','asset_root','scenario','texture','seed','ticks',
        'check_parity','device','controller','prepared_graph_directory','input_files'}
    if type(config) is not dict or set(config) != required:
        raise ValueError('Worker configuration has unexpected fields')
    if type(config['root_id']) is not str or re.fullmatch('[A-Za-z0-9_-]{1,80}',config['root_id']) is None:
        raise ValueError('Invalid frozen root ID')
    if config['scenario'] not in SCENARIOS or config['controller'] != 'flynn' or config['device'] != 'cpu':
        raise ValueError('Only approved navigation CPU FLYNN profiles are admitted')
    if config['texture'] not in ('checker','realistic') or config['texture']=='realistic' and config['scenario']!='texture-variation':
        raise ValueError('Invalid profile/texture combination')
    if config['check_parity'] is not False:
        raise ValueError('Parity must be false: a reference forward is forbidden')
    if type(config['ticks']) is not int or not 1 <= config['ticks'] <= 64:
        raise ValueError('Ticks must be an integer in [1,64]')
    if type(config['seed']) is not int or not 0 <= config['seed'] < 2**31:
        raise ValueError('Invalid frozen seed')
    for name in ('repo_root','asset_root','prepared_graph_directory'):
        _path(config[name])
    rows = config['input_files']
    if type(rows) is not list or not 1 <= len(rows) <= 10000:
        raise ValueError('A bounded externally pinned input roster is required')
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != {'path','sha256','size_bytes'}:
            raise ValueError('Malformed pinned input')
        path = _path(row['path']); _hash(row['sha256'])
        if str(path) in seen or type(row['size_bytes']) is not int or row['size_bytes'] < 0:
            raise ValueError('Invalid or duplicate pinned input')
        seen.add(str(path))
    return copy.deepcopy(config)


def _regular(path):
    path = Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)) or not path.is_file():
        raise ValueError('Input must be a regular file without symlink traversal')
    return path


def _verify_inputs(config):
    for row in config['input_files']:
        path = _regular(row['path'])
        if path.stat().st_size != row['size_bytes'] or file_sha256(path) != row['sha256']:
            raise ValueError('Frozen input differs: '+str(path))


def scientific_state_digest(snapshot, *, digest=None):
    """Exclude precisely two destination recorder identities, no scientific state."""
    if digest is None:
        from palimpsest.snapshots import state_digest
        digest = state_digest
    if type(snapshot) is not dict or type(snapshot.get('application')) is not dict:
        raise ValueError('Complete application state is required')
    state = copy.deepcopy(snapshot)
    for name in ('source_run_id','event_prefix'):
        if name not in state['application']:
            raise ValueError('Missing application recorder identity')
        del state['application'][name]
    return digest(state)


class _SnapshotBudget:
    def __init__(self, budget, maximum=SNAPSHOT_BYTES):
        self.budget, self.maximum = budget, maximum
    def check(self, additional_bytes, *, path):
        if additional_bytes > self.maximum:
            raise ValueError('Serialized snapshot exceeds 16MiB worker cap')
        return self.budget.check(additional_bytes,path=path)


def _write_json(path, value, budget):
    payload = (json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
    if len(payload) > 128*1024:
        raise ValueError('Worker control record exceeds 128KiB')
    budget.check(len(payload),path=path)
    with Path(path).open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def _descriptor(path, snapshot, bindings):
    return {'path':str(path),'file_sha256':file_sha256(path),'state_sha256':bindings.digest(snapshot)}


def _load_anchor(descriptor, config, bindings):
    if type(descriptor) is not dict or set(descriptor) != {'path','file_sha256','state_sha256'}:
        raise ValueError('An externally frozen original anchor descriptor is required')
    _hash(descriptor['file_sha256']); _hash(descriptor['state_sha256'])
    path = _regular(_path(descriptor['path']))
    if path.stat().st_size > SNAPSHOT_BYTES or file_sha256(path) != descriptor['file_sha256']:
        raise ValueError('Original anchor ZIP checksum differs')
    snapshot = bindings.read(path)
    if bindings.digest(snapshot) != descriptor['state_sha256']:
        raise ValueError('Original anchor typed state checksum differs')
    app = snapshot['application']
    expected = {'seed':config['seed'],'scenario':config['scenario'],'texture':config['texture'],
        'controller':'flynn','phase':'paused','episode':0,'total_tick':0}
    if any(type(app.get(key)) is not type(value) or app.get(key) != value for key,value in expected.items()):
        raise ValueError('Original anchor does not match frozen fresh root')
    return snapshot


def _run(mode, config, output, *, storage_budget, anchor_descriptor=None, gain=1, bindings):
    config = validate_config(config)
    if mode not in ('prepare-anchor','execute-condition'):
        raise ValueError('Unknown worker mode')
    if type(gain) not in (int,float) or gain not in GAINS or mode=='prepare-anchor' and gain != 1:
        raise ValueError('Only registered baseline/candidate gains are admitted')
    if mode=='prepare-anchor' and anchor_descriptor is not None:
        raise ValueError('Anchor preparation must start fresh')
    output = Path(output).absolute()
    storage_budget.check(0,path=output)
    output.mkdir(parents=False,exist_ok=False)
    report = {'schema':'change-audit-pilot-worker-v1','mode':mode,'root_id':config['root_id'],
        'gain':float(gain),'actual_scope':bindings.scope,'status':'failed','ticks':0,
        'forward_attempts':0,'before_first_tick_equal':False,'completed_requested_ticks':False,
        'check_parity':False,'sampling_eligibility_verified':False,'certified_improvement':False,
        'runtime_qualification':False,'errors':[]}
    engine = hook = None
    try:
        _verify_inputs(config)
        original = None
        if mode=='execute-condition':
            original = _load_anchor(anchor_descriptor,config,bindings)
            derivation = bindings.derive(original,gain,expected_snapshot_sha256=anchor_descriptor['state_sha256'])
            expected = derivation['snapshot']
            _write_json(output/'derivation-receipt.json',derivation['receipt'],storage_budget)
            report['anchor'] = copy.deepcopy(anchor_descriptor)
            if gain == 1:
                report['snapshot'] = copy.deepcopy(anchor_descriptor)
            else:
                path = output/'derived.snp'
                bindings.save(expected,path,storage_budget=_SnapshotBudget(storage_budget))
                report['snapshot'] = _descriptor(path,expected,bindings)
        engine = bindings.create_engine(config,output/'recording',storage_budget)
        engine.policy = bindings.wrap(engine.policy,gain)
        if bindings.scope == 'actual-cpu-flynn-navigation-engineering-pilot':
            engine.writer.manifest.update(audit_worker={'root_id':config['root_id'],
                'standalone_research_artifact':True,'generic_replay_registered':False,
                'check_parity':False,'policy_provenance':engine.policy.provenance})
            engine.writer.event('audit_gain_adapter_registered',gain=float(gain),
                provenance=engine.policy.provenance,generic_replay_registered=False)
        def count_forward(_module,_inputs):
            report['forward_attempts'] += 1
        hook = engine.policy.agent.cell.register_forward_pre_hook(count_forward, prepend=True)
        if engine.phase != 'paused' or engine.total_tick or engine.episode:
            raise ValueError('Engine did not open at the fresh paused boundary')
        if mode=='prepare-anchor':
            initial = bindings.capture(engine)
            if report['forward_attempts'] or engine.total_tick:
                raise RuntimeError('Anchor capture performed a policy inference or tick')
            # Validate gain-one snapshot identity using the same pure registered derivation.
            bindings.derive(initial,1,expected_snapshot_sha256=bindings.digest(initial))
            path = output/'anchor.snp'
            bindings.save(initial,path,storage_budget=_SnapshotBudget(storage_budget))
            report['anchor'] = _descriptor(path,initial,bindings)
            report['stop_reason'] = 'paused_anchor_prepared'
        else:
            engine.restore_branch(expected,replace_controller=False)
            actual = bindings.capture(engine)
            reference = scientific_state_digest(expected,digest=bindings.digest)
            observed = scientific_state_digest(actual,digest=bindings.digest)
            report['before_first_tick_expected_sha256'] = reference
            report['before_first_tick_observed_sha256'] = observed
            if reference != observed:
                raise ValueError('Restored scientific state differs before first tick')
            report['before_first_tick_equal'] = True
            if report['forward_attempts']:
                raise ValueError('Restore/capture performed an inference')
            for index in range(config['ticks']):
                before = engine.total_tick
                command = {'id':f'audit-step-{index:03d}','kind':'step',
                    'expected_state':engine.phase,'expected_episode':engine.episode,
                    'expected_revision':engine.revision,'payload':{}}
                engine.submit(command)
                engine.advance()
                if engine.total_tick == before+1:
                    report['ticks'] += 1
                if engine.phase == 'failed':
                    raise RuntimeError('Engine failed during actual condition inference/recording')
                if engine.total_tick != before+1 or report['forward_attempts'] != report['ticks']:
                    raise RuntimeError('Expected exactly one actual forward per completed tick')
                if engine.phase in ('terminated','truncated'):
                    report['stop_reason'] = 'natural_terminal'
                    report['terminal_outcome'] = copy.deepcopy(engine.last_outcome)
                    break
                if engine.phase != 'paused':
                    raise RuntimeError('Single own-policy tick did not return to paused boundary')
            else:
                report['stop_reason'] = 'tick_limit'
            report['completed_requested_ticks'] = report['ticks']==config['ticks']
            contacts = engine.metrics.get('contact_ticks')
            if type(contacts) is not int or not 0 <= contacts <= report['ticks']:
                raise ValueError('Malformed observed contact-tick count')
            report['engineering_observed_input_contact_fraction'] = contacts/report['ticks'] if report['ticks'] else None
            report['contact_fraction_definition'] = 'pre-control input contact ticks / completed own-policy ticks; engineering observation only'
        if mode=='prepare-anchor' and (report['ticks'] or report['forward_attempts']):
            raise RuntimeError('Anchor preparation performed a policy inference or tick')
    except BaseException as error:
        report['errors'].append({'stage':'worker','type':type(error).__name__,'message':str(error)[:2048]})
    finally:
        if engine is not None:
            try:
                engine.close()
            except BaseException as error:
                report['errors'].append({'stage':'close','type':type(error).__name__,'message':str(error)[:2048]})
        if hook is not None:
            try:
                hook.remove()
            except BaseException as error:
                report['errors'].append({'stage':'hook_cleanup','type':type(error).__name__,'message':str(error)[:2048]})
        try:
            _verify_inputs(config)
            if anchor_descriptor is not None:
                _load_anchor(anchor_descriptor,config,bindings)
        except BaseException as error:
            report['errors'].append({'stage':'input_recheck','type':type(error).__name__,'message':str(error)[:2048]})
    if report['forward_attempts'] != report['ticks'] and not report['errors']:
        report['errors'].append({'stage':'post_close_accounting','type':'RuntimeError',
            'message':'Actual forward attempts differ from completed ticks after close'})
    report['status'] = 'failed' if report['errors'] else 'completed'
    _write_json(output/'stage-report.json',report,storage_budget)
    if report['errors']:
        raise WorkerFailure('Worker failed; retained '+str(output/'stage-report.json'))
    return report


def _verify_loaded_modules(config):
    """Bind production imports to the same source root the parent authenticated."""
    import importlib
    for name in ('assets','engine','flynn','snapshots','velocity_gain','velocity_gain_snapshot'):
        module = importlib.import_module('palimpsest.'+name)
        found = getattr(module,'__file__',None)
        expected = Path(config['repo_root'])/'src'/'palimpsest'/(name+'.py')
        if type(found) is not str or Path(found).absolute() != expected.absolute():
            raise ValueError('Loaded project module differs from frozen repo_root: '+name)


def _production_engine(config, recording, budget):
    """Engine lifecycle with its graph resolver restricted to an existing cache.

    Engine.open imports prepare_graph from assets inside the method. In this
    isolated sequential worker, temporarily replace exactly that module binding
    with the read-only cache-validation branch. The extraction function is never
    called, including when the directory disappears. Restore the binding even if
    Engine.open raises; its ordinary failure cleanup remains authoritative.
    """
    _verify_loaded_modules(config)
    from palimpsest import assets
    from palimpsest.engine import Engine

    def cached_graph(repo_root, asset_root):
        root, asset_root = Path(repo_root), Path(asset_root)
        if root != Path(config['repo_root']) or asset_root != Path(config['asset_root']):
            raise ValueError('Graph resolver received different frozen roots')
        manifest = assets.load_manifest(root)
        archive = next(row for row in manifest['files'] if row['id']=='graph_archive')
        if not assets._verified(assets._inside(asset_root,archive['path']),archive):
            raise ValueError('Existing graph archive differs; acquisition is forbidden')
        prepared = assets._inside(asset_root,'graph-'+archive['sha256'])
        if prepared != Path(config['prepared_graph_directory']) or not prepared.is_dir():
            raise ValueError('Frozen pre-existing graph directory required; extraction forbidden')
        metadata = json.loads(_regular(prepared/'palimpsest-prepared.json').read_text())
        edge = assets._inside(prepared,metadata['edge_path'])
        if metadata['archive_sha256'] != archive['sha256'] or not assets._verified(edge,manifest['graph']['edge_identity']):
            raise ValueError('Prepared graph differs')
        assets._check_mappings(root,edge.parent,manifest['graph']['mapping_files'],copy_missing=False)
        return edge

    original = assets.prepare_graph
    assets.prepare_graph = cached_graph
    try:
        return Engine.open(config['repo_root'],config['asset_root'],recording,
            controller='flynn',device='cpu',seed=config['seed'],max_bytes=RECORDING_BYTES,
            scenario=config['scenario'],texture=config['texture'],storage_budget=budget)
    finally:
        assets.prepare_graph = original


def _production_bindings(config):
    _verify_loaded_modules(config)
    # These imports do not load a model; runtime/model imports live in create_engine.
    from palimpsest import snapshots
    from palimpsest.velocity_gain import VelocityGainPolicy
    from palimpsest.velocity_gain_snapshot import derive_gain_snapshot
    return _Bindings(create_engine=_production_engine,wrap=VelocityGainPolicy,
        capture=lambda engine:snapshots.capture(engine.env,engine.observation,policy=engine.policy,
            teacher=engine.teacher,application=engine.application_state()),
        read=snapshots.read_snapshot,save=snapshots.save_snapshot,derive=derive_gain_snapshot,
        digest=snapshots.state_digest,scope='actual-cpu-flynn-navigation-engineering-pilot')


def _production_budget(budget):
    if budget.limits.max_bytes > 512*MiB or budget.limits.min_free_bytes < 6*1024**3:
        raise ValueError('Production pilot budget requires <=512MiB retained and >=6GiB free floor')


def prepare_anchor(config, output, *, storage_budget):
    validate_config(config); _production_budget(storage_budget)
    return _run('prepare-anchor',config,output,storage_budget=storage_budget,bindings=_production_bindings(config))


def execute_condition(config, output, anchor_descriptor, gain, *, storage_budget):
    validate_config(config); _production_budget(storage_budget)
    return _run('execute-condition',config,output,storage_budget=storage_budget,
        anchor_descriptor=anchor_descriptor,gain=gain,bindings=_production_bindings(config))


def _finite_json(path, *, expected_sha256=None):
    def reject(value): raise ValueError('Nonfinite JSON constant: '+value)
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    path=_regular(path)
    with path.open('rb') as stream:
        payload=stream.read(2*MiB+1)
    if len(payload) > 2*MiB: raise ValueError('Frozen config/descriptor exceeds 2MiB')
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != _hash(expected_sha256):
        raise ValueError('Frozen config checksum differs')
    return json.loads(payload,parse_constant=reject,object_pairs_hook=unique)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('prepare-anchor','execute-condition'))
    parser.add_argument('--config',required=True); parser.add_argument('--expected-config-sha256',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--pilot-root',required=True)
    parser.add_argument('--anchor'); parser.add_argument('--expected-anchor-sha256')
    parser.add_argument('--gain',type=float,default=1.)
    args=parser.parse_args(argv)
    anchor_expected=None
    if args.mode=='execute-condition':
        if not args.anchor or not args.expected_anchor_sha256:
            raise ValueError('Frozen anchor descriptor and external SHA256 are required')
        anchor_expected=_hash(args.expected_anchor_sha256)
    elif args.anchor or args.expected_anchor_sha256 or args.gain!=1:
        raise ValueError('Anchor preparation requires fresh gain one')
    expected=_hash(args.expected_config_sha256)
    config=_finite_json(args.config,expected_sha256=expected)
    from palimpsest.storage import StorageBudget, StorageLimits
    # Share the parent's single-writer lease; native log/control headroom is reserved.
    budget=StorageBudget([_path(args.pilot_root)],StorageLimits(max_bytes=512*MiB,min_free_bytes=6*1024**3),
        headroom_bytes=16*MiB)
    if args.mode=='prepare-anchor':
        result=prepare_anchor(config,args.output,storage_budget=budget)
    else:
        anchor=_finite_json(args.anchor,expected_sha256=anchor_expected)
        result=execute_condition(config,args.output,anchor,args.gain,storage_budget=budget)
    if file_sha256(_regular(args.config)) != expected: raise WorkerFailure('Frozen config changed during execution')
    if anchor_expected is not None and file_sha256(_regular(args.anchor)) != anchor_expected:
        raise WorkerFailure('Frozen anchor descriptor changed during execution')
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
