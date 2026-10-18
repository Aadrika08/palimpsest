"""Offline proofs for the characterization-04 controls; never runs the real observer, parent, auditor, archive or derivation.

The chain runs the controls' own helpers (observer/audit/archive argv, observed, build_record,
check_audit, check_archive, binding) over the AUTHORED characterization-04 project from
tests/puck_episode_authored.py. The real
worktree is read, never written; preparation02/03 stages are lstat-compared only.
The fixture lives under /home/utkarsh/.cache/palimpsest-char04-proof-* (bwrap refuses a /tmp capsule) and is removed.
Usage: python3.11 -I -S -B offline-proof.py [--preflight-dry-run]
"""
from pathlib import Path
import ast,importlib.util,json,os,shutil,sys,tempfile,unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
TOOLS=ROOT/'docs/plans/puck-cpu-runtime-characterization-04-tools'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
P=module('proof_preflight',TOOLS/'preflight.py');C=P.C
A=module('proof_authored',ROOT/'tests/puck_episode_authored.py')
CHAIN={}
BASE='/home/utkarsh/.cache'


def setUpModule():
    """One authored chain: freeze, observe, audit, record, archive, bind, derive, bind again."""
    CHAIN['untouched_before']=C.untouched()
    # bwrap cannot bind a capsule below /tmp (its sandbox owns /tmp) and runs/ is read-only for these proofs,
    # so the authored project lives on the project disk outside the repository, under a palimpsest-* name.
    base=Path(tempfile.mkdtemp(prefix='palimpsest-char04-proof-',dir=BASE));CHAIN['base']=base
    try:chain(base)
    except BaseException:shutil.rmtree(base);raise


def chain(base):
    project=A.episode_project(base);root=project['root'];CHAIN.update(project=project,root=root)
    parent=C.load(root/C.PARENT,'proof_authored_parent');auditor=C.load(root/C.AUDITOR,'proof_authored_auditor')
    config=parent.configuration(parent.source_rows());raw=C.pretty(config)
    parent.validate_configuration(json.loads(raw));auditor.validate_configuration(json.loads(raw))
    (root/C.CONFIG).parent.mkdir(parents=True,exist_ok=True);(root/C.CONFIG).write_bytes(raw)
    CHAIN.update(parent=parent,raw=raw,sha=C.sha(raw));tmp=base/'records';tmp.mkdir()
    CHAIN['observer']=C.run_once(C.observer_command(root,C.sha(raw)),tmp/'observer.stdout',tmp/'observer.stderr',timeout=C.OBSERVER_BOUND,cwd=root)
    CHAIN['observation']=C.observed(root,raw)
    published=tmp/'audit.json';command=C.audit_command(root,C.sha(raw),CHAIN['observation']['transport_sha256'],published)
    CHAIN['audit_terminal']=C.run_once(command,tmp/'audit.stdout',tmp/'audit.stderr',timeout=C.AUDIT_BOUND,cwd=root)
    CHAIN.update(audit_command=command,published=published,audit_stdout=tmp/'audit.stdout',audit_stderr=tmp/'audit.stderr')
    CHAIN['record']=C.build_record(command,CHAIN['audit_terminal']['returncode'],CHAIN['audit_terminal']['elapsed_seconds'],
        published,tmp/'audit.stdout',tmp/'audit.stderr')
    CHAIN['audit_raw']=published.read_bytes();CHAIN['authored_auditor_sha']=C.sha((root/C.AUDITOR).read_bytes())
    CHAIN['archive_terminal']=C.run_once(C.archive_command(root,published),tmp/'archive.stdout',tmp/'archive.stderr',timeout=C.ARCHIVE_BOUND,cwd=root)
    CHAIN['index']=C.check_archive(root,raw,CHAIN['audit_raw'],(tmp/'archive.stdout').read_bytes())
    # The authored auditor clone is patched, so preparation04's clones are re-pinned to it exactly as the chain tests do.
    A.authored_scale(project);CHAIN['qualifier']=C.load(root/C.QUALIFIER,'proof_authored_qualifier')
    CHAIN['binding_synthetic']=C.binding(root,CHAIN['qualifier'],parent,raw)
    CHAIN['candidate']=derive(root,project)
    CHAIN['binding_derived']=C.binding(root,CHAIN['qualifier'],parent,raw,json.loads(CHAIN['candidate']))
    CHAIN['untouched_after']=C.untouched()


def tearDownModule():
    summary=dict(observer={k:CHAIN['observer'][k] for k in ('returncode','outer_timeout','elapsed_seconds')},
        observation={k:v for k,v in CHAIN['observation'].items() if k!='import_misses'},
        audit={k:CHAIN['audit_terminal'][k] for k in ('returncode','outer_timeout','elapsed_seconds')},
        archive={k:CHAIN['archive_terminal'][k] for k in ('returncode','outer_timeout','elapsed_seconds')},index=CHAIN['index'],
        binding_synthetic=CHAIN['binding_synthetic'],binding_derived=CHAIN['binding_derived'],
        candidate_sha256=C.sha(CHAIN['candidate']),untouched_unchanged=CHAIN['untouched_before']==CHAIN['untouched_after'])
    print(json.dumps(summary,indent=2,sort_keys=True))
    shutil.rmtree(CHAIN['base'])


def derive(root,project):
    """Candidate 02 through the real derivation CLI on the archived authored bytes (authored template)."""
    helper=b'AUTHORED_PROSPECTIVE_HELPER = True\n';generated=A.write(root,'docs/authored/generated/_authored_cpu_generated.py',helper)
    template=A.write(root,'docs/authored/template-candidate.json',dict(kind='puck-cpu-observed-import-profile-candidate-v1',version=1,
        import_profile=dict(kind='puck-producer-import-profile-v2',version=2,exports=[],module_changes=[],native_origins=[],
            native_cache=[dict(name='_cython_authored',producer='authoredcy._creator',phase='module_exec',
                               delegate_attributes=['cython_function_or_method','generator'])]),
        additional_package_inputs=[dict(root='docs/authored/generated',files=[dict(generated,path='_authored_cpu_generated.py')])],
        authored_scope=A.AUTHORED))
    archive=root/C.ARCHIVE;output=root/'docs/authored/candidate-02.json'
    code,stdout,stderr=A.run([C.PYTHON,'-I','-B',str(root/'scripts/derive_puck_episode_profile.py'),
        '--configuration',str(archive/'frozen-configuration.json'),'--result',str(archive/'raw/result.json'),
        '--source',str(archive/'raw/payload/source/characterization.json'),'--replay',str(archive/'raw/payload/replay/characterization.json'),
        '--audit',str(archive/'outcome-audit-04.json'),'--template',str(root/template['path']),
        '--inventory',str(root/project['inputs']['inventory']['path']),'--native',str(root/project['inputs']['native']['path']),
        '--site-root',str(project['site']),'--output',str(output)],root)
    assert code==0,(stdout,stderr)
    return output.read_bytes()


class Proofs(unittest.TestCase):
    def test_configuration_and_freeze_are_the_frozen_bytes(self):
        parent=C.load(ROOT/C.PARENT,'proof_real_parent');auditor=C.load(ROOT/C.AUDITOR,'proof_real_auditor')
        qualifier=C.load(ROOT/C.QUALIFIER,'proof_real_qualifier')
        raw=C.read(ROOT/C.CONFIG);config=json.loads(raw)
        self.assertEqual(C.pretty(parent.configuration(parent.source_rows())),raw)
        parent.validate_configuration(config);auditor.validate_configuration(config)
        self.assertEqual((config['kind'],config['version'],config['output']),('puck-cpu-runtime-characterization-v3',3,C.OUTPUT))
        self.assertEqual([r['path'] for r in config['sources']],list(qualifier.PREPARATION04_SOURCES))
        self.assertEqual(config['episode']['run_ids'],dict(source='a6effc7912fec337875d13ae69445e43',replay='6c04b9ed22c383fda860fa3b4f8bab13'))
        self.assertIn(parent.NATIVE_METADATA_PIN,config['inputs']);self.assertIn(parent.OBSERVATION02_PIN,config['inputs'])
        freeze=json.loads(C.read(ROOT/C.FREEZE))
        self.assertEqual(freeze['pins']['configuration'],dict(path=C.CONFIG,size_bytes=len(raw),sha256=C.sha(raw)))
        self.assertEqual(freeze['pins']['auditor']['sha256'],C.AUDITOR_SHA);self.assertEqual(qualifier.CHARACTERIZATION04_AUDITOR_SHA256,C.AUDITOR_SHA)
        self.assertEqual(freeze['command'],C.observer_command(ROOT,C.sha(raw)))
        self.assertEqual(freeze['archive']['command'],C.archive_command(ROOT,C.AUDIT_OUTPUT))

    def test_outer_bounds_exceed_the_source_clocks(self):
        observer=C.load(ROOT/C.OBSERVER,'proof_real_observer');parent=C.load(ROOT/C.PARENT,'proof_bound_parent')
        self.assertEqual((observer.NORMAL_SECONDS,observer.HARD_SECONDS,observer.CLEANUP_SECONDS),(420,435,5))
        self.assertGreater(C.OBSERVER_BOUND,observer.HARD_SECONDS+observer.CLEANUP_SECONDS)
        self.assertLess(parent.LIMITS['hard_seconds'],observer.NORMAL_SECONDS)
        text=(ROOT/C.AUDITOR).read_text();self.assertIn('signal.setitimer(signal.ITIMER_REAL,310)',text);self.assertIn('started+300',text)
        self.assertGreater(C.AUDIT_BOUND,310)

    def test_authored_observer_transport_is_observed(self):
        t=CHAIN['observer'];o=CHAIN['observation']
        self.assertEqual((t['returncode'],t['outer_timeout']),(0,False))
        self.assertEqual(json.loads((CHAIN['root']/C.TRANSPORT).read_bytes()),json.loads(Path(t['stdout']['path']).read_bytes()))
        self.assertEqual((o['ticks_completed'],o['replay']['status']),(48,'passed'))

    def test_authored_audit_passes_and_record_is_preparation01_shaped(self):
        t=CHAIN['audit_terminal'];value,raw=CHAIN['record'];audit=json.loads(CHAIN['audit_raw'])
        self.assertEqual((t['returncode'],t['outer_timeout']),(0,False));self.assertEqual(len(CHAIN['audit_command']),15)
        C.check_audit(audit,observation=CHAIN['observation'],config_sha=CHAIN['sha'],auditor_sha=CHAIN['authored_auditor_sha'])
        self.assertEqual(set(value),C.RECORD_KEYS);self.assertEqual(raw,C.pretty(value))
        old=json.loads((ROOT/'docs/reports/puck-cpu-held-preparation-01/audit/palimpsest-puck-cpu-held-preparation-01-audit-01.external-cli.json').read_bytes())
        self.assertEqual(set(old),set(value))

    def test_check_audit_refuses_other_auditors_and_failures(self):
        audit=json.loads(CHAIN['audit_raw']);kw=dict(observation=CHAIN['observation'],config_sha=CHAIN['sha'])
        with self.assertRaises(RuntimeError):C.check_audit(audit,**kw)  # authored clone bytes are not the pinned 1608a3d7 auditor
        for change in (dict(status='FAIL'),dict(kind='cpu-characterization-outcome-audit-v2'),dict(transport_sha256='0'*64),
                       dict(verified=dict(audit['verified'],result_sha256='0'*64)),dict(executable=True)):
            with self.subTest(change=sorted(change)),self.assertRaises(RuntimeError):
                C.check_audit(dict(audit,**change),auditor_sha=CHAIN['authored_auditor_sha'],**kw)

    def test_builder_refuses_bad_terminals(self):
        command,published,out,err=CHAIN['audit_command'],CHAIN['published'],CHAIN['audit_stdout'],CHAIN['audit_stderr']
        with self.assertRaises(RuntimeError):C.build_record(['/usr/bin/timeout','330s']+command,0,10.5,published,out,err)
        with self.assertRaises(RuntimeError):C.build_record(command,1,10.5,published,out,err)
        with self.assertRaises(RuntimeError):C.build_record(command,0,float(C.AUDIT_BOUND),published,out,err)
        scratch=CHAIN['base']/'bad.stderr';scratch.write_bytes(b'warning\n')
        with self.assertRaises(RuntimeError):C.build_record(command,0,10.5,published,out,scratch)

    def test_archive_index_binds_every_preparation04_path(self):
        index=CHAIN['index'];q=CHAIN['qualifier']
        rows={r['path'] for r in json.loads((CHAIN['root']/C.ARCHIVE/'evidence-index.json').read_bytes())['entries']}
        self.assertLessEqual(set(q.EPISODE_OBSERVATION_PATHS.values()),rows);self.assertEqual(index['file_count'],len(rows))
        self.assertEqual((CHAIN['root']/C.ARCHIVE/'frozen-configuration.json').read_bytes(),CHAIN['raw'])
        self.assertEqual((CHAIN['root']/C.ARCHIVE/'outcome-audit-04.json').read_bytes(),CHAIN['audit_raw'])

    def test_preparation04_binds_the_archive_with_synthetic_and_derived_candidates(self):
        for key,kind in (('binding_synthetic','synthetic'),('binding_derived','derived')):
            self.assertEqual({k:CHAIN[key][k] for k in ('validate_observation_links','validate_episode_observation','candidate','undeclared_import_misses')},
                dict(validate_observation_links='PASS',validate_episode_observation='PASS',candidate=kind,undeclared_import_misses=0))
        candidate=json.loads(CHAIN['candidate'])
        self.assertEqual(candidate['kind'],'puck-cpu-episode-import-profile-candidate-v2')
        self.assertEqual(candidate['outcome_audit_sha256'],C.sha(CHAIN['audit_raw']))
        self.assertEqual(candidate['characterization_configuration_sha256'],CHAIN['sha'])

    def test_real_preparation04_refuses_an_unpinned_auditor(self):
        real=C.load(ROOT/C.QUALIFIER,'proof_unpinned_qualifier')
        with self.assertRaisesRegex(ValueError,'pinned auditor bytes'):C.binding(CHAIN['root'],real,CHAIN['parent'],CHAIN['raw'])

    def test_tampered_archive_or_candidate_is_refused(self):
        root=CHAIN['root'];target=root/C.ARCHIVE/'raw/payload/replay/characterization.json';original=target.read_bytes()
        try:
            target.write_bytes(original[:-2]+b' \n')
            with self.assertRaises(RuntimeError):C.check_archive(root,CHAIN['raw'],CHAIN['audit_raw'],(CHAIN['base']/'records/archive.stdout').read_bytes())
            with self.assertRaises(ValueError):C.binding(root,CHAIN['qualifier'],CHAIN['parent'],CHAIN['raw'])
        finally:target.write_bytes(original)
        candidate=json.loads(CHAIN['candidate'])
        for change in (dict(import_misses=candidate['import_misses']+['zz_unobserved']),dict(outcome_audit_sha256='0'*64)):
            with self.subTest(change=sorted(change)),self.assertRaises(ValueError):
                C.binding(root,CHAIN['qualifier'],CHAIN['parent'],CHAIN['raw'],dict(candidate,**change))

    def test_one_shot_tools_preflight_before_their_single_invocation(self):
        for name,phase in (('run-observer-once.py','observer'),('run-audit-once.py','audit'),('archive.py','archive')):
            text=(TOOLS/name).read_text();calls=[n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Call)]
            checks=[n for n in calls if ast.unparse(n.func)=='P.check'];runs=[n for n in calls if ast.unparse(n.func)=='C.run_once']
            self.assertEqual([ast.literal_eval(n.args[0]) for n in checks],[phase],name);self.assertEqual(len(runs),1,name)
            self.assertLess(checks[0].lineno,runs[0].lineno,name);self.assertNotIn('/usr/bin/timeout',text)

    def test_preflight_requires_the_boot_absences_and_untouched_stages(self):
        text=(TOOLS/'preflight.py').read_text()
        self.assertIn("require(C.boot_id()==C.BOOT,",text);self.assertEqual(C.BOOT,'7f875223-b4cf-421e-b04d-81e3c1f19460')
        for name in ('C.OUTPUT','C.TRANSPORT','C.PARENT_STREAMS','C.ARCHIVE','C.RECORDS_ARCHIVE','C.CANDIDATE','C.AUDIT_OUTPUT'):self.assertIn(name,text)
        self.assertEqual(C.UNTOUCHED[:2],('/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03'))
        self.assertEqual(CHAIN['untouched_before'],CHAIN['untouched_after'])

    def test_run_once_is_exclusive(self):
        out,err=CHAIN['base']/'run.stdout',CHAIN['base']/'run.stderr'
        terminal=C.run_once([C.PYTHON,'-I','-S','-B','-c','print(12)'],out,err,timeout=30,cwd=CHAIN['base'])
        self.assertEqual((terminal['returncode'],terminal['outer_timeout'],terminal['stdout']['sha256']),(0,False,C.sha(b'12\n')))
        with self.assertRaises(FileExistsError):C.run_once([C.PYTHON,'-c','pass'],out,err,timeout=30,cwd=CHAIN['base'])


def dry_run_preflight():
    return P.check('observer',dry_run=True)


if __name__=='__main__':
    if sys.argv[1:]==['--preflight-dry-run']:
        print(C.pretty(dry_run_preflight()).decode(),end='')
    else:unittest.main(verbosity=2)
