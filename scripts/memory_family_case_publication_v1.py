"""Pure accepted supervisor-attestation validation; no publication or execution.

Callers supply already validated terminal contracts and continuously held control
bytes. This function neither opens evidence nor grants custody/qualification.
"""
from __future__ import annotations
import copy
import hashlib
from pathlib import PurePosixPath
import re
import uuid
from palimpsest import artifacts, memory
from scripts import memory_family_analysis_v3 as analysis
from scripts import memory_family_compact_v4 as compact
from scripts import memory_case_execution_pins_v1 as pins

CONDITIONS = tuple(compact.PROTOCOL['analysis_contract']['conditions'])
AUDIT_KEYS = set('schema publication_protocol_sha256 case_slot source_commit condition_commits observer owners claims'.split())
OBSERVER_KEYS = set('source_sha256 qualification_sha256 boot_id pid_namespace clock ticks_per_second'.split())
OWNER_KEYS = set('operation condition run_id registration job owner supervisor cleanup commit pid starttime pgid launch_ns reaped_ns drained_ns returncode status'.split())
SUPERVISOR_KEYS = set('schema case_id run_id operation condition observer job pid starttime pgid launch_ns reaped_ns drained_ns returncode status'.split())
CLEANUP_KEYS = set('schema case_id run_id operation condition observer job pid starttime pgid drained_ns status'.split())
MAX_BYTES = 32 * 1024 * 1024


def _fields(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f'{label} has missing or unknown fields')


def _integer(value, minimum, label):
    if type(value) is not int or value < minimum:
        raise ValueError(f'Invalid {label}')


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Invalid SHA-256')


def _run_id(value):
    if type(value) is not str:
        raise ValueError('Invalid run ID')
    try:
        if uuid.UUID(value).hex != value: raise ValueError('Noncanonical run ID')
    except (ValueError, AttributeError) as error:
        raise ValueError('Invalid run ID') from error


def _descriptor(value):
    _fields(value, ('path', 'size_bytes', 'sha256'), 'Descriptor')
    path = value['path']
    if (type(path) is not str or not path or path.startswith('/') or '\\' in path
            or PurePosixPath(path).as_posix() != path or any(p in ('', '.', '..') for p in path.split('/'))):
        raise ValueError('Noncanonical relative descriptor path')
    _integer(value['size_bytes'], 0, 'descriptor size')
    _digest(value['sha256'])


def _equal(left, right, label):
    if memory.canonical_bytes(left) != memory.canonical_bytes(right):
        raise ValueError(f'{label} differs')


def _payload(descriptor, controls):
    _descriptor(descriptor)
    if descriptor['size_bytes'] > compact.MiB: raise ValueError('Control payload exceeds bound')
    payload = controls[descriptor['path']]
    if (type(payload) is not bytes or len(payload) != descriptor['size_bytes']
            or hashlib.sha256(payload).hexdigest() != descriptor['sha256']):
        raise ValueError('Held control bytes differ from descriptor')
    return payload


def _canonical(descriptor, controls, keys, label):
    payload = _payload(descriptor, controls)
    obj = artifacts._json(payload)
    _fields(obj, keys, label)
    if memory.canonical_bytes(obj) != payload: raise ValueError(f'{label} is not canonical JSON')
    return obj


def _require_execution_pin(audit):
    payload = memory.canonical_bytes(audit)
    if len(payload) > MAX_BYTES: raise ValueError('Execution audit exceeds combined case-file allowance')
    digest = hashlib.sha256(payload).hexdigest()
    if digest not in pins.ACCEPTED_EXECUTION_AUDIT_SHA256:
        raise PermissionError('Execution audit has no independently accepted pin')


def validate_execution_audit(audit, *, case_slot, source_commit, condition_commits,
                             contracts, control_payloads, publication_protocol_sha256):
    """Validate a pinned attestation against supplied contracts and held bytes.

    Trust admission precedes any access/copy of protected contracts or controls.
    Returned data is a deep copy and carries no live custody or authority.
    """
    audit = copy.deepcopy(audit)
    _require_execution_pin(audit)
    slot, source_commit, commits, contracts, controls = copy.deepcopy(
        (case_slot, source_commit, condition_commits, contracts, control_payloads))
    _fields(audit, AUDIT_KEYS, 'Execution audit')
    if audit['schema'] != 'memory-family-case-execution-audit-v1': raise ValueError('Old execution schema')
    _digest(publication_protocol_sha256)
    _equal(audit['publication_protocol_sha256'], publication_protocol_sha256, 'Publication protocol')
    _equal(audit['case_slot'], slot, 'Case slot')
    _fields(slot, ('case_id', 'case_sha256', 'source_run_id', 'condition_run_ids'), 'Case slot')
    memory._id(slot['case_id']); _digest(slot['case_sha256'])
    _fields(slot['condition_run_ids'], CONDITIONS, 'Condition run IDs')
    ids = [slot['source_run_id'], *slot['condition_run_ids'].values()]
    for run in ids: _run_id(run)
    if len(set(ids)) != 10: raise ValueError('Run identities overlap')
    _fields(commits, CONDITIONS, 'Condition commits')
    _fields(contracts, ('source', *CONDITIONS), 'Terminal contracts')
    _descriptor(source_commit)
    for value in commits.values(): _descriptor(value)
    _equal(audit['source_commit'], source_commit, 'Source commit')
    _equal(audit['condition_commits'], commits, 'Condition commits')
    _equal(audit['claims'], compact.PROTOCOL['claims'], 'All-false claims')
    observer = audit['observer']; _fields(observer, OBSERVER_KEYS, 'Observer')
    _digest(observer['source_sha256']); _digest(observer['qualification_sha256'])
    try:
        if str(uuid.UUID(observer['boot_id'])) != observer['boot_id']: raise ValueError('Noncanonical boot ID')
    except (ValueError, TypeError, AttributeError) as error: raise ValueError('Invalid observer boot ID') from error
    if type(observer['pid_namespace']) is not str or re.fullmatch(r'pid:\[[1-9][0-9]*\]',observer['pid_namespace']) is None:
        raise ValueError('Invalid PID namespace')
    if observer['clock'] != 'CLOCK_BOOTTIME': raise ValueError('Invalid observer clock')
    _integer(observer['ticks_per_second'], 1, 'tick frequency')
    row = contracts['own']['case']['row']
    order = analysis.condition_order(row)
    if order.index('own') > order.index('oracle'): raise ValueError('Registered order conflicts with prior-own')
    owners = audit['owners']
    if type(owners) is not list or len(owners) != 10: raise ValueError('Exactly ten owners required')
    identities = set(); previous = None; descriptors = set()
    for name, owner in zip(('source', *order), owners):
        _fields(owner, OWNER_KEYS, 'Owner attestation')
        condition = None if name == 'source' else name
        operation = 'source' if condition is None else 'condition'
        run = slot['source_run_id'] if condition is None else slot['condition_run_ids'][name]
        contract = contracts[name]
        if (owner['operation'] != operation or owner['condition'] != condition or owner['run_id'] != run):
            raise ValueError('Owner order/identity differs from registration')
        _equal(contract['case'], contracts['own']['case'], 'Shared case')
        if contract['case']['case_id'] != slot['case_id'] or contract['case']['case_sha256'] != slot['case_sha256'] or contract['run_id'] != run:
            raise ValueError('Terminal contract differs from case slot')
        expected_commit = source_commit if condition is None else commits[name]
        _equal(owner['commit'], expected_commit, 'Expected commit')
        for role in ('registration','job','owner','supervisor','cleanup','commit'):
            _descriptor(owner[role])
            if owner[role]['path'] in descriptors: raise ValueError('Repeated descriptor path')
            descriptors.add(owner[role]['path'])
        registration_bytes = _payload(owner['registration'], controls)
        if registration_bytes != memory.canonical_bytes(contract): raise ValueError('Terminal export bytes differ')
        for role in ('job','supervisor','cleanup'):
            _equal(owner[role], contract['controls'][role], f'{role} control descriptor')
            _payload(owner[role], controls)
        _equal(owner['owner'], contract['owner_record'], 'Owner record descriptor')
        source_fields = {'schema','case_id','run_id','owner_source_sha256','claims'}
        owner_fields = source_fields if condition is None else source_fields | {'condition','source_run_id'}
        record = _canonical(owner['owner'], controls, owner_fields, 'Compact owner record')
        expected = dict(schema='memory-family-source-owner-v4' if condition is None else 'memory-family-condition-owner-v1',
            case_id=slot['case_id'],run_id=run,owner_source_sha256=contract['owner_source_sha256'],claims=compact.PROTOCOL['claims'])
        if condition is not None: expected.update(condition=condition,source_run_id=slot['source_run_id'])
        _equal(record, expected, 'Compact owner identities')
        for key in ('pid','starttime','pgid'): _integer(owner[key],1,key)
        for key in ('launch_ns','reaped_ns','drained_ns'): _integer(owner[key],0,key)
        if owner['pid'] != owner['pgid']: raise ValueError('Owner PID must equal PGID')
        identity = owner['pid'], owner['starttime']
        if identity in identities: raise ValueError('Reused process identity')
        identities.add(identity)
        if type(owner['returncode']) is not int or owner['returncode'] != 0 or owner['status'] != 'completed':
            raise ValueError('Owner did not complete normally')
        if not owner['launch_ns'] <= owner['reaped_ns'] <= owner['drained_ns']:
            raise ValueError('Invalid owner lifetime')
        if previous is not None and previous > owner['launch_ns']: raise ValueError('Overlapping owners')
        previous = owner['drained_ns']
        ticks = observer['ticks_per_second']; start = owner['starttime']
        if owner['launch_ns']*ticks > (start+1)*10**9 or (start-1)*10**9 > owner['reaped_ns']*ticks:
            raise ValueError('Starttime is outside launch/reap bracket')
        supervisor = _canonical(owner['supervisor'], controls, SUPERVISOR_KEYS, 'Supervisor')
        expected = {k:owner[k] for k in SUPERVISOR_KEYS - {'schema','case_id','observer'}}
        expected.update(schema='memory-family-order-supervisor-v1',case_id=slot['case_id'],observer=observer)
        _equal(supervisor,expected,'Prospective supervisor')
        cleanup = _canonical(owner['cleanup'], controls, CLEANUP_KEYS, 'Cleanup')
        expected = {k:owner[k] for k in CLEANUP_KEYS - {'schema','case_id','observer','status'}}
        expected.update(schema='memory-family-order-cleanup-v1',case_id=slot['case_id'],observer=observer,status='drained')
        _equal(cleanup,expected,'Prospective cleanup')
    _require_execution_pin(audit)
    return copy.deepcopy(audit)


# Policy files are independently read, held and rechecked. Neither belongs to
# the accepted audit's behavior-source closure.
EXECUTION_POLICY_PATH = 'scripts/memory_case_execution_pins_v1.py'
QUALIFICATION_POLICY_PATH = 'scripts/memory_condition_qualification_pins_v1.py'
PUBLICATION_PATH = 'docs/plans/memory-case-publication-v1-protocol.json'


def _policy_assignment(payload, name):
    """Read one constant assignment without executing policy source bytes."""
    import ast
    tree = ast.parse(payload)
    matches = [node.value for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == name
                       for target in node.targets)]
    if len(matches) != 1:
        raise ValueError('Acceptance policy must have one named assignment')
    value = matches[0]
    if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id == 'frozenset' and not value.keywords
            and len(value.args) <= 1):
        return frozenset() if not value.args else frozenset(ast.literal_eval(value.args[0]))
    return ast.literal_eval(value)


def _read_acceptance_policy(lifetime, audit, deadline):
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    values = {}
    for path, name in ((EXECUTION_POLICY_PATH, 'ACCEPTED_EXECUTION_AUDIT_SHA256'),
                       (QUALIFICATION_POLICY_PATH, 'TRUSTED_QUALIFICATION_PINS')):
        payload = artifacts._read(compact.ROOT / path, compact.MiB)
        descriptor = source._descriptor(path, payload)
        _, held, check = seal._bind(lifetime, compact.ROOT, descriptor, compact.MiB, deadline)
        values[name] = _policy_assignment(held, name)
        lifetime.callback(check)
    digest = hashlib.sha256(memory.canonical_bytes(audit)).hexdigest()
    if digest not in values['ACCEPTED_EXECUTION_AUDIT_SHA256']:
        raise PermissionError('No independently accepted execution policy pin')
    return values


def publish_retained_case(evidence_root, registrations, *, case_slot,
                          condition_commits, execution_audit, deadline):
    """Publish one admitted retained case; empty real anchors refuse all writes.

    The final marker is registerable only after successful durable publication
    and descriptor teardown. Returned retained values confer no future custody.
    """
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    source.audit._public_deadline(deadline)
    execution_audit = copy.deepcopy(execution_audit)
    _require_execution_pin(execution_audit)
    with seal._ValidatingStack() as policy_lifetime:
        policy = _read_acceptance_policy(policy_lifetime, execution_audit, deadline)
        # Protected caller objects and all case files follow both policy gates.
        registrations, slot, commits = copy.deepcopy((registrations, case_slot, condition_commits))
        return _publish_admitted_case(evidence_root, registrations, slot, commits,
                                      execution_audit, deadline, policy, policy_lifetime)


MANIFEST_KEYS = set('analysis_cells case_id claims condition_run_ids protocol_sha256 run_receipts schema snapshot source_run_id'.split())
CLOSE_KEYS = set('schema protocol_sha256 publication_protocol_sha256 case_id manifest execution_audit retained_inventory retained_directories retained_bytes claims'.split())
COMMIT_KEYS = set('schema protocol_sha256 publication_protocol_sha256 case_id manifest close claims'.split())
PUBLICATION_BOUNDS = dict(retained_files=418, retained_directories=33,
                          case_files=3, case_file_bytes=MAX_BYTES, final_entries=454)
PUBLICATION_SCHEMAS = {
    'manifest': {'schema': 'memory-family-compact-case-v1', 'keys': sorted(MANIFEST_KEYS)},
    'close': {'schema': 'memory-family-case-close-v1', 'keys': sorted(CLOSE_KEYS)},
    'commit': {'schema': 'memory-family-case-commit-v1', 'keys': sorted(COMMIT_KEYS)},
    'execution_audit': {'schema': 'memory-family-case-execution-audit-v1', 'keys': sorted(AUDIT_KEYS)},
    'observer': {'keys': sorted(OBSERVER_KEYS)},
    'owner': {'keys': sorted(OWNER_KEYS)},
    'supervisor': {'schema': 'memory-family-order-supervisor-v1', 'keys': sorted(SUPERVISOR_KEYS)},
    'cleanup': {'schema': 'memory-family-order-cleanup-v1', 'keys': sorted(CLEANUP_KEYS)},
}


def _publication_profile(lifetime, deadline):
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    payload = artifacts._read(compact.ROOT / PUBLICATION_PATH, compact.MiB)
    descriptor = source._descriptor(PUBLICATION_PATH, payload)
    _, payload, _ = seal._bind(lifetime, compact.ROOT, descriptor, compact.MiB, deadline)
    value = source._canonical(payload, {'schema', 'base_protocol', 'condition_extension',
        'schemas', 'bounds', 'source_pins', 'claims'}, 'Publication extension')
    base = source._descriptor(compact.PROTOCOL_PATH.relative_to(compact.ROOT).as_posix(),
                              memory.canonical_bytes(compact.PROTOCOL))
    extension_bytes = artifacts._read(compact.ROOT / seal.EXTENSION_PATH, compact.MiB)
    extension = source._descriptor(seal.EXTENSION_PATH, extension_bytes)
    if (value['schema'] != 'memory-case-publication-v1-protocol'
            or value['base_protocol'] != base or value['condition_extension'] != extension
            or value['schemas'] != PUBLICATION_SCHEMAS or value['bounds'] != PUBLICATION_BOUNDS
            or value['claims'] != compact.PROTOCOL['claims']):
        raise ValueError('Publication extension contract differs')
    rows = value['source_pins']
    if type(rows) is not list or not rows or len(rows) > 512:
        raise ValueError('Publication source closure bound differs')
    for row in rows: _descriptor(row)
    paths = [row['path'] for row in rows]
    if (paths != sorted(set(paths))
            or {EXECUTION_POLICY_PATH, QUALIFICATION_POLICY_PATH} & set(paths)
            or not {'scripts/memory_family_case_publication_v1.py',
                        'scripts/memory_family_case_custody_v1.py',
                        'scripts/memory_family_retained_case_v1.py'} <= set(paths)):
        raise ValueError('Publication source closure differs')
    for row in [base, extension, *rows]:
        seal._bind(lifetime, compact.ROOT, row, 2 * compact.MiB, deadline)
    return descriptor, [descriptor, base, extension, *rows]


def _unique_descriptors(rows):
    values = {}
    for row in rows:
        _descriptor(row)
        if row['path'] in values and values[row['path']] != row:
            raise ValueError('Conflicting dependency descriptors: '+row['path'])
        values[row['path']] = copy.deepcopy(row)
    return sorted(values.values(), key=lambda row: row['path'])


def _check_policy_membership(policy, audit, contracts):
    _require_execution_pin(audit)
    if hashlib.sha256(memory.canonical_bytes(audit)).hexdigest() not in policy['ACCEPTED_EXECUTION_AUDIT_SHA256']:
        raise PermissionError('Execution acceptance was revoked')
    from scripts import memory_family_condition_seal_v4 as seal
    for contract in contracts.values():
        if 'qualification' not in contract: continue
        descriptor = contract['qualification']
        identity = tuple(descriptor[key] for key in ('path','size_bytes','sha256'))
        if identity not in policy['TRUSTED_QUALIFICATION_PINS']:
            raise PermissionError('No independently accepted exact qualification policy pin')
        seal._require_qualification_pin(descriptor)


def _publish_admitted_case(evidence_root, registrations, slot, commits, audit,
                           deadline, policy, policy_lifetime):
    from pathlib import PurePosixPath
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    from scripts import memory_family_retained_case_v1 as cases
    from scripts.memory_family_case_custody_v1 import _CasePublication
    root = artifacts._safe_path(evidence_root)
    _fields(slot, {'case_id','case_sha256','source_run_id','condition_run_ids'}, 'Case slot')
    _fields(registrations, CONDITIONS, 'Condition registrations')
    _fields(commits, CONDITIONS, 'Condition commits')
    case_id = slot['case_id']; memory._id(case_id)
    contracts = {}; external = []; code = []
    with seal._ValidatingStack() as discovery:
        # Terminal exports are unprotected admission headers. Require every
        # qualification before source/snapshot/history/retained-file reads.
        for condition in CONDITIONS:
            registration = registrations[condition]; _descriptor(registration)
            if registration['path'].startswith(('cases/','.pending/')):
                raise ValueError('Terminal export must be external')
            _, payload, _ = seal._bind(discovery, root, registration, compact.MiB, deadline)
            contract = source._canonical(payload, seal.REGISTRATION_KEYS, 'Condition terminal export')
            contracts[condition] = contract
            _check_policy_membership(policy, audit, {condition:contract})
        profile, profile_rows = _publication_profile(discovery, deadline)
        code.extend(profile_rows)
        for condition in CONDITIONS:
            contract, _, _ = seal._registration(root, registrations[condition],
                case_id, condition, deadline, discovery)
            if contract != contracts[condition]: raise ValueError('Terminal export changed')
            external.extend([registrations[condition], *contract['controls'].values(),
                *contract['history_bundles'].values(), contract['qualification']])
            extension = artifacts._json(artifacts._read(compact.ROOT / seal.EXTENSION_PATH, compact.MiB))
            code.extend(extension['source_pins'])
            _, receipt_bytes, _ = seal._bind(discovery, root, contract['qualification'], compact.MiB, deadline)
            receipt = source._canonical(receipt_bytes, cases.retained.qualification.RECEIPT_KEYS,
                                        'Case qualification receipt')
            cases.retained.qualification._validate_receipt(receipt)
            # The receipt's historical extra source/assets/runtime rosters are
            # provenance. Hold the selected consumer's actual closure below;
            # never reopen historical model or runtime inputs.
        common = contracts['own']
        source_registration = common['source']['registration']
        values = source._inputs(root, source_registration, case_id, deadline, discovery)
        contracts['source'] = source_contract = values[0]
        external.extend([source_registration, *source_contract['controls'].values()])
        source_commit = common['source']['commit']
        entries = cases._inventory(root, case_id, source_commit, None, discovery, deadline)
        for condition in CONDITIONS:
            entries.extend(cases._inventory(root, case_id, commits[condition], condition, discovery, deadline))
        entries = _unique_descriptors(entries)
        code.extend({key:row[key] for key in ('path','size_bytes','sha256')}
                    for row in compact.PROTOCOL['behavior_sources'])
        # Acceptance source bytes are independently held, not audit subject pins.
        for path in (EXECUTION_POLICY_PATH, QUALIFICATION_POLICY_PATH):
            code.append(source._descriptor(path, artifacts._read(compact.ROOT / path, compact.MiB)))
        dependencies = [{'root': str(root), 'entries': _unique_descriptors(external)},
                        {'root': str(compact.ROOT), 'entries': _unique_descriptors(code)}]
        # Enter the independent full hold before closing discovery custody.
        with _CasePublication(root, case_id, entries, deadline, dependencies=dependencies,
                recheck_acceptance=lambda:_check_policy_membership(policy,audit,contracts)) as publication:
            retained = cases.read_retained_staged_case(root, registrations, case_slot=slot,
                                                       condition_commits=commits, deadline=deadline)
            controls = {}
            for name, contract in contracts.items():
                registration = source_registration if name=='source' else registrations[name]
                for descriptor in [registration, contract['owner_record'], *contract['controls'].values()]:
                    _, payload, _ = seal._bind(discovery, root, descriptor, compact.MiB, deadline,
                        case_id=case_id, allow_empty=descriptor['size_bytes']==0)
                    controls[descriptor['path']] = payload
            validate_execution_audit(audit, case_slot=slot, source_commit=retained['source_commit'],
                condition_commits=commits, contracts=contracts, control_payloads=controls,
                publication_protocol_sha256=profile['sha256'])
            final_entries = [{**row,'path':'cases/'+row['path'][len('.pending/'):]} for row in entries]
            directories = sorted({parent.as_posix() for row in final_entries
                for parent in PurePosixPath(row['path']).parents
                if parent.as_posix().startswith(f'cases/{case_id}')})
            manifest = dict(schema='memory-family-compact-case-v1', protocol_sha256=compact.PROTOCOL_SHA256,
                analysis_cells=retained['retained_cells'], case_id=case_id, claims=copy.deepcopy(compact.PROTOCOL['claims']),
                condition_run_ids=retained['condition_run_ids'], source_run_id=retained['source_run_id'],
                run_receipts={'source':retained['source_commit'],'conditions':commits},snapshot=retained['snapshot'])
            manifest_bytes = memory.canonical_bytes(manifest)
            base = f'cases/{case_id}/'
            manifest_descriptor = source._descriptor(base+'manifest.json',manifest_bytes)
            close = dict(schema='memory-family-case-close-v1', protocol_sha256=compact.PROTOCOL_SHA256,
                publication_protocol_sha256=profile['sha256'],case_id=case_id,manifest=manifest_descriptor,
                execution_audit=audit,retained_inventory=final_entries,retained_directories=directories,
                retained_bytes=sum(row['size_bytes'] for row in entries),claims=copy.deepcopy(compact.PROTOCOL['claims']))
            close_bytes = memory.canonical_bytes(close)
            close_descriptor = source._descriptor(base+'close.json',close_bytes)
            marker = dict(schema='memory-family-case-commit-v1', protocol_sha256=compact.PROTOCOL_SHA256,
                publication_protocol_sha256=profile['sha256'],case_id=case_id,manifest=manifest_descriptor,
                close=close_descriptor,claims=copy.deepcopy(compact.PROTOCOL['claims']))
            marker_bytes = memory.canonical_bytes(marker)
            payloads={'manifest.json':manifest_bytes,'close.json':close_bytes,'commit.json':marker_bytes}
            # Drain nested staged-only contexts while the independent capability
            # retains every input. No staged path is reopened after publication.
            discovery.close()
            _check_policy_membership(policy,audit,contracts);publication.recheck()
            publication.write_case_files(payloads)
            _check_policy_membership(policy,audit,contracts);publication.recheck()
            publication.publish()
            _check_policy_membership(policy,audit,contracts)
            policy_lifetime.close()
            publication.recheck()
            result = copy.deepcopy({'case_commit': source._descriptor(base+'commit.json',marker_bytes),
                      'retained': retained, 'order_evidence':'accepted-supervisor-attestation'})
            source.audit._deadline(deadline)
    return result


from scripts.memory_family_case_custody_v1 import CasePublicationIndeterminate


def read_retained_published_case(evidence_root, registrations, *, case_slot,
                                condition_commits, execution_audit, case_commit, deadline):
    """Read an externally registered final marker under independent trust."""
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    source.audit._public_deadline(deadline)
    audit = copy.deepcopy(execution_audit)
    _require_execution_pin(audit)
    with seal._ValidatingStack() as policy_lifetime:
        policy = _read_acceptance_policy(policy_lifetime, audit, deadline)
        registrations, slot, commits, expected = copy.deepcopy(
            (registrations, case_slot, condition_commits, case_commit))
        result = _read_admitted_published_case(evidence_root, registrations, slot,
            commits, audit, expected, deadline, policy)
    source.audit._deadline(deadline)
    return result


def _read_admitted_published_case(evidence_root, registrations, slot, commits,
                                  audit, expected, deadline, policy):
    from pathlib import PurePosixPath
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts import memory_family_producer_v4 as source
    from scripts import memory_family_retained_case_v1 as cases
    from scripts.memory_family_replay_custody_v4 import HeldReplayFiles
    root = artifacts._safe_path(evidence_root)
    _fields(slot, {'case_id','case_sha256','source_run_id','condition_run_ids'}, 'Case slot')
    _fields(registrations, CONDITIONS, 'Condition registrations')
    _fields(commits, CONDITIONS, 'Condition commits')
    case_id = slot['case_id']; memory._id(case_id)
    if not compact._PATH_COMPONENT.fullmatch(case_id):
        raise ValueError('Invalid published case identifier')
    base = f'cases/{case_id}/'
    _descriptor(expected)
    if expected['path'] != base+'commit.json' or expected['size_bytes'] > MAX_BYTES:
        raise ValueError('Expected case commit differs from the registered case')
    contracts = {}; external = []; code = []
    with seal._ValidatingStack() as lifetime:
        # External terminal exports are admission headers; every qualification
        # is admitted before opening any protected final-case leaf.
        for condition in CONDITIONS:
            registration = registrations[condition]; _descriptor(registration)
            if registration['path'].startswith(('cases/', '.pending/')):
                raise ValueError('Terminal export must be external')
            _, payload, _ = seal._bind(lifetime, root, registration, compact.MiB, deadline)
            contract = source._canonical(payload, seal.REGISTRATION_KEYS, 'Condition terminal export')
            contracts[condition] = contract
            _check_policy_membership(policy, audit, {condition:contract})
        profile, profile_rows = _publication_profile(lifetime, deadline)
        code.extend(profile_rows)
        _, marker_bytes, _ = seal._bind(lifetime, root, expected, MAX_BYTES,
            deadline, case_id=case_id, location='published')
        marker = source._canonical(marker_bytes, COMMIT_KEYS, 'Published case commit')

        def identity(value, schema):
            if value['schema'] != schema or value['case_id'] != case_id:
                raise ValueError('Published case receipt identity differs')
            _equal(value['protocol_sha256'], compact.PROTOCOL_SHA256, 'Published base protocol')
            _equal(value['publication_protocol_sha256'], profile['sha256'], 'Published publication protocol')
            _equal(value['claims'], compact.PROTOCOL['claims'], 'Published claims')

        identity(marker, 'memory-family-case-commit-v1')
        files = {'commit.json':expected, 'manifest.json':marker['manifest'], 'close.json':marker['close']}
        for name, descriptor in files.items():
            _descriptor(descriptor)
            if descriptor['path'] != base+name:
                raise ValueError('Published root descriptor crosses a case')
        if sum(row['size_bytes'] for row in files.values()) > MAX_BYTES:
            raise ValueError('Published root files exceed combined allowance')
        _, close_bytes, _ = seal._bind(lifetime, root, files['close.json'], MAX_BYTES,
            deadline, case_id=case_id, location='published')
        close = source._canonical(close_bytes, CLOSE_KEYS, 'Published case close')
        identity(close, 'memory-family-case-close-v1')
        _equal(close['manifest'], files['manifest.json'], 'Published close manifest')
        _equal(close['execution_audit'], audit, 'Published accepted execution audit')
        _, manifest_bytes, _ = seal._bind(lifetime, root, files['manifest.json'], MAX_BYTES,
            deadline, case_id=case_id, location='published')
        source._canonical(manifest_bytes, MANIFEST_KEYS, 'Published case manifest')
        for condition in CONDITIONS:
            contract, _, _ = seal._registration(root, registrations[condition], case_id,
                condition, deadline, lifetime, location='published')
            if contract != contracts[condition]:
                raise ValueError('Terminal export changed')
            external.extend([registrations[condition], *contract['controls'].values(),
                *contract['history_bundles'].values(), contract['qualification']])
            extension = artifacts._json(artifacts._read(compact.ROOT / seal.EXTENSION_PATH, compact.MiB))
            code.extend(extension['source_pins'])
            _, receipt_bytes, _ = seal._bind(lifetime, root, contract['qualification'], compact.MiB, deadline)
            receipt = source._canonical(receipt_bytes, cases.retained.qualification.RECEIPT_KEYS,
                'Case qualification receipt')
            cases.retained.qualification._validate_receipt(receipt)
        common = contracts['own']; source_registration = common['source']['registration']
        values = source._inputs(root, source_registration, case_id, deadline, lifetime, location='published')
        contracts['source'] = source_contract = values[0]
        external.extend([source_registration, *source_contract['controls'].values()])
        entries = cases._inventory(root, case_id, common['source']['commit'], None,
            lifetime, deadline, location='published')
        for condition in CONDITIONS:
            entries.extend(cases._inventory(root, case_id, commits[condition], condition,
                lifetime, deadline, location='published'))
        entries = _unique_descriptors(entries)
        directories = sorted({parent.as_posix() for row in entries
            for parent in PurePosixPath(row['path']).parents
            if parent.as_posix().startswith(f'cases/{case_id}')})
        total_bytes = sum(row['size_bytes'] for row in entries)
        if (len(entries) > 418 or len(directories) != 33 or len(entries)+len(directories)+3 > 454
                or total_bytes > (32+16+1+9*(25+1))*compact.MiB):
            raise ValueError('Published inventory exceeds inherited bounds')
        _equal(close['retained_inventory'], entries, 'Published derived inventory')
        _equal(close['retained_directories'], directories, 'Published derived directories')
        _equal(close['retained_bytes'], total_bytes, 'Published retained bytes')
        code.extend({key:row[key] for key in ('path','size_bytes','sha256')}
            for row in compact.PROTOCOL['behavior_sources'])
        # Historical extra qualification rosters are provenance. Hold the actual
        # consumer closure; never reopen the historical numerical model/runtime.
        for path in (EXECUTION_POLICY_PATH, QUALIFICATION_POLICY_PATH):
            code.append(source._descriptor(path, artifacts._read(compact.ROOT / path, compact.MiB)))
        internal = lifetime.enter_context(HeldReplayFiles(root,
            _unique_descriptors([*entries, *files.values()]), deadline,
            exact_subtrees=(f'cases/{case_id}',)))
        external_hold = lifetime.enter_context(HeldReplayFiles(root, _unique_descriptors(external), deadline))
        code_hold = lifetime.enter_context(HeldReplayFiles(compact.ROOT, _unique_descriptors(code), deadline))
        retained = cases._read_retained_case(root, registrations, case_slot=slot,
            condition_commits=commits, deadline=deadline, location='published', case_files=files)
        controls = {}
        for name, contract in contracts.items():
            registration = source_registration if name == 'source' else registrations[name]
            for descriptor in [registration, contract['owner_record'], *contract['controls'].values()]:
                _, payload, _ = seal._bind(lifetime, root, descriptor, compact.MiB, deadline,
                    case_id=case_id, location='published', allow_empty=descriptor['size_bytes']==0)
                controls[descriptor['path']] = payload
        validate_execution_audit(audit, case_slot=slot, source_commit=retained['source_commit'],
            condition_commits=commits, contracts=contracts, control_payloads=controls,
            publication_protocol_sha256=profile['sha256'])
        derived_manifest = dict(schema='memory-family-compact-case-v1',
            protocol_sha256=compact.PROTOCOL_SHA256, analysis_cells=retained['retained_cells'],
            case_id=case_id, claims=copy.deepcopy(compact.PROTOCOL['claims']),
            condition_run_ids=retained['condition_run_ids'], source_run_id=retained['source_run_id'],
            run_receipts={'source':retained['source_commit'], 'conditions':commits}, snapshot=retained['snapshot'])
        if manifest_bytes != memory.canonical_bytes(derived_manifest):
            raise ValueError('Published manifest differs from independently derived semantics')
        _check_policy_membership(policy, audit, contracts)
        for held in (internal, external_hold, code_hold):
            held.recheck()
        result = copy.deepcopy({'case_commit':expected, 'retained':retained,
            'order_evidence':'accepted-supervisor-attestation'})
    source.audit._deadline(deadline)
    return result
