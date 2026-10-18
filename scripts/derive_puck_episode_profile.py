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
import posixpath
import stat
import struct
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
    """Each kept template cache row checked against its observed creator keys, plus every later key's producers.

    Keys observed before the creator phase closes (including those added by nested
    phases) are creator keys and must equal the template's. Keys observed after it
    closes become late delegates of the phase innermost when the held guard first
    sees them.
    """
    names={row['name'] for row in rows};result=[]
    for value in reports.values():
        for event in value['native_cache_dispatch']['events']:
            if event['first'] and event['cache'] not in names:
                raise ValueError('Observed shared cache module is not a template native cache row: '+event['cache'])
    for row in rows:
        late={}
        for phase,value in reports.items():
            events=[e for e in value['native_cache_dispatch']['events'] if e['cache']==row['name']]
            if (not events or not events[0]['first'] or any(e['first'] for e in events[1:])
                    or (events[0]['producer'],events[0]['phase'])!=(row['producer'],row['phase'])):
                raise ValueError('Shared cache '+row['name']+' was not first observed at its template creator in '+phase)
            closed=[e['closed'] for e in events]
            if closed!=sorted(closed) or closed[0]:
                raise ValueError('Shared cache '+row['name']+' creator close order differs in '+phase)
            if sorted({k for e in events if not e['closed'] for k in e['added']})!=row['delegate_attributes']:
                raise ValueError('Shared cache '+row['name']+' creator keys differ from the template in '+phase)
            for event in events:
                if not event['closed']:continue
                if event['producer'] is None:
                    raise ValueError('Shared cache '+row['name']+' later key appeared outside any producer phase in '+phase)
                for key in event['added']:late.setdefault(key,set()).add((event['producer'],event['phase']))
        if late:
            row=dict(row,late_delegates=[dict(attribute=key,producers=[dict(producer=p,phase=f) for p,f in sorted(late[key])])
                                         for key in sorted(late)])
        result.append(row)
    return result


def module_aliases(reports,site_root):
    """Site extensions observed under their compiled bare name too, identical in both phases."""
    observed={}
    for phase,value in reports.items():
        observed[phase]=sorted((row['name'],row['spec_name']) for row in value['cache']['modules']
            if row.get('classification')=='alias' and '.' not in row['name']
            and row['name'] not in sys.stdlib_module_names and type(row.get('spec_name')) is str
            and type(row.get('file')) is str and row['file'].startswith(site_root+'/'))
    if len(set(map(tuple,observed.values())))!=1:
        raise ValueError('Source and replay observe different module aliases')
    return [dict(name=name,target=target) for name,target in next(iter(observed.values()))]


def export_reached(export,by_name):
    """An early consistency check that a declared export path is plausible in the observed cache.

    Characterization records producer edges only for exceptional cache identities,
    so a step may also cross an ordinary module by name (``producer.attribute`` or
    a top-level ``attribute``); the final step must be a recorded edge into the
    export. The held bindings verify the exact raw producer edge at run time.
    """
    possible={export['producer']}
    for attribute in export['attributes']:
        reached={name for name,row in by_name.items() if any(edge['producer'] in possible
                 and edge['attribute']==attribute for edge in row.get('exports',[]))}
        for name in {attribute}|{p+'.'+attribute for p in possible}:
            row=by_name.get(name)
            if row is not None and row.get('spec_name')==name:reached.add(name)
        possible=reached
    row=by_name.get(export['name'])
    return export['name'] in possible and row is not None and any(
        edge['attribute']==export['attributes'][-1] for edge in row.get('exports',[]))


def elf_dynamic(raw):
    """DT_NEEDED names and RPATH/RUNPATH entries of one ELF64 little-endian shared object."""
    if raw[:4]!=b'\x7fELF' or raw[4]!=2 or raw[5]!=1:
        raise ValueError('Site extension is not an ELF64 little-endian object')
    phoff,=struct.unpack_from('<Q',raw,0x20);size,count=struct.unpack_from('<HH',raw,0x36)
    loads=[];dynamic=None
    for index in range(count):
        kind,_,offset,address,_,length=struct.unpack_from('<IIQQQQ',raw,phoff+index*size)
        if kind==1:loads.append((address,offset,length))
        elif kind==2:dynamic=(offset,length)
    if dynamic is None:return [],[]
    entries=[];strtab=None
    for offset in range(dynamic[0],dynamic[0]+dynamic[1]-15,16):
        tag,value=struct.unpack_from('<qQ',raw,offset)
        if tag==0:break
        if tag==5:strtab=value
        elif tag in (1,15,29):entries.append((tag,value))
    if not entries:return [],[]
    base=next((offset+strtab-address for address,offset,length in loads if strtab is not None and address<=strtab<address+length),None)
    if base is None:raise ValueError('Site extension string table is outside its loaded segments')
    def text(at):return raw[base+at:raw.index(b'\0',base+at)].decode()
    return ([text(v) for t,v in entries if t==1],
            [path for t,v in entries if t in (15,29) for path in text(v).split(':') if path])


def native_origin_rows(rows,modules,files,site_root):
    """The template origins plus held-directory origins every static \$ORIGIN dependency needs.

    A leaf-FD load (/proc/self/fd/N) cannot resolve a DT_NEEDED library found only
    through an \$ORIGIN-relative RUNPATH/RPATH directory, as the accepted Pillow
    correction established; each such extension's bytes must match the inventory.
    """
    files={row['path']:row for row in files};declared={row['name']:row for row in rows}
    for module in modules:
        if module['kind']!='extension' or module['name'] in declared:continue
        entry=files.get(module['path']);raw=(Path(site_root)/module['path']).read_bytes()
        if entry is None or len(raw)!=entry['size_bytes'] or sha(raw)!=entry['sha256']:
            raise ValueError('Site extension bytes differ from the retained inventory: '+module['name'])
        needed,paths=elf_dynamic(raw);origin=posixpath.dirname(module['path'])
        for path in paths:
            if '$ORIGIN' not in path.replace('${ORIGIN}','$ORIGIN'):continue
            directory=posixpath.normpath(path.replace('${ORIGIN}','$ORIGIN').replace('$ORIGIN',origin))
            if directory=='..' or directory.startswith('../') or directory.startswith('/'):continue
            if any(posixpath.normpath(posixpath.join(directory,name)) in files for name in needed):
                declared[module['name']]=dict(name=module['name'],policy='held-directory-observed-v1');break
    return sorted(declared.values(),key=lambda r:r['name'])


def derive_profile(reports,template,inventory,site_root):
    """The candidate profile, module paths and namespaces from two validated characterization reports."""
    old=load(template,'Template candidate');profile=copy.deepcopy(old.get('import_profile'))
    if (old.get('kind')!='puck-cpu-observed-import-profile-candidate-v1' or type(profile) is not dict
            or profile.get('kind')!='puck-producer-import-profile-v2'):
        raise ValueError('Accepted v1 template candidate with an enhanced profile required')
    observed={row['name'] for value in reports.values() for row in value['cache']['modules']}
    for key in ('exports','module_changes','native_origins','native_cache'):
        profile[key]=[row for row in profile[key] if row['name'] in observed]
    profile['native_cache']=native_cache_rows(profile['native_cache'],reports)
    aliases=module_aliases(reports,site_root)
    if aliases:profile['module_aliases']=aliases
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
            if not export_reached(export,by_name):
                raise ValueError('Declared export edge is absent from the '+phase+' object graph: '+export['name'])
        physical,virtual=_module_maps(site_root,dict(cache=dict(modules=site)),profile,census,allow_native_cache=True)
        for target,items in ((modules,physical),(namespaces,virtual)):
            for item in items:
                if target.setdefault(item['name'],item)!=item:
                    raise ValueError('Source and replay map one module differently: '+item['name'])
    module_paths=sorted(modules.values(),key=lambda r:r['name']);namespace_rows=sorted(namespaces.values(),key=lambda r:r['name'])
    profile['native_origins']=native_origin_rows(profile['native_origins'],module_paths,rows,site_root)
    validate_profile(profile,module_paths,namespace_rows,allow_native_cache=True)
    misses=sorted({name for value in reports.values() for name in value['import_misses']
                   if name.split('.')[0] not in QUALIFIER.STDLIB_311})
    undeclared=sorted(set(misses)-set(QUALIFIER.EPISODE_NEGATIVE_IMPORTS)-set(QUALIFIER.EPISODE_HIDDEN_IMPORTS))
    if undeclared:raise ValueError('Characterized import misses are undeclared by the episode rosters: '+', '.join(undeclared[:16]))
    return old,profile,module_paths,namespace_rows,served,misses


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
    old,profile,module_paths,namespace_rows,served,misses=derive_profile(reports,template,inventory,site_root)
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
