"""One fixed pre04 pin/preservation/resource snapshot; never launches an allocation."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat

ROOT = Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONFIG_SHA = '6fa33667eb5c4d5ebe94f13a8e485be8ef3b2929f29c30ad1ee479baccfe47b8'
FREEZE_SHA = 'a34d83b15c41d8833daa9e28b63b406dd094472b41943d910326d663d4fc64e7'

def checked(path, pin):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1
        assert before.st_size == pin['size_bytes'] <= 64 * 1024**2
        digest = hashlib.sha256()
        chunks = []
        while chunk := os.read(fd, 256 * 1024):
            digest.update(chunk)
            chunks.append(chunk)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        assert stamp(before) == stamp(os.fstat(fd)) == stamp(os.stat(path, follow_symlinks=False))
        data = b''.join(chunks)
        assert len(data) == pin['size_bytes'] and digest.hexdigest() == pin['sha256'], str(path)
        return data
    finally:
        os.close(fd)

config_raw = checked(ROOT / 'docs/plans/puck-cpu-held-qualification-04.json', dict(size_bytes=8835, sha256=CONFIG_SHA))
freeze_raw = checked(ROOT / 'docs/plans/puck-cpu-held-qualification-04-freeze.json', dict(size_bytes=7599, sha256=FREEZE_SHA))
config, freeze = json.loads(config_raw), json.loads(freeze_raw)
assert config['kind'] == 'puck-cpu-held-runtime-allocation-v4'
assert config['phase'] == 'qualify' and config['version'] == config['allocation_id'] == 4
assert config['root'] == str(ROOT) and config['limits'] == freeze['limits']
assert freeze['review']['status'] == 'GO for one actual04 after fresh admission'
assert freeze['review']['material_findings'] == []
assert freeze['review']['reviewed_configuration_sha256'] == CONFIG_SHA
current = config['sources'] + list(config['inputs'].values()) + list(config['preparation_acceptance'].values())
assert len(current) == 44 and len(freeze['pins']) == 6 and len(freeze['current_prepared_bytes_only']) == 4
for row in current + list(freeze['pins'].values()) + list(freeze['current_prepared_bytes_only'].values()):
    checked(ROOT / row['path'], row)
checked(Path(config['interpreter']['path']), config['interpreter'])
historical = json.loads(checked(ROOT / config['preparation_acceptance']['configuration']['path'], config['preparation_acceptance']['configuration']))
prepared = json.loads(checked(ROOT / config['preparation_acceptance']['result']['path'], config['preparation_acceptance']['result']))
assert prepared['status'] == 'prepared' and prepared['held_four_imports_observed'] is False
assert config['inputs'] == historical['inputs']
assert config['negative_imports'] == ['numpy._distributor_init_local', 'org', 'torch._rocm_init']
assert config['expected_versions'] == historical['expected_versions']
assert config['environment'] == historical['environment']

archives = originals = excluded = 0
index_hashes = dict(zip(['01', '02', '03'], ['ed80850b0e208dd41114eea7948edf30d5f201e77ae584002472d25334f58c4d', 'c53d236540e8daaf36f97f848bb001284dac25c0cd7497b8fb28fba5cad573ec', '458e7f91334ca9a5e9050a122f54917197d9d14163529a66b0a27f41262aa581']))
for number in ['01', '02', '03']:
    archive = ROOT / f'docs/reports/puck-cpu-held-qualification-{number}'
    index_path = archive / 'evidence-index.json'
    index = json.loads(checked(index_path, dict(size_bytes=index_path.stat().st_size, sha256=index_hashes[number])))
    assert index['entry_count'] == len(index['entries'])
    for row in index['entries']:
        archived_raw = checked(archive / row['path'], row)
        archives += 1
        if 'original_path' not in row:
            continue
        original = Path(row['original_path'])
        if original.is_relative_to(ROOT / 'scripts'):
            excluded += 1
            continue
        assert checked(original, row) == archived_raw
        originals += 1
    assert not os.path.lexists(archive / 'raw/baseline-after.json')
    assert not os.path.lexists(ROOT / f'runs/puck-cpu-held-qualification-{number}/baseline-after.json')
assert (archives, originals, excluded) == (95, 83, 10)

capsules = 0
for number, directory in [('prepare', 'parent-source'), ('prepare', 'worker-source'), ('02', 'worker-source'), ('03', 'worker-source')]:
    old = historical if number == 'prepare' else json.loads((ROOT / f'docs/plans/puck-cpu-held-qualification-{number}.json').read_bytes())
    pins = {row['path']: row for row in old['sources']}
    base = ROOT / ('runs/puck-cpu-held-preparation-01' if number == 'prepare' else f'runs/puck-cpu-held-qualification-{number}') / directory
    leaves = sorted(p for p in base.rglob('*') if p.is_file() or p.is_symlink())
    assert len(leaves) == (24 if directory == 'parent-source' else 10)
    for path in leaves:
        relative = str(path.relative_to(base))
        checked(path, pins[relative])
        capsules += 1
assert capsules == 54

frozen03 = json.loads((ROOT / 'docs/plans/puck-cpu-held-qualification-03-freeze.json').read_bytes())
for row in frozen03['pins'].values():
    checked(ROOT / 'docs/reports/puck-cpu-held-qualification-03/frozen' / row['path'], row)
assert len(frozen03['pins']) == 5
roots = []
for row in prepared['staged_roots']:
    path = Path(config['stage_parent']) / 'inputs' / f"root-{row['root_index']:04d}"
    state = path.lstat()
    assert stat.S_ISDIR(state.st_mode) and stat.S_IMODE(state.st_mode) == 0o700
    assert (state.st_dev, state.st_ino) == (row['device'], row['inode'])
    roots.append(dict(path=str(path), device=state.st_dev, inode=state.st_ino, mode='0700'))
assert len(roots) == 4
expected_failures = ['224cb9bdb18228f6e8da7a47e7455cd604a6e756df5fd017294b9221f26d9299', '085d19bdd39d392aaeab0c1590ec92b99e0bb2a4e8945f5d23dd51733fbab56b', 'ba5cad51576c3dd593c479d052328fcb4181943d3f5acdbdaa7cdee145f1254b']
for number, expected in zip(['01', '02', '03'], expected_failures):
    raw = (ROOT / f'runs/puck-cpu-held-qualification-{number}/result.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected and json.loads(raw)['status'] == 'FAIL'

output = ROOT / 'runs/puck-cpu-held-qualification-04'
absent = [output, Path(str(output) + '-external-cli.stdout'), Path(str(output) + '-external-cli.stderr'), Path(str(output) + '-external-cli-transport.json'), Path(freeze['audit']['output'])]
assert all(not os.path.lexists(path) for path in absent)
meminfo = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
free = lambda path: (lambda state: state.f_bavail * state.f_frsize)(os.statvfs(path))
resource = dict(mem_available_bytes=int(meminfo['MemAvailable'].split()[0]) * 1024, tmpfs_available_bytes=free(config['stage_parent']), disk_available_bytes=free(ROOT))
required = dict(mem_available_bytes=config['limits']['min_available_ram_bytes'], tmpfs_available_bytes=config['limits']['min_tmpfs_free_bytes'], disk_available_bytes=config['limits']['min_free_bytes'])
report = dict(kind='puck-cpu-held-qualification04-preflight-v1', at=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='ADMITTED' if all(resource[k] >= required[k] for k in required) else 'NOT_ADMITTED', configuration_sha256=CONFIG_SHA, freeze_sha256=FREEZE_SHA, resource=resource, required=required, verified_current_source_input_acceptance_pins=44, verified_controls=6, verified_current_byte_pins=4, verified_historical_capsules=34, verified_all_prior_capsules=54, verified_prior_archive_artifacts=archives, verified_immutable_original_prior_artifacts=originals, historical_live_script_comparisons_excluded=excluded, staged_roots=roots, prior_baseline_after_absent=True, prior_qualifications01_02_03_failed_consumed_preserved=True, output_paths_absent=[str(p) for p in absent], actual04_invoked=False, byte_scope='dated pre04 data-only census9f19b42f at16:06:25UTC; parent must freshly verify staged bytes under custody before imports', qualification_claims=[])
target = ROOT / 'runs/puck-cpu-held-qualification-04-resource-preflight-01.json'
with target.open('x') as stream:
    stream.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps(report, sort_keys=True))
