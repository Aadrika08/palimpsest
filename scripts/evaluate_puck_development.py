"""Fixed 12-owner development. Retained external1260 TERM/+15 inside1280 required.

No held-out, retry, selection, fitting or production Engine admission. A completed
batch reports every natural outcome; its separate each-model goal gate can fail.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from palimpsest import puck_development as development, puck_student as student
from palimpsest.records import iter_ticks
from palimpsest.snapshots import state_digest
from palimpsest.storage import StorageBudget, StorageLimits, _safe_path
from verify_puck_mechanics import (MiB,digest,write_json,read_json,protocol,
                                  development_sources,inventory,supervised_owner)


def bindings(balanced):
    if type(balanced) is not bool:raise ValueError('Fixed balanced selector must be boolean')
    if balanced:
        from palimpsest import puck_balanced_development, puck_balanced_student
        from verify_puck_mechanics import balanced_development_sources
        return puck_balanced_development,puck_balanced_student,balanced_development_sources,'learning_student_balanced_development'
    return development,student,development_sources,'learning_student_development'


def main(args):
    started=time.monotonic()
    development,student,development_sources,envelope=bindings(getattr(args,'balanced',False))
    root,output,retained=args.repo.resolve(),_safe_path(args.output),_safe_path(args.retention_root)
    if Path(__file__).resolve()!=root/'scripts/evaluate_puck_development.py':raise ValueError('Wrong evaluator checkout')
    if output.exists() or not output.is_relative_to(retained):raise ValueError('Fresh output inside retention root required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=5).strip()
    if commit!=args.expected_commit:raise ValueError('Frozen development HEAD differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=root,check=True,capture_output=True,timeout=5)
    spec=development.protocol(root);native=protocol(root);rows=development.plan(root);limits=spec['limits']
    upstream=root/'upstream/fly-gym'
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True,timeout=5).strip()!=native['upstream_commit']:
        raise ValueError('Pinned upstream revision differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=upstream,check=True,capture_output=True,timeout=5)
    models={str(seed):student.admit_bundle(root,args.bundle_root,seed)[1] for seed in spec['model_order']}
    frozen=development_sources(root);immutable={}
    budget=StorageBudget((output,),StorageLimits(max_bytes=limits['bytes'],min_free_bytes=limits['min_free_bytes'],
                        max_runs=12,max_snapshots=1),headroom_bytes=8*MiB)
    retention=StorageBudget((retained,),StorageLimits(max_bytes=limits['total_retained_bytes'],min_free_bytes=limits['min_free_bytes']))
    report={'status':'running','commit':commit,'development_protocol_sha256':development.PROTOCOL_SHA256,
            'source_hashes':frozen,'models':models,'owners':[{**r,'status':'not_started'} for r in rows],
            'admission':{'status':'not_started'},'held_out':'locked','qualification_claims':[],'finalization_errors':[]}
    with budget.lock():
        try:
            allowance=sum(r['max_bytes'] for r in rows)
            budget.check(allowance,path=output);retention.check(allowance+8*MiB,path=output)
            report['full_plan_admission_bytes']=allowance;write_json(output/'report.json',report,budget)
            environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg',
                         'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
            for index,item in enumerate(report['owners']):
                if time.monotonic()-started+limits['owner_seconds']>limits['inner_seconds']:
                    raise TimeoutError('Insufficient internal time for another full development owner')
                for name,previous in immutable.items():
                    if inventory(output/name)!=previous:raise ValueError('Completed development evidence changed: '+name)
                remaining=sum(r['max_bytes'] for r in rows[index:])
                budget.check(remaining,path=output);retention.check(remaining+8*MiB,path=output)
                row=rows[index];destination=output/row['id'];reference=None
                if row['model_seed']!=21:
                    base=report['owners'][index-(row['model_seed']-21)]
                    reference={'owner_id':base['id'],'result_sha256':base['result_sha256'],
                               'snapshot_sha256':base['result']['snapshots']['initial']['sha256']}
                config={'repo':str(root),'output':str(destination),'row':row,'sources':frozen,
                        envelope:development.PROTOCOL_SHA256,'bundle_root':str(args.bundle_root.resolve()),
                        'initial_reference':reference}
                command=[sys.executable,str(root/'scripts/verify_puck_mechanics.py'),'--child',json.dumps(config,separators=(',',':'))]
                item.update(status='running',output=str(destination));write_json(output/'report.json',report,budget)
                item['supervision']=supervised_owner(command,destination,environment,budget,row,0);item['status']='failed'
                if (destination/'result.json').is_file():
                    item['result']=read_json(destination/'result.json');item['result_sha256']=digest(destination/'result.json')
                result=item.get('result',{})
                if not item['supervision']['passed'] or result.get('status')!='passed':
                    raise RuntimeError(row['id']+': development/protocol/watchdog/cleanup failure')
                count=result.get('ticks')
                if (type(count) is not int or not 1<=count<=600 or result.get('model_calls')!=count or
                        state_digest(result.get('row'))!=state_digest(row) or result.get('completed_control_tick')!=count or
                        result.get('own_supervisor_cursor',{}).get('tick')!=count or set(result.get('snapshots',{}))!={'initial'} or
                        result.get('initial_match',{}).get('status')!='passed' or result['initial_match']['reference']!=reference):
                    raise ValueError('Development identity/cursor/call/snapshot/initial-match coverage differs')
                manifest_path=destination/'recording/manifest.json';manifest=read_json(manifest_path);observed=0
                for numeric in iter_ticks(destination/'recording'):
                    if numeric['episode']!=0 or numeric['tick']!=observed or observed>=count or any(k.startswith('teacher') for k in numeric):
                        raise ValueError('Development recording episode/tick/schema differs')
                    observed+=1
                if (manifest.get('schema')!=spec['record_schema'] or manifest.get('development_protocol_sha256')!=development.PROTOCOL_SHA256 or
                        manifest.get('status')!='completed' or state_digest(manifest.get('row'))!=state_digest(row) or
                        state_digest(manifest.get('source_hashes'))!=state_digest(frozen) or manifest.get('initial_reference')!=reference or
                        any(state_digest(manifest.get(k))!=state_digest(v) for k,v in student.identity(root,models[str(row['model_seed'])]).items()) or
                        observed!=count or manifest.get('recorded_ticks')!=count or
                        manifest.get('outcome')!=result['final_state']['reason'] or not result['final_state']['reason'] or
                        result['completion']!=manifest.get('outcome')):
                    raise ValueError('Completed development outcome/coverage differs')
                item.update(status='completed',outcome=manifest['outcome'],manifest_sha256=digest(manifest_path))
                immutable[row['id']]=inventory(destination);write_json(output/'report.json',report,budget)
            report['admission']=development.admission(report['owners'],root);report['status']='completed'
        except Exception as error:
            report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:4096]})
            for item in report['owners']:
                if item['status']=='running':item.update(status='failed',parent_error=report['error'])
        finally:
            try:
                report['sources_unchanged']=development_sources(root)==frozen
                if not report['sources_unchanged']:raise ValueError('Frozen development sources changed')
            except Exception as error:report['finalization_errors'].append('sources: '+str(error)[:1024])
            try:
                report['models_unchanged']={str(seed):student.admit_bundle(root,args.bundle_root,seed)[1] for seed in spec['model_order']}==models
                if not report['models_unchanged']:raise ValueError('Frozen student bundles changed')
            except Exception as error:report['finalization_errors'].append('models: '+str(error)[:1024])
            try:
                report['prior_owner_evidence_unchanged']=all(inventory(output/name)==old for name,old in immutable.items())
                if not report['prior_owner_evidence_unchanged']:raise ValueError('Completed development evidence changed')
            except Exception as error:report['finalization_errors'].append('immutable evidence: '+str(error)[:1024])
            try:report['retained_inventory']={k:v for k,v in inventory(output).items() if k!='report.json'}
            except Exception as error:report['finalization_errors'].append('inventory: '+str(error)[:1024])
            for name,storage in (('storage',budget),('retention_storage',retention)):
                try:report[name]=storage.check(0,path=output)
                except Exception as error:report['finalization_errors'].append(name+': '+str(error)[:1024])
            report['elapsed_seconds']=time.monotonic()-started
            if report['elapsed_seconds']>limits['inner_seconds']:report['finalization_errors'].append('Development internal1200-second ceiling exceeded')
            if report['finalization_errors']:report['status']='failed'
            write_json(output/'report.json',report,budget)
            if time.monotonic()-started>limits['inner_seconds'] and report['status']!='failed':
                report['status']='failed';report['finalization_errors'].append('Development deadline crossed during publication')
                write_json(output/'report.json',report,budget)
    # Owners are gone and the lease is released. Publication/lease-exit time is
    # inside the same ceiling; a retained failure may never become a late pass.
    if time.monotonic()-started>limits['inner_seconds'] and report['status']!='failed':
        report['status']='failed';report['finalization_errors'].append('Development deadline crossed before return')
        write_json(output/'report.json',report,budget)
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retention-root',type=Path,required=True)
    parser.add_argument('--bundle-root',type=Path,required=True)
    parser.add_argument('--balanced',action='store_true',help='Use only the fixed balanced-development protocol and bundles')
    raise SystemExit(main(parser.parse_args()))
