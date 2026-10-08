"""Pure contracts for the prospective puck on-policy layout source slice."""
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest import puck_profile as puck


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IDS = list(range(7100, 7108))
EXPECTED = [
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7100,
     'split': 'on_policy_collection', 'slot': 0,
     'rover_pose': [-1.25, -0.75, 0.25], 'puck_xy': [-0.5, -0.5],
     'goal_xy': [0.5, -0.5], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7101,
     'split': 'on_policy_collection', 'slot': 1,
     'rover_pose': [-1.375, 0.0, -0.25], 'puck_xy': [-0.5, -0.25],
     'goal_xy': [0.75, 0.0], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7102,
     'split': 'on_policy_collection', 'slot': 2,
     'rover_pose': [-1.5, 0.0, 0.375], 'puck_xy': [-0.5, 0.25],
     'goal_xy': [1.0, 0.0], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7103,
     'split': 'on_policy_collection', 'slot': 3,
     'rover_pose': [-1.25, 0.75, -0.375], 'puck_xy': [-0.5, 0.5],
     'goal_xy': [1.25, 0.5], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7104,
     'split': 'on_policy_development', 'slot': 4,
     'rover_pose': [-1.125, -0.75, 0.5], 'puck_xy': [-0.25, -0.5],
     'goal_xy': [0.875, -0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7105,
     'split': 'on_policy_development', 'slot': 5,
     'rover_pose': [-1.25, 0.0, -0.5], 'puck_xy': [-0.25, -0.25],
     'goal_xy': [1.125, -0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7106,
     'split': 'on_policy_development', 'slot': 6,
     'rover_pose': [-1.0, 0.0, 0.125], 'puck_xy': [-0.25, 0.25],
     'goal_xy': [1.375, 0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7107,
     'split': 'on_policy_development', 'slot': 7,
     'rover_pose': [-1.125, 0.75, -0.125], 'puck_xy': [-0.25, 0.5],
     'goal_xy': [1.625, 0.375], 'initial_qvel': 'all zeros'},
]

RESERVED_IDS = (6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123)
LINEAGE_SHA256 = hashlib.sha256(b'synthetic-v3-reservation-lineage').hexdigest()


def canonical_bytes(value):
    return json.dumps(value, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8') + b'\n'


def digest(value):
    raw = value if type(value) is bytes else canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def inventory_scene(scene_id, marker):
    return {
        'scene_id': scene_id,
        'canonical_scene_sha256': digest({'canonical': marker}),
        'scientific_initial_sha256': digest({'initial': marker}),
        'payload_sha256': digest({'payload': marker}),
    }


def inventory_snapshot():
    roots = []
    records = []
    for kind in ('ref', 'worktree', 'raw_registry', 'manifest'):
        path = f'/synthetic/inventory/{kind}'
        roots.append({
            'kind': kind, 'path': path, 'resolved_path': path,
            'exists': True, 'readable': True, 'is_directory': True,
            'is_symlink': False, 'identity_sha256': digest({'root': kind}),
        })
        records.append({
            'kind': kind, 'name': f'synthetic-{kind}', 'root': path,
            'identity_sha256': digest({'record': kind}), 'role': 'prior',
            'lineage_sha256': None,
            'scenes': [inventory_scene(6000, 'prior-raw')]
            if kind == 'raw_registry' else [],
            'metadata': {'byte_count': 6110, 'unrelated_hash': '6110-is-not-a-scene'},
        })
    records[-1] = {
        'kind': 'manifest', 'name': 'synthetic-v3-self-reservation',
        'root': roots[-1]['path'],
        'identity_sha256': digest({'record': 'self-reservation'}),
        'role': 'self_reservation', 'lineage_sha256': LINEAGE_SHA256,
        'scenes': [{
            'scene_id': scene_id, 'canonical_scene_sha256': None,
            'scientific_initial_sha256': None, 'payload_sha256': None,
        } for scene_id in RESERVED_IDS],
        'metadata': {'protocol_byte_count': 6110},
    }
    return {
        'version': 1, 'complete': True, 'remote_refs_fresh': True,
        'held_out_accessed': False, 'roots': roots, 'records': records,
    }


def fake_candidate(scene_id, slot, split, *, canonical_marker=None,
                   initial_marker=None, payload_marker=None):
    y = -0.7 + slot * 0.2
    layout = {
        'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': scene_id,
        'split': split, 'slot': slot,
        'rover_pose': [-1.0, float(y + 0.25), float(-0.2 + slot * 0.05)],
        'puck_xy': [-0.25, float(y)], 'goal_xy': [1.0, float(y)],
        'initial_qvel': 'all zeros',
    }
    return {
        'layout': layout,
        'canonical_scene': {'schema': 'synthetic-canonical-v1',
                            'marker': canonical_marker or f'canonical-{scene_id}'},
        'scientific_initial': {'schema': 'synthetic-initial-v1',
                               'marker': initial_marker or f'initial-{scene_id}'},
        'payload': {'schema': 'synthetic-payload-v1',
                    'marker': payload_marker or f'payload-{scene_id}'},
    }


def subject():
    spec = importlib.util.find_spec('palimpsest.puck_on_policy')
    if spec is None:
        raise AssertionError('pure puck on-policy layout minter is missing')
    return importlib.import_module('palimpsest.puck_on_policy')


class StopBeforeNative(Exception):
    pass


class PuckOnPolicyLayoutTests(unittest.TestCase):
    def test_fixed_finite_domain_is_deterministic_one_to_one_and_task_valid(self):
        on_policy = subject()
        first = on_policy.mint_layouts(FIXTURE_IDS)
        second = on_policy.mint_layouts(tuple(FIXTURE_IDS))
        self.assertEqual(first, EXPECTED)
        self.assertEqual(second, EXPECTED)
        self.assertIsNot(first, second)
        self.assertEqual(len({row['seed'] for row in first}), 8)
        scientific = {(tuple(row['rover_pose']), tuple(row['puck_xy']), tuple(row['goal_xy']))
                      for row in first}
        complete = {json.dumps(row, sort_keys=True, separators=(',', ':')) for row in first}
        self.assertEqual((len(scientific), len(complete)), (8, 8))
        for row in first:
            self.assertTrue(all(math.isfinite(value) for value in
                                row['rover_pose'] + row['puck_xy'] + row['goal_xy']))
            self.assertLessEqual(max(map(abs, row['rover_pose'][:2] + row['puck_xy'] + row['goal_xy'])), 5)
            self.assertLessEqual(abs(row['rover_pose'][2]), math.pi)
            self.assertGreater(math.dist(row['rover_pose'][:2], row['puck_xy']), .55)
            self.assertGreater(math.dist(row['puck_xy'], row['goal_xy']), .99)
        first[0]['rover_pose'][0] = 99
        self.assertEqual(on_policy.mint_layouts(FIXTURE_IDS), EXPECTED)

    def test_bad_domains_duplicates_and_occupied_ids_fail_without_writing(self):
        on_policy = subject()
        bad = [
            FIXTURE_IDS[:-1],
            FIXTURE_IDS + [7108],
            [*FIXTURE_IDS[:-1], FIXTURE_IDS[-2]],
            list(reversed(FIXTURE_IDS)),
            [True, *FIXTURE_IDS[1:]],
            [2**31, *FIXTURE_IDS[1:]],
        ]
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            try:
                os.chdir(directory)
                for values in bad:
                    with self.subTest(values=values), self.assertRaises(ValueError):
                        on_policy.mint_layouts(values)
                with self.assertRaisesRegex(ValueError, 'collision'):
                    on_policy.mint_layouts(FIXTURE_IDS, occupied_scene_ids=[7000, 7103, 7200])
            finally:
                os.chdir(previous)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_reserved_roster_is_locked_without_invoking_it(self):
        on_policy = subject()
        protocol = json.loads((ROOT / 'docs/plans/m6-puck-navigation-v3-on-policy-relabeling-protocol.json').read_text())
        reserved = protocol['scene_reservations']['collection'] + protocol['scene_reservations']['development']
        self.assertEqual(tuple(reserved), on_policy.RESERVED_SCENE_IDS)
        with patch.object(on_policy, 'RESERVED_SCENE_IDS', (FIXTURE_IDS[0],)):
            with self.assertRaisesRegex(ValueError, 'locked'):
                on_policy.mint_layouts(FIXTURE_IDS)
            row = EXPECTED[0]
            with self.assertRaisesRegex(ValueError, 'locked'):
                on_policy.admit_layout(row, seed=row['seed'], split=row['split'])

    def test_layout_admission_rejects_tamper_and_returns_fresh_exact_rows(self):
        on_policy = subject()
        for expected in EXPECTED:
            actual = on_policy.admit_layout(expected, seed=expected['seed'], split=expected['split'])
            self.assertEqual(actual, expected)
            self.assertIsNot(actual, expected)
            self.assertIsNot(actual['rover_pose'], expected['rover_pose'])
        mutations = []
        for key, value in (
                ('version', 2), ('kind', 'puck-layout-v1'), ('seed', 7999),
                ('split', 'train'), ('slot', 7), ('initial_qvel', [])):
            changed = json.loads(json.dumps(EXPECTED[0])); changed[key] = value; mutations.append(changed)
        for key, index in (('rover_pose', 0), ('puck_xy', 1), ('goal_xy', 0)):
            changed = json.loads(json.dumps(EXPECTED[0])); changed[key][index] += .125; mutations.append(changed)
        changed = json.loads(json.dumps(EXPECTED[0])); changed['extra'] = True; mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                on_policy.admit_layout(changed, seed=7100, split='on_policy_collection')
        with self.assertRaises(ValueError):
            on_policy.admit_layout(EXPECTED[0], seed=7101, split='on_policy_collection')
        with self.assertRaises(ValueError):
            on_policy.admit_layout(EXPECTED[0], seed=7100, split='on_policy_development')

    def test_layout_admission_rejects_negative_zero_payload_drift(self):
        on_policy = subject()
        changed = json.loads(json.dumps(EXPECTED[1]))
        self.assertEqual(changed['goal_xy'][1], 0.0)
        changed['goal_xy'][1] = -0.0
        with self.assertRaises(ValueError):
            on_policy.admit_layout(changed, seed=7101, split='on_policy_collection')

    def test_reset_seam_is_keyword_only_and_reaches_only_the_existing_native_boundary(self):
        on_policy = subject()
        layout_signature = inspect.signature(puck.layout)
        self.assertEqual(str(layout_signature), '(repo_root, seed, split)')
        signature = inspect.signature(puck.authored_reset)
        self.assertEqual(list(signature.parameters),
                         ['env', 'repo_root', 'seed', 'split', 'episode_id', 'explicit_layout'])
        self.assertEqual(signature.parameters['explicit_layout'].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(signature.parameters['explicit_layout'].default)
        with self.assertRaises(TypeError):
            puck.authored_reset(object(), ROOT, 7100, 'on_policy_collection', 'fixture', EXPECTED[0])
        with self.assertRaises(ValueError):
            puck.layout(ROOT, 7100, 'on_policy_collection')

        ranges = np.zeros((65, 2))
        ranges[3:60] = [-1e-6, 1e-6]
        ranges[2] = [-.002, .002]
        model = SimpleNamespace(jnt_range=ranges)
        env = SimpleNamespace(model=model, _puck_profile_identity={
            'protocol_sha256': puck.PROTOCOL_SHA256, 'model_sha256': 'fixture-model'},
            _puck_bindings={})
        fake_mujoco = SimpleNamespace(MjData=lambda _model: (_ for _ in ()).throw(StopBeforeNative()))
        with patch.dict(sys.modules, {'mujoco': fake_mujoco}), \
                patch.object(puck, '_admit_owner', return_value=({}, {})), \
                patch('palimpsest.snapshots._model_digest', return_value='fixture-model'):
            with self.assertRaises(StopBeforeNative):
                puck.authored_reset(env, ROOT, 6000, 'train', 'historical-default')
            with self.assertRaises(StopBeforeNative):
                puck.authored_reset(env, ROOT, 7100, 'on_policy_collection', 'fixture-explicit',
                                    explicit_layout=on_policy.mint_layouts(FIXTURE_IDS)[0])
            with self.assertRaises(ValueError):
                puck.authored_reset(env, ROOT, 7100, 'on_policy_collection', 'fixture-missing')

    def test_fresh_import_does_not_load_torch_or_mujoco(self):
        code = (f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); "
                "import palimpsest.puck_on_policy, palimpsest.puck_profile; "
                "bad=sorted({'torch','mujoco'} & set(sys.modules)); "
                "assert not bad, bad")
        result = subprocess.run([sys.executable, '-I', '-c', code], text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


class PuckReservationAndMintAdmissionTests(unittest.TestCase):
    def api(self, name):
        on_policy = subject()
        self.assertTrue(hasattr(on_policy, name), f'{name} admission API is missing')
        return on_policy, getattr(on_policy, name)

    def reserve(self, directory, before=None, after=None):
        _, reserve = self.api('reserve_scene_roster')
        before = inventory_snapshot() if before is None else before
        after = copy.deepcopy(before) if after is None else after
        return reserve(directory, before, after, lineage_sha256=LINEAGE_SHA256)

    def test_typed_inventory_reserves_exact_stable_self_lineage_atomically(self):
        on_policy, _ = self.api('reserve_scene_roster')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            real_replace = os.replace
            replacements = []

            def replace(source, target):
                source, target = Path(source), Path(target)
                self.assertTrue(source.is_file())
                self.assertFalse(target.exists())
                replacements.append((source.name, target.name))
                real_replace(source, target)

            with patch.object(on_policy.os, 'replace', side_effect=replace):
                result = self.reserve(root, snapshot, copy.deepcopy(snapshot))

            target = root / 'reservation.json'
            self.assertEqual(replacements, [('.reservation.json.pending', 'reservation.json')])
            self.assertEqual(set(result), {'manifest_path', 'manifest_bytes', 'manifest_sha256'})
            self.assertEqual(Path(result['manifest_path']), target)
            self.assertEqual(target.read_bytes(), result['manifest_bytes'])
            manifest = json.loads(result['manifest_bytes'])
            self.assertEqual(result['manifest_bytes'], canonical_bytes(manifest))
            self.assertEqual(result['manifest_sha256'], digest(result['manifest_bytes']))
            self.assertEqual(manifest['scene_ids'], list(RESERVED_IDS))
            self.assertEqual(manifest['lineage_sha256'], LINEAGE_SHA256)
            self.assertEqual(manifest['inventory'], snapshot)
            self.assertEqual(manifest['inventory_before_sha256'], digest(snapshot))
            self.assertEqual(manifest['inventory_after_sha256'], digest(snapshot))
            self.assertEqual(manifest['occupied_scene_ids'], [6000])
            self.assertEqual([item.name for item in root.iterdir()], ['reservation.json'])
            self.assertEqual(on_policy.RESERVED_SCENE_IDS, RESERVED_IDS)

    def test_partial_duplicate_or_out_of_lineage_reserved_rosters_fail(self):
        mutations = {}

        partial = inventory_snapshot()
        partial['records'][-1]['scenes'].pop()
        mutations['partial roster'] = partial

        reordered = inventory_snapshot()
        reordered['records'][-1]['scenes'].reverse()
        mutations['reordered roster'] = reordered

        duplicate = inventory_snapshot()
        duplicate['records'].append(copy.deepcopy(duplicate['records'][-1]))
        duplicate['records'][-1]['name'] = 'duplicate-self-reservation'
        mutations['duplicate lineage'] = duplicate

        wrong_lineage = inventory_snapshot()
        wrong_lineage['records'][-1]['lineage_sha256'] = digest({'wrong': 'lineage'})
        mutations['wrong lineage'] = wrong_lineage

        prior_collision = inventory_snapshot()
        prior_collision['records'][2]['scenes'].append(inventory_scene(6110, 'prior-collision'))
        mutations['prior ID collision'] = prior_collision

        extra_lineage = inventory_snapshot()
        extra_lineage['records'][0]['lineage_sha256'] = LINEAGE_SHA256
        mutations['extra lineage occurrence'] = extra_lineage

        for label, snapshot in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    self.reserve(Path(directory).resolve(), snapshot, copy.deepcopy(snapshot))
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_stale_changing_symlink_alias_and_heldout_inventory_fail(self):
        stable_mutations = {}
        for label, mutate in (
                ('incomplete', lambda item: item.update(complete=False)),
                ('stale refs', lambda item: item.update(remote_refs_fresh=False)),
                ('held-out access', lambda item: item.update(held_out_accessed=True)),
                ('missing root', lambda item: item['roots'][0].update(exists=False)),
                ('unreadable root', lambda item: item['roots'][0].update(readable=False)),
                ('non-directory root', lambda item: item['roots'][0].update(is_directory=False)),
                ('symlink root', lambda item: item['roots'][0].update(is_symlink=True)),
                ('alias root', lambda item: item['roots'][0].update(
                    resolved_path='/synthetic/inventory/alias')),
                ('missing root kind', lambda item: item['roots'].pop(1)),
                ('unknown record kind', lambda item: item['records'][0].update(kind='text')),
                ('unbound record root', lambda item: item['records'][0].update(
                    root='/synthetic/inventory/missing')),
                ('invalid identity', lambda item: item['records'][0].update(
                    identity_sha256='not-a-digest'))):
            snapshot = inventory_snapshot()
            mutate(snapshot)
            stable_mutations[label] = snapshot

        for label, snapshot in stable_mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    self.reserve(Path(directory).resolve(), snapshot, copy.deepcopy(snapshot))
                self.assertEqual(list(Path(directory).iterdir()), [])

        before = inventory_snapshot()
        after = copy.deepcopy(before)
        after['roots'][0]['identity_sha256'] = digest({'changed': 'root'})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.reserve(Path(directory).resolve(), before, after)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_fake_minter_stages_exact_order_and_collection_only_projection(self):
        on_policy, stage = self.api('stage_scene_manifest')
        _, project = self.api('collection_scene_projection')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as scene_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            calls = []

            def minter(scene_id, slot, split):
                calls.append((scene_id, slot, split))
                return fake_candidate(scene_id, slot, split)

            real_replace = os.replace
            replacements = []

            def replace(source, target):
                source, target = Path(source), Path(target)
                self.assertTrue(source.is_file())
                self.assertFalse(target.exists())
                replacements.append((source.name, target.name))
                real_replace(source, target)

            with patch.object(on_policy, 'mint_layouts', side_effect=AssertionError(
                    'the reviewed real minter must remain uninvoked')), \
                    patch.object(on_policy.os, 'replace', side_effect=replace):
                result = stage(Path(scene_directory).resolve(), reservation['manifest_bytes'],
                               minter, inventory_after=copy.deepcopy(snapshot))

            expected_calls = [
                (scene_id, slot, 'on_policy_collection' if slot < 4
                 else 'on_policy_development')
                for slot, scene_id in enumerate(RESERVED_IDS)]
            self.assertEqual(calls, expected_calls)
            self.assertEqual(replacements, [('.scene-manifest.json.pending',
                                             'scene-manifest.json')])
            target = Path(scene_directory) / 'scene-manifest.json'
            manifest_bytes = target.read_bytes()
            manifest = json.loads(manifest_bytes)
            self.assertEqual(manifest_bytes, canonical_bytes(manifest))
            self.assertEqual(manifest['scene_ids'], list(RESERVED_IDS))
            self.assertEqual([row['scene_id'] for row in manifest['scenes']],
                             list(RESERVED_IDS))
            self.assertEqual(result['manifest_sha256'], digest(manifest_bytes))
            self.assertEqual(Path(result['manifest_path']), target)
            projection_bytes = result['collection_projection_bytes']
            self.assertEqual(projection_bytes,
                             project(manifest_bytes, audience='collection'))
            projection = json.loads(projection_bytes)
            self.assertEqual(projection_bytes, canonical_bytes(projection))
            self.assertEqual(projection['scene_ids'], list(RESERVED_IDS[:4]))
            self.assertEqual([row['scene_id'] for row in projection['scenes']],
                             list(RESERVED_IDS[:4]))
            self.assertNotIn(b'6120', projection_bytes)
            self.assertNotIn(b'on_policy_development', projection_bytes)
            self.assertNotIn(b'development-', projection_bytes)
            self.assertNotIn(b'path', projection_bytes)
            for audience in ('development', 'held_out'):
                with self.subTest(audience=audience), self.assertRaises(ValueError):
                    project(manifest_bytes, audience=audience)

    def test_id_and_all_three_identity_collision_classes_fail_closed(self):
        on_policy, identities = self.api('scene_candidate_identities')
        _, stage = self.api('stage_scene_manifest')
        first = fake_candidate(RESERVED_IDS[0], 0, 'on_policy_collection')
        first_identities = identities(first)
        for collision_field in ('canonical_scene_sha256',
                                'scientific_initial_sha256', 'payload_sha256'):
            snapshot = inventory_snapshot()
            snapshot['records'][2]['scenes'][0][collision_field] = \
                first_identities[collision_field]
            with self.subTest(prior_collision=collision_field), \
                    tempfile.TemporaryDirectory() as reservation_directory, \
                    tempfile.TemporaryDirectory() as scene_directory:
                reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
                with self.assertRaisesRegex(ValueError, 'collision'):
                    stage(Path(scene_directory).resolve(), reservation['manifest_bytes'],
                          fake_candidate, inventory_after=copy.deepcopy(snapshot))
                self.assertEqual(list(Path(scene_directory).iterdir()), [])

        source = fake_candidate(RESERVED_IDS[0], 0, 'on_policy_collection')
        objects = {
            'canonical_scene': source['canonical_scene'],
            'scientific_initial': source['scientific_initial'],
            'payload': source['payload'],
        }
        for field, duplicate_value in objects.items():
            snapshot = inventory_snapshot()

            def colliding_minter(scene_id, slot, split, *, field=field,
                                 duplicate_value=duplicate_value):
                candidate = fake_candidate(scene_id, slot, split)
                if scene_id == RESERVED_IDS[4]:
                    candidate[field] = copy.deepcopy(duplicate_value)
                return candidate

            with self.subTest(cross_split_collision=field), \
                    tempfile.TemporaryDirectory() as reservation_directory, \
                    tempfile.TemporaryDirectory() as scene_directory:
                reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
                with self.assertRaisesRegex(ValueError, 'collision'):
                    stage(Path(scene_directory).resolve(), reservation['manifest_bytes'],
                          colliding_minter, inventory_after=copy.deepcopy(snapshot))
                self.assertEqual(list(Path(scene_directory).iterdir()), [])

    def test_minter_layout_inventory_and_publication_failures_leave_no_scene_manifest(self):
        on_policy, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)

            def exploding_minter(scene_id, slot, split):
                if slot == 2:
                    raise RuntimeError('synthetic minter failure')
                return fake_candidate(scene_id, slot, split)

            def invalid_layout_minter(scene_id, slot, split):
                candidate = fake_candidate(scene_id, slot, split)
                if slot == 2:
                    candidate['layout']['goal_xy'] = candidate['layout']['puck_xy'][:]
                return candidate

            changed = copy.deepcopy(snapshot)
            changed['records'][0]['identity_sha256'] = digest({'changed': 'after mint'})
            cases = (
                ('minter', exploding_minter, copy.deepcopy(snapshot), None),
                ('layout', invalid_layout_minter, copy.deepcopy(snapshot), None),
                ('inventory', fake_candidate, changed, None),
                ('fsync', fake_candidate, copy.deepcopy(snapshot), 'fsync'),
                ('rename', fake_candidate, copy.deepcopy(snapshot), 'replace'),
            )
            for label, minter, final_inventory, fault in cases:
                with self.subTest(label=label), tempfile.TemporaryDirectory() as scene_directory:
                    context = (patch.object(on_policy.os, 'fsync', side_effect=OSError('fsync'))
                               if fault == 'fsync' else
                               patch.object(on_policy.os, 'replace', side_effect=OSError('rename'))
                               if fault == 'replace' else patch.object(on_policy.os, 'replace',
                                                                       wraps=os.replace))
                    with context, self.assertRaises((ValueError, RuntimeError, OSError)):
                        stage(Path(scene_directory).resolve(), reservation['manifest_bytes'],
                              minter, inventory_after=final_inventory)
                    self.assertEqual(list(Path(scene_directory).iterdir()), [])

    def test_output_alias_and_symlink_paths_are_rejected_without_publication(self):
        _, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as parent_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            parent = Path(parent_directory).resolve()
            real = parent / 'real'; real.mkdir()
            alias = parent / 'alias'; alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                stage(alias, reservation['manifest_bytes'], fake_candidate,
                      inventory_after=copy.deepcopy(snapshot))
            self.assertEqual(list(real.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
