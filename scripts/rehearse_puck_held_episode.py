"""Stage-3 guarded rehearsal of the held episode: a diagnostic, never an allocation.

Into a private scratch tmpfs stage (never /tmp/palimpsest-puck-cpu-held-0*) and a
fresh scratch output directory, it

1. checks the v6 native leaves, aliases, EGL vendor JSON and trusted baseline;
2. runs the characterization-04 worker unguarded in the v6 namespace (source,
   then replay over the source output) to observe the real import closure;
3. derives the episode profile from those two reports through the real
   candidate-02 derivation path;
4. stages the site, the v6 natives and the generated root with the real stager
   in the preparation namespace;
5. runs the REAL guarded v4 bootstrap twice (worker A source, then a fresh
   worker B replay over A's read-only output) with allocation 16's limits
   (2 GiB RSS, 8 GiB address space, 16 MiB files, 64 MiB scratch and output,
   360 s per worker), then summarizes timings, peak RSS, guard failures,
   process creation, held entries and outputs in rehearsal.json.

It writes nothing under runs/ and grants no runtime, collection or study authority.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import secrets
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
RUN_IDS=dict(source='5e1f0c2a9b8d47e6a3c2b1d0e9f8a7b6',replay='6f2a1d3b0c9e48f7b4d3c2e1f0a9b8c7')
NINE_LIBRARIES=('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6','libpthread.so.0','librt.so.1','libutil.so.1')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(name):
    spec=importlib.util.spec_from_file_location('_rehearsal_'+Path(name).stem,ROOT/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def pretty(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def write(path,raw):
    path=Path(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with open(path,'xb') as stream:stream.write(raw)


def tail(path,limit=4000):
    raw=Path(path).read_bytes() if Path(path).exists() else b''
    return raw[-limit:].decode('utf-8','replace')


def tree_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file() and not p.is_symlink())


def rehearse(**arguments):
    """Run every rehearsal step; always write rehearsal.json, with the first failure if one stops it."""
    output=Path(arguments['output']);summary={}
    try:
        return _rehearse(summary=summary,**arguments)
    except BaseException as error:
        summary['error']=type(error).__name__+': '+str(error)[:4000];raise
    finally:
        if output.is_dir() and summary:write(output/'rehearsal.json',pretty(summary))


def _rehearse(*,summary,site,inventory,layout,template,generated,native,baseline,upstream,output,stage):
    started=time.monotonic();output=Path(output);stage=Path(stage)
    if re.fullmatch(r'/tmp/palimpsest-puck-cpu-held-0\d.*',str(stage)) or not str(stage).startswith('/tmp/'):
        raise ValueError('The rehearsal stage must be a private /tmp path outside the allocation stage families')
    if os.path.lexists(output) or os.path.lexists(stage):raise FileExistsError('Rehearsal output or stage already exists')
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_cpu_registration import build_cpu_source_registration,native_leaf_row,egl_vendor_control
    from palimpsest.puck_cpu_namespace import sandbox_command
    import build_puck_python_louvain as baseline_api
    q=load('scripts/qualify_puck_cpu_held_runtime.py');c=load('scripts/characterize_puck_cpu_episode.py')
    d=load('scripts/derive_puck_episode_profile.py');e=load('scripts/run_puck_cpu_held_episode.py')
    output.mkdir(mode=0o700);summary.update(kind='puck-held-episode-guarded-rehearsal-v1',diagnostic_only=True,allocation=False,
        runtime_qualified=False,collection_authorized=False,study_authorized=False,phases={})
    raws={name:Path(path).read_bytes() for name,path in (('inventory',inventory),('layout',layout),('template',template),
                                                          ('native',native),('baseline',baseline))}
    native_doc=json.loads(raws['native']);baseline_doc=json.loads(raws['baseline']);deadline=time.monotonic()+600
    # 1. Host checks.
    began=time.monotonic()
    for row in native_doc['native_files']:
        if native_leaf_row(row['path'],deadline)!={k:row[k] for k in ('size_bytes','sha256')}:raise ValueError('Native leaf drifted: '+row['path'])
    for path,target in native_doc['aliases']:
        if os.readlink(path)!=target:raise ValueError('Native alias drifted: '+path)
    vendor=egl_vendor_control(native_doc,Path(native_doc['egl_vendor']['path']).read_bytes())
    baseline_summary=baseline_api.verify_baseline(baseline_doc,deadline)
    summary['phases']['host_checks']=dict(seconds=time.monotonic()-began,native_files=len(native_doc['native_files']))
    # The union source capsule: this repository's sources with the pinned upstream fly-gym files.
    capsule=output/'capsule';files=sorted(set(c.CAPSULE)|set(q.EPISODE_WORKER_SOURCES))
    for path in files:
        source=Path(upstream)/path[len('upstream/fly-gym/'):] if path.startswith('upstream/fly-gym/') else ROOT/path
        write(capsule/path,source.read_bytes())
    pins={p:dict(path=p,size_bytes=(capsule/p).stat().st_size,sha256=sha((capsule/p).read_bytes())) for p in files}
    wheels=json.loads(raws['layout'])['wheels']
    distributions=[dict(name=w['name'],version=w['version'],root_index=0,metadata_path=w['metadata_path']) for w in wheels]
    # 2. Unguarded characterization-04 worker in the v6 namespace, against this site.
    c.SITE=str(site);c.ENVIRONMENT=dict(c.ENVIRONMENT,PYGLFW_LIBRARY=str(site)+'/glfw/x11/libglfw.so')
    control=output/'char04-control';write(control/'egl-vendor.json',vendor);reports={}
    for phase in ('source','replay'):
        payload=output/('char04-payload-'+phase);payload.mkdir(mode=0o700)
        request=c.canonical(c.episode_request(phase,source_files=[pins[p] for p in c.CAPSULE],distributions=distributions))
        write(control/('request-'+phase+'.json'),request)
        command=c.sandbox_command(baseline_doc,native_doc,phase=phase,capsule=capsule,capsule_files=c.CAPSULE,
            controls={'egl-vendor.json':control/'egl-vendor.json','request-'+phase+'.json':control/('request-'+phase+'.json')},
            payload=payload,request='request-'+phase+'.json',request_sha=sha(request),
            source_run=output/'char04-payload-source' if phase=='replay' else None)
        began=time.monotonic()
        with open(output/('char04-'+phase+'.stdout'),'xb') as out,open(output/('char04-'+phase+'.stderr'),'xb') as err:
            code=subprocess.run(command,stdout=out,stderr=err,timeout=400).returncode
        report=json.loads((payload/'characterization.json').read_bytes()) if (payload/'characterization.json').exists() else None
        reports[phase]=report
        summary['phases']['char04_'+phase]=dict(seconds=time.monotonic()-began,returncode=code,
            status=report and report['status'],error=report and report.get('error'),
            process_creation_attempts=report and report['process_creation_attempts'],
            native_cache_dispatch=report and report['native_cache_dispatch'],import_misses=report and report['import_misses'],
            cache_entries=report and len(report['cache']['modules'] if report['cache'] else []),
            renderer=report and (report['episode_result'] or {}).get('renderer'),
            replay=report and (report['episode_result'] or {}).get('replay'),stderr_tail=tail(output/('char04-'+phase+'.stderr'),1500))
        if code!=0:raise RuntimeError('Unguarded characterization '+phase+' failed; see rehearsal.json')
    # 3. Candidate profile through the real derivation path.
    leaves=native_doc['dynamic_leaves']
    for phase,value in reports.items():c.validate_report(value,phase=phase,request_sha256=value['request_sha256'],
                                                         worker_sha256=pins[c.WORKER]['sha256'],dynamic_leaves=leaves)
    old,profile,module_paths,namespaces,served,misses=d.derive_profile(reports,raws['template'],raws['inventory'],str(site))
    candidate=dict(kind='puck-cpu-episode-import-profile-candidate-v2',version=2,expected_versions=dict(c.VERSIONS),
        import_profile=profile,module_paths=module_paths,namespaces=namespaces,
        additional_package_inputs=old['additional_package_inputs'],import_misses=misses,source_modules=sorted(served),
        native_phase_qualified=False,held_runtime_qualified=False,native_authorized=False,collection_authorized=False,
        study_authorized=False,executable=False,qualification_claims=[])
    candidate_raw=pretty(candidate);write(output/'candidate-rehearsal.json',candidate_raw)
    summary['candidate']=dict(sha256=sha(candidate_raw),module_paths=len(module_paths),namespaces=len(namespaces),
        native_cache=profile['native_cache'],exports=len(profile['exports']),import_misses=misses)
    # 4. Stage with the real stager in the preparation namespace.
    pins_raw={k:dict(size_bytes=len(v),sha256=sha(v)) for k,v in (('inventory',raws['inventory']),('layout',raws['layout']),
              ('candidate',candidate_raw),('native',raws['native']))}
    source_reg=build_cpu_source_registration(raws['inventory'],raws['layout'],candidate_raw,raws['native'],expected_pins=pins_raw,
        site_root=str(site),generated_root=str(generated),deadline=time.monotonic()+170)
    prepare_control=output/'prepare-control';copy_raw=json.dumps(source_reg,sort_keys=True,separators=(',',':'),ensure_ascii=False,
                                                              allow_nan=False).encode()
    write(prepare_control/'copy-registration.json',copy_raw);write(prepare_control/'candidate.json',candidate_raw)
    write(prepare_control/'layout.json',raws['layout'])
    request=q.canonical(dict(registration=dict(path='/puck/control/copy-registration.json',sha256=sha(copy_raw)),
        candidate=dict(path='/puck/control/candidate.json',sha256=sha(candidate_raw)),
        layout=dict(path='/puck/control/layout.json',sha256=sha(raws['layout']))))
    write(prepare_control/'stage-request.json',request)
    prepare_source=output/'prepare-source'
    for path in q.SOURCES:write(prepare_source/path,(ROOT/path).read_bytes())
    stage.mkdir(mode=0o700);os.chmod(stage,0o700)
    nine=sorted(['/etc/ld.so.cache',q.PYTHON,*('/usr/lib/'+n for n in NINE_LIBRARIES)])
    prepare_dir=output/'prepare';(prepare_dir/'payload').mkdir(parents=True);(prepare_dir/'logs').mkdir()
    command=sandbox_command(baseline_doc,native_doc,nine,phase='prepare',stage_parent=str(stage),source_root=str(prepare_source),
        control_root=str(prepare_control),output_root=str(prepare_dir/'payload'),
        command=[q.PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',sha(request)],
        environment=q.ENVIRONMENT,site_root=str(site),generated_root=str(generated),scratch_bytes=64*MiB)
    for key,value in (('NOFILE',40000),('AS',8192*MiB),('FSIZE',1024*MiB)):resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
    began=time.monotonic()
    observed=bounds.supervised(command,prepare_dir/'logs',cwd=ROOT,normal_deadline=began+180,hard_deadline=began+190,
        rss_bytes=2048*MiB,output_bytes=64*MiB,min_free_bytes=512*MiB,max_processes=3,output_root=prepare_dir,guard_state={},
        output_namespace_limits=(128,16),log_mode='direct',process_scope='group')
    summary['phases']['prepare']=dict(seconds=time.monotonic()-began,supervision=observed,stderr_tail=tail(prepare_dir/'logs/stderr.log',1500))
    if observed['status']!='completed':raise RuntimeError('Rehearsal staging failed; see rehearsal.json')
    dependency_raw=(prepare_dir/'payload/dependencies.json').read_bytes();dependencies=json.loads(dependency_raw)
    stage_receipt=json.loads((prepare_dir/'payload/stage.json').read_bytes());q.verify_staged_roots(str(stage),dependencies,stage_receipt['staged_roots'])
    summary['held_entries']=dict(files=sum(len(r['files']) for r in dependencies['roots']),
        bytes=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files']),
        modules=len(dependencies['modules']),namespaces=len(dependencies['namespaces']))
    # 5. The real guarded v4 bootstrap with allocation 16's limits: worker A, then a fresh worker B.
    episode_control=output/'episode-control';write(episode_control/'dependencies.json',dependency_raw)
    write(episode_control/'egl-vendor.json',vendor)
    worker_files=[pins[p] for p in q.EPISODE_WORKER_SOURCES];bootstrap=(capsule/e.BOOTSTRAP).read_bytes()
    config=dict(run_ids=dict(RUN_IDS))
    for key,value in (('NOFILE',e.LIMITS['max_fds']),('AS',e.LIMITS['address_space_bytes']),('FSIZE',e.LIMITS['file_bytes'])):
        resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
    for phase in ('source','replay'):
        _,registration_raw,worker=e.registration(config,phase,worker_files,dependency_raw,bootstrap,q)
        write(episode_control/('worker-registration-'+phase+'.json'),registration_raw)
        phase_dir=output/('episode-'+phase);(phase_dir/'payload').mkdir(parents=True);(phase_dir/'logs').mkdir()
        command=sandbox_command(baseline_doc,native_doc,[p for p in nine],phase='episode-'+phase,stage_parent=str(stage),
            source_root=str(capsule),control_root=str(episode_control),output_root=str(phase_dir/'payload'),
            command=q.qualification_command(worker),environment=e.ENVIRONMENT,scratch_bytes=e.LIMITS['scratch_bytes'],
            source_run_root=str(output/'episode-source/payload') if phase=='replay' else None,
            source_files=[r['path'] for r in worker_files])
        began=time.monotonic()
        observed=bounds.supervised(command,phase_dir/'logs',cwd=ROOT,normal_deadline=began+e.WORKER_SECONDS+5,
            hard_deadline=began+e.WORKER_SECONDS+15,rss_bytes=e.LIMITS['rss_bytes'],output_bytes=e.LIMITS['output_bytes'],
            min_free_bytes=512*MiB,max_processes=e.LIMITS['max_processes'],output_root=phase_dir,guard_state={},
            output_namespace_limits=(128,16),log_mode='direct',process_scope='descendants')
        stdout=(phase_dir/'logs/stdout.log').read_bytes() if (phase_dir/'logs/stdout.log').exists() else b''
        receipt=json.loads(stdout) if stdout.strip() else None;entry=(receipt or {}).get('entry_result') or {}
        phases=[json.loads(line) for line in (phase_dir/'logs/stderr.log').read_text('utf-8','replace').splitlines()
                if line.startswith('{"diagnostic_only"')]
        summary['phases']['episode_'+phase]=dict(seconds=time.monotonic()-began,supervision=observed,
            process_creation_attempts=(receipt or {}).get('process_creation_attempts'),denied_imports=(receipt or {}).get('denied_imports'),
            dependencies=(receipt or {}).get('dependencies',{}).get('file_count'),entry_result=entry,
            bootstrap_phases=[(p['phase'],round(p['elapsed_seconds'],3)) for p in phases],
            output_bytes=tree_bytes(phase_dir/'payload'),stderr_tail=tail(phase_dir/'logs/stderr.log',3000))
        if observed['status']!='completed':break
        bundle=entry.get('bundle')
        if bundle:
            validator=load('scripts/validate_palimpsest_bundle.py')
            summary['phases']['episode_'+phase]['bundle']=validator.validate_bundle(phase_dir/'payload'/bundle['path'],
                                                                                   phase_dir/'payload'/RUN_IDS[phase])
    summary['seconds']=time.monotonic()-started
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('site','inventory','layout','template','generated','native','baseline','upstream','output'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--stage',default='/tmp/puck-held-rehearsal-'+secrets.token_hex(6))
    args=parser.parse_args()
    if Path(sys.executable).resolve()!=Path('/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'):
        raise ValueError('The rehearsal requires the pinned CPython 3.11.15 interpreter')
    try:
        summary=rehearse(**{k:v for k,v in vars(args).items()})
        print(json.dumps({k:summary[k] for k in ('kind','seconds','held_entries')},sort_keys=True))
    finally:
        stage=Path(args.stage)
        if stage.is_dir() and not stage.is_symlink() and str(stage).startswith('/tmp/puck-held-rehearsal-'):
            for parent,directories,_ in os.walk(stage):
                for name in directories:os.chmod(os.path.join(parent,name),0o700)
            shutil.rmtree(stage)


if __name__=='__main__':main()
