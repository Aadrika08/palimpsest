"""Offline crosscheck of retained metadata; no numerical package imports."""
import datetime,hashlib,json,os,re,tomllib
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
root=Path('docs/reports/puck-cpu-footprint-02')
v=json.loads((root/'assessment.json').read_bytes())
assert len(v['wheels'])==70
assert sum(r['declared_expanded_bytes'] for r in v['wheels'])==1304650469
assert sum(r['file_count'] for r in v['wheels'])==26913
rounded=0
for row in v['wheels']:
    raw=(root/(row['name']+'-METADATA')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['metadata_sha256']
    entries=json.loads((root/(row['name']+'-entries.json')).read_bytes())
    assert sum(e['size_bytes'] for e in entries)==row['declared_expanded_bytes']
    assert sum(not e['name'].endswith('/') for e in entries)==row['file_count']
    rounded+=sum(((e['size_bytes']+4095)//4096)*4096 for e in entries if not e['name'].endswith('/'))
byname={r['name']:r for r in v['wheels']}
canon=lambda s:re.sub('[-_.]+','-',s).lower()
p=tomllib.loads(Path('pyproject.toml').read_text())
env=default_environment();env.update(python_version='3.11',python_full_version='3.11.15',sys_platform='linux',platform_system='Linux',platform_machine='x86_64',implementation_name='cpython',platform_python_implementation='CPython')
versions={n:r['version'] for n,r in byname.items()};versions['python-louvain']='0.16'
roots=[r for k in ('simulation','lab') for r in p['project']['optional-dependencies'][k]]+p['dependency-groups']['dev']
pending=[(Requirement(r),'project',frozenset()) for r in roots];seen={};checks=[];gaps=[]
while pending:
    req,parent,parent_extras=pending.pop()
    if req.marker and not any(req.marker.evaluate({**env,'extra':e}) for e in set(parent_extras)|{''}):continue
    name=canon(req.name);actual=versions.get(name)
    if actual is None or (req.specifier and actual not in req.specifier):
        gaps.append({'from':parent,'requirement':str(req),'selected':actual});continue
    checks.append({'from':parent,'requirement':str(req),'selected':actual})
    extra=set(req.extras);old=seen.get(name)
    if old is not None and extra<=old:continue
    merged=(old or set())|extra;seen[name]=merged
    if name not in byname:
        gaps.append({'name':name,'reason':'source-only package metadata/build not assessed'});continue
    pending.extend((Requirement(child),name,frozenset(merged)) for child in byname[name]['requires_dist'])
conflicts=[{'name':n,'requires_python':r['requires_python']} for n,r in byname.items() if r['requires_python'] and '3.11.15' not in SpecifierSet(r['requires_python'])]
check={'kind':'cpu-wheel-metadata-crosscheck-v1','packaging_version':'26.3','target_environment':env,'roots':roots,'selected_wheels':len(byname),'declared_expanded_bytes':v['total_declared_expanded_bytes'],'rounded_4k_file_bytes_estimate':rounded,'metadata_dependency_edges_checked':len(checks),'reached_distribution_count':len(seen),'gaps':gaps,'requires_python_conflicts':conflicts,'extra_selected_distributions':sorted(set(byname)-set(seen)),'licence_metadata_omissions':[n for n,r in byname.items() if not(r['licence'] or r['licence_expression'] or r['licence_files'])],'checks':checks,'payload_hashes_verified':False,'runtime_qualified':False,'collection_authorized':False,'executable':False}
(root/'crosscheck.json').write_text(json.dumps(check,sort_keys=True,indent=2)+'\n')
spaces={}
for path in ('.','/tmp','/dev/shm','/run/user/1000','/run'):
    s=os.statvfs(path);st=os.stat(path)
    spaces[str(Path(path).resolve())]={'capacity_bytes':s.f_blocks*s.f_frsize,'available_bytes':s.f_bavail*s.f_frsize,'flags':s.f_flag,'noexec':bool(s.f_flag&os.ST_NOEXEC),'readonly':bool(s.f_flag&os.ST_RDONLY),'writable_searchable_to_effective_user':os.access(path,os.W_OK|os.X_OK,effective_ids=True),'device':st.st_dev,'inode':st.st_ino,'size':st.st_size,'nlink':st.st_nlink,'mode':st.st_mode,'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:'))}
host={'measured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'mountinfo_sha256':hashlib.sha256(Path('/proc/self/mountinfo').read_bytes()).hexdigest(),'filesystems':spaces,'memory':mem,'not_reserved':True,'execution_permission_tested':False}
(root/'host-metadata.json').write_text(json.dumps(host,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:value for k,value in check.items() if k not in ('checks','target_environment','roots')},indent=2))
print('MemAvailable',mem['MemAvailable'])
print('direct',[(r['name'],r['version'],r['declared_expanded_bytes']) for r in v['wheels'] if r['name'] in ('numpy','torch','torchvision','mujoco')])
