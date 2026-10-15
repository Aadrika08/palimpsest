"""Independent ordinary CPU observation03 byte audit; never imports target code."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'runs/puck-cpu-runtime-characterization-03'
SITE = 'runs/puck-cpu-install-01/site'
PARENT = 'scripts/characterize_puck_cpu_runtime.py'
WORKER = 'scripts/characterize_puck_runtime_imports.py'
OBSERVER = 'scripts/observe_puck_cpu_runtime_characterization.py'
AUDITOR = 'scripts/audit_puck_cpu_runtime_characterization.py'
PYTHON = '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
ARCHIVE = 'docs/reports/puck-cpu-characterization-02'
ACCEPTANCE = 'docs/reports/puck-cpu-retained-admission-02'
PRIOR = 'docs/reports/puck-cpu-characterization-01'
PLAN = 'docs/plans/puck-cpu-distributed-roster-observation-01-proposal.md'
PROPOSAL_PIN = dict(path='docs/reports/puck-cpu-export-phase-preflight-v1/notes/distributed-rosters/review.json',
                    size_bytes=11683, sha256='de1aa2a7c7a0832b59f72cc07ffee5965a37657618ef8f70ea8f08238a815e04')
OBSERVATION_PINS = {'observation_configuration': {'path': 'docs/reports/puck-cpu-characterization-02/frozen-configuration.json', 'size_bytes': 11687, 'sha256': 'f9589323ba86f0b23b00924dfcd33f3c4f3fb69cb500ab43fc6ba37a68b4f15c'}, 'observation_report': {'path': 'docs/reports/puck-cpu-characterization-02/raw/payload/imports.json', 'size_bytes': 558, 'sha256': '5e6c9f0647005d4f827fdf61ad26f980b6a58e3a1ec2c7331e4b257312509cee'}, 'observation_result': {'path': 'docs/reports/puck-cpu-characterization-02/raw/result.json', 'size_bytes': 819, 'sha256': '088f668def76f09b1252473108346e4f7510bf2d9f698f6f4be3f48946ce8a44'}, 'observation_audit': {'path': 'docs/reports/puck-cpu-characterization-02/outcome-audit-02.json', 'size_bytes': 867, 'sha256': '2ba804cec194897038013de6853823b03e8733d2078d66ee58fb4d56496a7327'}, 'observation_index': {'path': 'docs/reports/puck-cpu-characterization-02/evidence-index.json', 'size_bytes': 322, 'sha256': '79e82b792e995680ee3281b3226d355707377f6a4d90cfd86c8232c2dd3cfd9a'}, 'observation_terminal': {'path': 'docs/reports/puck-cpu-characterization-02/external-terminal-observations.json', 'size_bytes': 260, 'sha256': '0894ff1fd751bc5e53087d3c6313edb5f3875c96dac23477eb310092ed942432'}}
SUPPORT = (
    dict(path=ARCHIVE+'/audit-support-characterization-v1.py', size_bytes=15971,
         sha256='ba1f54b2885901cae837bb710bb725e211d5aaf5fcddb8fc6bfeb786f2daac4e'),
    dict(path=ARCHIVE+'/audit-helper-install-v1.py', size_bytes=33686,
         sha256='a8945d3dc432831522e66c7817c0f3281e278e2a930ab1e31cbb14a26e17e406'),
    dict(path=ARCHIVE+'/audit-helper-admission-v3.py', size_bytes=15635,
         sha256='f6229e92238f260e001b6e49cf545dcddd9a371fb272118881fbec8b38961469'))
OLD_SOURCES = tuple(sorted(('docs/plans/puck-cpu-characterization-v2.md',
    'scripts/acquire_puck_cpu_payloads.py', 'scripts/admit_puck_retained_installation.py',
    'scripts/build_puck_python_louvain.py', PARENT, WORKER, 'scripts/install_puck_cpu.py',
    'src/palimpsest/__init__.py', 'src/palimpsest/bounded_qualification.py', 'src/palimpsest/evaluate.py',
    'src/palimpsest/puck_build_inputs.py', 'src/palimpsest/puck_execution_files.py',
    'src/palimpsest/puck_package_payloads.py', 'src/palimpsest/puck_retained_installation.py')))
SOURCES = tuple(sorted((set(OLD_SOURCES)-{'docs/plans/puck-cpu-characterization-v2.md'})
                       | {PLAN, OBSERVER, AUDITOR} | {row['path'] for row in SUPPORT}))
OLD_ROLES = dict(baseline='docs/plans/puck-python-louvain-host-baseline-v1.json',
    inventory='runs/puck-cpu-retained-admission-02/inventory.json',
    layout='docs/reports/puck-cpu-install-01/wheel-layout.json',
    accepted_result='runs/puck-cpu-retained-admission-02/result.json',
    accepted_snapshot='runs/puck-cpu-retained-admission-02/snapshot.json',
    accepted_audit=ACCEPTANCE+'/acceptance-audit-03.json',
    accepted_configuration='docs/plans/puck-cpu-retained-admission-02.json',
    accepted_index=ACCEPTANCE+'/evidence-index.json',
    native_metadata='docs/plans/puck-cpu-characterization-native-metadata-05.json',
    prior_configuration=PRIOR+'/frozen-configuration.json', prior_result=PRIOR+'/raw/result.json',
    prior_audit=PRIOR+'/failure-audit-01.json')
ROLES = dict(OLD_ROLES, **{role: row['path'] for role, row in OBSERVATION_PINS.items()},
             distributed_proposal=PROPOSAL_PIN['path'])
VERSIONS = dict(numpy='2.2.5', torch='2.9.0+cpu', torchvision='0.24.0+cpu', mujoco='3.3.6')
ENVIRONMENT = dict(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C.UTF-8', LANG='C.UTF-8',
    HOME='/scratch/home', TMPDIR='/scratch/tmp', PWD='/scratch', PATH='/nonexistent', TZ='UTC',
    CUDA_VISIBLE_DEVICES='', MUJOCO_GL='egl', PYOPENGL_PLATFORM='egl', MPLBACKEND='Agg',
    OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', OPENBLAS_MAIN_FREE='1',
    GOTOBLAS_MAIN_FREE='1', TORCH_DEVICE_BACKEND_AUTOLOAD='0')
LIMITS = {'normal_seconds': 180, 'child_hard_seconds': 190, 'hard_seconds': 195, 'rss_bytes': 1610612736, 'address_space_bytes': 8589934592, 'output_bytes': 67108864, 'scratch_bytes': 67108864, 'file_bytes': 8388608, 'min_free_bytes': 4294967296, 'min_available_ram_bytes': 134217728, 'max_processes': 3, 'max_fds': 40000}
FALSE = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
             study_authorized=False, executable=False, qualification_claims=[])
DISTRIBUTED = tuple('torch._C.'+name for name in ('_distributed_autograd', '_distributed_c10d', '_distributed_rpc'))
TRANSPORT_ENVIRONMENT = dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
SAMPLING_LIMITATION = ('Sampled PID/start identities only; not exhaustive unseen-process proof. '
    'PID/start recheck and signal are not atomic lifetime proof. '
    'Parent process-group supervision and closure require independent audit.')
ACCEPTED_SHA = '361480d57b661bafc7469571634d086f37b5a131a6501ddb43b011d5997257b7'
NATIVE_SHA = '40dcdd4fcfff38debd1807fe3926ed79c6d1889cae3e29b982f21c755d43cc1e'
PRIOR_SHAS = ('aafc5ca1d2d2325e75ec6682a4e5f4d5d90a26df644b073c5a4438e1720877be', '512e47afafce44ce1353bd25cd08e1cb94c5e1d91ad91368293cefebac51675f', '7a052930ea137ee44312ac4f921e9dd95e8aa1ef93b76639007f0c2aefd19280')
SITE_COUNTS = (9, 6, 3413)
BASELINE_COUNTS = (4233, 1048)
NATIVE_COUNTS = (8, 3, 7, 0)
PROBE = """import json,os,pathlib,stat,sys
parent_net,site,hidden=sys.argv[1:]
assert os.readlink('/proc/self/ns/net')!=parent_net
assert all(not line.split() or line.split()[0] in ('Iface','lo') for line in pathlib.Path('/proc/net/route').read_text().splitlines())
assert all(line.split()[-1]=='lo' for line in pathlib.Path('/proc/net/ipv6_route').read_text().splitlines() if line.split())
assert os.statvfs(site).f_flag & os.ST_RDONLY
assert not pathlib.Path(hidden).exists()
assert not pathlib.Path('/scratch/pycache').stat().st_mode & 0o077
assert not list(pathlib.Path('/scratch/pycache').iterdir())
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.pycache_prefix=='/scratch/pycache'
p=pathlib.Path('/scratch/tmp/probe');p.write_bytes(b'bounded');p.unlink()
print(json.dumps(dict(kind='cpu-characterization-namespace-v1',network_isolated=True,site_readonly=True,project_hidden=True,private_pycache_empty=True)))
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def finite(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value < maximum


def integer(value, maximum, minimum=0):
    return type(value) is int and minimum <= value <= maximum


def text(value, maximum=4096, nullable=False):
    return (nullable and value is None) or (type(value) is str and len(value) <= maximum and '\0' not in value)


def fields(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'Exact metadata fields required')


def claims(value):
    require(all(value.get(key) is False for key in FALSE if key != 'qualification_claims')
            and value.get('qualification_claims') == [], 'Ordinary observation granted authority')


def relative(value):
    require(type(value) is str and value and len(value.encode()) <= 4096 and '\0' not in value
            and '\\' not in value and not value.startswith('/')
            and all(part not in ('', '.', '..') for part in value.split('/')), 'Canonical relative path required')
    return value


def absolute(value):
    supplied = str(value); path = Path(value)
    require(path.is_absolute() and supplied == str(path) and '..' not in path.parts
            and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
            'Canonical absolute audit path inside ROOT required')
    return path


def pin_rows(rows, count):
    require(type(rows) is list and len(rows) == count, 'Exact source/input pin count required')
    names = []
    for row in rows:
        fields(row, ('path', 'size_bytes', 'sha256')); relative(row['path'])
        require(integer(row['size_bytes'], 1 << 30) and type(row['sha256']) is str
                and len(row['sha256']) == 64 and all(c in '0123456789abcdef' for c in row['sha256']), 'Exact byte pin required')
        names.append(row['path'])
    require(names == sorted(set(names)), 'Sorted distinct byte pins required')
    return {row['path']: row for row in rows}


def required_inputs(observation):
    require(type(observation) is dict and observation.get('kind') == 'puck-cpu-runtime-characterization-v1'
            and type(observation.get('version')) is int and observation['version'] == 1
            and observation.get('output') == 'runs/puck-cpu-runtime-characterization-02'
            and observation.get('site_root') == SITE and observation.get('roles') == OLD_ROLES
            and observation.get('environment') == ENVIRONMENT and observation.get('limits') == LIMITS
            and observation.get('expected_versions') == VERSIONS, 'Frozen observation02 scope differs')
    pin_rows(observation['sources'], 14)
    require(tuple(row['path'] for row in observation['sources']) == OLD_SOURCES, 'Frozen02 source boundary differs')
    rows = pin_rows(observation['inputs'], 42)
    rows = {path: dict(row) for path, row in rows.items()}
    for row in observation['sources']:
        path = ARCHIVE+'/source/'+row['path']; require(path not in rows, 'Overlapping historical capsule')
        rows[path] = dict(row, path=path)
    for row in (*OBSERVATION_PINS.values(), PROPOSAL_PIN):
        require(row['path'] not in rows, 'Overlapping observation role'); rows[row['path']] = dict(row)
    require(len(rows) == 63, 'Exact63 input closure required')
    return [rows[path] for path in sorted(rows)]


def distributed_expected(proposal):
    require(type(proposal) is dict and proposal.get('kind') == 'distributed-export-prospective-roster-review-v1', 'Pinned source proposal required')
    rows = proposal.get('proposed_rows'); fields(rows, ('autograd', 'c10d', 'rpc'))
    expected = {}
    for key, name in zip(('autograd', 'c10d', 'rpc'), DISTRIBUTED, strict=True):
        row = rows[key]
        require(row.get('name') == name and row.get('phase') == 'module_exec_publish'
                and row.get('attributes') == name.split('.') and row.get('class_binding') is None,
                'Source-proposed distributed child differs')
        names = row.get('delegate_attributes'); names_list(names, nonempty=True)
        expected[name] = list(names)
    return expected


def validate_configuration(config, observation, proposal):
    fields(config, ('kind', 'version', 'output', 'site_root', 'sources', 'inputs', 'roles', 'limits', 'environment', 'expected_versions'))
    require(config['kind'] == 'puck-cpu-runtime-characterization-v2' and type(config['version']) is int
            and config['version'] == 2 and config['output'] == OUTPUT and config['site_root'] == SITE
            and config['roles'] == ROLES and config['limits'] == LIMITS
            and config['environment'] == ENVIRONMENT and config['expected_versions'] == VERSIONS,
            'Exact characterization03 scope required')
    pin_rows(config['sources'], 19); pin_rows(config['inputs'], 63)
    require(tuple(row['path'] for row in config['sources']) == SOURCES
            and config['inputs'] == required_inputs(observation), 'Source/input epoch differs')
    require(not {row['path'] for row in config['sources']} & {row['path'] for row in config['inputs']}, 'Overlapping source/input pins')
    distributed_expected(proposal)


def names_list(value, *, nonempty=False):
    require(type(value) is list and (not nonempty or value) and len(value) <= 4096
            and all(type(name) is str and name and len(name) <= 512 and '\0' not in name for name in value)
            and value == sorted(set(value)), 'Bounded sorted distinct dispatch names required')


def paths(value):
    require(type(value) is list and len(value) <= 128 and all(text(item) for item in value), 'Bounded metadata paths required')


def validate_distributed_projection(value, expected):
    fields(value, ('kind', 'version', 'capture_point', 'stable', 'profile_accepted', 'runtime_qualified', 'modules'))
    require(value['kind'] == 'puck-cpu-distributed-exports-v1' and type(value['version']) is int and value['version'] == 1
            and value['capture_point'] == 'after_four_fixed_imports' and value['stable'] is True
            and value['profile_accepted'] is False and value['runtime_qualified'] is False
            and len(canonical(value)) <= 256 << 10, 'Complete stable terminal projection required')
    fields(expected, DISTRIBUTED)
    require(type(value['modules']) is list and len(value['modules']) == 3, 'Exactly three distributed children required')
    for name, row in zip(DISTRIBUTED, value['modules'], strict=True):
        names_list(expected[name], nonempty=True)
        fields(row, ('name', 'raw_attribute_identity', 'cache_identity', 'metadata', 'delegate_attributes', 'comparison'))
        require(row['name'] == name and row['raw_attribute_identity'] is True and row['cache_identity'] is True, 'Distributed child identity differs')
        metadata = row['metadata']; fields(metadata, ('name', 'module_type', 'file', 'package', 'loader_type', 'spec', 'path'))
        require(metadata['name'] == name and metadata['module_type'] == 'builtins.module'
                and text(metadata['file'], nullable=True) and text(metadata['package'], nullable=True)
                and text(metadata['loader_type'], 512, nullable=True), 'Distributed raw metadata differs')
        paths(metadata['path'])
        spec = metadata['spec']
        if spec is not None:
            fields(spec, ('name', 'origin', 'loader_type', 'submodule_search_locations'))
            require(text(spec['name'], 512, nullable=True) and text(spec['origin'], nullable=True)
                    and text(spec['loader_type'], 512, nullable=True), 'Distributed spec metadata differs')
            if spec['submodule_search_locations'] is not None: paths(spec['submodule_search_locations'])
        actual = row['delegate_attributes']; names_list(actual)
        comparison = row['comparison']; fields(comparison, ('expected', 'missing', 'extra', 'matches'))
        missing, extra = sorted(set(expected[name])-set(actual)), sorted(set(actual)-set(expected[name]))
        require(comparison['expected'] == expected[name] and comparison['missing'] == missing and comparison['extra'] == extra
                and comparison['matches'] is (not missing and not extra), 'Exact source-set comparison required')


def validate_cache(cache):
    fields(cache, ('modules', 'attribute_edges', 'module_objects', 'cache_entries', 'export_scope'))
    require(type(cache['modules']) is list and integer(cache['cache_entries'], 8192)
            and cache['cache_entries'] == len(cache['modules']) and integer(cache['attribute_edges'], 262144)
            and integer(cache['module_objects'], len(cache['modules']))
            and cache['export_scope'] == 'exceptional_cache_identities', 'Cache scope/bounds differ')
    names = []
    for row in cache['modules']:
        require(type(row) is dict and text(row.get('name'), 512) and row['name'], 'Cache row name required')
        names.append(row['name'])
        if row.get('classification') == 'nonmodule':
            fields(row, ('name', 'classification', 'type')); require(text(row['type'], 512), 'Nonmodule type required'); continue
        required = {'name', 'spec_name', 'file', 'classification', 'exports'}
        require(required <= set(row) <= required | {'spec_origin', 'type', 'spec_type', 'same_object_cache_names'}, 'Exact cache module fields required')
        require(text(row['spec_name'], 512, nullable=True) and text(row['file'], nullable=True), 'Cache module metadata bounds')
        classification = ('alias' if row['spec_name'] is not None and row['spec_name'] != row['name']
                          else 'virtual' if row['file'] is None and row['spec_name'] is None else 'module')
        require(row['classification'] == classification, 'Cache classification differs')
        for key in ('spec_origin', 'type', 'spec_type'):
            if key in row: require(text(row[key], 4096 if key == 'spec_origin' else 512, nullable=key == 'spec_origin'), 'Cache metadata text bounds')
        edges = row['exports']; require(type(edges) is list and len(edges) <= 262144, 'Cache export bounds')
        for edge in edges:
            fields(edge, ('producer', 'attribute')); require(text(edge['producer'], 512) and text(edge['attribute'], 512), 'Cache edge text bounds')
        tuples = [(edge['producer'], edge['attribute']) for edge in edges]
        require(tuples == sorted(set(tuples)), 'Sorted distinct cache exports required')
        if 'same_object_cache_names' in row:
            aliases = row['same_object_cache_names']; names_list(aliases, nonempty=True)
            require(len(aliases) >= 2 and row['name'] in aliases, 'Cache alias identity scope differs')
    require(names == sorted(set(names)), 'Sorted distinct cache rows required')


def validate_maps(value):
    fields(value, ('images', 'map_bytes', 'map_lines', 'persistent_snapshot_only', 'transient_anonymous_jit_closure_qualified'))
    require(integer(value['map_bytes'], 4 << 20) and integer(value['map_lines'], 65536)
            and type(value['images']) is list and len(value['images']) <= 65536
            and value['persistent_snapshot_only'] is True and value['transient_anonymous_jit_closure_qualified'] is False, 'Persistent map scope/bounds differ')
    keys = []; segments = 0
    for row in value['images']:
        fields(row, ('device', 'inode', 'path', 'segments', 'executable'))
        require(text(row['device'], 512) and text(row['path']) and row['path'].startswith('/')
                and integer(row['inode'], 2**64-1, 1) and integer(row['segments'], 65536, 1)
                and type(row['executable']) is bool, 'Mapped image metadata differs')
        keys.append((row['device'], row['inode'], row['path'])); segments += row['segments']
    require(keys == sorted(set(keys)) and segments <= value['map_lines'], 'Map order/count differs')


def validate_report(report, expected, request_sha, worker_sha):
    fields(report, set(FALSE) | {'kind', 'version', 'status', 'request_sha256', 'source_sha256', 'environment_sha256',
        'python_version', 'executable_path', 'pid', 'ppid', 'versions', 'imports', 'cache', 'maps', 'baseline_maps',
        'environment_delta', 'observation_errors', 'profile', 'expected_versions', 'pycache_prefix',
        'distributed_exports', 'observation_scope', 'seconds'})
    claims(report)
    require(report['kind'] == 'puck-runtime-import-characterization-result-v4' and type(report['version']) is int
            and report['version'] == 4 and report['profile'] == 'cpu-distributed-terminal-v1'
            and report['status'] == 'observed' and report['observation_scope'] == 'completed_imports'
            and report['request_sha256'] == request_sha and report['source_sha256'] == worker_sha
            and report['environment_sha256'] == hashlib.sha256(canonical(ENVIRONMENT)).hexdigest()
            and report['expected_versions'] == report['versions'] == VERSIONS
            and report['pycache_prefix'] == '/scratch/pycache' and report['environment_delta'] is None
            and report['observation_errors'] == [] and finite(report['seconds'], 180)
            and text(report['python_version']) and report['python_version'].startswith('3.11.15 ')
            and report['executable_path'] == PYTHON and integer(report['pid'], 2**31-1, 1)
            and integer(report['ppid'], 2**31-1) and len(canonical(report)) <= 1 << 20,
            'Complete four-import worker binding differs')
    rows = report['imports']; require(type(rows) is list and len(rows) == 4, 'Four import rows required')
    for name, row in zip(('numpy', 'torch', 'torchvision', 'mujoco'), rows, strict=True):
        fields(row, ('name', 'status', 'seconds', 'cache_entries'))
        require(row['name'] == name and row['status'] == 'observed' and finite(row['seconds'], 180)
                and integer(row['cache_entries'], 8192), 'Import order/status/bounds differ')
    validate_cache(report['cache']); validate_maps(report['maps']); validate_maps(report['baseline_maps'])
    validate_distributed_projection(report['distributed_exports'], expected)
    cache_rows = {row['name']: row for row in report['cache']['modules']}
    for name in ('torch', 'torch._C', *DISTRIBUTED):
        row = cache_rows.get(name)
        # describe_cache emits `type` only for a ModuleType subclass; the new
        # projection accepts exact ModuleType roots, so its rows must agree.
        require(row is not None and row['classification'] != 'nonmodule' and 'type' not in row,
                'Projection fixed roots must also be plain modules in cache')


def validate_transport(value, configuration, configuration_row):
    fields(value, set(FALSE) | {'kind', 'version', 'root', 'allocation_id', 'configuration', 'command', 'environment',
        'observed_returncode', 'elapsed_seconds', 'timed_out', 'parent_identity', 'sampled_identities',
        'sampled_survivors', 'sampled_cleanup_only', 'sampling_limitation', 'stdout', 'stderr'})
    claims(value)
    require(value['kind'] == 'puck-cpu-characterization-cli-transport-v1' and type(value['version']) is int
            and value['version'] == 1 and value['root'] == str(ROOT) and type(value['allocation_id']) is int
            and value['allocation_id'] == 3 and value['configuration'] == configuration_row
            and value['command'] == [PYTHON, '-I', '-S', '-B', str(ROOT/PARENT), '--configuration', str(configuration), '--sha256', configuration_row['sha256']]
            and value['environment'] == TRANSPORT_ENVIRONMENT and type(value['observed_returncode']) is int
            and value['observed_returncode'] == 0 and finite(value['elapsed_seconds'], 210)
            and value['timed_out'] is False and value['sampled_cleanup_only'] is True
            and value['sampled_survivors'] == [] and value['sampling_limitation'] == SAMPLING_LIMITATION,
            'Normal exact CLI transport required')
    rows = value['sampled_identities']; require(type(rows) is list and 1 <= len(rows) <= 64, 'Bounded sampled identities required')
    for row in [value['parent_identity'], *rows]:
        fields(row, ('pid', 'start_ticks'))
        require(integer(row['pid'], 2**31-1, 1) and integer(row['start_ticks'], 2**64-1, 1), 'PID/start identity required')
    require(len({(row['pid'], row['start_ticks']) for row in rows}) == len(rows)
            and value['parent_identity'] in rows, 'Unique sampled parent identity required')
    for name in ('stdout', 'stderr'):
        row = value[name]; fields(row, ('path', 'size_bytes', 'sha256'))
        require(row['path'] == OUTPUT+'-external-cli.'+name and integer(row['size_bytes'], 16 << 20)
                and type(row['sha256']) is str and len(row['sha256']) == 64
                and all(c in '0123456789abcdef' for c in row['sha256']), 'Bounded exact external stream pin required')


def verify_sampled_absence(identities):
    """Inspect only recorded lifetimes; neither signals nor a global census."""
    require(type(identities) is list and len(identities) <= 64, 'Bounded sampled identity close required')
    for identity in identities:
        fields(identity, ('pid', 'start_ticks'))
        require(integer(identity['pid'], 2**31-1, 1) and integer(identity['start_ticks'], 2**64-1, 1), 'Exact sampled lifetime required')
        try:
            fd = os.open('/proc/'+str(identity['pid'])+'/stat', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try: raw = os.read(fd, 4097)
            finally: os.close(fd)
        except (FileNotFoundError, ProcessLookupError):
            continue
        require(0 < len(raw) <= 4096, 'Bounded sampled process stat required')
        parts = raw[raw.rindex(b')')+2:].split()
        require(int(raw.split(b' ', 1)[0]) == identity['pid'] and len(parts) >= 20, 'Sampled process stat differs')
        require(int(parts[19]) != identity['start_ticks'], 'Sampled PID/start lifetime still exists')


def support():
    """Authenticate the complete immutable helper closure before any execution."""
    raw = []; stamps = []
    for row in SUPPORT:
        path = absolute(ROOT/row['path']); payload, stamp = initial_read(path, 1 << 20)
        require(len(payload) == row['size_bytes'] and hashlib.sha256(payload).hexdigest() == row['sha256'], 'Reviewed helper bytes differ')
        raw.append(payload); stamps.append(stamp)
    literal = b"HELPER = Path('/tmp/palimpsest_cpu_install_audit_v1.py')"
    require(raw[2].count(literal) == 1, 'Exact archived helper relocation literal required')
    adapted = [raw[0], raw[1], raw[2].replace(literal, ('HELPER = Path('+repr(str(ROOT/SUPPORT[1]['path']))+')').encode(), 1)]
    modules = []
    previous = sys.modules.get('palimpsest_cpu_install_audit_v1'); bytecode = sys.dont_write_bytecode
    try:
        for index in (1, 2, 0):
            row = SUPPORT[index]; name = 'palimpsest_cpu_install_audit_v1' if index == 1 else '_palimpsest_immutable_audit_'+str(index)
            module = types.ModuleType(name); module.__file__ = str(ROOT/row['path'])
            if index == 1: sys.modules[name] = module
            exec(compile(adapted[index], module.__file__, 'exec'), module.__dict__)
            modules.append((index, module))
    finally:
        sys.dont_write_bytecode = bytecode
        if previous is None: sys.modules.pop('palimpsest_cpu_install_audit_v1', None)
        else: sys.modules['palimpsest_cpu_install_audit_v1'] = previous
    values = dict(modules); p, a, r = values[0], values[1], values[2]; p.a, p.r = a, r
    for module in (p, a, r): module.BASE = ROOT
    p.RUN = ROOT/OUTPUT; r.RUN = ROOT/'runs/puck-cpu-retained-admission-02'
    attestations = []
    for index, row in enumerate(SUPPORT):
        path = ROOT/row['path']; p.remember(path, stamps[index])
        attestations.append(dict(path=row['path'], raw_sha256=row['sha256'], adapted_sha256=hashlib.sha256(adapted[index]).hexdigest()))
    return p, a, r, attestations


def namespace_command(baseline, native, request_sha, *, probe=False, parent_net=None):
    command = ['/usr/bin/bwrap', '--unshare-all', '--unshare-user', '--as-pid-1', '--disable-userns',
        '--die-with-parent', '--cap-drop', 'ALL', '--clearenv', '--hostname', 'palimpsest-cpu-observation',
        '--ro-bind', baseline['python_prefix'], baseline['python_prefix']]
    selected = {row['path'] for row in native['native_files']}
    selected.update(row.get('realpath') or row['path'] for row in baseline['external_libraries'])
    for path in sorted(selected): command += ['--ro-bind', path, path]
    aliases = dict(baseline['host_path_aliases'])
    for path, target in native['aliases']:
        require(path not in aliases or aliases[path] == target, 'Conflicting host aliases')
        aliases[path] = target
    for path, target in sorted(aliases.items(), key=lambda item: (item[0].count('/'), item[0])):
        command += ['--symlink', target, path]
    command += ['--ro-bind', str(ROOT/SITE), str(ROOT/SITE), '--ro-bind', str(ROOT/WORKER), '/driver.py',
        '--ro-bind', str(ROOT/OUTPUT/'request.json'), '/request.json', '--bind', str(ROOT/OUTPUT/'payload'), '/output',
        '--size', str(LIMITS['scratch_bytes']), '--tmpfs', '/scratch']
    for name in ('home', 'tmp', 'pycache'): command += ['--dir', '/scratch/'+name, '--chmod', '0700', '/scratch/'+name]
    command += ['--symlink', 'scratch/tmp', '/tmp', '--proc', '/proc', '--remount-ro', '/proc', '--dev', '/dev', '--remount-ro', '/dev', '--remount-ro', '/']
    for key, value in ENVIRONMENT.items(): command += ['--setenv', key, value]
    command += ['--chdir', '/scratch', PYTHON, '-I', '-S', '-B', '-X', 'pycache_prefix=/scratch/pycache']
    return command + (['-c', PROBE, parent_net or os.readlink('/proc/self/ns/net'), str(ROOT/SITE), str(ROOT/'docs')]
                      if probe else ['/driver.py', '/request.json', request_sha])


def decode(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'Duplicate JSON field'); value[key] = item
        return value
    def constant(value):
        raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def initial_read(path, maximum):
    path = absolute(path); fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    stamp = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= maximum, 'Bounded single-link audit data required')
        with os.fdopen(os.dup(fd), 'rb') as stream: raw = stream.read(maximum+1)
        require(len(raw) == before.st_size and stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat()), 'Audit data changed while read')
        return raw, stamp(before)
    finally:
        os.close(fd)


def validate_closure(closure):
    fields(closure, ('active_children', 'active_non_main_threads', 'all_handles_closed', 'all_receipts_fsynced', 'fd_count_before', 'fd_count_after'))
    require(closure['active_children'] == closure['active_non_main_threads'] == []
            and closure['all_handles_closed'] is True and closure['all_receipts_fsynced'] is True
            and integer(closure['fd_count_before'], 40000) and type(closure['fd_count_after']) is int
            and closure['fd_count_before'] == closure['fd_count_after'], 'Normal parent closure required')


def validate_parent(result, configuration_sha, report_sha, *, historical=False):
    fields(result, set(FALSE) | {'kind', 'status', 'configuration_sha256', 'report_sha256', 'versions',
        'namespace_probe_completed', 'worker_supervision_status', 'accepted_package_preparation_preserved',
        'closure', 'elapsed_seconds', 'sampled_parent_peak_rss_bytes'})
    claims(result)
    require(result['kind'] == 'puck-cpu-characterization-outcome-v'+('1' if historical else '2')
            and result['status'] == 'observed' and result['configuration_sha256'] == configuration_sha
            and result['report_sha256'] == report_sha and result['versions'] == VERSIONS
            and result['namespace_probe_completed'] is True and result['worker_supervision_status'] == 'completed'
            and result['accepted_package_preparation_preserved'] is True and finite(result['elapsed_seconds'], 180)
            and integer(result['sampled_parent_peak_rss_bytes'], LIMITS['rss_bytes']), 'Parent observation binding differs')
    validate_closure(result['closure'])


def validate_observation02(config, result, report, audit, index, terminal, pins):
    for row in required_inputs(config): require(pins.get(row['path']) == row, 'Historical02 input pin differs')
    sha = OBSERVATION_PINS['observation_configuration']['sha256']; report_sha = OBSERVATION_PINS['observation_report']['sha256']
    validate_parent(result, sha, report_sha, historical=True); claims(report); claims(audit)
    require(report.get('kind') == 'puck-runtime-import-characterization-result-v3'
            and type(report.get('version')) is int and report['version'] == 3
            and report.get('profile') == 'cpu-four-imports-v1' and report.get('status') == 'observed'
            and report.get('versions') == report.get('expected_versions') == VERSIONS
            and report.get('observation_errors') == [] and report.get('environment_delta') is None
            and report.get('observation_scope') == 'completed_imports' and 'error' not in report,
            'Historical02 completed import scope differs')
    verified = audit.get('verified', {})
    require(audit.get('kind') == 'cpu-characterization-independent-outcome-audit-v2' and audit.get('status') == 'PASS'
            and audit.get('expected_outcome') == 'success' and type(audit.get('caller_supplied_observed_parent_exit_code')) is int
            and audit['caller_supplied_observed_parent_exit_code'] == 0 and audit.get('ordinary_imports_observed') is True
            and audit.get('native_qualified') is False and audit.get('target_code_executed_by_auditor') is False
            and all(verified.get(key) == value for key, value in dict(configuration_sha256=sha, report_sha256=report_sha,
                result_sha256=OBSERVATION_PINS['observation_result']['sha256'], source_pins=14, input_pins=42,
                accepted_source_capsules=16, prior_source_capsules=14, parent_status='observed', worker_status='observed',
                worker_returncode=0, baseline_after_present=True).items()), 'Historical02 audit binding differs')
    require(index.get('kind') == 'cpu-characterization-evidence-index-v2' and index.get('actual_retry_performed') is False
            and index.get('original_output') == 'runs/puck-cpu-runtime-characterization-02'
            and terminal.get('kind') == 'cpu-characterization-external-terminal-observations-v2'
            and terminal.get('configuration_sha256') == sha and terminal.get('actual_retry_performed') is False
            and type(terminal.get('actual', {}).get('exit_code')) is int and terminal['actual']['exit_code'] == 0
            and terminal.get('outcome_audit', {}).get('status') == 'PASS'
            and type(terminal['outcome_audit'].get('exit_code')) is int and terminal['outcome_audit']['exit_code'] == 0,
            'Historical02 index/terminal scope differs')


def prefix_inventory(prefix, p, a):
    require(prefix.is_absolute() and prefix.resolve(strict=True) == prefix and stat.S_ISDIR(prefix.lstat().st_mode), 'Real trusted prefix required')
    files, links, total = [], [], 0
    for directory, directories, names in os.walk(prefix, followlinks=False):
        p.remember(Path(directory), a.fingerprint(Path(directory).lstat()))
        for name in sorted([*directories, *names]):
            path = Path(directory)/name; info = path.lstat(); relative_name = relative(path.relative_to(prefix).as_posix())
            if stat.S_ISLNK(info.st_mode):
                require(path.resolve(strict=True).is_relative_to(prefix), 'Trusted prefix symlink leaves prefix')
                links.append([relative_name, os.readlink(path)]); p.remember(path, a.fingerprint(info))
                if name in directories: directories.remove(name)
            elif stat.S_ISREG(info.st_mode):
                row, stamp = a.hash_file(path, 64 << 20, single_link=False); p.remember(path, stamp)
                total += row['size_bytes']; files.append([relative_name, row['size_bytes'], row['sha256']])
            else: require(stat.S_ISDIR(info.st_mode), 'Special file in trusted prefix')
            require(len(files)+len(links) <= 10000 and total <= 256 << 20, 'Trusted prefix bounds exceeded')
    value = dict(files=sorted(files), symlinks=sorted(links))
    value['prefix_manifest_sha256'] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return value


def audit(configuration, sha256, transport, transport_sha256):
    configuration = absolute(configuration); transport = absolute(transport)
    require(transport == ROOT/(OUTPUT+'-external-cli-transport.json'), 'Exact observation03 transport path required')
    initial = {}
    def checked(path, maximum=32 << 20, expected=None):
        raw, stamp = initial_read(path, maximum); initial[path] = stamp
        if expected is not None:
            require(len(raw) == expected['size_bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], 'Pinned audit bytes differ: '+str(path))
        return raw
    def json_at(path, maximum=32 << 20): return decode(checked(path, maximum))
    raw = checked(configuration, 1 << 20); config = decode(raw)
    require(hashlib.sha256(raw).hexdigest() == sha256
            and raw == (json.dumps(config, sort_keys=True, indent=2, allow_nan=False)+'\n').encode(), 'Frozen configuration bytes differ')
    observation = decode(checked(ROOT/OBSERVATION_PINS['observation_configuration']['path'], 1 << 20, OBSERVATION_PINS['observation_configuration']))
    proposal = decode(checked(ROOT/PROPOSAL_PIN['path'], 1 << 20, PROPOSAL_PIN))
    validate_configuration(config, observation, proposal)
    pins = {}
    for row in config['sources']+config['inputs']:
        require(row['path'] not in pins, 'Duplicate source/input pin')
        checked(ROOT/row['path'], 32 << 20, row); pins[row['path']] = row
    p, a, r, helper_attestations = support()
    for path, stamp in initial.items(): p.remember(path, stamp)
    def read(path, maximum=32 << 20): return p.read(path, maximum)
    def load_data(path, maximum=32 << 20): return decode(read(path, maximum))
    def get(role): return load_data(ROOT/config['roles'][role])
    run = ROOT/OUTPUT
    require(read(run/'configuration.json', 1 << 20) == canonical(config), 'Published configuration differs')
    old_values = [get(role) for role in ('observation_result', 'observation_report', 'observation_audit', 'observation_index', 'observation_terminal')]
    validate_observation02(observation, *old_values, pins)
    index = old_values[3]; entries = index.get('entries')
    require(type(entries) is list and 1 <= len(entries) <= 512 and type(index.get('file_count')) is int
            and index['file_count'] == len(entries), 'Bounded historical evidence index required')
    pin_rows(entries, len(entries))
    require(index.get('total_bytes') == sum(row['size_bytes'] for row in entries), 'Historical index byte total differs')
    for row in entries: p.hashed(ROOT/ARCHIVE/row['path'], {key: row[key] for key in ('size_bytes', 'sha256')})
    accepted, old, proof, snapshot = (get(role) for role in ('accepted_configuration', 'accepted_result', 'accepted_audit', 'accepted_snapshot'))
    require(pins[ROLES['accepted_configuration']]['sha256'] == ACCEPTED_SHA and old['status'] == proof['status'] == 'PASS'
            and old['claims']['package_preparation_accepted'] is proof['package_preparation_accepted'] is True
            and old['configuration_sha256'] == proof['verified']['configuration_sha256'] == ACCEPTED_SHA
            and old['snapshot_sha256'] == pins[ROLES['accepted_snapshot']]['sha256'], 'Accepted preparation binding differs')
    for key in ('runtime_qualified', 'numerical_imports_executed', 'study_authorized', 'collection_authorized'):
        require(old['claims'][key] is proof[key] is False, 'Package preparation overclaims authority')
    prior_config, prior_result, prior_audit = (get(role) for role in ('prior_configuration', 'prior_result', 'prior_audit'))
    for role, digest in zip(('prior_configuration', 'prior_result', 'prior_audit'), PRIOR_SHAS, strict=True):
        require(pins[ROLES[role]]['sha256'] == digest, 'Historical01 identity differs')
    claims(prior_result); claims(prior_audit)
    require(prior_result['status'] == 'FAIL' and prior_audit['status'] == 'PRESERVED_FAILURE_VERIFIED'
            and prior_audit['ordinary_imports_observed'] is False and prior_audit['native_qualified'] is False
            and prior_result['configuration_sha256'] == PRIOR_SHAS[0], 'Historical01 failure scope differs')
    require(len(accepted['sources']) == 16 and len(prior_config['sources']) == 14, 'Historical source capsule counts differ')
    required = set(OLD_ROLES.values())
    for value, archive in ((accepted, ACCEPTANCE), (prior_config, PRIOR)):
        for row in value['sources']:
            path = archive+'/source/'+relative(row['path']); required.add(path)
            require(path in pins and all(pins[path][key] == row[key] for key in ('size_bytes', 'sha256')), 'Historical source capsule differs')
    require(required == {row['path'] for row in observation['inputs']}, 'Historical42 input boundary differs')
    inventory, layout, native, baseline = (get(role) for role in ('inventory', 'layout', 'native_metadata', 'baseline'))
    site = ROOT/SITE; actual, directories, stamps = r.census(site)
    require(actual == r.rows_to_map(inventory['entries']) and directories == set(layout['predicted_destination_directories'])
            and snapshot['site_root'] == str(site) and (len(actual), len(directories), sum(row['size_bytes'] for row in actual.values())) == SITE_COUNTS,
            'Complete accepted SITE differs')
    require(pins[ROLES['native_metadata']]['sha256'] == NATIVE_SHA and native['kind'] == 'puck-cpu-characterization-native-metadata-v5'
            and native['status'] == 'COMPLETE' and native['root_scope'] == 'installed_shared_objects_and_interpreter'
            and native['required_missing_names'] == native['errors'] == native['oversized_native_files'] == []
            and (len(native['native_files']), len(native['aliases']), native['system_ELF_count_including_prefix'],
                 len([row for row in native['dependency_edges'] if row.get('needed') == 'libz.so.1'])) == NATIVE_COUNTS
            and any(row['needed'] == 'libcrypt.so.1' for row in native['optional_prefix_missing']), 'Native05 source/closure differs')
    for key in ('numerical_imports_executed', 'target_execution_performed', 'runtime_qualified', 'renderer_qualified'):
        require(native[key] is False, 'Static native metadata overclaims execution')
    for row in native['native_files']:
        require(type(row['path']) is str and (row['path'].startswith('/usr/lib/') or row['path'] in ('/usr/bin/ldconfig', '/etc/ld.so.cache'))
                and str(Path(row['path'])) == row['path'] and '..' not in Path(row['path']).parts, 'Selected native path differs')
        p.hashed(Path(row['path']), {key: row[key] for key in ('size_bytes', 'sha256')}, single_link=False, limit=64 << 20)
    for filename, target in native['aliases']+baseline['host_path_aliases']:
        path = Path(filename); info = path.lstat()
        require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == target, 'Native/host alias changed'); p.remember(path, a.fingerprint(info))
    for row in baseline['external_libraries']+[baseline['bwrap_executable']]:
        p.hashed(Path(row.get('realpath') or row['path']), dict(size_bytes=row['size'], sha256=row['sha256']), single_link=False, limit=64 << 20)
    prefix = prefix_inventory(Path(baseline['python_prefix']), p, a)
    require(all(prefix[key] == baseline[key] for key in prefix)
            and (len(prefix['files']), len(prefix['symlinks'])) == BASELINE_COUNTS, 'Complete trusted Python prefix differs')
    summary = dict(prefix_manifest_sha256=prefix['prefix_manifest_sha256'], regular_file_count=len(prefix['files']),
        symlink_count=len(prefix['symlinks']), regular_file_bytes=sum(row[1] for row in prefix['files']), external_file_count=len(baseline['external_libraries'])+1)
    require(load_data(run/'baseline-before.json') == summary == load_data(run/'baseline-after.json'), 'Baseline pre/post receipts differ')
    namespace = dict(kind='cpu-characterization-namespace-v1', network_isolated=True, site_readonly=True, project_hidden=True, private_pycache_empty=True)
    require(load_data(run/'namespace.json') == namespace == load_data(run/'probe-logs/stdout.log', 8 << 20), 'Namespace probe receipt differs')
    expected = distributed_expected(proposal)
    request_raw = read(run/'request.json', 65536); request = decode(request_raw); request_sha = hashlib.sha256(request_raw).hexdigest()
    require(request_raw == canonical(request) and request == dict(kind='puck-runtime-import-characterization-v3', version=3,
        site_root=str(site), output_root='/output', environment=ENVIRONMENT, expected_versions=VERSIONS,
        pycache_prefix='/scratch/pycache', distributed_expected=expected), 'Exact v3 request binding differs')
    for name in ('probe', 'worker'):
        supervision = load_data(run/(name+'-supervision.json'))
        fields(supervision, ('failure', 'finished_monotonic', 'matching_survivors', 'pid', 'returncode', 'rss_sampling_seconds', 'sampled_peak_rss_bytes', 'status'))
        require(supervision['status'] == 'completed' and type(supervision['returncode']) is int and supervision['returncode'] == 0
                and supervision['failure'] is None and supervision['matching_survivors'] == [] and supervision['rss_sampling_seconds'] == .05
                and integer(supervision['sampled_peak_rss_bytes'], LIMITS['rss_bytes']) and integer(supervision['pid'], 2**31-1, 1)
                and finite(supervision['finished_monotonic'], 1e12), 'Normal child supervision required')
        invocation = load_data(run/(name+'-invocation.json')); fields(invocation, ('command', 'configuration_sha256'))
        require(invocation['configuration_sha256'] == sha256
                and invocation['command'] == namespace_command(baseline, native, request_sha, probe=name == 'probe'), 'Full namespace argv differs')
        for leaf in ('stdout.log', 'stderr.log'): read(run/(name+'-logs')/leaf, 8 << 20)
    report_raw = read(run/'payload/imports.json', 1 << 20); report = decode(report_raw)
    require(report_raw == canonical(report), 'Canonical complete worker report required')
    validate_report(report, expected, request_sha, pins[WORKER]['sha256']); report_sha = hashlib.sha256(report_raw).hexdigest()
    require(load_data(run/'worker-logs/stdout.log', 8 << 20) == dict(report_sha256=report_sha, report_bytes=len(report_raw), status='observed'), 'Worker publication receipt differs')
    result_raw = read(run/'result.json', 1 << 20); result = decode(result_raw)
    require(result_raw == canonical(result), 'Canonical parent outcome required'); validate_parent(result, sha256, report_sha)
    transport_raw = read(transport, 65536); observed = decode(transport_raw)
    require(hashlib.sha256(transport_raw).hexdigest() == transport_sha256
            and transport_raw == (json.dumps(observed, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode(), 'Authenticated canonical transport required')
    configuration_row = dict(path=configuration.relative_to(ROOT).as_posix(), size_bytes=len(raw), sha256=sha256)
    validate_transport(observed, configuration, configuration_row)
    for name in ('stdout', 'stderr'):
        row = observed[name]; path = ROOT/row['path']; payload = read(path, 16 << 20)
        require(stat.S_IMODE(path.lstat().st_mode) == 0o600 and path.lstat().st_uid == os.geteuid()
                and len(payload) == row['size_bytes'] and hashlib.sha256(payload).hexdigest() == row['sha256'], 'External raw stream bytes differ')
        if name == 'stdout': require(decode(payload) == result, 'Observed parent stdout differs from saved outcome')
    require(stat.S_IMODE(transport.lstat().st_mode) == 0o600, 'Private external transport required')
    missing = [ROOT/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation, leaves in (('puck-cpu-install-01', ('inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json')),
                               ('puck-cpu-retained-admission-01', ('inventory.json', 'snapshot.json', 'baseline-after.json'))):
        missing.extend(ROOT/'runs'/allocation/leaf for leaf in leaves)
    require(all(not os.path.lexists(path) for path in missing), 'Historical missing receipt filled')
    for path, digest in (('runs/puck-cpu-install-01/result.json', r.ORIGINAL_SHA), ('runs/puck-cpu-retained-admission-01/result.json', r.PRIOR_ADMISSION_SHA)):
        payload = read(ROOT/path); require(hashlib.sha256(payload).hexdigest() == digest and decode(payload)['status'] == 'FAIL', 'Original failed outcome changed')
    _, after_dirs, after_stamps = r.census(site, hashes=False)
    require(after_dirs == directories and after_stamps == stamps, 'SITE fingerprints changed during audit')
    for path, stamp in p.STAMPS.items(): require(a.fingerprint(path.lstat()) == stamp, 'Input/receipt changed during audit: '+str(path))
    require(all(not os.path.lexists(path) for path in missing), 'Historical absence changed during audit')
    verify_sampled_absence(observed['sampled_identities'])
    return dict(configuration_sha256=sha256, transport_sha256=transport_sha256, report_sha256=report_sha,
        result_sha256=hashlib.sha256(result_raw).hexdigest(), source_pins=19, input_pins=63, roles=19,
        accepted_source_capsules=16, prior_source_capsules=14, observation_source_capsules=14,
        site_file_count=len(actual), site_directory_count=len(directories), site_regular_file_bytes=SITE_COUNTS[2],
        native_files=len(native['native_files']), native_aliases=len(native['aliases']), baseline_declared_files=BASELINE_COUNTS[0],
        baseline_declared_symlinks=BASELINE_COUNTS[1], full_baseline_namespace_recensused=True,
        old_missing_receipts=len(missing), receipt_fingerprints=len(p.STAMPS), helper_sources=helper_attestations,
        distributed_targets=list(DISTRIBUTED), distributed_terminal_stable=True,
        distributed_comparisons={row['name']: row['comparison'] for row in report['distributed_exports']['modules']},
        profile_accepted=False, sampled_cleanup_only=True, sampling_limitation=SAMPLING_LIMITATION,
        scope='ordinary fixed imports and terminal snapshots only; no lifecycle, held, native, renderer or study qualification')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True); parser.add_argument('--sha256', required=True)
    parser.add_argument('--transport', required=True); parser.add_argument('--transport-sha256', required=True)
    args = parser.parse_args(); started = time.monotonic()
    report = dict(FALSE, kind='cpu-characterization-independent-audit-v3', status='FAIL', ordinary_imports_observed=False,
                  native_qualified=False, target_code_executed_by_auditor=False)
    def expired(signum, frame): raise TimeoutError('180-second independent observation audit deadline')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        require(Path(sys.executable).resolve() == Path(PYTHON) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
                and not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_LIBRARY_PATH'), 'Original isolated audit interpreter required')
        for digest in (args.sha256, args.transport_sha256):
            require(len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'Explicit lowercase audit SHA required')
        report['verified'] = audit(args.configuration, args.sha256, args.transport, args.transport_sha256)
        require(finite(time.monotonic()-started, 180), 'Late independent audit')
        report.update(status='PASS', ordinary_imports_observed=True)
    except Exception as error:
        report['error'] = type(error).__name__+': '+str(error)[:2048]
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    report['elapsed_seconds'] = time.monotonic()-started
    print(canonical(report).decode(), end='', flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
