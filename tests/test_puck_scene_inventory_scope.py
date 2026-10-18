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
    with pytest.raises(ValueError,match='legacy'):
        with held(registration) as inventory:
            receipt=inventory.snapshot()
            assert receipt['declared_scope_covered'] is True and receipt['semantic_closure_resolved'] is True
            assert len(receipt['variants'])==3
            assert receipt['id_variants']
            inventory.legacy_projection()


def test_public_held_out_catalog_exposure_is_recorded_and_not_silently_mapped_to_legacy_flag(tmp_path):
    registration,_,_=fixture(tmp_path);payload=raw(catalog())
    path=Path(registration['files'][0]['path']);path.write_bytes(payload)
    registration['files'][0].update(size_bytes=len(payload),sha256=sha(payload))
    with pytest.raises(ValueError,match='legacy'):
        with held(registration) as inventory:
            assert inventory.snapshot()['held_out_catalog_read'] is True
            inventory.legacy_projection()


def add_live(registration,path,payload,kind):
    path.write_bytes(payload)
    registration['files'].append({'path':str(path),'kind':kind,'size_bytes':len(payload),'sha256':sha(payload)})
    registration['files'].sort(key=lambda row:row['path'])


def test_markdown_declared_scenes_follow_authenticated_local_json_link(tmp_path):
    registration,_,paths=fixture(tmp_path)
    add_live(registration,paths['manifests']/'note.md',b'Scene IDs: 6000; split: train\n[Task](catalog.json)\n','markdown')
    with held(registration) as inventory:
        receipt=inventory.snapshot();assert receipt['semantic_closure_resolved'] is True
        occurrence=next(row for v in receipt['variants'] if v['scene_id']==6000 for row in v['occurrences'] if row['document_path'].endswith('note.md'))
        assert occurrence['identity_sources']==[str(paths['manifests']/'catalog.json')]
        inventory.legacy_projection()


def test_unknown_markdown_declarations_block_projection_and_preserve_diagnostics(tmp_path):
    registration,_,paths=fixture(tmp_path)
    add_live(registration,paths['manifests']/'note.md',b'Scene IDs are perhaps 6000 or 6001\n','markdown')
    with pytest.raises(ValueError,match='legacy'):
        with held(registration) as inventory:
            assert inventory.snapshot()['blockers']
            inventory.legacy_projection()


def test_historical_markdown_links_never_select_uncommitted_worktree_file(tmp_path):
    registration,_,_=fixture(tmp_path,True);repo=Path(registration['repositories'][0]['repo'])
    note=b'Scene IDs: 6000; split: train\n[Task](catalog.json)\n'
    add_live(registration,repo/'note.md',note,'markdown');git(repo,'add','.');git(repo,'commit','-qm','authored link');git(repo,'push','-q','origin','main')
    commit=git(repo,'rev-parse','HEAD')
    registration['git_documents'].append({'repo':str(repo),'oid':git(repo,'rev-parse','HEAD:note.md'),'kind':'markdown','size_bytes':len(note),'sha256':sha(note)})
    value=catalog();value['layouts']=value['layouts'][:1];value['layouts'][0]['goal_xy'][0]=1.75
    payload=raw(value);(repo/'catalog.json').write_bytes(payload)
    next(row for row in registration['files'] if row['path']==str(repo/'catalog.json')).update(size_bytes=len(payload),sha256=sha(payload))
    with held(registration) as inventory:
        receipt=inventory.snapshot();assert receipt['semantic_closure_resolved'] is True
        notes=[(v,row) for v in receipt['variants'] if v['scene_id']==6000 for row in v['occurrences'] if row['document_path']==str(repo/'note.md')]
        old=next(v for v,row in notes if row['context'].get('commit')==commit)
        current=next(v for v,row in notes if row['context']['kind']=='filesystem')
        assert old['scientific_initial_sha256']!=current['scientific_initial_sha256']


def test_json_reference_budget_is_shared_across_live_and_historical_contexts(tmp_path,monkeypatch):
    from test_puck_scene_reference_resolution import report
    registration,_,_=fixture(tmp_path,True);repo=Path(registration['repositories'][0]['repo'])
    cat_raw=(repo/'catalog.json').read_bytes();payload=raw(report(b'{}',cat_raw))
    add_live(registration,repo/'report.json',payload,'teacher_collection_report')
    git(repo,'add','.');git(repo,'commit','-qm','authored missing reference');git(repo,'push','-q','origin','main')
    registration['git_documents'].append({'repo':str(repo),'oid':git(repo,'rev-parse','HEAD:report.json'),
        'kind':'teacher_collection_report','size_bytes':len(payload),'sha256':sha(payload)})
    monkeypatch.setattr(module(),'MAX_REFERENCES',1)
    with pytest.raises(ValueError,match='reference ceiling'):
        with held(registration):pass


def test_public_custody_metadata_budgets_cover_roots_and_selected_file_holders(tmp_path):
    from palimpsest.puck_scene_roots import HeldSceneInventoryRoots,_json
    from palimpsest.puck_execution_files import HeldCollectionFiles
    registration,forest,_=fixture(tmp_path)
    root_raw=_json(registration['root_contract'])
    with HeldSceneInventoryRoots(root_raw,expected_sha256=sha(root_raw),deadline=time.monotonic()+10) as roots:
        assert callable(getattr(roots,'retained_metadata_size_bytes',None)), 'Root metadata budget seam missing'
        assert 0<roots.retained_metadata_size_bytes()<=64*1024**2
    file=registration['files'][0]
    entries=[{'path':str(Path(file['path']).relative_to(forest)),'size_bytes':file['size_bytes'],'sha256':file['sha256']}]
    with HeldCollectionFiles(forest,entries,time.monotonic()+10) as files:
        assert callable(getattr(files,'retained_metadata_size_bytes',None)), 'File metadata budget seam missing'
        assert 0<files.retained_metadata_size_bytes()<=64*1024**2


def test_full_namespace_coverage_refuses_before_any_live_document_payload_read(tmp_path,monkeypatch):
    registration,_,_=fixture(tmp_path,True);registration['git_documents']=[]
    subject=module();reads=[];original=subject.HeldCollectionFiles.read
    def recording_read(holder,*args):
        reads.append(args);return original(holder,*args)
    monkeypatch.setattr(subject.HeldCollectionFiles,'read',recording_read)
    with pytest.raises(ValueError,match='classification coverage'):
        with held(registration):pass
    assert reads==[]


@pytest.mark.parametrize('note', [
    b'[Scene IDs: 6110](catalog.json)\n',
    b'[Scene IDs: 6110 catalog.json](catalog.json)\n',
    b'[Task](catalog.json "Scene IDs: 6110")\n',
    b'[r]: catalog.json "Scene IDs: 6110"\n',
    b'[Task][Scene IDs: 6110]\n',
    b'[Scene IDs: 6110][r]\n[r]: catalog.json\n',
    b'[Scene IDs: 6110]\n[Scene IDs: 6110]: catalog.json\n',
])
def test_reserved_scene_declaration_inside_link_label_blocks_projection(tmp_path,note):
    registration,_,paths=fixture(tmp_path)
    add_live(registration,paths['manifests']/'note.md',note,'markdown')
    with pytest.raises(ValueError,match='legacy'):
        with held(registration) as inventory:
            assert inventory.snapshot()['semantic_closure_resolved'] is False
            inventory.legacy_projection()
