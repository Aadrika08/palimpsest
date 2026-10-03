"""Exact six frozen executed-target research candidates; development only."""
from dataclasses import dataclass
import importlib.metadata
import hashlib
import math
from pathlib import Path
import platform
from . import artifacts,male_model,male_policy,male_research

INDEX_PATH='data/manifests/male-recovery-research-development-v1.json'
INDEX_SHA256='cf50fd2f6a96cfb1afd43e23eae05b76522116abdcf544ef41735033dc52b6b5'
PROTOCOL_PATH='docs/plans/m7-recovery-development-protocol.json'
PROTOCOL_SHA256='eebc94145507cffe26965704ed33b9be68cb91558bde0f5aa1b1d3cf90fcdcba'
PAIR_SEEDS=male_research.PAIR_SEEDS
CONTROLLERS=male_research.CONTROLLERS
MAX_JSON=4*1024**2


def protocol(root=None):
    root=Path(root) if root else Path(__file__).resolve().parents[2]
    raw=artifacts._read(root/PROTOCOL_PATH,65536)
    if male_policy._sha(raw)!=PROTOCOL_SHA256:raise ValueError('Recovery development protocol changed')
    return artifacts._json(raw)


def planned(stage):
    if stage!='dev':raise ValueError('Recovery development only; held-out remains locked')
    return male_research.planned('dev')


def read_pin(path,pin,cap=MAX_JSON):
    raw=artifacts._read(path,cap)
    if male_policy._sha(raw)!=pin:raise ValueError('Frozen recovery research input differs: '+str(path))
    return artifacts._json(raw)


def _index(root,path,pin):
    if pin!=INDEX_SHA256 or artifacts._safe_path(path)!=artifacts._safe_path(Path(root)/INDEX_PATH):
        raise ValueError('Only the exact named recovery research index is allowed')
    return read_pin(path,INDEX_SHA256)


def _gate(root,index):
    producer=artifacts._safe_path(Path(root)/index['producer_root'])
    terminal=read_pin(producer/index['training_terminal']['path'],index['training_terminal']['sha256'])
    outer=read_pin(producer/index['training_supervisor']['path'],index['training_supervisor']['sha256'])
    if (terminal.get('status')!='passed-research-training' or terminal.get('head')!=index['training_source_commit'] or
            terminal.get('inventories_unchanged') is not True or terminal.get('completed_pair_content_unchanged') is not True or
            terminal.get('before_inventory_sha256')!=index['before_after_inventory_sha256'] or
            terminal.get('after_inventory_sha256')!=index['before_after_inventory_sha256'] or
            outer.get('status')!='completed' or type(outer.get('returncode')) is not int or outer['returncode']!=0 or
            outer.get('elapsed_seconds',math.inf)>2160 or 'error' in outer or 'failure' in outer):
        raise ValueError('Normal unchanged completed recovery training required')
    cleanup=terminal.get('cleanup',{})
    if (cleanup.get('sampler_stopped') is not True or cleanup.get('sample_errors')!=[] or
            cleanup.get('forced_signals')!=[] or cleanup.get('survivors')!=[]):
        raise ValueError('Recovery training cleanup differs')
    rows=terminal.get('pairs')
    if (not isinstance(rows,list) or [r.get('training_seed') for r in rows]!=list(PAIR_SEEDS) or
            any(r.get('status')!='completed' or r.get('supervision',{}).get('status')!='completed' or
                r['supervision'].get('returncode')!=0 or 'error' in r['supervision'] or 'failure' in r['supervision'] for r in rows)):
        raise ValueError('All three normal completed training pairs required')
    code=index['training_source_code'];reader=code['reader']
    historical={**reader['current_reader_sources'],'scripts/prepare_male_recovery_data.py':reader['adapter_sha256'],**code['trainer']}
    for name,pin in historical.items():
        if male_policy._sha(artifacts._read(producer/name,MAX_JSON))!=pin:raise ValueError('Historical producer source changed')
    # Numerical semantics remain fixed; current admission/Engine producer identities are separate.
    if male_policy._sha(artifacts._read(Path(root)/'src/palimpsest/male_model.py',MAX_JSON))!=reader['current_reader_sources']['src/palimpsest/male_model.py']:
        raise ValueError('Current numerical model differs from admitted training')
    data=read_pin(producer/index['data_manifest']['path'],index['data_manifest']['sha256'])
    if (data.get('status')!='prepared-research-only' or data.get('counts')!={'train':2117,'dev':1228,'held_out':0} or
            {key:len(val) for key,val in data.get('ordered_sources',{}).items()}!={'train':10,'dev':4,'held_out':0} or
            [r.get('windows') for r in data.get('recovery_admission',[])]!=[[32,32,3],[32,32,3]]):
        raise ValueError('Exact executed-target censored data required')
    return producer,data,terminal


def _history(model):
    rows=model.get('history')
    if (model.get('status')!='completed' or not isinstance(rows,list) or len(rows)!=20 or
            any(type(row.get('epoch')) is not int for row in rows) or [row['epoch'] for row in rows]!=list(range(1,21))):
        raise ValueError('Every fixed recovery training epoch required')
    for row in rows:
        dev=row.get('dev',{})
        if type(row.get('train_ticks')) is not int or row['train_ticks']!=2117 or type(dev.get('ticks')) is not int or dev['ticks']!=1228:
            raise ValueError('Recovery epoch counts differ')
        for val in (row.get('train_loss'),dev.get('loss'),dev.get('velocity_mae'),dev.get('wrapped_heading_mae_radians')):
            if type(val) not in (int,float) or not math.isfinite(val) or val<0:raise ValueError('Invalid recovery fit metric')
    if type(model.get('selected_epoch')) is not int or model['selected_epoch']!=min(range(1,21),key=lambda n:rows[n-1]['dev']['loss']):
        raise ValueError('Earliest recovery dev minimum required')


def _bundle(root,index,seed,variant,graph_path,graph_manifest):
    if type(seed) is not int or seed not in PAIR_SEEDS or variant not in male_policy.VARIANTS:
        raise ValueError('Fixed recovery pair/variant required')
    producer,data,terminal=_gate(root,index)
    pair=index['pairs'][PAIR_SEEDS.index(seed)];directory=producer/pair['directory']
    names=['report.json','protocol.json','original-graph.json','original.pt','degree_rewired-graph.json','degree_rewired.pt']
    paths=[directory/name for name in names];before=artifacts._fingerprint(paths)
    payloads={name:artifacts._read(path,male_policy.MAX_FILE_BYTES) for name,path in zip(names,paths)}
    if male_policy._sha(payloads['report.json'])!=pair['report_sha256']:raise ValueError('Exact recovery training report required')
    report=artifacts._json(payloads['report.json']);training=artifacts._json(payloads['protocol.json'])
    if (report.get('status')!='completed-research-training' or report.get('training_completed') is not True or
            report.get('training_attempted') is not True or report.get('held_out_status')!='locked_unopened' or
            report.get('held_out_used_for_selection') is not False or report.get('qualification_claims')!=[] or
            report.get('data_manifest_sha256')!=index['data_manifest']['sha256'] or
            report.get('protocol_sha256')!=male_model.digest(training) or training.get('prepared_data')!=data or
            training.get('data_manifest_sha256')!=index['data_manifest']['sha256'] or
            training.get('source_code')!=index['training_source_code'] or training.get('model_inputs')!=index['model_inputs'] or
            training.get('runtime')!=index['runtime'] or training.get('feature_protocol')!=male_model.FEATURE_PROTOCOL):
        raise ValueError('Recovery report/data/source/protocol differs')
    # Frozen semantic settings come from the tracked preregistration, not the live producer module.
    learning=read_pin(Path(root)/'docs/plans/m7-recovery-learning-protocol.json',
        '091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28',65536)
    expected={**learning['training'],'training_seed':seed,'rewiring_seed':seed,'variants':list(male_policy.VARIANTS),
        'data_manifest_sha256':index['data_manifest']['sha256'],'research_protocol_sha256':
        '091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28',
        'order':learning['ordering'],'hidden_state':learning['right_censoring'],'wall_budget_seconds':600,
        'output_limit_bytes':64*1024**2,'qualification_claims':[]}
    if training.get('training')!=expected:raise ValueError('Frozen recovery fitting settings differ')
    ledger=report.get('files')
    if not isinstance(ledger,list) or len(ledger)!=5:raise ValueError('Recovery artifact ledger differs')
    entries={}
    for item in ledger:
        if (not isinstance(item,dict) or set(item)!={'path','sha256','size_bytes'} or item['path'] not in names[1:] or item['path'] in entries or
                type(item['size_bytes']) is not int or item['size_bytes']!=len(payloads[item['path']]) or item['sha256']!=male_policy._sha(payloads[item['path']])):
            raise ValueError('Recovery artifact byte/hash ledger differs')
        entries[item['path']]=item
    original=male_model.load_graph(graph_path,graph_manifest);control,rewiring=male_model.rewire(original,seed)
    graphs={'original':original,'degree_rewired':control}
    descriptions={name:{key:g[key] for key in ('topology_sha256','ordered_ids_sha256','source_graph_sha256','graph_manifest_sha256','type_missing_ids')} for name,g in graphs.items()}
    if training.get('graphs')!=descriptions or training.get('rewiring')!=rewiring:
        raise ValueError('Recovery topology/ordered IDs/rewiring differs')
    if not isinstance(report.get('models'),dict) or set(report['models'])!=set(male_policy.VARIANTS):raise ValueError('Both paired recovery models required')
    for name,model in report['models'].items():
        _history(model)
        if (model.get('graph_file')!=name+'-graph.json' or model.get('checkpoint')!=entries[name+'.pt'] or
                artifacts._json(payloads[name+'-graph.json'])!=graphs[name]):raise ValueError('Recovery model/checkpoint graph differs')
    # Recheck the source gate and byte fingerprint before returning admitted bytes.
    _gate(root,index)
    if artifacts._fingerprint(paths)!=before:raise ValueError('Recovery bundle changed during admission')
    provenance={'profile':male_policy.PROFILE,'variant':variant,'training_seed':seed,
        'training_report_sha256':pair['report_sha256'],'protocol_sha256':report['protocol_sha256'],
        'checkpoint_sha256':entries[variant+'.pt']['sha256'],'graph_sha256':male_model.digest(graphs[variant]),
        **descriptions[variant],'cell_source_sha256':male_model.CELL_SHA256,
        'feature_protocol':male_model.FEATURE_PROTOCOL,'feature_protocol_sha256':male_model.digest(male_model.FEATURE_PROTOCOL),
        'data_manifest_sha256':index['data_manifest']['sha256'],'training_source_code':index['training_source_code'],
        'training_runtime':index['runtime'],'qualification_claims':[],'biological_sensor_mapping':False,
        'evaluation_limit':'fixed executed-target research candidate; development only, no production admission or generalization claim'}
    return graphs[variant],payloads[variant+'.pt'],provenance


def runtime_identity():
    return {'python':platform.python_version(),'numpy':importlib.metadata.version('numpy'),
        'torch_distribution':importlib.metadata.version('torch')}


def resolve(root,assets,manifest_path,manifest_sha256,seed,controller,expected_identity=None):
    if controller not in male_policy.CONTROLLERS or type(seed) is not int or seed not in PAIR_SEEDS:
        raise ValueError('Fixed recovery seed/controller required')
    index=_index(root,manifest_path,manifest_sha256);protocol(root)
    if runtime_identity()!=index['runtime']:raise ValueError('Pinned recovery CPU runtime differs')
    args={'directory':artifacts._safe_path(Path(root)/index['producer_root'])/index['pairs'][PAIR_SEEDS.index(seed)]['directory'],
        'variant':male_policy.CONTROLLERS[controller],'expected_report_sha256':index['pairs'][PAIR_SEEDS.index(seed)]['report_sha256'],
        'graph_path':Path(assets)/'male-reduced-v1/source-graph.json','graph_manifest':Path(root)/'data/manifests/malecns-reduced-neighborhood-v1.json',
        'cell_path':Path(root)/'upstream/fly-gym/models/connectome_rnn_model.py','research_seed':seed,'repo_root':Path(root)}
    if male_policy._sha(artifacts._read(args['cell_path'],1024**2))!=male_model.CELL_SHA256:raise ValueError('Recovery cell source changed')
    _,_,provenance=_bundle(root,index,seed,args['variant'],args['graph_path'],args['graph_manifest'])
    identity=male_policy.validate_identity({'controller':controller,'variant':args['variant'],'profile':male_policy.PROFILE,
        'model_manifest_sha256':manifest_sha256,**{k:provenance[k] for k in male_policy.IDENTITY_HASHES if k!='model_manifest_sha256'}},controller)
    if expected_identity is not None and male_policy.validate_identity(expected_identity,controller)!=identity:
        raise ValueError('Expected recovery model differs')
    return identity,args


def load_policy(directory,variant,*,expected_report_sha256,graph_path,graph_manifest,cell_path,device='cpu',seed=0,research_seed=None,repo_root=None):
    if device!='cpu' or type(seed) is not int or not 0<=seed<2**31 or variant not in male_policy.VARIANTS or repo_root is None:
        raise ValueError('Explicit bounded recovery CPU policy required')
    index=_index(repo_root,Path(repo_root)/INDEX_PATH,INDEX_SHA256)
    if runtime_identity()!=index['runtime']:raise ValueError('Pinned recovery CPU runtime differs')
    if male_policy._sha(artifacts._read(cell_path,1024**2))!=male_model.CELL_SHA256:raise ValueError('Recovery cell source changed')
    if type(research_seed) is not int or research_seed not in PAIR_SEEDS:raise ValueError('Fixed recovery pair required')
    pair=index['pairs'][PAIR_SEEDS.index(research_seed)]
    if artifacts._safe_path(directory)!=artifacts._safe_path(Path(repo_root)/index['producer_root']/pair['directory']) or expected_report_sha256!=pair['report_sha256']:
        raise ValueError('Exact recovery directory/report required')
    graph,payload,provenance=_bundle(repo_root,index,research_seed,variant,graph_path,graph_manifest)
    policy=male_policy._load_checked_policy(graph,payload,provenance,cell_path,device=device,seed=seed)
    policy.provenance['recovery_reader_sources']=reader_sources(Path(repo_root))
    return policy


def passed_development(report,manifest_sha256,identities):
    return male_research._passed_development(report,manifest_sha256,identities,PROTOCOL_SHA256,planned('dev'))


def corpus_sources(data):
    """Recheck all fourteen frozen recording/snapshot inventories, without inference."""
    result={}
    def document(item):
        path=artifacts._safe_path(item['path'])
        value=read_pin(path,item['sha256'])
        result['recovery_input:'+str(path)]=item['sha256']
        return value
    baseline=document(data['baseline_collection']);document(data['recovery_report'])
    rows=[(Path(data['baseline_collection']['path']).parent/'runs'/row['run_id'],row['files']) for row in baseline['runs']]
    for expected,row in zip(data['protocol']['recovery_sources'],data['recovery_admission']):
        document({'path':str(Path(data['recovery_report']['path']).parent/expected['case_id']/'result.json'),
            'sha256':expected['result_sha256']})
        rows.append((Path(row['path']),row['files']))
    if len(rows)!=14:raise ValueError('All fourteen frozen recovery-training sources required')
    total=0
    for directory,entries in rows:
        directory=artifacts._safe_path(directory)
        paths=[]
        for name in ('recording','snapshots'):
            child=artifacts._safe_path(directory/name)
            for path in child.rglob('*') if child.exists() else ():
                path=artifacts._safe_path(path)
                if path.is_dir():continue
                if not path.is_file():raise ValueError('Nonregular research source')
                paths.append(path.relative_to(directory).as_posix())
                if len(paths)>128:raise ValueError('Research source inventory exceeds fixed count')
        if sorted(paths)!=sorted(row['path'] for row in entries):raise ValueError('Frozen corpus inventory differs')
        size=0
        for row in entries:
            path=artifacts._safe_path(directory/row['path'])
            if Path(row['path']).is_absolute() or '..' in Path(row['path']).parts:raise ValueError('Relative corpus file required')
            count=path.stat().st_size;size+=count
            if count!=row['bytes'] or size>160*1024**2:raise ValueError('Frozen corpus size differs')
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                while value:=stream.read(1024**2):digest.update(value)
            if digest.hexdigest()!=row['sha256']:raise ValueError('Frozen corpus bytes differ')
            result['recovery_input:'+str(path)]=row['sha256']
        total+=size
    if total!=data['total_source_bytes'] or total>3*1024**3:raise ValueError('Frozen corpus aggregate bytes differ')
    male_model.check_sources(data['baseline_admission'])
    return result


def reader_sources(root):
    """Small current software inventory; never duplicate the raw corpus in policy provenance."""
    names=[INDEX_PATH,PROTOCOL_PATH,'src/palimpsest/male_recovery_research.py','scripts/evaluate_male_recovery.py']
    return male_research.research_sources(root)|{name:male_policy._sha(artifacts._read(root/name,MAX_JSON)) for name in names}


def research_sources(root):
    index=_index(root,root/INDEX_PATH,INDEX_SHA256)
    _,data,_=_gate(root,index)
    return reader_sources(root)|corpus_sources(data)


@dataclass(frozen=True)
class Binding:
    manifest:Path
    manifest_sha256:str
    training_seed:int
    def resolve(self,root,assets,controller,device,scenario,texture,expected):
        if (device,scenario,texture)!=('cpu','reproduction','checker') or expected is None:
            raise ValueError('Recovery requires pinned CPU/reproduction/checker identity')
        return resolve(root,assets,self.manifest,self.manifest_sha256,self.training_seed,controller,expected)
    def load_policy(self,arguments,seed):return load_policy(**arguments,seed=seed)
    def provenance(self):
        return {'research_protocol_sha256':PROTOCOL_SHA256,'research_manifest_sha256':self.manifest_sha256,
            'training_seed':self.training_seed,'scope':'executed-target recovery research development; no production admission or held-out route'}


def worker(config,commands,replies,display,disconnected,stop,progress):
    from functools import partial
    from .engine import Engine
    from .worker import run_worker
    value=config.get('_male_research')
    if (not isinstance(value,dict) or set(value)!={'manifest','manifest_sha256','training_seed'} or
            any(config.get(key) is not None for key in ('job','snapshot_path','memory_u','intervention'))):
        raise ValueError('Recovery permits only fresh pinned roots')
    binding=Binding(Path(value['manifest']),value['manifest_sha256'],value['training_seed'])
    run_worker(config,commands,replies,display,disconnected,stop,progress,engine_factory=partial(Engine.open,research_binding=binding))
