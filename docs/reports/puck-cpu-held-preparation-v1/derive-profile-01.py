"""Derive a prospective CPU profile from authenticated retained data, no imports.

Only trusted local project helpers and stdlib execute. No vendor initialization,
fresh package census, staged copy, held qualification, model or study runs here.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import stat
import sys

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CAPSULE=ROOT/'docs/reports/puck-cpu-characterization-02'
OUTPUT=ROOT/'docs/plans/puck-cpu-observed-import-profile-candidate-01.json'

def sha(raw):return hashlib.sha256(raw).hexdigest()

def checked(path,digest,size=None):
    raw=path.read_bytes()
    assert sha(raw)==digest and (size is None or len(raw)==size),path
    return raw,json.loads(raw)

config_raw,config=checked(CAPSULE/'frozen-configuration.json',
    '4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8',13940)
observed_raw,observed=checked(CAPSULE/'raw/payload/imports.json',
    'f5c307bd361cd97e0f5a912610e2e639d62aa410aca4c393719667b24654b448',534299)
_,audit=checked(CAPSULE/'outcome-audit-02.json',
    '68db69256149ca20d4b698860898d33c4e6cbee2b840e4eeeb2fd5f21359eff3',1452)
template_raw,template=checked(ROOT/'docs/plans/puck-v3-observed-import-profile-candidate.json',
    '2e285931ab5fae36a96d3065d2341e5517d846c1020e94f17fd53cedaa4ac740',14437)
assert audit['status']=='PASS' and audit['ordinary_imports_observed'] is True
assert observed['status']=='observed' and observed['versions']==config['expected_versions']
assert [v['name'] for v in observed['imports']]==['numpy','torch','torchvision','mujoco']
inventory_pin=next(r for r in config['inputs'] if r['path']=='runs/puck-cpu-retained-admission-02/inventory.json')
inventory_raw,inventory=checked(CAPSULE/'inputs'/inventory_pin['path'],inventory_pin['sha256'],inventory_pin['size_bytes'])
inventory_rows={r['path']:r for r in inventory['entries']}
assert len(inventory_rows)==27225 and inventory['directory_count']==2074
rows={r['name']:r for r in observed['cache']['modules']}
old=template['import_profile'];profile=copy.deepcopy(old)
profile['exports']=[r for r in profile['exports'] if r['name'] in rows]
assert len(old['exports'])==42 and len(profile['exports'])==38
factory=next(r['class_binding'] for r in old['module_changes'] if r['name']=='torch.compiler.config')
for name in ('torch._dynamo.config','torch._functorch.config','torch._inductor.config'):
    assert rows[name]['type']=='torch.utils._config_module.install_config_module.<locals>.ConfigModuleInstance'
    profile['module_changes'].append(dict(name=name,kind='reclassify',class_binding=copy.deepcopy(factory)))
profile['module_changes'].sort(key=lambda r:r['name'])
profile.update(kind='puck-producer-import-profile-v2',version=2,native_cache=[
    dict(name='_cython_3_0_12',producer='numpy.random.bit_generator',phase='module_exec',
         delegate_attributes=['cython_function_or_method','generator']),
    dict(name='cython_runtime',producer='numpy.random.bit_generator',phase='module_exec',delegate_attributes=[])])
assert len(profile['module_changes'])==13 and len(profile['native_origins'])==11
# Check each declared attribute edge against the actual retained exceptional
# object graph. Multiple cache aliases may refer to the same observed object.
for export in profile['exports']:
    possible={export['producer']}
    for attribute in export['attributes']:
        possible={name for name,row in rows.items() if any(
            edge['producer'] in possible and edge['attribute']==attribute for edge in row.get('exports',[]))}
        assert possible,(export,attribute)
    assert export['name'] in possible,export

# This structural namespace is derived from the accepted inventory solely to
# plan relative module paths. It is not a fresh census or device/inode evidence.
structural={name:(None,None,stat.S_IFREG) for name in inventory_rows}
for name in inventory_rows:
    for parent in Path(name).parents:
        if str(parent)!='.':structural.setdefault(parent.as_posix(),(None,None,stat.S_IFDIR))
sys.pycache_prefix='/nonexistent/palimpsest-cpu-profile-source-cache'
sys.path.insert(0,str(ROOT/'src'))
from palimpsest.puck_runtime_registration import _module_maps
template_name='torch/distributed/nn/jit/templates/remote_module_template.py'
instantiator_name='torch/distributed/nn/jit/instantiator.py'
sources={}
for name in (template_name,instantiator_name):
    raw=(ROOT/config['site_root']/name).read_bytes();pin=inventory_rows[name]
    assert sha(raw)==pin['sha256'] and len(raw)==pin['size_bytes'],name
    sources[name]=ast.parse(raw.decode('utf-8'))
def function(tree,name):
    found=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(found)==1,name
    return found[0]
def assignment(nodes,name):
    found=[n.value for n in nodes if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
    assert len(found)==1,name
    return found[0]
def same(node,text):return ast.dump(node)==ast.dump(ast.parse(text,mode='eval').body)
inst=sources[instantiator_name];templ=sources[template_name]
assert ast.literal_eval(assignment(inst.body,'_FILE_PREFIX'))=='_remote_module_'
non_scriptable=function(inst,'instantiate_non_scriptable_remote_module_template')
assert same(assignment(non_scriptable.body,'generated_module_name'),'f"{_FILE_PREFIX}non_scriptable"')
args_node=assignment(non_scriptable.body,'str_dict')
assert isinstance(args_node,ast.Call) and same(args_node.func,'dict') and not args_node.args
arguments={k.arg:ast.literal_eval(k.value) for k in args_node.keywords}
assert arguments==dict(assign_module_interface_cls='module_interface_cls = None',args='*args',
    kwargs='**kwargs',arg_types='*args, **kwargs',arrow_and_return_type='',
    arrow_and_future_return_type='',jit_script_decorator='')
assert same(non_scriptable.body[-1].value,'_do_instantiate_remote_module_template(generated_module_name, str_dict, True)')
factory=function(inst,'_do_instantiate_remote_module_template')
assert same(assignment(factory.body,'generated_code_text'),'get_remote_module_template(enable_moving_cpu_tensors_to_cuda).format(**str_dict)')
selector=function(templ,'get_remote_module_template')
assert same(selector.body[0].value,'_TEMPLATE_PREFIX + (_REMOTE_FORWARD_TEMPLATE_ENABLE_MOVING_CPU_TENSORS_TO_CUDA if enable_moving_cpu_tensors_to_cuda else _REMOTE_FORWARD_TEMPLATE)')
prefix=ast.literal_eval(assignment(templ.body,'_TEMPLATE_PREFIX'))
suffix=ast.literal_eval(assignment(templ.body,'_REMOTE_FORWARD_TEMPLATE_ENABLE_MOVING_CPU_TENSORS_TO_CUDA'))
assert type(prefix) is type(suffix) is str and len(prefix)+len(suffix)<16384
generated_raw=(prefix+suffix).format(**arguments).encode('utf-8')
assert len(generated_raw)<16384
ast.parse(generated_raw.decode('utf-8'))
generated_name='_remote_module_non_scriptable'
observed_generated=rows[generated_name]
assert observed_generated['classification']=='module' and observed_generated['spec_name']==generated_name
assert observed_generated['file'].startswith('/scratch/tmp/') and Path(observed_generated['file']).name==generated_name+'.py'
base_observation=dict(observed,cache=dict(observed['cache'],modules=[r for r in observed['cache']['modules'] if r['name']!=generated_name]))
modules,namespaces=_module_maps(str(ROOT/config['site_root']),base_observation,profile,structural,allow_native_cache=True)
modules.append(dict(name=generated_name,root_index=3,path=generated_name+'.py',kind='python',is_package=False))
modules.sort(key=lambda r:r['name'])
from palimpsest.puck_dependency_bindings import validate_profile
validate_profile(profile,modules,namespaces,allow_native_cache=True)
selected=[
    'numpy/random/__init__.py','numpy/random/_pickle.py',
    'numpy/random/bit_generator.cpython-311-x86_64-linux-gnu.so',
    'numpy/random/_common.cpython-311-x86_64-linux-gnu.so',
    'torch/utils/_config_module.py','torch/_dynamo/config.py',
    'torch/_functorch/config.py','torch/_inductor/config.py',template_name,instantiator_name]
for name in selected:
    raw=(ROOT/config['site_root']/name).read_bytes();pin=inventory_rows[name]
    assert len(raw)==pin['size_bytes'] and sha(raw)==pin['sha256'],name
candidate=dict(kind='puck-cpu-observed-import-profile-candidate-v1',version=1,
    observation_report_sha256=sha(observed_raw),configuration_sha256=sha(config_raw),
    outcome_audit_sha256='68db69256149ca20d4b698860898d33c4e6cbee2b840e4eeeb2fd5f21359eff3',
    retained_inventory_sha256=sha(inventory_raw),template_sha256=sha(template_raw),
    expected_versions=config['expected_versions'],import_profile=profile,
    module_paths=modules,namespaces=namespaces,
    additional_package_inputs=[dict(root='docs/reports/puck-cpu-held-preparation-v1/generated',
        files=[dict(path=generated_name+'.py',size_bytes=len(generated_raw),sha256=sha(generated_raw))])],
    generated_source_derivation=dict(name=generated_name,observed_origin=observed_generated['file'],
        root_index=3,source_inputs=[inventory_rows[instantiator_name],inventory_rows[template_name]],
        method='AST-verified fixed non-scriptable True branch, literal strings and format arguments; no vendor code executed',
        scope='prospective registered bytes; original ephemeral source bytes were not retained or compared'),
    static_source_inputs=[inventory_rows[name] for name in selected],
    creator_status='static prediction from authenticated bytes; not observed first-creator evidence',
    mapping_status='relative-path planning from accepted inventory; no fresh namespace or device/inode census',
    limits_and_scope='candidate data only; final preparation/qualification must authenticate current bytes and observe the predicted phases',
    native_phase_qualified=False,held_runtime_qualified=False,native_authorized=False,
    collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[])
raw=(json.dumps(candidate,indent=2,sort_keys=True)+'\n').encode()
assert len(raw)<=1024**2
generated_dir=ROOT/'docs/reports/puck-cpu-held-preparation-v1/generated'
assert not OUTPUT.exists() and not generated_dir.exists()
generated_dir.mkdir(parents=True)
with (generated_dir/(generated_name+'.py')).open('xb') as stream:stream.write(generated_raw)
with OUTPUT.open('xb') as stream:stream.write(raw)
print(json.dumps(dict(path=str(OUTPUT),sha256=sha(raw),size_bytes=len(raw),
    physical_modules=len(modules),namespaces=len(namespaces),exports=38,module_changes=13,native_cache=2,
    generated_helper_sha256=sha(generated_raw),generated_helper_size_bytes=len(generated_raw))))
