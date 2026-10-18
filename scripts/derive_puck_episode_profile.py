"""Derive episode import-profile candidate 02 from characterization-04; no imports run.

Only trusted project helpers and stdlib execute. The derivation binds the frozen
characterization-04 configuration, its result, its outcome audit and both
reports by SHA-256, maps every observed site module with ``_module_maps`` over
the accepted inventory, leaves source-root modules to the held source
registration, and filters the accepted template profile to the names the
episode actually created. The candidate is data only and claims nothing.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from palimpsest.puck_dependency_bindings import validate_profile  # noqa: E402
from palimpsest.puck_runtime_registration import _module_maps  # noqa: E402


def _parent():
    spec=importlib.util.spec_from_file_location('_episode_characterization_parent',ROOT/'scripts/characterize_puck_cpu_episode.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def _qualifier():
    spec=importlib.util.spec_from_file_location('_episode_preparation_qualifier',ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


PARENT=_parent()
QUALIFIER=_qualifier()
KIND='puck-cpu-episode-import-profile-candidate-v2'
AUDIT_KIND='cpu-episode-characterization-outcome-audit-v1'
SOURCE_ROOT='/puck/source/'
SYSCONFIGDATA='_sysconfigdata__linux_x86_64-linux-gnu'
GENERATED='_remote_module_non_scriptable'
CLAIMS=dict(native_phase_qualified=False,held_runtime_qualified=False,native_authorized=False,
    collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[])


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(raw,what):
    if type(raw) is not bytes:raise ValueError(what+' bytes required')
    value=json.loads(raw)
    if type(value) is not dict:raise ValueError(what+' object required')
    return value


def split(rows,capsule,prefix):
    """Site rows for _module_maps; source-root names served by the source registration."""
    site=[];source=[]
    for row in rows:
        name=row['name'];file=row.get('file')
        if name==GENERATED:
            raise ValueError('Generated remote-module helper observed; derive it as preparation01 did')
        if name in ('__main__','__mp_main__') or name.split('.')[0] in sys.stdlib_module_names:
            continue
        if name==SYSCONFIGDATA:
            if file!=prefix+'/lib/python3.11/'+SYSCONFIGDATA+'.py':
                raise ValueError('The stdlib-name exception must be the pinned interpreter file')
            continue
        if type(file) is str and file.startswith(SOURCE_ROOT):
            if file[len(SOURCE_ROOT):] not in capsule:
                raise ValueError('Source-root module is outside the pinned episode capsule: '+name)
            source.append(name);continue
        site.append(row)
    return site,source


def native_cache_rows(rows,reports):
    """Each kept template cache row with its observed creator keys and every later key's producers."""
    names={row['name'] for row in rows};result=[]
    for value in reports.values():
        for event in value['native_cache_dispatch']['events']:
            if event['first'] and event['cache'] not in names:
                raise ValueError('Observed shared cache module is not a template native cache row: '+event['cache'])
    for row in rows:
        late={}
        for phase,value in reports.items():
            events=[e for e in value['native_cache_dispatch']['events'] if e['cache']==row['name']]
            if not events or not events[0]['first'] or (events[0]['producer'],events[0]['phase'])!=(row['producer'],row['phase']):
                raise ValueError('Shared cache '+row['name']+' was not first observed at its template creator in '+phase)
            if events[0]['added']!=row['delegate_attributes'] or any(e['first'] for e in events[1:]):
                raise ValueError('Shared cache '+row['name']+' creator keys differ from the template in '+phase)
            for event in events[1:]:
                for key in event['added']:late.setdefault(key,set()).add((event['producer'],event['phase']))
        if late:
            row=dict(row,late_delegates=[dict(attribute=key,producers=[dict(producer=p,phase=f) for p,f in sorted(late[key])])
                                         for key in sorted(late)])
        result.append(row)
    return result


def derive(*,configuration,result,source,replay,audit,template,inventory,native,site_root):
    # _module_maps reads sys.stdlib_module_names, so only the pinned 3.11.15 interpreter may derive.
    if sys.version_info[:3]!=(3,11,15) or Path(sys.executable).resolve()!=Path(PARENT.PYTHON):
        raise ValueError('Candidate 02 derivation requires the pinned CPython 3.11.15 interpreter')
    config=load(configuration,'Characterization-04 configuration');PARENT.validate_configuration(config)
    if config['environment']['PYGLFW_LIBRARY']!=site_root+'/glfw/x11/libglfw.so':
        raise ValueError('Site root differs from the frozen characterization-04 environment')
    pins={row['path']:row for row in config['inputs']}
    inventory_pin=pins[PARENT.ROLES['inventory']]
    if len(inventory)!=inventory_pin['size_bytes'] or sha(inventory)!=inventory_pin['sha256']:
        raise ValueError('Retained inventory differs from its characterization-04 pin')
    native_pin=pins[PARENT.ROLES['native_metadata']]
    if len(native)!=native_pin['size_bytes'] or sha(native)!=native_pin['sha256']:
        raise ValueError('Native metadata differs from its characterization-04 pin')
    leaves=load(native,'Native metadata').get('dynamic_leaves')
    outcome=load(result,'Characterization-04 result')
    if (outcome.get('kind')!='puck-cpu-characterization-outcome-v3' or outcome.get('status')!='observed'
            or type(outcome.get('version')) is not int or outcome['version']!=3
            or any(k in outcome for k in ('error','error_type'))
            or outcome.get('configuration_sha256')!=sha(configuration)
            or outcome.get('source_report_sha256')!=sha(source) or outcome.get('replay_report_sha256')!=sha(replay)
            or any(outcome.get(k) is not False for k in PARENT.CLAIMS if k!='qualification_claims')
            or outcome.get('qualification_claims')!=[]):
        raise ValueError('Characterization-04 must retain its observed outcome bound to both reports')
    checked=load(audit,'Characterization-04 outcome audit');verified=checked.get('verified')
    if (checked.get('kind')!=AUDIT_KIND or checked.get('status')!='PASS' or type(verified) is not dict
            or verified.get('configuration_sha256')!=sha(configuration) or verified.get('result_sha256')!=sha(result)
            or verified.get('source_report_sha256')!=sha(source) or verified.get('replay_report_sha256')!=sha(replay)):
        raise ValueError('Characterization-04 independent outcome audit must PASS for these bytes')
    worker=next(row['sha256'] for row in config['sources'] if row['path']==PARENT.WORKER)
    reports={}
    for phase,raw in (('source',source),('replay',replay)):
        value=load(raw,'Characterization-04 '+phase+' report')
        if PARENT.canonical(value)!=raw:raise ValueError('Canonical characterization-04 report required')
        PARENT.validate_report(value,phase=phase,request_sha256=value.get('request_sha256'),worker_sha256=worker,dynamic_leaves=leaves)
        reports[phase]=value
    old=load(template,'Template candidate');profile=copy.deepcopy(old.get('import_profile'))
    if (old.get('kind')!='puck-cpu-observed-import-profile-candidate-v1' or type(profile) is not dict
            or profile.get('kind')!='puck-producer-import-profile-v2'):
        raise ValueError('Accepted v1 template candidate with an enhanced profile required')
    observed={row['name'] for value in reports.values() for row in value['cache']['modules']}
    for key in ('exports','module_changes','native_origins','native_cache'):
        profile[key]=[row for row in profile[key] if row['name'] in observed]
    profile['native_cache']=native_cache_rows(profile['native_cache'],reports)
    rows=load(inventory,'Retained inventory')['entries']
    census={row['path']:(None,None,stat.S_IFREG) for row in rows}
    for row in rows:
        for parent in PurePosixPath(row['path']).parents:
            if str(parent)!='.':census.setdefault(parent.as_posix(),(None,None,stat.S_IFDIR))
    prefix=str(PurePosixPath(PARENT.PYTHON).parent.parent);modules={};namespaces={};served=set()
    for phase,value in reports.items():
        site,names=split(value['cache']['modules'],set(PARENT.CAPSULE),prefix);served.update(names)
        by_name={row['name']:row for row in value['cache']['modules']}
        for export in profile['exports']:
            possible={export['producer']}
            for attribute in export['attributes']:
                possible={name for name,row in by_name.items() if any(edge['producer'] in possible
                    and edge['attribute']==attribute for edge in row.get('exports',[]))}
            if export['name'] not in possible:
                raise ValueError('Declared export edge is absent from the '+phase+' object graph: '+export['name'])
        physical,virtual=_module_maps(site_root,dict(cache=dict(modules=site)),profile,census,allow_native_cache=True)
        for target,items in ((modules,physical),(namespaces,virtual)):
            for item in items:
                if target.setdefault(item['name'],item)!=item:
                    raise ValueError('Source and replay map one module differently: '+item['name'])
    module_paths=sorted(modules.values(),key=lambda r:r['name']);namespace_rows=sorted(namespaces.values(),key=lambda r:r['name'])
    validate_profile(profile,module_paths,namespace_rows,allow_native_cache=True)
    misses=sorted({name for value in reports.values() for name in value['import_misses']
                   if name.split('.')[0] not in QUALIFIER.STDLIB_311})
    undeclared=sorted(set(misses)-set(QUALIFIER.EPISODE_NEGATIVE_IMPORTS)-set(QUALIFIER.EPISODE_HIDDEN_IMPORTS))
    if undeclared:raise ValueError('Characterized import misses are undeclared by the episode rosters: '+', '.join(undeclared[:16]))
    return dict(kind=KIND,version=2,characterization_configuration_sha256=sha(configuration),
        observation_reports=dict(source=sha(source),replay=sha(replay)),observation_result_sha256=sha(result),
        outcome_audit_sha256=sha(audit),retained_inventory_sha256=sha(inventory),template_sha256=sha(template),
        native_metadata_sha256=pins[PARENT.NATIVE_METADATA_PIN['path']]['sha256'],
        expected_versions=dict(PARENT.VERSIONS),import_profile=profile,module_paths=module_paths,
        namespaces=namespace_rows,additional_package_inputs=copy.deepcopy(old['additional_package_inputs']),
        source_modules=sorted(served),import_misses=misses,
        mapping_status='relative-path planning from the accepted inventory; no fresh namespace or device/inode census',
        limits_and_scope=('candidate data only; preparation04 and the held episode must authenticate current '
                          'bytes and observe the predicted phases'),**copy.deepcopy(CLAIMS))


def write(candidate,output):
    raw=(json.dumps(candidate,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(raw)>16*1024**2:raise ValueError('Episode candidate exceeds 16 MiB')
    with Path(output).open('xb') as stream:stream.write(raw)
    return dict(path=str(output),size_bytes=len(raw),sha256=sha(raw),physical_modules=len(candidate['module_paths']),
                namespaces=len(candidate['namespaces']),source_modules=len(candidate['source_modules']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('configuration','result','source','replay','audit','template','inventory','native'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--site-root',required=True);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    raws={name:getattr(args,name).read_bytes() for name in ('configuration','result','source','replay','audit','template','inventory','native')}
    print(json.dumps(write(derive(site_root=args.site_root,**raws),args.output),sort_keys=True))


if __name__=='__main__':main()
