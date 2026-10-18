"""Versioned fixed import probes inside an authenticated dependency-held worker.

No inference, rendering, physics, data collection or scientific authority.
A successful result still needs independent parent/outcome admission.
"""
import importlib
import time
import types

MODULES=('numpy','torch','mujoco')
CPU_MODULES=('numpy','torch','torchvision','mujoco')


def qualify(admission):
    admission.recheck()
    config=admission._reg.get('qualification')
    if admission._reg['version']!=3 or type(config) is not dict:
        raise ValueError('Fixed runtime qualification registration required')
    qualification_version=config['version']
    cpu=qualification_version in (3,4)
    # Capture the prospective four-import expectations before any dependency
    # initializer can mutate the registration. Legacy descriptors keep v1 data.
    expected=(tuple((name,config['expected_versions'][name]) for name in CPU_MODULES)
              if cpu else None)
    # Earlier admitted bootstrap owners have no diagnostic hook.
    phase=getattr(admission,'_phase',None) if cpu else None
    rows=[]
    for index,name in enumerate(CPU_MODULES if cpu else MODULES):
        admission.recheck(); started=time.monotonic()
        if phase is not None: phase('import.'+name+'.enter')
        module=importlib.import_module(name)
        if phase is not None: phase('import.'+name+'.returned')
        admission.recheck()
        namespace=types.ModuleType.__dict__['__dict__'].__get__(module)
        version=namespace.get('__version__')
        if not isinstance(version,str) or len(version)>128:
            raise ValueError('Runtime qualification version metadata invalid: '+name)
        # TorchVersion is a str subclass: read base text without framework hooks.
        version=str.__str__(version)
        if version!=(expected[index][1] if cpu else config['expected_versions'][name]):
            raise ValueError('Runtime qualification version differs: '+name)
        rows.append({'name':name,'version':version,'seconds':time.monotonic()-started})
    admission.recheck()
    result={'kind':'puck-held-runtime-import-qualification-result-v'+('2' if cpu else '1'),'version':2 if cpu else 1,
            'status':'imports_completed','imports':rows,'held_imports_observed':True,
            'runtime_qualified':False,'native_authorized':False,
            'collection_authorized':False,'executable':False,'qualification_claims':[]}
    if cpu:result['qualification_version']=qualification_version
    return result
