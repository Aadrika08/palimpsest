"""Synthetic NumPy/admission checks; never read a retained corpus or use a lease."""
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_male_navigation_v2 as data
import prepare_male_recovery_data as old
import collect_male_navigation_v2 as nav
from palimpsest import artifacts, male_model


def sha(payload):return hashlib.sha256(payload).hexdigest()


def world(index=0):
    return {'arena':12.,'pose':[0.,0.,0.],'goal':[4.,0.,.2],
            'obstacles':[[float(index+1),2.,.3]]}


def sources():
    older=[{'run_id':'old-'+str(i),'episode':0,'split':'train' if i<2 else 'dev',
        'geometry':data.geometry_digests(world(i)),'feature_target_sha256':'f'+str(i),
        'raw_payload_sha256':'r'+str(i)} for i in range(3)]
    newer=[{'run_id':f'new-{seed}-{learner}','episode':0,'split':'train',
        'scene_seed':seed,'learner_seed':learner,'geometry':data.geometry_digests(world(seed)),
        'initial_fingerprint':{'scene':seed},'feature_target_sha256':f'f-{seed}-{learner}',
        'raw_payload_sha256':f'r-{seed}-{learner}'} for seed in range(3100,3104) for learner in (10,11,12)]
    return older,newer


def transfer_fixture(root):
    historical=root/'reader';historical.mkdir();files={};imported={}
    for i,name in enumerate(('scripts/prepare_male_recovery_data.py','src/palimpsest/male_model.py')):
        path=historical/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'# synthetic reader\n')
        files[name]=sha(path.read_bytes());imported[str(i)]={'path':str(path),'sha256':files[name]}
    identity={'root':str(historical),'head':'synthetic','sources':files}
    manifest={'ordered_sources':{'train':[],'dev':[],'held_out':[]}};mapping=[];arrays={}
    for i in range(14):
        split='train' if i<10 else 'dev';features=np.full((2,388),i,np.float32);targets=np.full((2,2),i/20,np.float32)
        prefix=f'source{i:03d}';arrays[prefix+'_features']=features;arrays[prefix+'_targets']=targets
        manifest['ordered_sources'][split].append({'run_id':str(i),'episode':0,'ticks':2,'feature_target_sha256':sha(features.tobytes()+targets.tobytes())})
        mapping.append({'split':split,'run_id':str(i),'episode':0,'ticks':2,'prefix':prefix})
    metadata={'derived_manifest':manifest,'historical_identity':identity,'imported_sources':imported,'arrays':mapping}
    (root/'historical-result.json').write_bytes(data.canonical(metadata));np.savez(root/'historical-arrays.npz',**arrays)
    p={'source_binding':{'old_historical_reader':{'code':{'src/palimpsest/male_model.py':files['src/palimpsest/male_model.py']}}}}
    return p,identity,manifest,arrays,metadata


class NavigationData(unittest.TestCase):
    def test_lazy_import_and_frozen_protocol(self):
        p=data.protocol();self.assertEqual(p['counts']['combined_rows'],8425)
        self.assertEqual(p['limits']['internal_seconds_from_entry'],180)
        self.assertEqual(p['limits']['external_normal_through_exit_seconds'],230)
        before={name:sys.modules.get(name) for name in ('torch','mujoco')}
        completed=subprocess.run([sys.executable,'-c',
            "import prepare_male_navigation_v2, sys; assert not ({'torch','mujoco'} & set(sys.modules))"],
            cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'scripts')},capture_output=True,text=True,timeout=20)
        self.assertEqual(completed.returncode,0,completed.stderr[-1024:])
        self.assertEqual(before,{name:sys.modules.get(name) for name in before})

    def test_exact_geometry_and_three_learner_exception(self):
        base=world();base['obstacles'].append([-0.,3.,.4])
        changed=copy.deepcopy(base);changed['pose']=[-0.,0.,math.tau];changed['obstacles'].reverse()
        self.assertEqual(data.geometry_digests(base),data.geometry_digests(changed))
        changed['goal'][0]+=1e-12
        self.assertEqual(data.geometry_digests(base)['layout'],data.geometry_digests(changed)['layout'])
        self.assertNotEqual(data.geometry_digests(base)['full_scene'],data.geometry_digests(changed)['full_scene'])
        older,newer=sources();data.disjoint_sources(older,newer)
        same=copy.deepcopy(older);same[1]['geometry']=same[0]['geometry'];data.disjoint_sources(same,newer)
        for kind in ('old-split','old-new','new-scene','learner','fingerprint','payload','run-id'):
            a,b=copy.deepcopy((older,newer))
            if kind=='old-split':a[2]['geometry']=a[0]['geometry']
            elif kind=='old-new':b[0]['geometry']=a[0]['geometry']
            elif kind=='new-scene':b[3]['geometry']=b[0]['geometry']
            elif kind=='learner':b[1]['learner_seed']=10
            elif kind=='fingerprint':b[1]['initial_fingerprint']={'changed':True}
            elif kind=='payload':b[0]['raw_payload_sha256']=a[0]['raw_payload_sha256']
            else:b[0]['run_id']=a[0]['run_id']
            with self.subTest(kind=kind),self.assertRaises(ValueError):data.disjoint_sources(a,b)

    def test_actual_feature_boundary_and_returned_advice_labels(self):
        raw={'cam_left':np.zeros((128,128,3),np.uint8),'cam_right':np.ones((128,128,3),np.uint8),
             'sensors':np.array([0.,0.,1.,0.],np.float32),'action':np.array([.7,0],np.float32),
             'nav_advice_action':np.array([-.2,.4],np.float32)}
        features,targets=data.advice_arrays([raw],math.inf)
        np.testing.assert_array_equal(features[0],male_model.features(raw))
        np.testing.assert_array_equal(targets[0],raw['nav_advice_action'])
        self.assertFalse(np.array_equal(targets[0],raw['action']))
        changed={**raw,'teacher_private_pose':np.array([900,900]),'action':np.array([99,99],np.float32)}
        np.testing.assert_array_equal(data.advice_arrays([changed],math.inf)[0],features)
        with self.assertRaises(ValueError):data.advice_arrays([{**raw,'nav_advice_action':raw['nav_advice_action'].astype(np.float64)}],math.inf)
        with self.assertRaisesRegex(ValueError,'row cap'):data.advice_arrays([raw]*601,math.inf)

    def test_safe_historical_transfer_and_compressed_or_substituted_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p,identity,manifest,arrays,metadata=transfer_fixture(root)
            with patch.object(data,'protocol',return_value=p):
                admitted=data.read_old_transfer(root,manifest,identity)
                self.assertEqual(len(admitted['train']),10);self.assertEqual(len(admitted['dev']),4)
                for mutation in ('compressed','dtype','shape','extra','import','order','bytes'):
                    a=copy.deepcopy(arrays);m=copy.deepcopy(metadata)
                    if mutation=='dtype':a['source000_targets']=a['source000_targets'].astype(object)
                    elif mutation=='shape':a['source000_features']=np.zeros((20000,388),np.float32)
                    elif mutation=='extra':a['unexpected']=np.zeros(1,np.float32)
                    elif mutation=='import':m['imported_sources']['0']['path']=str(root/'outside.py')
                    elif mutation=='order':m['arrays'][0]['run_id']='substituted'
                    elif mutation=='bytes':a['source000_targets'][0,0]+=1
                    (root/'historical-result.json').write_bytes(data.canonical(m))
                    (np.savez_compressed if mutation=='compressed' else np.savez)(root/'historical-arrays.npz',**a)
                    with self.subTest(mutation=mutation),self.assertRaises(ValueError):data.read_old_transfer(root,manifest,identity)

    def test_growing_input_running_read_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'growing';file.write_bytes(b'x')
            with patch.object(Path,'open',return_value=io.BytesIO(b'xx')):
                with self.assertRaisesRegex(ValueError,'Growing'):data.file_sha(file,maximum=1)

    def test_after_inventory_retains_changed_source_and_document(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);file=root/'document.json';file.write_bytes(b'{}')
            p={'immutable_inputs':{'input':{'path':str(file),'sha256':sha(b'{}')}},
               'old_baseline_document':{'path':str(file),'sha256':sha(b'{}')},'old_recovery_document':{'path':str(file),'sha256':sha(b'{}')}}
            run=root/'run';(run/'recording').mkdir(parents=True);record=run/'recording/chunk';record.write_bytes(b'new')
            expected=[{'path':'recording/chunk','bytes':3,'sha256':sha(b'old')}];file.write_bytes(b'[]')
            with patch.object(data,'reader_identity',return_value={'changed':'bytes'}),patch.object(data,'historical_identity',return_value={'head':'changed'}):
                with self.assertRaises(ValueError):data.validate_after(root/'after.json',p,{}, {},{},[(run,expected)],math.inf)
            obtained=data.read_json(root/'after.json');self.assertTrue(obtained['errors'])
            self.assertEqual(obtained['documents']['input']['sha256'],sha(b'[]'))
            self.assertEqual(obtained['sources'][0]['files'][0]['sha256'],sha(b'new'))

    def test_child_final_source_drift_retains_after_and_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=root/'old.json';manifest.write_bytes(b'{}')
            p={'immutable_inputs':{'old_manifest':{'path':str(manifest),'sha256':sha(b'{}')}}}
            initial={'head':'before'}
            with patch.object(data,'historical_identity',return_value={'head':'after'}),patch.object(data,'imported_historical_sources',return_value={}):
                with self.assertRaisesRegex(ValueError,'source drift'):
                    data.write_payload(root/'historical-arrays.npz',b'payload',100,math.inf,
                        lambda:data.historical_after(root/'historical-after-arrays.json',p,initial,math.inf))
            self.assertFalse((root/'historical-arrays.npz').exists())
            self.assertEqual((root/'historical-arrays.npz.pending').read_bytes(),b'payload')
            self.assertEqual(data.read_json(root/'historical-after-arrays.json')['historical_identity'],{'head':'after'})
            # An unchanged old.prepare refusal also gets the fixed child receipt,
            # before control reaches either transfer publication callback.
            historical=root/'reader';(historical/'scripts').mkdir(parents=True)
            (historical/'scripts/prepare_male_recovery_data.py').write_text("def prepare(*a, **k):\n    raise ValueError('injected reader drift')\n")
            child_output=root/'child';child_output.mkdir()
            manifest=root/'old-data'/'old.json';manifest.parent.mkdir();manifest.write_bytes(b'{}')
            p['immutable_inputs']['old_manifest']={'path':str(manifest),'sha256':sha(b'{}')}
            p.update(old_baseline_document={'path':str(root/'old'/'baseline.json')},
                old_recovery_document={'path':str(root/'old'/'recovery.json')},
                source_binding={'old_historical_reader':{'root':str(historical)}})
            p['immutable_inputs']['accepted_collection']={'path':str(root/'producer'/'runs'/'collection'/'report.json')}
            identity={'root':str(historical),'head':'before','sources':{}}
            context={'output':str(child_output),'deadline':float(time.monotonic()+20),'protocol_sha256':data.PROTOCOL_SHA,
                'script_sha256':data.SELF_SHA,'historical_identity':identity}
            (child_output/'historical-context.json').write_bytes(data.canonical(context))
            code="""import json,sys
sys.path.insert(0,sys.argv[1])
import prepare_male_navigation_v2 as d
sys.path.remove(sys.argv[1])
p=json.loads(sys.argv[2]); initial=json.loads(sys.argv[3])
d.protocol=lambda:p
d.historical_identity=lambda p,deadline,enforce=True:initial if enforce else {**initial,'head':'after'}
d.imported_historical_sources=lambda identity:{}
d.historical_child(sys.argv[4])
"""
            completed=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'scripts'),json.dumps(p),json.dumps(identity),
                str(child_output/'historical-context.json')],capture_output=True,text=True,timeout=25)
            self.assertNotEqual(completed.returncode,0);self.assertIn('injected reader drift',completed.stderr)
            self.assertEqual(data.read_json(child_output/'historical-after-failure.json')['historical_identity']['head'],'after')
            self.assertFalse((child_output/'historical-result.json').exists())

    def test_collection_requires_normal_source_owner_enclosure_and_drain(self):
        p=data.protocol();clean={'sampler_stopped':True,'forced_signals':[],'survivors':[],'sample_errors':[],
            'conflicting_owned_identities':[]}
        report={'status':'completed-collection','profile':nav.PROFILE,'study_sha256':nav.PLAN_SHA,
            'contact_profile_sha256':nav.PROFILE_SHA,'qualification_claims':[],'owners_completed':12,'numeric_ticks':5080,
            'cases':{case['id']:{} for case in nav.CASES},'source_pins':{},'final_source_pins':{},
            'assets_before':{'ok':True},'assets_after':{'ok':True},'identities_before':{},'identities_after':{}}
        documents={'accepted_collection':report,'collection_terminal':{'status':'completed-collection','cleanup':clean,
            'controls_unchanged':True,'inventories_unchanged':True,'report_sha256':p['immutable_inputs']['accepted_collection']['sha256'],
            'head':p['source_binding']['navigation_producer_commit']},
            'collection_enclosing':{'status':'completed-collection','outer_cleanup':clean,'controls_unchanged':True,'outer_inventory_unchanged':True},
            'exec_drain':{'exec_exitcode':0,'matching_survivors':[],'forced_signals':[]},
            'collector_supervisor':{'status':'completed','returncode':0},'launcher_supervisor':{'status':'completed','returncode':0}}
        self.assertEqual(data.admit_collection(p,documents),report)
        for key,field,value in (('collector_supervisor','failure',{'type':'LogLimit'}),
            ('collection_terminal','head','wrong'),('exec_drain','exec_exitcode',False),
            ('accepted_collection','numeric_ticks',5079)):
            changed=copy.deepcopy(documents);changed[key][field]=value
            with self.subTest(key=key,field=field),self.assertRaises(ValueError):data.admit_collection(p,changed)

    def test_publication_fsync_and_late_final_validation_never_admit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(data.os,'fsync',side_effect=OSError('injected final sync')):
                with self.assertRaises(OSError):data.write_payload(root/'fsync.json',b'{}',100,math.inf)
            self.assertTrue((root/'fsync.json.pending').exists());self.assertFalse((root/'fsync.json').exists())
            with self.assertRaises(TimeoutError):data.write_payload(root/'late.json',b'{}',100,0)
            self.assertTrue((root/'late.json.pending').exists());self.assertFalse((root/'late.json').exists())

    def test_overlap_refusal_before_any_output_or_failure_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);corpus=root/'corpus';corpus.mkdir();document=corpus/'report.json';document.write_bytes(b'{}')
            p={'immutable_inputs':{'accepted_collection':{'path':str(document)}},
               'old_baseline_document':{'path':str(document)},'old_recovery_document':{'path':str(document)},
               'source_binding':{'old_historical_reader':{'root':str(root/'historical')}}}
            with patch.object(data,'protocol',return_value=p):
                with self.assertRaisesRegex(ValueError,'overlaps'):data.main(['--output',str(corpus/'fresh')])
            self.assertFalse((corpus/'fresh').exists());self.assertEqual(document.read_bytes(),b'{}')

    def test_staged_prepare_uses_actual_counts_disjointness_and_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            f=staged_fixture(Path(directory))
            with f['patches']():
                result=data.prepare(f['output'])
            self.assertEqual(result['status'],'prepared-navigation-advice-research-only')
            self.assertEqual(len(result['new_sources']),12)
            self.assertEqual(sum(x['ticks'] for x in result['arms']['augmented']['train']),7197)
            self.assertEqual(result['arms']['old']['dev'],result['arms']['augmented']['dev'])
            self.assertTrue((f['output']/'after-admission.json').is_file())
            self.assertTrue((f['output']/'after-final-sync.json').is_file())
            self.assertEqual(data.read_json(f['output']/'data-manifest.json'),result)
            # A failed child preserves its obtainable after state before refusal.
            f['output']=f['output'].with_name('failed-output')
            with f['patches'](),patch('palimpsest.evaluate.bounded_process',return_value={'status':'failed','returncode':1}):
                with self.assertRaisesRegex(ValueError,'child did not complete'):data.prepare(f['output'])
            self.assertTrue((f['output']/'after-historical-child-failure.json').is_file())
            self.assertFalse((f['output']/'data-manifest.json').exists())


def staged_fixture(root):
    """Real orchestration/filesystem; only fixed source and native-reader boundaries fake."""
    from contextlib import ExitStack,contextmanager
    baseline=root/'baseline';recovery=root/'recovery';collection=root/'producer'/'runs'/'collection'
    manifests={};events={};rows={};old_data={'train':[],'dev':[],'held_out':[]};baseline_runs=[];recovery_admission=[]
    def make_run(path,index,count):
        (path/'recording').mkdir(parents=True);file=path/'recording/chunk';file.write_bytes(str(index).encode())
        manifests[path]={'run_id':path.name};events[path]=[{'kind':'episode_started','episode':0,'world':world(index)}]
        rows[path]=[{'episode':0,'cam_left':np.array([index],np.uint8),'cam_right':np.array([index],np.uint8),
            'sensors':np.array([0,0,1,0],np.float32),'action':np.array([index/100,0],np.float32),
            'nav_advice_action':np.array([index/200,0],np.float32),'simulation_time':np.array((i+1)*.02),
            'eyes':np.array([True,True]),'fixture_features':np.full(388,index,np.float32)} for i in range(count)]
        return [{'path':'recording/chunk','bytes':file.stat().st_size,'sha256':sha(file.read_bytes())}]
    for i,count in enumerate([248]*7+[247]+[307]*4+[67]*2):
        name=f'{i+1:032x}';split='dev' if 8<=i<12 else 'train'
        run=(baseline/'runs'/name) if i<12 else (recovery/name)
        files=make_run(run,i,count)
        old_data[split].append({'run_id':name,'episode':0,'features':np.full((count,388),i,np.float32),'targets':np.full((count,2),i/20,np.float32)})
        if i<12:baseline_runs.append({'run_id':name,'files':files})
        else:recovery_admission.append({'run_id':name,'path':str(run),'files':files})
    old_manifest={'ordered_sources':{split:[{'run_id':x['run_id'],'episode':0,'ticks':len(x['targets']),
        'feature_target_sha256':sha(x['features'].tobytes()+x['targets'].tobytes())} for x in entries] for split,entries in old_data.items()},'recovery_admission':recovery_admission}
    report={'cases':{},'identities_before':{},'artifacts_sha256':{}}
    for i,(case,count) in enumerate(zip(nav.CASES,[600,485,496,600,196,600,600,243,198,600,276,186],strict=True)):
        stage=collection/case['id'];run=stage/f'{100+i:032x}';files=make_run(run,100+i,count)
        result={'case':case,'outcome':{'reason':'time_limit'},'contact_incidence':{},'initial_world':world(case['scene_seed']),
            'initial_fingerprint':{'scene':case['scene_seed']}}
        (stage/'result.json').write_bytes(data.canonical(result))
        report['cases'][case['id']]={'case':case,'run':str(run),'result_path':str(stage/'result.json'),'result_sha256':sha(data.canonical(result)),
            'status':'completed-recording','outcome':result['outcome'],'contact_incidence':{},'supervision':{'status':'completed','returncode':0}}
        report['identities_before'][str(case['learner_seed'])]={}
        for entry in files:report['artifacts_sha256'][str(run.relative_to(collection)/entry['path'])]=entry['sha256']
    documents={'accepted_collection':report,'old_manifest':old_manifest,'old_baseline_document':{'runs':baseline_runs},'old_recovery_document':{}}
    p={'immutable_inputs':{},'old_baseline_document':{},'old_recovery_document':{},'source_binding':{'old_historical_reader':{'root':str(root/'historical')}},'counts':data.protocol()['counts']}
    for name,value in documents.items():
        path=(baseline/'collection.json' if name=='old_baseline_document' else recovery/'report.json' if name=='old_recovery_document' else collection/'report.json' if name=='accepted_collection' else root/'old-data'/'manifest.json')
        path.parent.mkdir(parents=True,exist_ok=True);payload=data.canonical(value);path.write_bytes(payload)
        item={'path':str(path),'sha256':sha(payload),'bytes':len(payload)}
        if name.startswith('old_') and name.endswith('_document'):p[name]=item
        else:p['immutable_inputs'][name]=item
    artifact_proxy=SimpleNamespace(_safe_path=artifacts._safe_path,_id=artifacts._id,_manifest=lambda run:manifests[run],
        _events=lambda run:events[run],_world=artifacts._world)
    model_proxy=SimpleNamespace(features=lambda row:row['fixture_features'].copy(),FEATURE_PROTOCOL=male_model.FEATURE_PROTOCOL,digest=male_model.digest)
    navigation=SimpleNamespace(CASES=nav.CASES,admit_record=lambda run,result,identity:len(rows[run]))
    fixture={'output':root/'output'}
    @contextmanager
    def patches():
        with ExitStack() as stack:
            for name,value in {'protocol':p,'reader_identity':{'reader':'fixed'},'historical_identity':{'historical':'fixed'},
                'helpers':(artifact_proxy,model_proxy,lambda path:iter(rows[path.parent]),old,navigation),
                'read_old_transfer':old_data,'admit_collection':report}.items():
                stack.enter_context(patch.object(data,name,return_value=value))
            stack.enter_context(patch('palimpsest.evaluate.bounded_process',return_value={'status':'completed','returncode':0}))
            yield
    fixture['patches']=patches
    return fixture


if __name__=='__main__':unittest.main()
