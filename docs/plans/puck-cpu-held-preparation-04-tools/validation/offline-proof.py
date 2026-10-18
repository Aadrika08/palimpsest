"""Offline proofs for the preparation04 controls; never runs the observer, qualifier main, auditor main, staging or retirement.

Fixtures live only under /tmp/palimpsest-prep04-proof-*; the real worktree is read, never written,
and the consumed preparation02/03 stages are only lstat-ed.
Usage: python3.11 -I -S -B offline-proof.py [--preflight-dry-run]
"""
from pathlib import Path
import ast,copy,importlib.util,json,os,shutil,subprocess,tempfile,unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
TOOLS=ROOT/'docs/plans/puck-cpu-held-preparation-04-tools'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
P=module('proof_preflight',TOOLS/'preflight.py');C=P.C
RETIRE=module('proof_retire',TOOLS/'retire-consumed-stages.py')
PREP01=ROOT/'docs/reports/puck-cpu-held-preparation-01'
CHAR04_IDS=('a6effc7912fec337875d13ae69445e43','6c04b9ed22c383fda860fa3b4f8bab13')


class Fixture:
    """A synthetic preparation04 project root: the real configuration (root replaced), a v15 result and
    audit derived from retained preparation01 evidence, and the real qualifier/episode parent/episode auditor."""
    def __init__(self,base):
        self.base=Path(base);self.root=self.base/'root'
        for name in (C.QUALIFIER,C.EPISODE_PARENT,C.EPISODE_AUDITOR):self.write(name,(ROOT/name).read_bytes())
        self.q=C.load(self.root/C.QUALIFIER,'proof_fixture_qualifier')
        config=json.loads(C.read(ROOT/C.CONFIG));config['root']=str(self.root);self.config=config
        self.config_raw=self.q.canonical(config);self.write(C.CONFIG,self.config_raw);self.write(C.OUTPUT+'/configuration.json',self.config_raw)
        self.write(config['inputs']['candidate']['path'],(ROOT/config['inputs']['candidate']['path']).read_bytes())
        result=json.loads(C.read(PREP01/'raw/result.json'))
        result.update(kind='puck-cpu-held-runtime-outcome-v15',version=15,allocation_id=15,configuration_sha256=C.sha(self.config_raw),
            stage_parent=C.STAGE,sources=config['sources'],inputs=config['inputs'])
        self.result=result;self.result_raw=self.q.canonical(result);self.write(C.OUTPUT+'/result.json',self.result_raw)
        self.transport_sha=C.sha(b'synthetic preparation04 transport\n')
        audit=json.loads(C.read(PREP01/'audit/palimpsest-puck-cpu-held-preparation-01-audit-01.json'))
        audit.update(kind='puck-cpu-held-runtime-independent-audit-v15',version=15,allocation_id=15,auditor_source_sha256=C.AUDITOR_SHA,
            configuration_sha256=C.sha(self.config_raw),result_sha256=C.sha(self.result_raw),transport_sha256=self.transport_sha,
            dependencies_sha256=result['dependencies']['sha256'])
        self.audit=audit;self.audit_raw=self.q.canonical(audit)
        self.tmp=self.base/'tmp';self.tmp.mkdir()
        self.published=self.tmp/'audit.json';self.stdout=self.tmp/'audit.stdout';self.stderr=self.tmp/'audit.stderr'
        for path,raw in ((self.published,self.audit_raw),(self.stdout,self.audit_raw),(self.stderr,b'')):path.write_bytes(raw)
        self.command=C.audit_command(self.root,C.sha(self.config_raw),self.transport_sha,self.published)
        self.paths=dict(configuration=C.CONFIG,result=C.OUTPUT+'/result.json',independent_audit=C.ARCHIVED_AUDIT,externally_observed_auditor_cli=C.ARCHIVED_RECORD)
    def write(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():path.unlink()
        path.write_bytes(raw);return path
    def record(self,**changes):
        value,_=C.build_record(self.command,0,11.5,self.published,self.stdout,self.stderr);value.update(changes);return value,C.pretty(value)
    def accept(self,record_raw,audit_raw=None):
        audit_raw=self.audit_raw if audit_raw is None else audit_raw
        self.write(C.ARCHIVED_AUDIT,audit_raw);self.write(C.ARCHIVED_RECORD,record_raw)
        blobs=dict(configuration=self.config_raw,result=self.result_raw,independent_audit=audit_raw,externally_observed_auditor_cli=record_raw)
        _,memory=C.prove_allocation16(self.root,self.paths,blobs)
        config,disk=C.prove_allocation16(self.root,self.paths)
        return config,memory,disk


class Proofs(unittest.TestCase):
    def setUp(self):
        base=tempfile.mkdtemp(prefix='palimpsest-prep04-proof-',dir='/tmp');self.addCleanup(shutil.rmtree,base)
        self.base=Path(base);self.f=Fixture(base)

    def test_configuration_and_freeze_are_the_frozen_bytes(self):
        q=C.load(ROOT/C.QUALIFIER,'proof_real_qualifier');auditor=C.load(ROOT/C.AUDITOR,'proof_real_auditor')
        raw=C.read(ROOT/C.CONFIG);config=q.decode(raw)
        self.assertEqual(q.canonical(config),raw);q.validate_configuration(config);auditor.configuration(config,False)
        self.assertEqual((config['kind'],config['version'],config['allocation_id'],config['phase'],config['stage_parent']),
            ('puck-cpu-held-runtime-allocation-v15',15,15,'prepare',C.STAGE))
        self.assertEqual([r['path'] for r in config['sources']],list(q.PREPARATION04_SOURCES))
        self.assertEqual(config['sources'],json.loads(C.read(ROOT/'docs/reports/puck-cpu-characterization-04/frozen-configuration.json'))['sources'])
        self.assertEqual(config['inputs']['candidate']['sha256'],'3a59499b3f5eb661ec12256baf85b002f8ef5f234e64fc450ef3c8645ffa0704')
        self.assertEqual(config['inputs']['native']['path'],'docs/plans/puck-cpu-characterization-native-metadata-06.json')
        for row in config['sources']:
            if not row['path'].startswith('upstream/'):self.assertEqual((ROOT/row['path']).read_bytes(),C.git('show','HEAD:'+row['path']))
        q.validate_inputs(config,{role:(ROOT/row['path']).read_bytes() for role,row in config['inputs'].items()})
        freeze=json.loads(C.read(ROOT/C.FREEZE))
        self.assertEqual(freeze['pins']['configuration'],dict(path=C.CONFIG,size_bytes=len(raw),sha256=C.sha(raw)))
        self.assertEqual(freeze['pins']['auditor']['sha256'],C.AUDITOR_SHA);self.assertEqual(q.PREPARATION04_AUDITOR_SHA256,C.AUDITOR_SHA)
        self.assertEqual(freeze['command'],C.observer_command(ROOT,C.sha(raw)))
        self.assertEqual(freeze['stage_plan']['required_tmpfs_free_bytes'],config['limits']['min_tmpfs_free_bytes']+freeze['stage_plan']['bytes'])

    def test_outer_bounds_exceed_the_source_clocks(self):
        observer=C.load(ROOT/C.OBSERVER,'proof_observer')
        self.assertEqual((observer.NORMAL_SECONDS,observer.HARD_SECONDS,observer.CLEANUP_SECONDS),(210,225,5))
        self.assertNotIn(15,observer.EXTENDED_SECONDS);self.assertGreater(C.OBSERVER_BOUND,observer.HARD_SECONDS+observer.CLEANUP_SECONDS)
        text=(ROOT/C.AUDITOR).read_text();self.assertIn('signal.setitimer(signal.ITIMER_REAL,130)',text);self.assertGreater(C.AUDIT_BOUND,130)

    def test_record_is_accepted_by_allocation16_parent_and_episode_auditor(self):
        value,raw=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        C.check_audit(self.f.audit,config_sha=C.sha(self.f.config_raw),transport_sha=self.f.transport_sha,
            result_sha=C.sha(self.f.result_raw),dependencies_sha=self.f.result['dependencies']['sha256'])
        config,memory,disk=self.f.accept(raw)
        self.assertEqual(memory,dict(episode_validate_configuration='PASS',episode_validate_acceptance='PASS',require_declared_misses='PASS',
            sources=98,stage_parent=C.STAGE))
        self.assertEqual({k:disk[k] for k in ('episode_auditor_validate_configuration','episode_auditor_validate_acceptance')},
            dict(episode_auditor_validate_configuration='PASS',episode_auditor_validate_acceptance='PASS'))
        self.assertEqual(set(value),C.RECORD_KEYS);self.assertEqual(config['inputs'],self.f.config['inputs'])
        self.assertEqual(set(json.loads((PREP01/'audit/palimpsest-puck-cpu-held-preparation-01-audit-01.external-cli.json').read_bytes())),set(value))

    def test_builder_refuses_bad_terminals(self):
        f=self.f
        with self.assertRaises(RuntimeError):C.build_record(['/usr/bin/timeout','150s']+f.command,0,11.5,f.published,f.stdout,f.stderr)
        with self.assertRaises(RuntimeError):C.build_record(f.command,1,11.5,f.published,f.stdout,f.stderr)
        with self.assertRaises(RuntimeError):C.build_record(f.command,0,130.0,f.published,f.stdout,f.stderr)
        f.stderr.write_bytes(b'warning\n')
        with self.assertRaises(RuntimeError):C.build_record(f.command,0,11.5,f.published,f.stdout,f.stderr)

    def test_allocation16_refuses_malformed_records_and_audits(self):
        f=self.f
        for change in (dict(observed_returncode=1),dict(command=f.command[:10]+[str(f.root/'runs/puck-cpu-held-preparation-03-external-cli-transport.json')]+f.command[11:]),
                       dict(stderr=dict(path=str(f.stderr),size_bytes=8,sha256='0'*64))):
            with self.subTest(change=sorted(change)),self.assertRaises(ValueError):f.accept(f.record(**change)[1])
        for change in (dict(auditor_source_sha256='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'),
                       dict(kind='puck-cpu-held-runtime-independent-audit-v13',version=13,allocation_id=13),dict(status='FAIL'),
                       dict(dependencies_sha256='0'*64)):
            with self.subTest(change=sorted(change)):
                raw=f.q.canonical(dict(f.audit,**change))
                for path in (f.published,f.stdout):path.write_bytes(raw)
                _,record=C.build_record(f.command,0,11.5,f.published,f.stdout,f.stderr)
                with self.assertRaises(ValueError):f.accept(record,raw)

    def test_allocation16_refuses_reused_run_ids_and_undeclared_misses(self):
        f=self.f;_,raw=C.build_record(f.command,0,11.5,f.published,f.stdout,f.stderr);f.accept(raw)
        episode=C.load(f.root/C.EPISODE_PARENT,'proof_ids_episode');q=f.q
        acceptance={k:dict(path=v,size_bytes=len((f.root/v).read_bytes()),sha256=C.sha((f.root/v).read_bytes())) for k,v in f.paths.items()}
        config=C.allocation16(f.root,episode,q,f.config,acceptance,dict(source=CHAR04_IDS[0],replay='f'*32))
        with self.assertRaises(ValueError):episode.validate_configuration(config,q)
        candidate=json.loads((ROOT/f.config['inputs']['candidate']['path']).read_bytes())
        episode.require_declared_misses(candidate)
        with self.assertRaises(ValueError):episode.require_declared_misses(dict(candidate,import_misses=candidate['import_misses']+['zz_undeclared']))

    def test_consumed_stage_guard_tolerates_only_recorded_retirement(self):
        saved=(C.CONSUMED,C.CONSUMED_OUTPUTS);root=self.base/'project'
        stages=tuple(str(self.base/('stage-0'+n)) for n in '23');outputs=('runs/prep-02','runs/prep-03')
        for p in stages:os.mkdir(p)
        for p in outputs:(root/p).mkdir(parents=True)
        try:
            C.CONSUMED,C.CONSUMED_OUTPUTS=stages,outputs
            self.assertTrue(all(r['exists'] for r in C.consumed(root)))
            os.rmdir(stages[0])
            with self.assertRaises(RuntimeError):C.consumed(root)
            with self.assertRaises(RuntimeError):C.consumed(root,dict(boot_id='other',stages=[dict(path=stages[0],status='RETIRED')]))
            rows=C.consumed(root,dict(boot_id=C.BOOT,stages=[dict(path=stages[0],status='RETIRED')]))
            self.assertEqual([r['exists'] for r in rows],[False,True,True,True])
            (root/outputs[0]).rmdir()
            with self.assertRaises(RuntimeError):C.consumed(root,dict(boot_id=C.BOOT,stages=[dict(path=stages[0],status='RETIRED')]))
        finally:C.CONSUMED,C.CONSUMED_OUTPUTS=saved
        real=C.consumed()
        self.assertEqual([r['path'] for r in real],[*C.CONSUMED,*(str(ROOT/p) for p in C.CONSUMED_OUTPUTS)])

    def test_retirement_tool_refuses_other_paths_and_censuses_without_following_links(self):
        for args in ([],[C.CONSUMED[0]],list(reversed(C.CONSUMED)),[str(self.base),C.CONSUMED[1]],[*C.CONSUMED,'/tmp/palimpsest-puck-cpu-held-04']):
            process=subprocess.run([C.PYTHON,'-I','-S','-B',str(TOOLS/'retire-consumed-stages.py'),*args],capture_output=True,timeout=30,
                env=C.ENVIRONMENT,cwd=self.base)
            self.assertNotEqual(process.returncode,0,args);self.assertIn(b'Usage',process.stderr)
        self.assertTrue(all(os.path.isdir(p) for p in C.CONSUMED))
        stage=self.base/'census';(stage/'inputs/root-0000').mkdir(parents=True);(stage/'inputs/root-0000/a.txt').write_bytes(b'abc')
        os.symlink('/etc/passwd',stage/'inputs/link')
        summary,rows=RETIRE.census(str(stage))
        self.assertEqual((summary['files'],summary['directories'],summary['symlinks'],summary['file_bytes']),(1,2,1,3))
        self.assertEqual([r for r in rows if r['type']=='symlink'][0]['target'],'/etc/passwd')
        self.assertEqual(RETIRE.census(str(stage))[0]['census_sha256'],summary['census_sha256'])
        text=(TOOLS/'retire-consumed-stages.py').read_text()
        self.assertLess(text.index('C.write_new(C.ROOT/CENSUS'),text.index('shutil.rmtree(row'))

    def test_one_shot_tools_preflight_before_their_single_invocation(self):
        for name,phase,runs in (('run-observer-once.py','observer',1),('run-audit-once.py','audit',1),('archive.py','archive',0)):
            text=(TOOLS/name).read_text();calls=[n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Call)]
            checks=[n for n in calls if ast.unparse(n.func)=='P.check'];runs_=[n for n in calls if ast.unparse(n.func)=='C.run_once']
            self.assertEqual([ast.literal_eval(n.args[0]) for n in checks],[phase],name);self.assertEqual(len(runs_),runs,name)
            if runs:self.assertLess(checks[0].lineno,runs_[0].lineno,name)
            self.assertNotIn('/usr/bin/timeout',text)

    def test_stat_roots_and_run_once_and_archive_copy_on_fixture(self):
        archive=module('proof_archive',TOOLS/'archive.py')
        stage=self.base/'stage';rows=[]
        for i in range(4):
            path=stage/'inputs'/('root-'+str(i).zfill(4));path.mkdir(parents=True);state=path.stat()
            rows.append(dict(root_index=i,device=state.st_dev,inode=state.st_ino))
        self.assertTrue(all(r['matches'] for r in C.stat_roots(stage,rows)['roots']))
        with self.assertRaises(RuntimeError):C.stat_roots(stage,[dict(rows[0],inode=rows[0]['inode']+1)]+rows[1:])
        out,err=self.base/'run.stdout',self.base/'run.stderr'
        terminal=C.run_once([C.PYTHON,'-I','-S','-B','-c','print(15)'],out,err,timeout=30,cwd=self.base)
        self.assertEqual((terminal['returncode'],terminal['outer_timeout'],terminal['stdout']['sha256']),(0,False,C.sha(b'15\n')))
        with self.assertRaises(FileExistsError):C.run_once([C.PYTHON,'-c','pass'],out,err,timeout=30,cwd=self.base)
        target=self.base/'archive/audit/copy.json';rows=archive.copy([(self.f.published,target)])
        self.assertEqual(target.read_bytes(),self.f.audit_raw)
        with self.assertRaises(FileExistsError):archive.copy([(self.f.published,target)])

    def test_preflight_requires_boot_stage_family_and_room_for_the_stage(self):
        text=(TOOLS/'preflight.py').read_text()
        self.assertIn("require(C.boot_id()==C.BOOT,",text);self.assertIn("glob.glob('/tmp/palimpsest-puck-cpu-held-04*')",text)
        self.assertEqual((C.BOOT,C.STAGE,C.OUTPUT),('7f875223-b4cf-421e-b04d-81e3c1f19460','/tmp/palimpsest-puck-cpu-held-04','runs/puck-cpu-held-preparation-04'))
        freeze=json.loads(C.read(ROOT/C.FREEZE));self.assertGreater(freeze['stage_plan']['bytes'],1500*1024**2)
        self.assertEqual(freeze['stage_plan']['tmpfs_floor_bytes'],2048*1024**2)


def dry_run_preflight():
    return P.check('observer',dry_run=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--preflight-dry-run']:
        print(C.pretty(dry_run_preflight()).decode(),end='')
    else:unittest.main(verbosity=2)
