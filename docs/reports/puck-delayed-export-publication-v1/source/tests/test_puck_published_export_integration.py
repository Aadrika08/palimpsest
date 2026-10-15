"""One AUTHORED phase pair; no installed vendor or real allocation acceptance."""
import copy
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

import pytest

from test_puck_cpu_held_parent_integration import (
    AUTHORED, ROOT, canonical, digest, load, project, run_cli,
)


def test_authored_publication_survives_separate_parent_and_independent_audits(tmp_path):
    assert tmp_path.resolve().is_relative_to((ROOT / 'runs').resolve()), (
        'Use a persistent runs/ pytest basetemp, outside /tmp')
    auditor_path = ROOT / 'scripts/audit_puck_cpu_held_runtime.py'
    auditor = load(auditor_path, 'cpu_published_export_independent_auditor')
    root, api, inputs, sources = project(tmp_path, published_export=True)
    stage = Path('/tmp') / ('palimpsest-puck-cpu-held-authored-' + secrets.token_hex(12))
    assert not os.path.lexists(stage)
    fd_before = len(os.listdir('/proc/self/fd'))
    expected = [dict(name='torch.authored_publication', producer='torch',
                     phase='module_exec_publish', attributes=['authored_child'],
                     delegate_attributes=['answer'])]

    def audit_phase(phase):
        configuration = root / ('authored-' + phase + '-configuration.json')
        transport = root / ('authored-' + phase + '-transport.json')
        before = len(os.listdir('/proc/self/fd'))
        try:
            return auditor.audit(configuration, digest(configuration.read_bytes()),
                                 transport, digest(transport.read_bytes()),
                                 deadline=time.monotonic() + 30)
        finally:
            assert len(os.listdir('/proc/self/fd')) == before

    try:
        prepare = api.configuration_template(phase='prepare', root=str(root), stage_parent=str(stage),
                                             sources=sources, inputs=inputs, negative_imports=['org'])
        code, stdout, stderr = run_cli(root, api, 'prepare', prepare)
        preparation_path = root / api.OUTPUTS['prepare'] / 'result.json'
        preparation_raw = preparation_path.read_bytes() if preparation_path.exists() else b''
        assert code == 0, (code, stdout, stderr, preparation_raw)
        prepared = json.loads(preparation_raw)
        assert json.loads(stdout) == prepared and prepared['status'] == 'prepared'
        assert prepared['held_four_imports_observed'] is False
        identities = [(stage / 'inputs' / ('root-' + str(i).zfill(4))).stat() for i in range(4)]
        dependencies_raw = (root / api.OUTPUTS['prepare'] / 'payload/dependencies.json').read_bytes()
        dependencies = json.loads(dependencies_raw)
        assert [len(r['files']) for r in dependencies['roots']] == [9, 7, 1, 1]
        prepare_audit = audit_phase('prepare')
        assert prepare_audit['status'] == 'PASS'
        (root / 'authored-published-prepare-independent-audit.json').write_bytes(canonical(prepare_audit))

        preparation = dict(path=str(preparation_path.relative_to(root)),
                           size_bytes=len(preparation_raw), sha256=digest(preparation_raw))
        qualify = api.configuration_template(phase='qualify', root=str(root), stage_parent=str(stage),
                                             sources=sources, inputs=inputs, negative_imports=['org'],
                                             preparation=preparation)
        code, stdout, stderr = run_cli(root, api, 'qualify', qualify)
        base = root / api.OUTPUTS['qualify']
        result_path = base / 'result.json'
        result_raw = result_path.read_bytes() if result_path.exists() else b''
        assert code == 0, (code, stdout, stderr, result_raw)
        outcome = json.loads(result_raw)
        assert json.loads(stdout) == outcome and outcome['status'] == 'imports_completed'
        assert outcome['held_four_imports_observed'] is True
        worker_path = base / 'logs/stdout.log'
        worker = json.loads(worker_path.read_bytes())
        assert [(r['name'], r['version']) for r in worker['entry_result']['imports']] == list(api.VERSIONS.items())
        assert worker['dependencies']['published_export_modules'] == expected
        assert dict((r['name'], r['path']) for r in worker['dependencies']['loaded_modules'])[
            '_authored_cpu_generated'] == '_authored_cpu_generated.py'
        registration_raw = (base / 'control/worker-registration.json').read_bytes()
        registration = json.loads(registration_raw)
        assert registration['source_root'] == registration['cwd'] == '/puck/source'
        assert registration['source_files'] == [r for r in sources if r['path'] in api.WORKER_SOURCES]
        for pin in registration['source_files']:
            capsule = root / api.OUTPUTS['prepare'] / 'worker-source' / pin['path']
            raw = capsule.read_bytes()
            assert len(raw) == pin['size_bytes'] and digest(raw) == pin['sha256']
        api.validate_worker_result(worker, registration_sha256=digest(registration_raw),
                                   dependency_sha256=digest(dependencies_raw),
                                   dependencies=dependencies, negative_imports=['org'])
        auditor.binding_receipt(worker['dependencies'], dependencies)
        qualify_audit = audit_phase('qualify')
        assert qualify_audit['status'] == 'PASS'
        (root / 'authored-published-qualify-independent-audit.json').write_bytes(canonical(qualify_audit))

        configuration = root / 'authored-qualify-configuration.json'
        transport_path = root / 'authored-qualify-transport.json'
        published = root / 'authored-published-qualify-audit-cli.json'
        command = [api.PYTHON, '-I', '-S', '-B', str(auditor_path),
                   '--configuration', str(configuration), '--sha256', digest(configuration.read_bytes()),
                   '--transport', str(transport_path), '--transport-sha256', digest(transport_path.read_bytes()),
                   '--output', str(published)]
        started = time.monotonic()
        process = subprocess.run(command, cwd=root, capture_output=True, timeout=30,
                                 env=dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8',
                                          PYTHONDONTWRITEBYTECODE='1'))
        channels = {}
        for name, payload in (('stdout', process.stdout), ('stderr', process.stderr)):
            leaf = 'authored-published-qualify-audit-cli.' + name
            (root / leaf).write_bytes(payload)
            channels[name] = dict(path=leaf, size_bytes=len(payload), sha256=digest(payload))
        (root / 'authored-published-qualify-audit-cli-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1', authored_scope=AUTHORED,
            command=command, observed_returncode=process.returncode,
            elapsed_seconds=time.monotonic() - started, **channels)))
        assert process.returncode == 0, (process.returncode, process.stdout, process.stderr)
        assert process.stdout == published.read_bytes()
        cli_audit = json.loads(process.stdout)
        assert cli_audit['status'] == 'PASS'
        assert cli_audit['auditor_source_sha256'] == digest(auditor_path.read_bytes())

        changed = copy.deepcopy(worker)
        changed['dependencies']['published_export_modules'][0]['attributes'] = ['unrelated_child']
        with pytest.raises(ValueError):
            api.validate_worker_result(changed, registration_sha256=digest(registration_raw),
                                       dependency_sha256=digest(dependencies_raw),
                                       dependencies=dependencies, negative_imports=['org'])
        with pytest.raises(ValueError):
            auditor.binding_receipt(changed['dependencies'], dependencies)

        # Rebind every enclosing digest so the full audit must reject the proof's
        # semantics, rather than a stale stream/result/transport hash.
        stdout_path = root / 'authored-qualify-cli.stdout'
        originals = {p: p.read_bytes() for p in (worker_path, result_path, stdout_path, transport_path)}
        try:
            worker_raw = canonical(changed)
            worker_path.write_bytes(worker_raw)
            changed_result = json.loads(result_raw)
            changed_result['worker_stdout_sha256'] = digest(worker_raw)
            changed_result_raw = canonical(changed_result)
            result_path.write_bytes(changed_result_raw)
            stdout_path.write_bytes(changed_result_raw)
            changed_transport = json.loads(originals[transport_path])
            changed_transport['stdout'].update(size_bytes=len(changed_result_raw), sha256=digest(changed_result_raw))
            transport_path.write_bytes(canonical(changed_transport))
            with pytest.raises(ValueError, match='(?i)publish'):
                audit_phase('qualify')
        finally:
            for path, raw in originals.items():
                path.write_bytes(raw)

        for report in (prepared, outcome, prepare_audit, qualify_audit, cli_audit):
            assert all(report[k] is False for k in api.CLAIMS if k != 'qualification_claims')
            assert report['qualification_claims'] == []
            assert report['closure']['active_children'] == report['closure']['active_non_main_threads'] == []
            assert report['closure']['fd_count_before'] == report['closure']['fd_count_after']
        for i, before in enumerate(identities):
            after = (stage / 'inputs' / ('root-' + str(i).zfill(4))).stat()
            assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        code, _, stderr = run_cli(root, api, 'qualify-rerun', qualify)
        assert code != 0 and b'CPU allocation already reserved' in stderr
        assert preparation_path.read_bytes() == preparation_raw
        assert all(path.read_bytes() == raw for path, raw in originals.items())
        (root / 'authored-publication-test-observations.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED, published_export_modules=expected,
            prepare_audit='PASS', qualify_audit='PASS', auditor_cli_returncode=process.returncode,
            rebound_publication_proof_rejected=True, consumed_output_reentry_refused=True,
            actual_vendor_imports=False)))
    finally:
        if os.path.lexists(stage):
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
        (root / 'authored-published-stage-cleanup.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED, owned_stage=str(stage), absent=not os.path.lexists(stage))))
        assert not os.path.lexists(stage)
        assert len(os.listdir('/proc/self/fd')) == fd_before
