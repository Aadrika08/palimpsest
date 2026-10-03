"""One frozen research seed pair; reused numerical fitter, no production loader."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import time

from palimpsest import artifacts, male_model
from palimpsest.storage import StorageBudget, StorageLimits
import prepare_male_recovery_data as data_reader
from train_male_reduced import fit, evaluate, make_model, rewire, load_graph

ROOT=Path(__file__).resolve().parents[1]
DATA_SHA256='402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014'
FITTER_SHA256='75d3fc1fd71bab6b749c158a58fe9d802fc10253f4416d1c8f5739a2bdf4ff4a'
MAX_FILE=8*1024**2
MAX_REPORT=4*1024**2
VARIANTS=('original','degree_rewired')


def fixed_training(seed):
    if type(seed) is not int or seed not in (10,11,12):raise ValueError('Fixed paired seed 10/11/12 required')
    p=data_reader.protocol()
    return {**p['training'],'training_seed':seed,'rewiring_seed':seed,'variants':list(VARIANTS),
        'data_manifest_sha256':DATA_SHA256,'research_protocol_sha256':data_reader.PROTOCOL_SHA256,
        'order':p['ordering'],'hidden_state':p['right_censoring'],
        'wall_budget_seconds':600,'output_limit_bytes':64*1024**2,'qualification_claims':[]}


def code_identity():
    sources={name:hashlib.sha256(artifacts._read(ROOT/name,MAX_REPORT)).hexdigest() for name in
        ('scripts/train_male_reduced.py','scripts/train_male_recovery.py','uv.lock')}
    if sources['scripts/train_male_reduced.py']!=FITTER_SHA256:raise ValueError('Unchanged numerical fitter source required')
    return {'reader':data_reader.reader_identity(),'trainer':sources}


def output_path(output,seed,data_path,manifest):
    output=artifacts._safe_path(output)
    if output.name!=f'seed-{seed}':raise ValueError('Fresh fixed seed-N pair directory required')
    if output.exists():raise FileExistsError('Pair directory already exists; no resume/overwrite')
    for path in (data_path,manifest['baseline_collection']['path'],manifest['recovery_report']['path']):
        source=artifacts._safe_path(path).parent;managed=output.parent
        if source==managed or source in managed.parents or managed in source.parents:
            raise ValueError('Managed training output must be outside every input corpus tree')
    return output


def check_data(manifest,data_path,deadline):
    actual=data_reader.frozen_json(data_path,DATA_SHA256)
    if actual!=manifest:raise ValueError('Prepared data manifest changed')
    if {key:manifest[key] for key in ('current_reader_sources','adapter_sha256')}!=data_reader.reader_identity():
        raise ValueError('Prepared data reader differs')
    p=data_reader.protocol()
    baseline_path=Path(manifest['baseline_collection']['path'])
    baseline=data_reader.frozen_json(baseline_path,p['baseline_collection_sha256'])
    for source in baseline['runs']:
        data_reader.inventory(baseline_path.parent/'runs'/source['run_id'],source['files'],deadline)
    recovery_path=Path(manifest['recovery_report']['path'])
    data_reader.frozen_json(recovery_path,p['recovery_report_sha256'])
    for expected,source in zip(p['recovery_sources'],manifest['recovery_admission']):
        if source['run_id']!=expected['run_id']:raise ValueError('Recovery source order differs')
        data_reader.frozen_json(recovery_path.parent/expected['case_id']/'result.json',expected['result_sha256'])
        data_reader.inventory(Path(source['path']),source['files'],deadline)
    male_model.check_sources(manifest['baseline_admission'])


def prepare(args,deadline):
    initial=code_identity()
    data_path=artifacts._safe_path(args.data_manifest)
    manifest=data_reader.frozen_json(data_path,DATA_SHA256)
    if (manifest['status']!='prepared-research-only' or manifest['protocol_sha256']!=data_reader.PROTOCOL_SHA256 or
            manifest['counts']!={'train':2117,'dev':1228,'held_out':0} or
            {key:len(value) for key,value in manifest['ordered_sources'].items()}!={'train':10,'dev':4,'held_out':0} or
            len(manifest['recovery_admission'])!=2 or
            any(row['windows']!=[32,32,3] or row['ending']!='right_censored_coverage_complete'
                for row in manifest['recovery_admission'])):raise ValueError('Fixed prepared research data differs')
    output=output_path(args.output,args.training_seed,data_path,manifest)
    data,admitted=data_reader.prepare(Path(manifest['baseline_collection']['path']),
        Path(manifest['recovery_report']['path']),deadline=min(deadline,time.monotonic()+180.))
    if admitted!=manifest:raise ValueError('Independent re-admission differs from pinned preparation')
    graph=load_graph(args.graph,args.graph_manifest)
    cell=artifacts._read(args.cell_source,1024**2)
    if hashlib.sha256(cell).hexdigest()!=male_model.CELL_SHA256:raise ValueError('Pinned upstream cell differs')
    control,rewiring=rewire(graph,args.training_seed)
    inputs={str(artifacts._safe_path(path)):hashlib.sha256(artifacts._read(path,MAX_REPORT)).hexdigest()
            for path in (args.graph,args.graph_manifest,args.cell_source)}
    if code_identity()!=initial:raise ValueError('Trainer/reader drift during preparation')
    check_data(manifest,data_path,deadline)
    protocol={'version':1,'id':'male-recovery-executed-target-research-v1',
        'training':fixed_training(args.training_seed),'data_manifest_path':str(data_path),
        'data_manifest_sha256':DATA_SHA256,'prepared_data':manifest,'source_code':initial,'model_inputs':inputs,
        'graphs':{name:{key:g[key] for key in ('topology_sha256','ordered_ids_sha256','source_graph_sha256',
            'graph_manifest_sha256','type_missing_ids')} for name,g in (('original',graph),('degree_rewired',control))},
        'rewiring':rewiring,'feature_protocol':male_model.FEATURE_PROTOCOL,
        'runtime':{'python':platform.python_version(),'numpy':importlib.metadata.version('numpy'),
            'torch_distribution':importlib.metadata.version('torch')},'held_out_status':'locked_unopened',
        'objective':'Actual executed-action imitation; expert metadata never supplies targets',
        'qualification_claims':[]}
    return output,data,{'original':graph,'degree_rewired':control},protocol


def check_context(protocol,deadline):
    if code_identity()!=protocol['source_code']:raise ValueError('Trainer/reader source changed')
    for name,expected in protocol['model_inputs'].items():
        if hashlib.sha256(artifacts._read(name,MAX_REPORT)).hexdigest()!=expected:
            raise ValueError('Graph/extraction/cell source changed')
    check_data(protocol['prepared_data'],Path(protocol['data_manifest_path']),deadline)


def validate_fit(result):
    history=result.get('history')
    if (not isinstance(history,list) or len(history)!=20 or
            any(type(row.get('epoch')) is not int for row in history) or
            [row.get('epoch') for row in history]!=list(range(1,21))):
        raise ValueError('All 20 frozen epochs required')
    for row in history:
        if (type(row.get('train_ticks')) is not int or type(row.get('dev',{}).get('ticks')) is not int or
                row['train_ticks']!=2117 or row['dev']['ticks']!=1228):raise ValueError('Epoch data counts differ')
        for value in (row.get('train_loss'),row['dev'].get('loss'),row['dev'].get('velocity_mae'),row['dev'].get('wrapped_heading_mae_radians')):
            if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Nonfinite/invalid fit metric')
    if type(result.get('selected_epoch')) is not int or result['selected_epoch']!=min(range(1,21),key=lambda epoch:history[epoch-1]['dev']['loss']):
        raise ValueError('Earliest exact dev minimum required')


def write_artifact(path,payload,deadline,budget=None,maximum=MAX_FILE):
    if len(payload)>maximum:raise ValueError('Research artifact exceeds byte cap')
    if time.monotonic()>deadline:raise TimeoutError('Research pair deadline exceeded')
    if budget:budget.check(len(payload),path=path)
    with path.open('xb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())
    if time.monotonic()>deadline:raise TimeoutError('Artifact sync exceeded pair deadline')
    return {'path':path.name,'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload)}


def stage_report(output,report,deadline,budget=None):
    if (output/'report.json').exists():raise FileExistsError('Research report is immutable')
    return write_artifact(output/'report.pending',male_model.canonical(report),deadline,budget,MAX_REPORT)


def publish_report(output,deadline,validate):
    """Publish only after payload sync and successful lease/resource cleanup."""
    validate()
    if time.monotonic()>deadline:raise TimeoutError('Final source validation exceeded pair deadline')
    if (output/'report.json').exists():raise FileExistsError('Research report is immutable')
    (output/'report.pending').replace(output/'report.json')  # Last fallible operation.


def train(args):
    deadline=time.monotonic()+600.
    output,data,graphs,protocol=prepare(args,deadline)
    budget=StorageBudget((output.parent,),StorageLimits(max_bytes=192*1024**2,min_free_bytes=1024**3,
        max_runs=3,max_snapshots=1,max_exports=1))
    report={'status':'running','training_completed':False,'training_attempted':False,
        'protocol_sha256':male_model.digest(protocol),'data_manifest_sha256':DATA_SHA256,
        'held_out_status':'locked_unopened','held_out_used_for_selection':False,
        'models':{variant:{'status':'not_started'} for variant in VARIANTS},'files':[],'qualification_claims':[]}
    active=None;created=False
    try:
        with budget.lock():
            budget.check(64*1024**2,path=output)
            output.mkdir(exist_ok=False);created=True
            def write(name,payload):
                if budget.usage()['used_bytes']+len(payload)>192*1024**2:
                    raise ValueError('Aggregate pair output limit exceeded')
                size=sum(path.stat().st_size for path in output.iterdir() if path.is_file())
                if size+len(payload)>64*1024**2:raise ValueError('Pair output limit exceeded')
                item=write_artifact(output/name,payload,deadline,budget)
                report['files'].append(item);return item
            write('protocol.json',male_model.canonical(protocol))
            check_context(protocol,deadline)
            import torch  # Only explicit actual-training entry point.
            for variant in VARIANTS:
                active=variant;report['models'][variant]={'status':'running'};report['training_attempted']=True
                model,result=fit(graphs[variant],data,args.cell_source,deadline,protocol['training'])
                validate_fit(result);check_context(protocol,deadline)
                graph_file=variant+'-graph.json';write(graph_file,male_model.canonical(graphs[variant]))
                checkpoint={'format':'palimpsest-male-reduced-v1','protocol_sha256':report['protocol_sha256'],
                    'graph_sha256':male_model.digest(graphs[variant]),'ordered_ids_sha256':graphs[variant]['ordered_ids_sha256'],
                    'state_dict':model.state_dict()}
                buffer=io.BytesIO();torch.save(checkpoint,buffer)
                item=write(variant+'.pt',buffer.getvalue())
                report['models'][variant]={'status':'completed',**result,'checkpoint':item,'graph_file':graph_file}
                del model,checkpoint,buffer;active=None
            report.update(status='completed-research-training',training_completed=True)
            check_context(protocol,deadline)
            stage_report(output,report,deadline,budget)
        # Lease cleanup completed; renamed staged bytes add no new storage.
        publish_report(output,deadline,lambda:check_context(protocol,deadline))
        return report
    except BaseException as error:
        report.update(status='failed-research-training',training_completed=False,
            error={'type':type(error).__name__,'message':str(error)[:1024]})
        if active is not None:report['models'][active].update(status='failed',error=report['error'])
        if created:
            try:
                write_artifact(output/'failure.json',male_model.canonical(report),math.inf,budget,MAX_REPORT)
            except BaseException as reporting:error.add_note('Failure report also failed: '+str(reporting)[:256])
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-manifest',type=Path,default=ROOT/'runs/m7-recovery-learning-data-development-7d5fc1f-20261003/data-manifest.json')
    parser.add_argument('--training-seed',type=int,choices=(10,11,12),required=True)
    parser.add_argument('--graph',type=Path,default=ROOT/'data/assets/flynn/male-reduced-v1/source-graph.json')
    parser.add_argument('--graph-manifest',type=Path,default=ROOT/'data/manifests/malecns-reduced-neighborhood-v1.json')
    parser.add_argument('--cell-source',type=Path,default=ROOT/'upstream/fly-gym/models/connectome_rnn_model.py')
    parser.add_argument('--output',type=Path,required=True,help='Fresh aggregate-root/seed-N pair directory')
    args=parser.parse_args(argv);train(args)


if __name__=='__main__':main()
