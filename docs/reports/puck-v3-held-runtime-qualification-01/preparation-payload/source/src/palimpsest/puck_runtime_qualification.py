"""Fixed three-import probe inside an authenticated, dependency-held worker.

No inference, rendering, physics, data collection or scientific authority.
A successful result still needs independent parent/outcome admission.
"""
import importlib
import time
import types

MODULES=('numpy','torch','mujoco')


def qualify(admission):
    admission.recheck()
    config=admission._reg.get('qualification')
    if admission._reg['version']!=3 or type(config) is not dict:
        raise ValueError('Fixed runtime qualification registration required')
    rows=[]
    for name in MODULES:
        admission.recheck(); started=time.monotonic()
        module=importlib.import_module(name)
        admission.recheck()
        namespace=types.ModuleType.__dict__['__dict__'].__get__(module)
        version=namespace.get('__version__')
        if not isinstance(version,str) or len(version)>128:
            raise ValueError('Runtime qualification version metadata invalid: '+name)
        # TorchVersion is a str subclass: read base text without framework hooks.
        version=str.__str__(version)
        if version!=config['expected_versions'][name]:
            raise ValueError('Runtime qualification version differs: '+name)
        rows.append({'name':name,'version':version,'seconds':time.monotonic()-started})
    admission.recheck()
    return {'kind':'puck-held-runtime-import-qualification-result-v1','version':1,
            'status':'imports_completed','imports':rows,'held_imports_observed':True,
            'runtime_qualified':False,'native_authorized':False,
            'collection_authorized':False,'executable':False,'qualification_claims':[]}
