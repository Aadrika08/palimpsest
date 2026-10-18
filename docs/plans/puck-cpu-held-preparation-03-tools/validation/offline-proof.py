"""Offline proofs for the preparation03 controls; never runs the observer, qualifier main, auditor main or staging.

Fixtures live only under /tmp/palimpsest-prep03-proof-*; the real worktree is read, never written.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,shutil,tempfile,unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
TOOLS=ROOT/'docs/plans/puck-cpu-held-preparation-03-tools'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
P=module('proof_preflight',TOOLS/'preflight.py');C=P.C
ARCHIVE=module('proof_archive',TOOLS/'archive.py')
PREP01_RECORD=ROOT/'docs/reports/puck-cpu-held-preparation-01/audit/palimpsest-puck-cpu-held-preparation-01-audit-01.external-cli.json'
PREP01_AUDIT=ROOT/'docs/reports/puck-cpu-held-preparation-01/audit/palimpsest-puck-cpu-held-preparation-01-audit-01.json'
PREP01_RESULT=ROOT/'docs/reports/puck-cpu-held-preparation-01/raw/result.json'
REAL_AUDITOR=ROOT/'scripts/audit_puck_cpu_held_runtime.py'


class Fixture:
    """A synthetic preparation03 project root whose bytes are derived from retained preparation01 evidence."""
    def __init__(self,base):
        self.base=Path(base);self.root=self.base/'root'
        (self.root/'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/qualify_puck_cpu_held_runtime.py',self.root/'scripts/qualify_puck_cpu_held_runtime.py')
        self.parent=C.load(self.root/'scripts/qualify_puck_cpu_held_runtime.py','proof_fixture_parent')
        self.auditor=C.load(REAL_AUDITOR,'proof_fixture_auditor')
        assert self.parent.ROOT==self.root and self.auditor.__file__==str(REAL_AUDITOR)
        config=json.loads(C.read(ROOT/C.CONFIG));config['root']=str(self.root)
        self.config_raw=self.parent.canonical(config);self.write(C.CONFIG,self.config_raw)
        result=json.loads(C.read(PREP01_RESULT))
        result.update(kind='puck-cpu-held-runtime-outcome-v13',version=13,allocation_id=13,configuration_sha256=C.sha(self.config_raw),
            stage_parent=C.STAGE,sources=config['sources'],inputs=config['inputs'])
        self.result_raw=self.parent.canonical(result);self.write(C.OUTPUT+'/result.json',self.result_raw)
        self.transport_sha=C.sha(b'synthetic preparation03 transport\n')
        audit=json.loads(C.read(PREP01_AUDIT))
        audit.update(kind='puck-cpu-held-runtime-independent-audit-v13',version=13,allocation_id=13,
            auditor_source_sha256=C.sha(C.read(REAL_AUDITOR)),configuration_sha256=C.sha(self.config_raw),
            result_sha256=C.sha(self.result_raw),transport_sha256=self.transport_sha)
        self.audit=audit;self.audit_raw=self.auditor.canonical(audit)
        self.tmp=self.base/'tmp';self.tmp.mkdir()
        self.published=self.tmp/'audit.json';self.stdout=self.tmp/'audit.stdout';self.stderr=self.tmp/'audit.stderr'
        for path,raw in ((self.published,self.audit_raw),(self.stdout,self.audit_raw),(self.stderr,b'')):path.write_bytes(raw)
        self.command=C.audit_command(self.root,C.sha(self.config_raw),self.transport_sha,self.published)
        self.candidate=json.loads(C.read(ROOT/C.CANDIDATE_D_SOURCE))['inputs']['candidate']
        self.paths=dict(configuration=C.CONFIG,result=C.OUTPUT+'/result.json',independent_audit=C.ARCHIVED_AUDIT,externally_observed_auditor_cli=C.ARCHIVED_RECORD)
    def write(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return path
    def accept(self,record_raw,audit_raw=None):
        audit_raw=self.audit_raw if audit_raw is None else audit_raw
        for name,raw in ((C.ARCHIVED_AUDIT,audit_raw),(C.ARCHIVED_RECORD,record_raw)):
            path=self.root/name
            if path.exists():path.unlink()
            self.write(name,raw)
        config14,proof=C.prove_parent(self.parent,self.auditor,self.config_raw,self.result_raw,audit_raw,record_raw,self.paths,self.candidate)
        proof.update(C.prove_auditor_files(self.auditor,config14));return proof


class Proofs(unittest.TestCase):
    def setUp(self):
        base=tempfile.mkdtemp(prefix='palimpsest-prep03-proof-',dir='/tmp');self.addCleanup(shutil.rmtree,base)
        self.f=Fixture(base)

    def record(self,**changes):
        value,raw=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        value.update(changes);return value,C.pretty(value)

    def test_configuration_and_freeze_are_the_frozen_bytes(self):
        parent=C.load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','proof_real_parent');auditor=self.f.auditor
        raw=C.read(ROOT/C.CONFIG);config=parent.decode(raw);prep01=parent.decode(C.read(ROOT/'docs/plans/puck-cpu-held-preparation-01.json'))
        self.assertEqual(parent.canonical(config),raw)
        parent.validate_configuration(config);auditor.configuration(config,False)
        self.assertEqual({k for k in prep01 if prep01[k]!=config[k]},{'kind','version','allocation_id','stage_parent','sources'})
        for row in config['sources']:self.assertEqual((ROOT/row['path']).read_bytes(),C.git('show','HEAD:'+row['path']))
        freeze=json.loads(C.read(ROOT/C.FREEZE))
        self.assertEqual(freeze['pins']['configuration'],dict(path=C.CONFIG,size_bytes=len(raw),sha256=C.sha(raw)))
        self.assertEqual(freeze['pins']['auditor']['sha256'],'6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd')
        self.assertEqual(freeze['command'][4:],[str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(ROOT/C.CONFIG),'--sha256',C.sha(raw)])

    def test_record_builder_reproduces_preparation01_shape_and_bytes(self):
        old_raw=PREP01_RECORD.read_bytes();old=json.loads(old_raw)
        self.assertEqual(C.pretty(old),old_raw)
        audit=PREP01_AUDIT.read_bytes()
        for path,raw in ((self.f.published,audit),(self.f.stdout,audit)):path.unlink();path.write_bytes(raw)
        command=old['command'][:-1]+[str(self.f.published)]
        value,raw=C.build_record(command,0,old['elapsed_seconds'],self.f.published,self.f.stdout,self.f.stderr)
        expected=copy.deepcopy(old);expected['command']=command
        for name,path in (('published',self.f.published),('stdout',self.f.stdout),('stderr',self.f.stderr)):expected[name]['path']=str(path)
        self.assertEqual(raw,C.pretty(expected));self.assertEqual(set(value),set(old))
        for name in ('published','stdout','stderr'):self.assertEqual({k:value[name][k] for k in ('size_bytes','sha256')},{k:old[name][k] for k in ('size_bytes','sha256')})

    def test_record_is_accepted_by_parent_and_auditor_for_epoch14(self):
        value,raw=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        C.check_audit(self.f.audit,config_sha=C.sha(self.f.config_raw),transport_sha=self.f.transport_sha,
            result_sha=C.sha(self.f.result_raw),auditor_sha='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd')
        self.assertEqual(self.f.accept(raw),dict(parent_validate_preparation_acceptance='PASS',auditor_configuration='PASS',
            auditor_preparation_epoch='PASS',auditor_historical_acceptance='PASS',epoch=14,normal_seconds=360,negative_imports=32,
            hidden_imports=['networkx','pandas','sklearn','torch.utils._cxx_pytree']))
        self.assertEqual(len(value['command']),15)

    def test_compact_record_bytes_are_also_accepted(self):
        value,_=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        self.f.accept(self.f.parent.canonical(value))

    def test_builder_refuses_bad_terminals(self):
        wrapped=['/usr/bin/timeout','--signal=TERM','--kill-after=5s','155s']+self.f.command
        with self.assertRaises(RuntimeError):C.build_record(wrapped,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        with self.assertRaises(RuntimeError):C.build_record(self.f.command,1,11.5,self.f.published,self.f.stdout,self.f.stderr)
        with self.assertRaises(RuntimeError):C.build_record(self.f.command,0,130.0,self.f.published,self.f.stdout,self.f.stderr)
        self.f.stderr.write_bytes(b'warning\n')
        with self.assertRaises(RuntimeError):C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        self.f.stderr.write_bytes(b'');self.f.stdout.write_bytes(self.f.audit_raw+b' ')
        with self.assertRaises(RuntimeError):C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)

    def test_validators_refuse_malformed_records(self):
        cases=[dict(at='2026-10-17T00:00:00+00:00'),dict(elapsed_seconds=130.0),dict(observed_returncode=1),
            dict(command=['/usr/bin/timeout','155s']+self.f.command),
            dict(command=self.f.command[:10]+[str(self.f.root/'runs/puck-cpu-held-preparation-01-external-cli-transport.json')]+self.f.command[11:])]
        for change in cases:
            with self.subTest(change=sorted(change)):
                _,raw=self.record(**change)
                with self.assertRaises(ValueError):self.f.accept(raw)

    def test_validators_refuse_legacy_auditor_or_preparation01_audit(self):
        for change in (dict(auditor_source_sha256='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'),
                dict(kind='puck-cpu-held-runtime-independent-audit-v1',version=1),dict(allocation_id=1),
                dict(auditor_source_sha256='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'),dict(kind='puck-cpu-held-runtime-independent-audit-v12',version=12,allocation_id=12)):
            with self.subTest(change=sorted(change)):
                audit=dict(self.f.audit,**change);raw=self.f.auditor.canonical(audit)
                for path in (self.f.published,self.f.stdout):path.write_bytes(raw)
                _,record=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
                with self.assertRaises(ValueError):self.f.accept(record,raw)

    def test_stat_roots_and_run_once_and_archive_copy_on_fixture(self):
        stage=self.f.base/'stage';rows=[]
        for i in range(4):
            path=stage/'inputs'/('root-'+str(i).zfill(4));path.mkdir(parents=True);state=path.stat()
            rows.append(dict(root_index=i,device=state.st_dev,inode=state.st_ino))
        self.assertTrue(all(r['matches'] for r in C.stat_roots(stage,rows)['roots']))
        with self.assertRaises(RuntimeError):C.stat_roots(stage,[dict(rows[0],inode=rows[0]['inode']+1)]+rows[1:])
        with self.assertRaises(FileNotFoundError):C.stat_roots(self.f.base/'lost-on-reboot',rows)
        out,err=self.f.tmp/'run.stdout',self.f.tmp/'run.stderr'
        terminal=C.run_once([C.PYTHON,'-I','-S','-B','-c','print(12)'],out,err,timeout=30,cwd=self.f.base)
        self.assertEqual((terminal['returncode'],terminal['outer_timeout'],terminal['stdout']['sha256']),(0,False,C.sha(b'12\n')))
        with self.assertRaises(FileExistsError):C.run_once([C.PYTHON,'-c','pass'],out,err,timeout=30,cwd=self.f.base)
        target=self.f.base/'archive/audit/copy.json'
        rows=ARCHIVE.copy([(self.f.published,target)])
        self.assertEqual(target.read_bytes(),self.f.audit_raw);self.assertEqual(rows[0]['sha256'],C.sha(self.f.audit_raw))
        with self.assertRaises(FileExistsError):ARCHIVE.copy([(self.f.published,target)])

    def test_one_shot_tools_preflight_before_their_single_invocation(self):
        for name,phase,runs in (('run-observer-once.py','observer',1),('run-audit-once.py','audit',1),('archive.py','archive',0)):
            tree=ast.parse((TOOLS/name).read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
            checks=[n for n in calls if ast.unparse(n.func)=='P.check']
            runs_=[n for n in calls if ast.unparse(n.func)=='C.run_once']
            self.assertEqual([ast.literal_eval(n.args[0]) for n in checks],[phase],name)
            self.assertEqual(len(runs_),runs,name)
            if runs:self.assertLess(checks[0].lineno,runs_[0].lineno,name)
            self.assertNotIn('/usr/bin/timeout',(TOOLS/name).read_text())

    def test_qualification11_cannot_consume_preparation03(self):
        value,raw=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        blobs=dict(configuration=self.f.config_raw,result=self.f.result_raw,independent_audit=self.f.audit_raw,externally_observed_auditor_cli=raw)
        acceptance={role:dict(path=self.f.paths[role],size_bytes=len(b),sha256=C.sha(b)) for role,b in blobs.items()}
        config=C.epoch14(self.f.parent.decode(self.f.config_raw),acceptance,self.f.candidate,self.f.parent)
        config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,limits=dict(self.f.parent.LIMITS['qualify']))
        for stage,output,message in (('/tmp/palimpsest-puck-cpu-held-03','runs/puck-cpu-held-preparation-03','preparation02 tmpfs allocation path'),
                ('/tmp/palimpsest-puck-cpu-held-02','runs/puck-cpu-held-preparation-02','Accepted CPU preparation02 required')):
            config['stage_parent']=stage;config['preparation_acceptance']['result']['path']=output+'/result.json'
            with self.assertRaisesRegex(ValueError,message):self.f.parent.validate_preparation_acceptance(config,blobs)

    def test_epoch14_worker_registration_uses_the_360s_clock(self):
        parent=C.load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','proof_worker_parent')
        config=json.loads(C.read(ROOT/C.CONFIG));config['negative_imports']=list(parent.QUALIFY11_NEGATIVE_IMPORTS)
        depraw=C.read(ROOT/'docs/reports/puck-cpu-held-preparation-01/raw/payload/dependencies.json')
        self.assertEqual(C.prove_worker(parent,config,depraw),dict(worker_registration='PASS',worker_deadline_seconds=360))
        files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
        for seconds in (180,361):
            with self.assertRaises(ValueError):
                parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=5,
                    hidden_imports=parent.QUALIFY11_HIDDEN_IMPORTS,deadline_seconds=seconds)

    def test_preflight_requires_the_preparation_boot(self):
        text=(TOOLS/'preflight.py').read_text()
        self.assertIn("require(C.boot_id()==C.BOOT,",text)
        self.assertEqual(C.BOOT,'7f875223-b4cf-421e-b04d-81e3c1f19460')
        self.assertEqual((C.STAGE,C.OUTPUT),('/tmp/palimpsest-puck-cpu-held-03','runs/puck-cpu-held-preparation-03'))


def dry_run_preflight():
    return P.check('observer',dry_run=True)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--preflight-dry-run']:
        print(C.pretty(dry_run_preflight()).decode(),end='')
    else:unittest.main(verbosity=2)
