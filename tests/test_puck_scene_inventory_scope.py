"""Complete inventory integration on authored forests and tiny Git repositories."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import time
import pytest
from test_puck_scene_git import git
from test_puck_scene_catalog import catalog
from palimpsest import puck_on_policy as p


def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(value):return hashlib.sha256(value if type(value) is bytes else raw(value)).hexdigest()
def module():
    name='palimpsest.puck_scene_inventory_scope'
    assert importlib.util.find_spec(name),'Complete held inventory coordinator missing'
    return importlib.import_module(name)


def fixture(tmp_path, with_git=False):
    forest=tmp_path/'project';forest.mkdir()
    paths={name:forest/name for name in ('refs','worktrees','registry','manifests')}
    for path in paths.values():path.mkdir()
    cat=catalog();cat['layouts']=cat['layouts'][:1]
    path=paths['manifests']/'catalog.json';payload=raw(cat);path.write_bytes(payload)
    files=[{'path':str(path),'kind':'task_catalog','size_bytes':len(payload),'sha256':sha(payload)}]
    repos=[];git_docs=[]
    if with_git:
        repo=paths['worktrees']/'repo';repo.mkdir();remote=tmp_path/'remote.git';remote.mkdir()
        git(repo,'init','-q','--initial-branch=main');git(remote,'init','-q','--bare')
        (repo/'catalog.json').write_bytes(payload)
        git(repo,'add','.');git(repo,'commit','-qm','authored catalog')
        git(repo,'remote','add','origin',str(remote));git(repo,'push','-q','origin','main')
        oid=git(repo,'rev-parse','HEAD:catalog.json')
        files.append({'path':str(repo/'catalog.json'),'kind':'task_catalog','size_bytes':len(payload),'sha256':sha(payload)})
        repos=[{'repo':str(repo),'remote':'origin','expected_remote_url':str(remote)}]
        git_docs=[{'repo':str(repo),'oid':oid,'kind':'task_catalog','size_bytes':len(payload),'sha256':sha(payload)}]
        paths['refs']=repo/'.git'
    registration={'id':'puck-scene-inventory-scope-v1','version':1,
        'root_contract':{'id':'puck-scene-root-search-v1','version':1,'search_roots':[str(forest)],'opaque_subtrees':[]},
        'repositories':repos,'files':sorted(files,key=lambda r:r['path']), 'git_documents':git_docs,'origins':[],
        'retained_reference_roots':[str(paths['registry']),str(paths['manifests'])],
        'role_roots':[{'kind':kind,'path':str(paths[name])} for kind,name in
            (('ref','refs'),('worktree','worktrees'),('raw_registry','registry'),('manifest','manifests'))],
        'prospective':{'lineage_sha256':p.PROTOCOL_SHA256,'scene_ids':list(p.RESERVED_SCENE_IDS)}}
    return registration,forest,paths


def held(registration):
    payload=raw(registration)
    return module().HeldPuckSceneInventory(payload,expected_sha256=sha(payload),deadline=time.monotonic()+30)


@pytest.mark.parametrize('with_git',[False,True])
def test_complete_authored_scope_feeds_legacy_collision_projection(with_git,tmp_path):
    registration,_,_=fixture(tmp_path,with_git)
    with held(registration) as inventory:
        receipt=inventory.snapshot()
        assert receipt['declared_scope_covered'] is True
        assert receipt['semantic_closure_resolved'] is True
        assert receipt['inventory_complete'] is False
        assert receipt['executable'] is receipt['reservation_authorized'] is receipt['collection_authorized'] is False
        assert [v['scene_id'] for v in receipt['variants']]==[5100,6000]
        projection=inventory.legacy_projection()
        assert projection['complete'] is True and projection['remote_refs_fresh'] is True
        assert p._validate_inventory(projection,p.PROTOCOL_SHA256)['occupied_scene_ids']==[5100,6000]
        assert len(projection['records'])==5
        inventory.recheck()
    with pytest.raises(RuntimeError):inventory.snapshot()
    with pytest.raises(RuntimeError):inventory.legacy_projection()


@pytest.mark.parametrize('defect',['omit-file','extra-file','extra-repo','unknown-schema','bare-repo','opaque','alias'])
def test_incomplete_source_coverage_refuses_before_projection(defect,tmp_path):
    registration,forest,paths=fixture(tmp_path)
    if defect=='omit-file':registration['files']=[]
    elif defect=='extra-file':(forest/'unlisted.md').write_text('# Unlisted document\n')
    elif defect=='extra-repo':(forest/'.git').mkdir()
    elif defect=='unknown-schema':registration['files'][0]['kind']='unknown'
    elif defect=='bare-repo':
        (forest/'HEAD').write_text('ref: refs/heads/main\n');(forest/'objects').mkdir();(forest/'refs').mkdir(exist_ok=True)
    elif defect=='opaque':
        registration['root_contract']['opaque_subtrees']=[{'path':str(paths['registry']),'reason':'not observed'}]
    else:
        registration['files'].append(copy.deepcopy(registration['files'][0]))
    with pytest.raises((ValueError,RuntimeError)):
        with held(registration) as inventory:inventory.legacy_projection()


def test_changed_selected_bytes_and_namespace_poison_every_public_operation(tmp_path):
    registration,forest,_=fixture(tmp_path)
    inventory=held(registration);inventory.__enter__()
    (forest/'new.md').write_text('# Drift\n')
    with pytest.raises(RuntimeError):inventory.recheck()
    for operation in (inventory.snapshot,inventory.legacy_projection,inventory.recheck):
        with pytest.raises(RuntimeError):operation()
    with pytest.raises(RuntimeError):inventory.__exit__(None,None,None)


def test_distinct_historical_scene_variants_are_preserved_and_stop_legacy_projection(tmp_path):
    registration,_,paths=fixture(tmp_path,True);repo=Path(registration['repositories'][0]['repo'])
    value=catalog();value['layouts']=value['layouts'][:1];value['layouts'][0]['goal_xy'][0]=1.75
    payload=raw(value);(repo/'catalog.json').write_bytes(payload);git(repo,'add','.');git(repo,'commit','-qm','authored variant');git(repo,'push','-q','origin','main')
    for row in registration['files']:
        if row['path']==str(repo/'catalog.json'):row.update(size_bytes=len(payload),sha256=sha(payload))
    registration['git_documents'].append({'repo':str(repo),'oid':git(repo,'rev-parse','HEAD:catalog.json'),
        'kind':'task_catalog','size_bytes':len(payload),'sha256':sha(payload)})
    with held(registration) as inventory:
        receipt=inventory.snapshot()
        assert receipt['declared_scope_covered'] is True and receipt['semantic_closure_resolved'] is True
        assert len(receipt['variants'])==3
        assert receipt['id_variants']
        with pytest.raises(ValueError,match='legacy'):inventory.legacy_projection()


def test_public_held_out_catalog_exposure_is_recorded_and_not_silently_mapped_to_legacy_flag(tmp_path):
    registration,_,_=fixture(tmp_path);payload=raw(catalog())
    path=Path(registration['files'][0]['path']);path.write_bytes(payload)
    registration['files'][0].update(size_bytes=len(payload),sha256=sha(payload))
    with held(registration) as inventory:
        assert inventory.snapshot()['held_out_catalog_read'] is True
        with pytest.raises(ValueError,match='legacy'):inventory.legacy_projection()
