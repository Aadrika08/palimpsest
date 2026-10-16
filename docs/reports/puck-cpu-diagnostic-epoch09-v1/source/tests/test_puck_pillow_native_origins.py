"""Authored Pillow-shaped ELF chains; no installed Pillow or vendor imports.

Held-directory origin detects persistent target mismatches. It does not stop
transient swaps or establish race-free native execution.
"""
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

import pytest


ROOT=Path(__file__).resolve().parents[1]
HELPER='libpalimpsest_pillow_helper.so'
TRANSITIVE='libpalimpsest_pillow_transitive.so'


def authored_pillow_images(site,build,*,python_extensions=False):
    """Compile only these two authored targets and their finite shared chain."""
    compiler=shutil.which('cc')
    if compiler is None:pytest.skip('authored Pillow-origin probe requires cc')
    site=Path(site);build=Path(build)
    package=site/'PIL';libraries=site/'pillow.libs'
    package.mkdir(mode=0o700,parents=True,exist_ok=True)
    libraries.mkdir(mode=0o700);build.mkdir(mode=0o700,parents=True)
    transitive=build/'transitive.c'
    transitive.write_text('int palimpsest_pillow_transitive(void){return 17;}\n')
    helper=build/'helper.c'
    helper.write_text('extern int palimpsest_pillow_transitive(void);\n'
        'int palimpsest_pillow_helper(void){return palimpsest_pillow_transitive()+23;}\n')
    subprocess.run([compiler,'-shared','-fPIC',str(transitive),'-o',str(libraries/TRANSITIVE),
        '-Wl,-soname,'+TRANSITIVE],check=True,capture_output=True,timeout=15)
    subprocess.run([compiler,'-shared','-fPIC',str(helper),'-o',str(libraries/HELPER),
        '-L'+str(libraries),'-lpalimpsest_pillow_transitive','-Wl,-soname,'+HELPER,
        '-Wl,-z,origin','-Wl,-rpath,$ORIGIN'],check=True,capture_output=True,timeout=15)
    suffix=importlib.machinery.EXTENSION_SUFFIXES[0] if python_extensions else '.so'
    targets=[]
    for leaf in ('_imaging','_imagingft'):
        source=build/(leaf+'.c')
        if python_extensions:
            text=('#include <Python.h>\nextern int palimpsest_pillow_helper(void);\n'
                'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"PIL.'+leaf+'",NULL,-1,NULL};\n'
                'PyMODINIT_FUNC PyInit_'+leaf+'(void){\n'
                'if(palimpsest_pillow_helper()!=40){PyErr_SetString(PyExc_RuntimeError,"AUTHORED helper mismatch");return NULL;}\n'
                'return PyModule_Create(&mod);}\n')
        else:
            text=('extern int palimpsest_pillow_helper(void);\n'
                'int palimpsest_pillow_value(void){return palimpsest_pillow_helper()+7;}\n')
        source.write_text(text)
        target=package/(leaf+suffix)
        include=['-I'+sysconfig.get_paths()['include']] if python_extensions else []
        subprocess.run([compiler,'-shared','-fPIC',*include,str(source),'-o',str(target),
            '-L'+str(libraries),'-lpalimpsest_pillow_helper','-Wl,-z,origin',
            '-Wl,-rpath,$ORIGIN/../pillow.libs'],check=True,capture_output=True,timeout=15)
        targets.append(target)
    return targets+[libraries/HELPER,libraries/TRANSITIVE]


_CHILD=r'''
import ctypes,json,os,sys
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
from palimpsest.puck_native_origins import native_load_path,require_native_target
fd,parent_fd=map(int,sys.argv[2:4])
policy,mode,leaf,site=sys.argv[4:8]
state=os.fstat(fd);identity=(state.st_dev,state.st_ino)
row={'root_index':0,'path':'PIL/'+leaf}
holder=SimpleNamespace(_files={row['path']:(fd,parent_fd,leaf,identity)})
class Provider:
    _holders=[holder]
    checks=0
    def _target_recheck(self,actual,path):
        assert actual is holder and path==row['path']
        self.checks+=1
        edge=os.stat(leaf,dir_fd=parent_fd,follow_symlinks=False)
        target=os.fstat(fd)
        if (edge.st_dev,edge.st_ino)!=identity or (target.st_dev,target.st_ino)!=identity:
            raise RuntimeError('AUTHORED persistent target edge differs')
provider=Provider()
load_path=native_load_path(provider,row,policy)
try:image=ctypes.CDLL(load_path)
except OSError as error:
    assert policy=='exact-file-fd-v1' and mode=='missing-sibling',str(error)
    assert 'libpalimpsest_pillow_helper.so' in str(error),str(error)
    print(json.dumps({'missing_sibling':True,'checks':provider.checks}))
    sys.exit(0)
assert policy=='held-directory-observed-v1' and mode!='missing-sibling'
image.palimpsest_pillow_value.restype=ctypes.c_int
assert image.palimpsest_pillow_value()==47
observed={}
with open('/proc/self/maps','rb') as stream:
    for line in stream:
        fields=line.split(None,5)
        if len(fields)<5 or not int(fields[4]):continue
        major,minor=(int(v,16) for v in fields[3].split(b':'))
        key=(os.makedev(major,minor),int(fields[4]))
        observed.setdefault(key,set()).add(os.fsdecode(fields[5].strip()) if len(fields)==6 else '')
assert identity in observed
dependencies=[]
for name in ('libpalimpsest_pillow_helper.so','libpalimpsest_pillow_transitive.so'):
    dependency=os.stat(site+'/pillow.libs/'+name,follow_symlinks=False)
    key=(dependency.st_dev,dependency.st_ino)
    assert key in observed,name
    dependencies.append({'name':name,'device':key[0],'inode':key[1]})
if mode=='persistent-swap':
    os.replace(site+'/PIL/.replacement-'+leaf,site+'/PIL/'+leaf)
    try:require_native_target(provider,row,policy,observed)
    except RuntimeError as error:assert 'persistent target edge' in str(error)
    else:raise AssertionError('persistent target mismatch was accepted')
    result={'persistent_mismatch_refused':True}
elif mode=='missing-target-map':
    observed.pop(identity)
    try:require_native_target(provider,row,policy,observed)
    except RuntimeError as error:assert 'target image was not observed' in str(error)
    else:raise AssertionError('missing exact target map was accepted')
    result={'missing_target_refused':True}
else:
    assert mode=='normal'
    require_native_target(provider,row,policy,observed)
    result={'return_value':47,'target_mapped':True}
result.update(device=identity[0],inode=identity[1],dependencies=dependencies,checks=provider.checks)
print(json.dumps(result))
'''


def run_authored_pillow_child(site,target,policy,mode):
    directory=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        leaf=os.open(target,os.O_RDONLY)
        try:
            state=os.fstat(leaf)
            if mode=='persistent-swap':shutil.copyfile(target,target.with_name('.replacement-'+target.name))
            environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
            child=subprocess.run([sys.executable,'-I','-S','-B','-c',_CHILD,str(ROOT/'src'),
                str(leaf),str(directory),policy,mode,target.name,str(site)],pass_fds=(leaf,directory),
                env=environment,check=True,capture_output=True,text=True,timeout=15)
            return json.loads(child.stdout),state
        finally:os.close(leaf)
    finally:os.close(directory)


@pytest.mark.parametrize('leaf',['_imaging.so','_imagingft.so'])
def test_pillow_directory_origin_maps_target_sibling_helper_and_transitive_leaf(tmp_path,leaf):
    site=tmp_path/'site';images=authored_pillow_images(site,tmp_path/'build')
    target=site/'PIL'/leaf
    before=len(os.listdir('/proc/self/fd'))
    result,state=run_authored_pillow_child(site,target,'held-directory-observed-v1','normal')
    assert result['return_value']==47 and result['target_mapped'] is True and result['checks']==2
    assert (result['device'],result['inode'])==(state.st_dev,state.st_ino)
    assert result['dependencies']==[dict(name=p.name,device=p.stat().st_dev,inode=p.stat().st_ino) for p in images[2:]]
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('leaf',['_imaging.so','_imagingft.so'])
def test_pillow_exact_leaf_fd_cannot_find_the_sibling_library_tree(tmp_path,leaf):
    site=tmp_path/'site';authored_pillow_images(site,tmp_path/'build')
    result,_=run_authored_pillow_child(site,site/'PIL'/leaf,'exact-file-fd-v1','missing-sibling')
    assert result=={'missing_sibling':True,'checks':1}


@pytest.mark.parametrize('leaf',['_imaging.so','_imagingft.so'])
@pytest.mark.parametrize('mode',['persistent-swap','missing-target-map'])
def test_pillow_directory_origin_still_refuses_persistent_target_identity_mismatch(tmp_path,leaf,mode):
    site=tmp_path/'site';authored_pillow_images(site,tmp_path/'build')
    result,_=run_authored_pillow_child(site,site/'PIL'/leaf,'held-directory-observed-v1',mode)
    assert result['persistent_mismatch_refused' if mode=='persistent-swap' else 'missing_target_refused'] is True
    assert result['checks']==(2 if mode=='persistent-swap' else 1)
