"""Closed04 capsules with authored historical failures, never installed vendors."""
import copy
from contextlib import contextmanager
import json

from test_puck_cpu_held_amendment import amendment_fixture
from test_puck_cpu_held_parent_integration import ROOT, digest, run_cli


BINDINGS='src/palimpsest/puck_dependency_bindings.py'


def source_pins(root,api):
    return [dict(path=p,size_bytes=(root/p).stat().st_size,sha256=digest((root/p).read_bytes())) for p in api.SOURCES]


@contextmanager
def amendment04_fixture(tmp_path,*,binding_failure=False):
    with amendment_fixture(tmp_path,rocm_probe=True,historical_bindings=True,binding_failure=binding_failure) as case:
        root,m,config=(case[k] for k in ('root','api','config'))
        bindings=root/BINDINGS;fresh=bindings.read_bytes()
        historical=(ROOT/'docs/reports/puck-cpu-held-preparation-01/raw/worker-source'/BINDINGS).read_bytes()
        bindings.write_bytes(historical)
        previous=copy.deepcopy(config);previous['sources']=source_pins(root,m)
        try:
            code,stdout,stderr=run_cli(root,m,'qualify02',previous)
            assert code==1,(code,stdout,stderr)
            output=root/'runs/puck-cpu-held-qualification-02'
            assert json.loads(stdout)['status']=='FAIL' and not (output/'baseline-after.json').exists()
            assert b'torch._rocm_init' in (output/'logs/stderr.log').read_bytes()
            if binding_failure:
                previous.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,
                                negative_imports=['org','torch._rocm_init'])
                code,stdout,stderr=run_cli(root,m,'qualify03',previous)
                assert code==1,(code,stdout,stderr)
                output=root/'runs/puck-cpu-held-qualification-03'
                assert json.loads(stdout)['status']=='FAIL' and not (output/'baseline-after.json').exists()
                trace=(output/'logs/stderr.log').read_bytes()
                assert b'Dependency producer attribute binding is missing' in trace
                assert b'export=' not in trace and b'component ' not in trace
            for epoch in ('02','03'):
                output=root/('runs/puck-cpu-held-qualification-'+epoch)
                for p in list(output.rglob('*'))+list(root.glob('authored-qualify'+epoch+'-*')):
                    if p.is_file():case['legacy_bytes'][str(p.relative_to(root))]=p.read_bytes()
        finally:bindings.write_bytes(fresh)
        updated=copy.deepcopy(config)
        updated.update(kind='puck-cpu-held-runtime-allocation-v4',version=4,allocation_id=4,
            negative_imports=['org','torch._rocm_init'],sources=source_pins(root,m))
        assert not (root/'runs/puck-cpu-held-qualification-04').exists()
        yield dict(case,config=updated)


def test_authored04_uses_exact_new_bindings_capsule_and_preserves_historical_bytes(tmp_path):
    with amendment04_fixture(tmp_path) as case:
        root,m,config,stage=(case[k] for k in ('root','api','config','stage'))
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        code,stdout,stderr=run_cli(root,m,'qualify04',config)
        output=root/'runs/puck-cpu-held-qualification-04'
        retained=(output/'result.json').read_bytes() if (output/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,retained)
        result=json.loads(retained)
        assert stdout==retained and result['status']=='imports_completed'
        assert (result['kind'],result['version'],result['allocation_id'])==('puck-cpu-held-runtime-outcome-v4',4,4)
        registration=json.loads((output/'control/worker-registration.json').read_bytes())
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in m.WORKER_SOURCES]
        for row in registration['source_files']:
            data=(output/'worker-source'/row['path']).read_bytes()
            assert len(data)==row['size_bytes'] and digest(data)==row['sha256']
        old=root/'runs/puck-cpu-held-preparation-01/worker-source'/BINDINGS
        assert old.read_bytes()!=(output/'worker-source'/BINDINGS).read_bytes()==(root/BINDINGS).read_bytes()
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        assert all(result[k]==v for k,v in m.CLAIMS.items())
        assert result['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5)
        for path,data in case['legacy_bytes'].items():assert (root/path).read_bytes()==data
        code,_,stderr=run_cli(root,m,'qualify04-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr and (output/'result.json').read_bytes()==retained
        for path,data in case['legacy_bytes'].items():assert (root/path).read_bytes()==data
    assert not stage.exists()


def test_authored04_preserves03_generic_failure_and_adds_exact_chained_context(tmp_path):
    with amendment04_fixture(tmp_path,binding_failure=True) as case:
        root,m,config=(case[k] for k in ('root','api','config'))
        code,stdout,stderr=run_cli(root,m,'qualify04',config)
        output=root/'runs/puck-cpu-held-qualification-04'
        assert code==1,(code,stdout,stderr)
        assert (output/'result.json').is_file(), 'Closed04 must retain a failed terminal outcome'
        result=json.loads((output/'result.json').read_bytes())
        assert json.loads(stdout)==result and result['status']=='FAIL'
        assert (result['kind'],result['version'],result['allocation_id'])==('puck-cpu-held-runtime-outcome-v4',4,4)
        assert result['held_four_imports_observed'] is False and not (output/'baseline-after.json').exists()
        assert (output/'logs/stdout.log').read_bytes()==b''
        trace=(output/'logs/stderr.log').read_text()
        for expected in ["component '_authored_missing' at index 0", "producer='torch'", "phase='module_exec'",
                         "export='torch._authored_missing'", "attributes=['_authored_missing']", 'The above exception was the direct cause']:
            assert expected in trace
        assert all(result[k]==v for k,v in m.CLAIMS.items())
        assert result['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5)
        for path,data in case['legacy_bytes'].items():assert (root/path).read_bytes()==data
