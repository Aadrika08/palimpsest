"""Fixed 20-owner teacher collection; separate reviewed native GO is required.

Reuses the mechanics owner and watchdog, not a second native loop. Run only under
retained TERM1560/+15 inside bounded_process1580 with independent descendant
containment. No training, student, held-out, restore, replay or retry admission.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from palimpsest import puck_learning as learning, puck_teacher as teacher
from palimpsest.storage import StorageBudget, StorageLimits, _safe_path
from palimpsest.records import iter_ticks
from verify_puck_mechanics import (MiB, digest, write_json, read_json, protocol,
                                  teacher_sources, inventory, supervised_owner)


def main(args):
    root,output,retained=args.repo.resolve(),_safe_path(args.output),_safe_path(args.retention_root)
    if Path(__file__).resolve()!=root/'scripts/collect_puck_teachers.py':raise ValueError('Wrong collector checkout')
    if output.exists() or not output.is_relative_to(retained):raise ValueError('Fresh output inside retention root required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=5).strip()
    if commit!=args.expected_commit:raise ValueError('Frozen collector HEAD differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=root,check=True,capture_output=True,timeout=5)
    spec=learning.load_protocol(root);native=protocol(root);rows=teacher.plan(root);limits=spec['limits']
    upstream=root/'upstream/fly-gym'
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True,timeout=5).strip()!=native['upstream_commit']:
        raise ValueError('Pinned upstream revision differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=upstream,check=True,capture_output=True,timeout=5)
    frozen=teacher_sources(root);started=time.monotonic();immutable={}
    budget=StorageBudget((output,),StorageLimits(max_bytes=limits['teacher']['bytes'],min_free_bytes=limits['min_free_bytes'],
                        max_runs=20,max_snapshots=1),headroom_bytes=8*MiB)
    retention=StorageBudget((retained,),StorageLimits(max_bytes=limits['total_retained_bytes'],min_free_bytes=limits['min_free_bytes']))
    report={'status':'running','commit':commit,**teacher.identity(root),'source_hashes':frozen,
            'sources':[{'seed':r['seed'],'split':r['split'],'path':str(output/r['id']/'recording'),
                        'manifest_sha256':None} for r in rows],
            'owners':[{**r,'status':'not_started'} for r in rows],
            'admission':{'status':'not_started','rows':[{'seed':r['seed'],'split':r['split'],'status':'not_started'} for r in rows]},
            'qualification_claims':[],'finalization_errors':[]}
    with budget.lock():
        try:
            allowance=sum(r['max_bytes'] for r in rows)
            budget.check(allowance,path=output);retention.check(allowance+8*MiB,path=output)
            report['full_plan_admission_bytes']=allowance
            write_json(output/'report.json',report,budget)
            environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg',
                         'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}
            for index,item in enumerate(report['owners']):
                if time.monotonic()-started+limits['owner_seconds']>limits['teacher']['inner_seconds']:
                    raise TimeoutError('Insufficient internal time for another full teacher owner')
                for name,previous in immutable.items():
                    if inventory(output/name)!=previous:raise ValueError('Completed teacher evidence changed: '+name)
                remaining=sum(r['max_bytes'] for r in rows[index:])
                budget.check(remaining,path=output);retention.check(remaining+8*MiB,path=output)
                row=rows[index];destination=output/row['id']
                config={'repo':str(root),'output':str(destination),'row':row,'sources':frozen,
                        'learning_teacher':learning.PROTOCOL_SHA256}
                command=[sys.executable,str(root/'scripts/verify_puck_mechanics.py'),'--child',json.dumps(config,separators=(',',':'))]
                item.update(status='running',output=str(destination));write_json(output/'report.json',report,budget)
                item['supervision']=supervised_owner(command,destination,environment,budget,row,0)
                item['status']='failed'
                if (destination/'result.json').is_file():
                    item['result']=read_json(destination/'result.json');item['result_sha256']=digest(destination/'result.json')
                result=item.get('result',{})
                if not item['supervision']['passed'] or result.get('status')!='passed':
                    raise RuntimeError(row['id']+': teacher/protocol/watchdog/cleanup failure')
                count=result.get('ticks')
                if (type(count) is not int or not 1<=count<=600 or result.get('controller_calls')!=count or
                        result.get('row')!=row or result.get('completed_control_tick')!=count or
                        result.get('own_supervisor_cursor',{}).get('tick')!=count or set(result.get('snapshots',{}))!={'initial'}):
                    raise ValueError('Teacher owner identity/cursor/call/snapshot coverage differs')
                manifest_path=destination/'recording/manifest.json';manifest=read_json(manifest_path)
                observed=0
                for numeric in iter_ticks(destination/'recording'):
                    if numeric['episode']!=0 or numeric['tick']!=observed or observed>=count:
                        raise ValueError('Teacher recording episode/tick coverage differs')
                    observed+=1
                if (manifest['status']!='completed' or observed!=count or manifest['recorded_ticks']!=count or
                        manifest.get('outcome')!=result['final_state']['reason'] or result['completion']!=manifest.get('outcome')):
                    raise ValueError('Completed teacher outcome/coverage differs')
                report['sources'][index]['manifest_sha256']=digest(manifest_path)
                item.update(status='completed',outcome=manifest['outcome'])
                immutable[row['id']]=inventory(destination)
                write_json(output/'report.json',report,budget)
            admitted=learning.admit_batch(report['sources'],root)
            report['admission']={key:value for key,value in admitted.items() if key!='data'}
            report['status']='passed' if admitted['status']=='passed' else 'failed'
        except Exception as error:
            report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:4096]})
            for item in report['owners']:
                if item['status']=='running':item.update(status='failed',parent_error=report['error'])
        finally:
            try:
                report['sources_unchanged']=teacher_sources(root)==frozen
                if not report['sources_unchanged']:raise ValueError('Frozen collection sources changed')
            except Exception as error:report['finalization_errors'].append('sources: '+str(error)[:1024])
            try:
                report['prior_owner_evidence_unchanged']=all(inventory(output/name)==old for name,old in immutable.items())
                if not report['prior_owner_evidence_unchanged']:raise ValueError('Completed teacher evidence changed')
            except Exception as error:report['finalization_errors'].append('immutable evidence: '+str(error)[:1024])
            try:report['retained_inventory']={k:v for k,v in inventory(output).items() if k!='report.json'}
            except Exception as error:report['finalization_errors'].append('inventory: '+str(error)[:1024])
            for name,storage in (('storage',budget),('retention_storage',retention)):
                try:report[name]=storage.check(0,path=output)
                except Exception as error:report['finalization_errors'].append(name+': '+str(error)[:1024])
            report['elapsed_seconds']=time.monotonic()-started
            if report['elapsed_seconds']>limits['teacher']['inner_seconds']:
                report['finalization_errors'].append('deadline: teacher internal 1500-second ceiling exceeded')
            if report['finalization_errors']:report['status']='failed'
            write_json(output/'report.json',report,budget)
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retention-root',type=Path,required=True)
    raise SystemExit(main(parser.parse_args()))
