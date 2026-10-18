import base64, csv, hashlib, io, itertools, json, math, os, re, resource, signal, stat, sys, time, zipfile, zlib
from email import policy
from email.parser import BytesParser
from pathlib import Path

ROOT = Path('/home/utkarsh/.codex/worktrees/0071/brain')
REL = 'docs/plans/puck-cpu-payload-acquisition-01.json'
CONFIG_SHA = '91d1dcaabb34f4177650c3c72d2295233bd42814dcd433b369be3e0f8b1c5402'
REPORT = Path('/tmp/palimpsest-cpu-payload-acquisition-01-audit.json')
SOURCE_COMMIT = 'eeb82bf03d41fb819a29e639bf341b6b2cb59206'
START = time.monotonic()
DEADLINE = START + 175
HARD_CAP = 2 * 1024**3
MAX_REPORT = 128 * 1024
CHUNK = 128 * 1024
PINNED_PATHS = ['docs/plans/puck-cpu-payload-acquisition-v1.md', 'pyproject.toml', 'scripts/acquire_puck_cpu_payloads.py', 'src/palimpsest/__init__.py', 'src/palimpsest/bounded_qualification.py', 'src/palimpsest/evaluate.py', 'src/palimpsest/puck_execution_files.py', 'src/palimpsest/puck_package_payloads.py', 'uv.lock']
FALSE = {'collection_authorized': False, 'executable': False, 'installed': False, 'licence_contents_audited': False, 'numerical_imports_executed': False, 'qualification_claims': [], 'runtime_qualified': False, 'source_build_executed': False, 'study_authorized': False}
AUDIT = {'kind': 'puck-cpu-payload-independent-terminal-audit-v1', 'version': 1, 'status': 'refusal', 'source_commit_verified_before_audit': SOURCE_COMMIT, 'configuration_sha256': CONFIG_SHA, 'findings': [], 'audit_limits': {'wall_seconds': 180, 'cooperative_seconds': 175, 'decoded_aggregate_bytes': HARD_CAP, 'report_bytes': MAX_REPORT, 'address_space_bytes': HARD_CAP}, 'audit_command': 'timeout --kill-after=2s 180s /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python -I -S -B - < audit-program-from-tool-call', 'limitations': ['Parent exit 0 is externally observed by root via exec session 21273, final chunk 8e93d1; auditor did not own that handle.', 'Worker group and exact argv route scans are point-in-time checks, not universal host process cleanup.', 'Source archive remains hashed only, unbuilt and uninstalled; source members and licence acceptance are outside this audit.', 'Sampled RSS and operational clocks are not a RAM reservation, hostile-code sandbox, hard RSS guarantee, WCET or numerical/runtime qualification.']}
PINS = []
IDENTITIES = {}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def clock():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError('independent audit deadline exhausted')

def identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def regular(path, cap):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size <= cap, 'nonregular, linked or oversized file: ' + str(path))
    return s

def file_bytes(path, cap, expected_sha=None, expected_size=None, retain=True):
    clock()
    before = regular(path, cap)
    if expected_size is not None:
        require(before.st_size == expected_size, 'file size mismatch: ' + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        require(identity(os.fstat(fd)) == identity(before), 'file changed during open: ' + str(path))
        h, count = hashlib.sha256(), 0
        chunks = []
        while True:
            clock()
            block = os.read(fd, CHUNK)
            if not block:
                break
            count += len(block)
            require(count <= cap, 'read cap exceeded: ' + str(path))
            h.update(block)
            if retain:
                chunks.append(block)
        require(count == before.st_size and identity(os.fstat(fd)) == identity(before) == identity(path.lstat()), 'file changed during read: ' + str(path))
    finally:
        os.close(fd)
    actual = h.hexdigest()
    if expected_sha is not None:
        require(actual == expected_sha, 'file SHA256 mismatch: ' + str(path))
    IDENTITIES[str(path)] = identity(before)
    return b''.join(chunks) if retain else (count, actual)

def parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    def bad(value):
        raise ValueError('nonfinite JSON constant')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()

def norm(value):
    return re.sub(r'[-_.]+', '-', value).lower()

def one(message, key):
    values = message.get_all(key, [])
    require(len(values) == 1, 'metadata requires exactly one ' + key)
    return str(values[0])

def tags(value):
    parts = value.split('-')
    require(len(parts) == 3 and all(re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*', p) for p in parts), 'invalid wheel tag')
    return {'-'.join(v) for v in itertools.product(*(p.split('.') for p in parts))}

def all_claims(value, label):
    require({k: value.get(k) for k in FALSE} == FALSE, label + ' authority claims differ')

try:
    require(not REPORT.exists(), 'audit report already exists; refusing overwrite')
    resource.setrlimit(resource.RLIMIT_AS, (HARD_CAP, HARD_CAP))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_REPORT, MAX_REPORT))
    def alarm(signum, frame):
        raise TimeoutError('independent audit alarm exhausted')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(175)
    config_raw = file_bytes(ROOT / REL, 4 * 1024**2, CONFIG_SHA, 2642)
    config = parse(config_raw)
    require(canonical(config) == config_raw, 'configuration is not exact canonical JSON')
    require(config['kind'] == 'puck-cpu-payload-acquisition-v1' and config['version'] == 1, 'configuration kind/version differs')
    require(config['claims'] == FALSE, 'configuration claims differ')
    require([p['path'] for p in config['sources']] == PINNED_PATHS, 'source capsule differs')
    for row in config['sources'] + [config['candidate'], config['assessment']]:
        require(set(row) == {'path', 'size_bytes', 'sha256'}, 'pin descriptor fields differ')
        require(not Path(row['path']).is_absolute() and all(p not in ('', '.', '..') for p in row['path'].split('/')), 'unsafe pin path')
        file_bytes(ROOT / row['path'], 32 * 1024**2, row['sha256'], row['size_bytes'], retain=False)
        PINS.append(row)
    interp = config['interpreter']
    require(Path(sys.executable).resolve() == Path(interp['path']), 'audit interpreter resolution differs from pinned interpreter')
    file_bytes(Path(interp['path']), 64 * 1024**2, interp['sha256'], interp['size_bytes'], retain=False)
    PINS.append(interp)
    candidate = parse(file_bytes(ROOT / config['candidate']['path'], 4 * 1024**2, config['candidate']['sha256'], config['candidate']['size_bytes']))
    assessment = parse(file_bytes(ROOT / config['assessment']['path'], 4 * 1024**2, config['assessment']['sha256'], config['assessment']['size_bytes']))
    require(config['assessment'] in candidate['evidence'], 'candidate does not bind assessment descriptor')
    require(candidate['kind'] == 'puck-cpu-runtime-candidate-v1' and candidate['version'] == 1 and assessment['kind'] == 'puck-cpu-wheel-metadata-assessment-v1' and assessment['version'] == 1, 'selection evidence kind/version differs')
    specs = []
    for row in assessment['wheels']:
        specs.append({'name': row['name'], 'version': row['version'], 'filename': row['filename'], 'url': row['url'], 'size_bytes': row['archive_bytes'], 'sha256': row['archive_sha256_index_declared'], 'metadata_sha256': row['metadata_sha256'], 'format': 'wheel'})
    require(len(assessment['missing']) == 1, 'source dependency count differs')
    missing = assessment['missing'][0]
    require((missing['name'], missing['version']) == ('python-louvain', '0.16'), 'source dependency identity differs')
    sd = missing['sdist']
    specs.append({'name': missing['name'], 'version': missing['version'], 'filename': sd['url'].rsplit('/', 1)[1], 'url': sd['url'], 'size_bytes': sd['size'], 'sha256': sd['hash'].removeprefix('sha256:'), 'metadata_sha256': None, 'format': 'sdist'})
    specs.sort(key=lambda row: row['name'])
    require(len(specs) == 71 and sum(r['format'] == 'wheel' for r in specs) == 70 and sum(r['size_bytes'] for r in specs) == 385328518, 'exact archive scope differs')
    require(sorted(r['name'] + '==' + r['version'] for r in specs) == candidate['target']['candidate_pins'] and candidate['target']['candidate_pin_count'] == 71, 'candidate pin set differs')
    require(len({r['filename'] for r in specs}) == 71, 'duplicate archive leaf')
    limits = config['limits']
    expected_limits = {'address_space_bytes': 2147483648, 'hard_seconds': 615, 'max_archive_bytes': 268435456, 'max_download_bytes': 419430400, 'max_fds': 256, 'max_member_bytes': 1073741824, 'max_members': 32768, 'max_metadata_bytes': 4194304, 'max_output_directories': 3, 'max_output_files': 160, 'max_report_bytes': 16777216, 'max_requests': 71, 'max_uncompressed_bytes': 2147483648, 'min_available_ram_bytes': 2147483648, 'min_free_bytes': 4294967296, 'normal_seconds': 600, 'output_bytes': 536870912, 'rss_bytes': 1073741824, 'socket_seconds': 20}
    require(limits == expected_limits, 'frozen limits differ')
    require(config['output'] == 'runs/puck-cpu-payload-acquisition-01', 'allocated output differs')
    output = ROOT / config['output']
    require(stat.S_ISDIR(output.lstat().st_mode) and not output.is_symlink(), 'output root is not ordinary directory')
    expected_files = {'configuration.json', 'worker-result.json', 'outcome.json', 'outer/stdout.log', 'outer/stderr.log'} | {'archives/' + r['filename'] for r in specs} | {'manifests/' + r['filename'] + '.json' for r in specs}
    actual_files, actual_dirs, retained_bytes, output_identities = set(), set(), 0, {}
    for directory, dirs, files in os.walk(output, followlinks=False):
        clock()
        for name in dirs:
            path = Path(directory) / name
            require(stat.S_ISDIR(path.lstat().st_mode) and not path.is_symlink(), 'nonordinary output directory')
            actual_dirs.add(path.relative_to(output).as_posix())
        for name in files:
            path = Path(directory) / name
            s = regular(path, limits['output_bytes'])
            actual_files.add(path.relative_to(output).as_posix())
            retained_bytes += s.st_size
            output_identities[str(path)] = identity(s)
    require(actual_dirs == {'archives', 'manifests', 'outer'} and actual_files == expected_files, 'unexpected or missing output entries')
    require(len(actual_files) <= limits['max_output_files'] and len(actual_dirs) <= limits['max_output_directories'] and retained_bytes <= limits['output_bytes'], 'retained output allocation exceeded')
    require(file_bytes(output / 'configuration.json', 4 * 1024**2) == config_raw, 'retained configuration copy differs')
    worker_raw = file_bytes(output / 'worker-result.json', 1024**2)
    worker = parse(worker_raw)
    outcome_raw = file_bytes(output / 'outcome.json', 1024**2)
    outcome = parse(outcome_raw)
    require(worker['kind'] == 'puck-cpu-payload-worker-result-v1' and outcome['kind'] == 'puck-cpu-payload-acquisition-result-v1' and worker['version'] == outcome['version'] == 1, 'terminal result kind/version differs')
    all_claims(worker, 'worker')
    all_claims(outcome, 'parent')
    require(worker['status'] == outcome['status'] == 'payloads_verified' and worker['configuration_sha256'] == outcome['configuration_sha256'] == CONFIG_SHA, 'terminal status/configuration differs')
    require(outcome['worker_result_sha256'] == hashlib.sha256(canonical(worker)).hexdigest() == hashlib.sha256(worker_raw).hexdigest(), 'worker result hash differs')
    require(worker['archive_count'] == outcome['archive_count'] == outcome['expected_archive_count'] == 71 and worker['wheel_count'] == outcome['wheel_count'] == 70 and worker['downloaded_bytes'] == outcome['downloaded_bytes'] == 385328518, 'terminal counters differ')
    require(type(outcome['elapsed_seconds']) in (int, float) and 0 <= outcome['elapsed_seconds'] < limits['normal_seconds'], 'parent normal deadline differs')
    observed = outcome['supervision']
    require(observed['status'] == 'completed' and observed['returncode'] == 0 and observed['failure'] is None and observed['matching_survivors'] == [] and observed['pid'] == 2331707, 'supervision terminal state differs')
    require(0 <= observed['sampled_peak_rss_bytes'] <= limits['rss_bytes'] and observed['rss_sampling_seconds'] == 0.05, 'supervision sampled RSS differs')
    require(len(worker['requests']) == 71 and len(worker['artifacts']) == 71, 'request/artifact count differs')
    require(sum(r['body_bytes'] for r in worker['requests']) == 385328518 <= limits['max_download_bytes'], 'request byte budget differs')
    artifacts = {r['filename']: r for r in worker['artifacts']}
    require(len(artifacts) == 71 and set(artifacts) == {r['filename'] for r in specs}, 'artifact descriptor set differs')
    for spec, req in zip(specs, worker['requests']):
        require(req['url'] == spec['url'] and req['status'] == 200 and req['body_bytes'] == spec['size_bytes'] and type(req['elapsed_seconds']) in (int, float) and math.isfinite(req['elapsed_seconds']) and 0 <= req['elapsed_seconds'] < 600, 'request descriptor mismatch: ' + spec['filename'])
    require(sum(r['elapsed_seconds'] for r in worker['requests']) <= outcome['elapsed_seconds'], 'request timing exceeds parent elapsed')
    aggregate_members = aggregate_decoded = aggregate_regular = licences = 0
    wheel_rows = []
    for spec in specs:
        clock()
        filename = spec['filename']
        desc = artifacts[filename]
        require(desc['name'] == spec['name'] and desc['version'] == spec['version'] and desc['format'] == spec['format'] and desc['archive_sha256'] == spec['sha256'] and desc['manifest'] == 'manifests/' + filename + '.json', 'artifact descriptor identity differs: ' + filename)
        manifest_raw = file_bytes(output / desc['manifest'], limits['max_report_bytes'], desc['manifest_sha256'], desc['manifest_size_bytes'])
        manifest = parse(manifest_raw)
        require(all(manifest[k] == spec[k] for k in ('name', 'version', 'filename', 'size_bytes', 'sha256')) and manifest['archive_payload_verified'] is True, 'manifest archive identity differs: ' + filename)
        archive_path = output / 'archives' / filename
        file_bytes(archive_path, limits['max_archive_bytes'], spec['sha256'], spec['size_bytes'], retain=False)
        if spec['format'] == 'sdist':
            require(manifest == {k: spec[k] for k in ('name', 'version', 'filename', 'size_bytes', 'sha256')} | {'archive_payload_verified': True, 'source_members_inspected': False, 'source_build_executed': False}, 'source manifest claims differ')
            continue
        name_parts = filename[:-4].split('-')
        dist = name_parts[0] + '-' + name_parts[1] + '.dist-info'
        metadata_path, wheel_path, record_path = [dist + '/' + name for name in ('METADATA', 'WHEEL', 'RECORD')]
        special_paths = {metadata_path, wheel_path, record_path}
        collected, regular_files, special, seen, bare_paths = [], {}, {}, set(), {}
        decoded = 0
        fd = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            initial = os.fstat(fd)
            require(identity(initial) == output_identities[str(archive_path)], 'archive changed before ZIP audit')
            with os.fdopen(fd, 'rb', closefd=False) as source:
                with zipfile.ZipFile(source, 'r') as archive:
                    infos = archive.infolist()
                    aggregate_members += len(infos)
                    require(aggregate_members <= limits['max_members'], 'aggregate wheel member cap exceeded')
                    require(aggregate_decoded + sum(i.file_size for i in infos) <= min(HARD_CAP, limits['max_uncompressed_bytes']), 'declared aggregate decode cap exceeded')
                    for info in infos:
                        clock()
                        path = info.orig_filename
                        directory = info.is_dir()
                        bare = path[:-1] if directory else path
                        require(path == info.filename and bare and '\\' not in path and not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in path) and all(p not in ('', '.', '..') for p in bare.split('/')) and bare not in seen, 'unsafe or duplicated wheel path: ' + filename)
                        seen.add(bare)
                        bare_paths[bare] = directory
                        mode = stat.S_IFMT(info.external_attr >> 16)
                        require(mode in ((0, stat.S_IFDIR) if directory else (0, stat.S_IFREG)) and not (directory and info.file_size), 'special wheel member: ' + filename)
                        require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not info.flag_bits & 0x41, 'unsupported wheel compression/encryption')
                        require(info.file_size <= limits['max_member_bytes'], 'wheel member size cap exceeded')
                        require(not bare.split('/')[0].endswith('.dist-info') or bare.split('/')[0] == dist, 'different wheel dist-info identity')
                        hashes = {alg: hashlib.new(alg) for alg in ('sha256', 'sha384', 'sha512')}
                        chunks, count, crc = [], 0, 0
                        if directory:
                            require(info.CRC == 0, 'directory CRC differs')
                        else:
                            with archive.open(info, 'r') as stream:
                                while True:
                                    clock()
                                    block = stream.read(CHUNK)
                                    if not block:
                                        break
                                    count += len(block)
                                    aggregate_decoded += len(block)
                                    require(count <= limits['max_member_bytes'] and aggregate_decoded <= min(HARD_CAP, limits['max_uncompressed_bytes']), 'actual aggregate/member decode cap exceeded')
                                    if path in special_paths:
                                        require(count <= limits['max_metadata_bytes'], 'wheel metadata cap exceeded')
                                        chunks.append(block)
                                    crc = zlib.crc32(block, crc)
                                    for h in hashes.values():
                                        h.update(block)
                            require(count == info.file_size and crc == info.CRC, 'independent ZIP actual size/CRC differs: ' + path)
                            aggregate_regular += 1
                        decoded += count
                        row = {'path': path, 'size_bytes': count, 'sha256': hashes['sha256'].hexdigest(), 'mode': info.external_attr >> 16}
                        collected.append(row)
                        if not directory:
                            regular_files[path] = {'size': count, 'digests': {k: v.digest() for k, v in hashes.items()}}
                        if path in special_paths:
                            special[path] = b''.join(chunks)
            require(identity(os.fstat(fd)) == identity(initial) == identity(archive_path.lstat()), 'archive changed during independent ZIP audit')
        finally:
            os.close(fd)
        for bare in bare_paths:
            parts = bare.split('/')
            require(not any(bare_paths.get('/'.join(parts[:i])) is False for i in range(1, len(parts))), 'wheel path prefix collision')
        require(special_paths <= set(regular_files), 'wheel mandatory metadata missing')
        metadata_sha = hashlib.sha256(special[metadata_path]).hexdigest()
        require(metadata_sha == spec['metadata_sha256'] == manifest['metadata_sha256'], 'metadata SHA256 differs')
        special[metadata_path].decode('utf-8')
        md = BytesParser(policy=policy.default).parsebytes(special[metadata_path])
        require(not md.defects and norm(one(md, 'Name')) == spec['name'] and one(md, 'Version') == spec['version'], 'metadata identity differs')
        wh = BytesParser(policy=policy.default).parsebytes(special[wheel_path])
        require(not wh.defects and not wh.get_payload().strip() and one(wh, 'Wheel-Version') == '1.0', 'WHEEL metadata differs')
        purity = one(wh, 'Root-Is-Purelib')
        wheel_tags = set().union(*(tags(str(v)) for v in wh.get_all('Tag', [])))
        require(purity in ('true', 'false') and wheel_tags == tags('-'.join(name_parts[-3:])), 'WHEEL filename tags/purity differ')
        rows = {}
        for row in csv.reader(io.StringIO(special[record_path].decode('utf-8'), newline=''), strict=True):
            require(len(row) == 3 and row[0] not in rows, 'invalid or duplicated RECORD row')
            rows[row[0]] = row[1:]
        require(set(rows) == set(regular_files), 'RECORD coverage differs')
        for path, (encoded, size) in rows.items():
            if path == record_path:
                require(encoded == size == '', 'RECORD self entry differs')
                continue
            alg, value = encoded.split('=', 1)
            require(alg in ('sha256', 'sha384', 'sha512') and re.fullmatch(r'[A-Za-z0-9_-]+', value), 'unsupported RECORD hash')
            actual_digest = regular_files[path]['digests'][alg]
            require(base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)) == actual_digest, 'independent RECORD hash mismatch: ' + path)
            require(re.fullmatch(r'0|[1-9][0-9]*', size) and int(size) == regular_files[path]['size'], 'independent RECORD size mismatch: ' + path)
        collected.sort(key=lambda r: r['path'])
        require(manifest['members'] == collected and manifest['member_count'] == len(collected) and manifest['uncompressed_bytes'] == decoded and manifest['record_verified'] is True, 'manifest member inventory differs: ' + filename)
        independent_licences = [r for r in collected if r['path'] in regular_files and (r['path'].startswith(dist + '/licenses/') or r['path'].rsplit('/', 1)[-1].lower().startswith(('license', 'licence', 'copying', 'notice')))]
        require(manifest['licence_candidates'] == independent_licences, 'licence candidate inventory differs')
        licences += len(independent_licences)
        require(manifest['wheel'] == {'version': '1.0', 'root_is_purelib': purity == 'true', 'tags': sorted(wheel_tags)}, 'manifest WHEEL fields differ')
        require(manifest['metadata'] == {'name': one(md, 'Name'), 'version': one(md, 'Version'), 'license_expression': md.get('License-Expression'), 'license': md.get('License'), 'license_files': md.get_all('License-File', []), 'requires_dist': md.get_all('Requires-Dist', [])}, 'manifest METADATA fields differ')
        wheel_rows.append({'name': spec['name'], 'filename': filename, 'archive_sha256': spec['sha256'], 'manifest_sha256': desc['manifest_sha256'], 'members': len(collected), 'decoded_bytes': decoded})
    require(aggregate_members == worker['wheel_member_count'] == 28237 and aggregate_decoded == worker['wheel_uncompressed_bytes'] == 1304650469, 'aggregate wheel counts differ')
    stdout = parse(file_bytes(output / 'outer/stdout.log', 1024**2))
    require(stdout == worker and file_bytes(output / 'outer/stderr.log', 1024**2) == b'', 'worker terminal logs differ')
    group_survivors, route_survivors, proc_unreadable = [], [], 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            status = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            if status[0] in ('Z', 'X'):
                continue
            if int(status[2]) == 2331707:
                group_survivors.append(int(proc.name))
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
            if b'--configuration' in argv and b'--sha256' in argv and CONFIG_SHA.encode() in argv and any(v.endswith(b'/acquire_puck_cpu_payloads.py') for v in argv):
                route_survivors.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            proc_unreadable += 1
    require(not group_survivors and not route_survivors, 'matching acquisition process route survives')
    for path, expected in {**IDENTITIES, **output_identities}.items():
        clock()
        require(identity(Path(path).lstat()) == expected, 'retained evidence changed by end of audit: ' + path)
    AUDIT.update(status='GO', pins=PINS, counts={'archives': 71, 'wheels': 70, 'source_archives': 1, 'archive_bytes': 385328518, 'wheel_members': aggregate_members, 'regular_wheel_members': aggregate_regular, 'decoded_wheel_bytes': aggregate_decoded, 'verified_manifests': 71, 'licence_candidates_inventoried': licences, 'output_files': len(actual_files), 'output_directories': len(actual_dirs), 'retained_output_bytes': retained_bytes, 'record_verified_wheels': 70}, parent_observation={'status': outcome['status'], 'elapsed_seconds': outcome['elapsed_seconds'], 'externally_observed_exitcode': 0, 'exit_evidence': 'root exec session 21273 final chunk 8e93d1', 'sampled_peak_rss_bytes': observed['sampled_peak_rss_bytes'], 'worker_pid': observed['pid'], 'worker_returncode': observed['returncode'], 'recorded_matching_survivors': observed['matching_survivors']}, process_scan={'worker_group': 2331707, 'live_group_members': group_survivors, 'live_exact_configuration_routes': route_survivors, 'unreadable_proc_entries': proc_unreadable}, worker_result_sha256=hashlib.sha256(worker_raw).hexdigest(), outcome_sha256=hashlib.sha256(outcome_raw).hexdigest(), configuration_and_sources_unchanged_through_audit=True, false_claims=FALSE, acquisition_limits=limits, wheels=wheel_rows)
except BaseException as error:
    AUDIT['findings'].append({'type': type(error).__name__, 'message': str(error)})
finally:
    signal.alarm(0)
    AUDIT['elapsed_seconds'] = time.monotonic() - START
    raw = (json.dumps(AUDIT, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()
    if len(raw) > MAX_REPORT:
        raw = (json.dumps({'kind': AUDIT['kind'], 'status': 'refusal', 'findings': [{'message': 'audit report exceeds 128KiB cap'}], 'elapsed_seconds': AUDIT['elapsed_seconds']}, sort_keys=True, separators=(',', ':')) + '\n').encode()
    with REPORT.open('xb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    print(json.dumps({'status': AUDIT['status'], 'findings': AUDIT['findings'], 'counts': AUDIT.get('counts'), 'elapsed_seconds': AUDIT['elapsed_seconds'], 'report': str(REPORT), 'report_bytes': len(raw), 'report_sha256': hashlib.sha256(raw).hexdigest()}, sort_keys=True, separators=(',', ':')))
raise SystemExit(0 if AUDIT['status'] == 'GO' else 1)
