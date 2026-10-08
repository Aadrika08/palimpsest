"""Pure compact-family fixtures; never open retained data or run an owner."""
import copy
import hashlib
import importlib
import os
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
import pytest

from palimpsest import artifacts, memory, snapshots


ROOT = Path(__file__).parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-compact-evidence-v4-protocol.json'
RETAINED = (
    'encoded_input', 'sensors', 'action', 'control', 'pose', 'next_pose',
    'reward', 'simulation_time', 'raw_output', 'eyes', 'revision',
)
CAMERAS = ('cam_left', 'cam_right', 'raw_cam_left', 'raw_cam_right')


def _compact():
    try:
        return importlib.import_module('scripts.memory_family_compact_v4')
    except ModuleNotFoundError:
        pytest.fail('memory_family_compact_v4 is not implemented', pytrace=False)


def _row(tick):
    left = np.full((128, 128, 3), tick, np.uint8)
    right = np.full((128, 128, 3), tick + 1, np.uint8)
    return {
        'episode': 0,
        'tick': tick,
        'encoded_input': np.linspace(-1, 1, 4813, dtype=np.float32) + tick,
        'sensors': np.array([0.0, 0.25, 1.0, -1.0], np.float32),
        'action': np.array([0.2, -0.1], np.float32),
        'control': np.array([0.19, -0.09], np.float64),
        'pose': np.array([tick, 0.5, -0.25], np.float64),
        'next_pose': np.array([tick + 0.1, 0.5, -0.2], np.float64),
        'reward': np.array(0.5, np.float64),
        'simulation_time': np.array(tick * 0.02, np.float64),
        'raw_output': np.array([0.21, -0.11], np.float32),
        'eyes': np.array([True, True], np.bool_),
        'revision': np.array(3, np.int64),
        'cam_left': left,
        'cam_right': right,
        'raw_cam_left': left.copy(),
        'raw_cam_right': right.copy(),
        'latency': np.array(0.01, np.float64),
        'step_latency': np.array(0.02, np.float64),
        'population_stats': np.array([[2.0, 0.5, 0.0, 1.0]], np.float64),
    }


def _legacy(rows, run_id):
    arrays = {
        name: {'dtype': value.dtype.str, 'shape': list(value.shape)}
        for name, value in rows[0].items() if name not in {'episode', 'tick'}
    }
    events = [
        {'sequence': 0, 'kind': 'episode_started', 'episode': 0,
         'episode_step': rows[0]['tick']},
        {'sequence': 1, 'kind': 'memory_decision_armed', 'episode': 0,
         'episode_step': rows[0]['tick']},
        {'sequence': 2, 'kind': 'chunk', 'path': 'chunks/000000.npz',
         'sha256': 'a' * 64, 'episode': 0, 'start': rows[0]['tick'],
         'count': len(rows), 'arrays': arrays},
    ]
    manifest = memory.canonical_bytes({
        'run_id': run_id, 'status': 'completed',
        'recording_format': 'palimpsest-npz-v1',
        'recorded_ticks': len(rows), 'recorded_chunks': 1,
        'recorded_events': len(events),
    }) + b'\n'
    event_bytes = b''.join(memory.canonical_bytes(event) + b'\n'
                           for event in events)
    return manifest, event_bytes, events


def _snapshot_reference(source_run_id):
    return {
        'kind': 'shared-source',
        'source_run_id': source_run_id,
        'source_receipt_sha256': 'b' * 64,
        'path': 'cases/case-7/source/snapshots/initial.snp',
        'size_bytes': 1234,
        'sha256': 'c' * 64,
    }


def _fixture():
    compact = _compact()
    run_id = uuid.UUID(int=701).hex
    source_run_id = uuid.UUID(int=700).hex
    rows = [_row(7), _row(8)]
    legacy_manifest, legacy_events, events = _legacy(rows, run_id)
    snapshot_reference = _snapshot_reference(source_run_id)
    bundle = compact.convert_synthetic(
        run_id=run_id, case_id='memory-family-v3-fixture-change',
        operation='condition', condition='own', rows=rows,
        legacy_manifest_bytes=legacy_manifest,
        legacy_events_bytes=legacy_events,
        snapshot_reference=snapshot_reference,
        event_tick=7, decision_tick=8,
    )
    return compact, rows, events, legacy_manifest, legacy_events, \
        snapshot_reference, bundle


def test_protocol_is_canonical_and_freezes_exact_false_claim_contract():
    assert PROTOCOL_PATH.is_file(), 'canonical compact protocol is missing'
    payload = PROTOCOL_PATH.read_bytes()
    protocol = artifacts._json(payload)
    compact = _compact()

    assert payload == memory.canonical_bytes(protocol) == compact.PROTOCOL_BYTES
    assert protocol['schema'] == 'memory-family-compact-protocol-v4'
    assert protocol['recording_format'] == 'palimpsest-family-compact-v1'
    assert protocol['analysis_contract']['protocol'] == {
        'path': 'docs/plans/memory-family-analysis-v3-protocol.json',
        'size_bytes': 2210,
        'sha256': '02e252fb5bdf41c48b2b384378e8a70eee98480829e25e1f0dcf269faebdce9b',
    }
    assert protocol['analysis_contract']['conditions'] == [
        'own', 'swapped', 'sham', 'no-U', 'hand-authored',
        'history-independent', 'traversal', 'retrieval', 'oracle',
    ]
    assert protocol['analysis_contract']['families'] == 48
    assert protocol['analysis_contract']['cases'] == 144
    assert protocol['analysis_contract']['owners'] == 1440
    assert protocol['analysis_contract']['retries'] == 0
    assert protocol['analysis_contract']['replacements'] == 0

    fields = protocol['row']['fields']
    assert [field['name'] for field in fields] == [
        *RETAINED,
        'cam_left_sha256', 'cam_right_sha256',
        'raw_cam_left_sha256', 'raw_cam_right_sha256', 'row_digest',
    ]
    assert sum(field['bytes'] for field in fields) == \
        protocol['row']['bytes_per_tick'] == 19_534
    assert protocol['audit_ticks'] == {
        'case_list_sha256': '009135479864b4a1c83c611683ada7efce298d29e9a807a7740b07ee6d09112c',
        'final_ticks': 2, 'maximum': 16, 'neighborhood_radius': 1,
        'quantile_denominator': 5, 'quantile_points': 6,
        'selected_frame_shape': [128, 128, 3],
        'selected_frame_dtype': '|u1',
        'generator_interpreter': {
            'path': '../lab-hardening/.venv/bin/python',
            'version': '3.11.15',
        },
        'prerequisite_ids_checked': ['gate-a', 'fixture-prefix'],
        'superseded_unpinned': {
            'case_list_sha256': 'b5f603d175a4799864442055399656cb760c8d9ff82bfed354827b4d940a4bb5',
            'path': '/usr/bin/python', 'version': '3.14.7',
        },
    }

    source = protocol['recordings']['source']
    condition = protocol['recordings']['condition']
    assert source['calculated_max_bytes'] == (
        1200 * 19_534 + 16 * 2 * 128 * 128 * 3 + 7 * 1024**2 + 1024**2
    ) == 33_402_272
    assert condition['calculated_max_bytes'] == (
        900 * 19_534 + 16 * 2 * 128 * 128 * 3 + 5 * 1024**2 + 1024**2
    ) == 25_444_920
    assert source['ceiling_bytes'] == 32 * 1024**2
    assert condition['ceiling_bytes'] == 25 * 1024**2

    storage = protocol['storage']
    assert storage['producer_steady_bytes'] == 45_751_468_032
    assert storage['prerequisite_bytes'] == 8 * 1024**3
    assert storage['non_recording_bytes'] == 6_710_886_400
    assert storage['transient_bytes'] == 560 * 1024**2
    assert storage['allocation_max_bytes'] == 61_639_491_584
    assert storage['minimum_capacity_bytes'] == \
        storage['allocation_max_bytes'] + storage['free_space_floor_bytes'] == \
        63_786_975_232
    assert storage['entries'] == {
        'cap': 77_824, 'headroom': 384, 'peak': 77_440,
        'prerequisites': 474, 'steady': 77_391, 'transient': 49,
    }
    assert storage['max_runs'] == 1448
    assert storage['max_exports'] == 1592
    assert storage['snapshots'] == {
        'aggregate': 154, 'condition_local': 0, 'family_sources': 144,
        'maximum_per_run': 2, 'prerequisites': 10,
    }
    assert protocol['claims'] == {
        'allocation_authorized': False,
        'camera_to_encoded_input_independently_reauditable': False,
        'cell_replay_verified': False,
        'compact_oracle_equivalent': False,
        'full_pixel_replay': False,
        'held_out_used': False,
        'namespace_coverage_complete': False,
        'native_allocation': False,
        'native_owner_launch_authorized': False,
        'pruning_authorized': False,
        'qualification_claims': [],
        'storage_allocation_admitted': False,
    }
    assert compact.validate_protocol(copy.deepcopy(protocol)) == protocol


def test_protocol_binds_exact_present_sources_and_marks_future_roles_unresolved():
    compact = _compact()
    assert compact.behavior_source_identities(ROOT) == compact.PROTOCOL['behavior_sources']
    assert compact.PROTOCOL['future_behavior_sources'] == [
        {'id': 'raw_audit', 'path': 'scripts/memory_family_raw_audit_v4.py'},
        {'id': 'pair_admission', 'path': 'scripts/memory_family_oracle_admission_v4.py'},
        {'id': 'producer', 'path': 'scripts/memory_family_producer_v4.py'},
    ]
    assert all(set(row) == {'id', 'path', 'size_bytes', 'sha256'}
               for row in compact.PROTOCOL['behavior_sources'])


def test_import_is_pure_and_does_not_load_native_or_model_modules():
    code = (
        "import json,sys; import scripts.memory_family_compact_v4 as c; "
        "print(json.dumps({'protocol': c.PROTOCOL['schema'], "
        "'forbidden': sorted(set(sys.modules) & "
        "{'torch','mujoco','palimpsest.engine','palimpsest.model'})}))"
    )
    env = {**os.environ, 'PYTHONPATH': 'src:.', 'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT, env=env,
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert artifacts._json(result.stdout.encode()) == {
        'protocol': 'memory-family-compact-protocol-v4', 'forbidden': [],
    }


def test_synthetic_converter_and_strict_reader_round_trip_frozen_projection():
    compact, rows, events, legacy_manifest, legacy_events, snapshot_ref, bundle = \
        _fixture()
    read = compact.read_compact(bundle)

    assert read['legacy_manifest_bytes'] == legacy_manifest
    assert read['legacy_events_bytes'] == legacy_events
    assert [event['sequence'] for event in read['events']] == [0, 1]
    assert read['snapshot_reference'] == snapshot_ref
    assert list(read['selected_frames']) == [7, 8]
    assert set(bundle) == {
        'manifest.json', 'legacy-manifest.json', 'legacy-events.jsonl',
        'chunk-index.json', 'audit-frames.npz', 'chunks/000000.npz',
    }

    index = artifacts._json(bundle['chunk-index.json'])
    assert index['schema'] == 'memory-family-compact-chunk-index-v1'
    assert len(index['chunks']) == 1
    assert index['chunks'][0]['legacy_sequence'] == events[2]['sequence']
    assert index['chunks'][0]['legacy_path'] == events[2]['path']
    assert index['chunks'][0]['legacy_sha256'] == events[2]['sha256']
    assert index['chunks'][0]['episode'] == 0
    assert index['chunks'][0]['start'] == 7
    assert index['chunks'][0]['count'] == 2

    expected_trace = hashlib.sha256()
    raw_trace = hashlib.sha256()
    for original, restored in zip(rows, read['rows']):
        assert restored['episode'] == original['episode']
        assert restored['tick'] == original['tick']
        for field in RETAINED:
            np.testing.assert_array_equal(restored[field], original[field])
        for camera in CAMERAS:
            expected = bytes.fromhex(snapshots.state_digest(original[camera]))
            np.testing.assert_array_equal(
                restored[f'{camera}_sha256'], np.frombuffer(expected, np.uint8))
        digest = bytes.fromhex(snapshots.state_digest({
            key: value for key, value in original.items()
            if key not in {'latency', 'step_latency'}
        }))
        np.testing.assert_array_equal(
            restored['row_digest'], np.frombuffer(digest, np.uint8))
        expected_trace.update(digest.hex().encode('ascii'))
        raw_trace.update(digest)
        for eye in ('raw_cam_left', 'raw_cam_right'):
            np.testing.assert_array_equal(
                read['selected_frames'][original['tick']][eye], original[eye])
    assert read['trace_digest'] == expected_trace.hexdigest()
    assert read['trace_digest'] != raw_trace.hexdigest()


def test_audit_tick_rule_is_bounded_for_every_generated_development_case():
    compact = _compact()
    from palimpsest import memory_decision_world as world
    from scripts.memory_family_v3 import build_slots

    generated = build_slots(
        'development', [0], [{'id': 'fixture-prefix', 'kind': 'prefix'}]
    )
    assert len(generated['cases']) == 144
    assert memory.sha256(generated['cases']) == \
        '009135479864b4a1c83c611683ada7efce298d29e9a807a7740b07ee6d09112c'
    source_max = max(len(compact.audit_ticks(range(n)))
                     for n in range(1, 1201))
    condition_max = 0
    for case in generated['cases']:
        schedule = world.registered_profile(case['profile_sha256'])['arm_schedule']
        for n in range(1, 901):
            selected = compact.audit_ticks(
                range(n),
                event_tick=(schedule['event_offset']
                            if case['event_enabled'] else None),
                decision_tick=schedule['decision_offset'],
            )
            condition_max = max(condition_max, len(selected))
    assert (source_max, condition_max) == (7, 11)
    assert condition_max <= 16


@pytest.mark.parametrize('defect', [
    'dtype', 'nonfinite', 'eyes', 'camera', 'gap', 'snapshot-path',
    'legacy-count',
])
def test_converter_rejects_invalid_raw_projection_before_bundle(defect):
    compact = _compact()
    run_id = uuid.UUID(int=801).hex
    rows = [_row(7), _row(8)]
    snapshot_ref = _snapshot_reference(uuid.UUID(int=800).hex)
    if defect == 'dtype':
        rows[0]['encoded_input'] = rows[0]['encoded_input'].astype(np.float64)
    elif defect == 'nonfinite':
        rows[0]['reward'][...] = np.nan
    elif defect == 'eyes':
        rows[0]['eyes'][0] = False
    elif defect == 'camera':
        rows[0]['raw_cam_left'][0, 0, 0] ^= 1
    elif defect == 'gap':
        rows[1]['tick'] = 9
    elif defect == 'snapshot-path':
        snapshot_ref['path'] = '../source.snp'
    legacy_manifest, legacy_events, _ = _legacy(rows, run_id)
    if defect == 'legacy-count':
        parsed = [artifacts._json(line) for line in legacy_events.splitlines()]
        parsed[-1]['count'] += 1
        legacy_events = b''.join(memory.canonical_bytes(event) + b'\n'
                                 for event in parsed)
    with pytest.raises(ValueError):
        compact.convert_synthetic(
            run_id=run_id, case_id='memory-family-v3-fixture-change',
            operation='condition', condition='own', rows=rows,
            legacy_manifest_bytes=legacy_manifest,
            legacy_events_bytes=legacy_events,
            snapshot_reference=snapshot_ref, event_tick=7, decision_tick=8,
        )


@pytest.mark.parametrize('defect', [
    'manifest-extra', 'chunk-bytes', 'legacy-events', 'missing-frame',
])
def test_reader_rejects_unknown_schema_or_tampered_bound_payload(defect):
    compact, _, _, _, _, _, bundle = _fixture()
    changed = dict(bundle)
    if defect == 'manifest-extra':
        manifest = artifacts._json(changed['manifest.json'])
        manifest['unknown'] = True
        changed['manifest.json'] = memory.canonical_bytes(manifest)
    elif defect == 'chunk-bytes':
        changed['chunks/000000.npz'] += b'corrupt'
    elif defect == 'legacy-events':
        changed['legacy-events.jsonl'] += b'\n'
    else:
        changed.pop('audit-frames.npz')
    with pytest.raises(ValueError):
        compact.read_compact(changed)
