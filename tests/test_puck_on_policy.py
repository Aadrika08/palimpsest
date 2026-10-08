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
PROTOCOL_SHA256 = 'fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13'


def canonical_bytes(value):
    return json.dumps(value, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8') + b'\n'


def digest(value):
    raw = value if type(value) is bytes else canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def commit_receipt(name, manifest_bytes, *, protocol_sha256, reservation_sha256=None):
    return {
        'version': 1,
        'kind': 'puck-on-policy-publication-commit-v1',
        'target': name,
        'manifest_sha256': digest(manifest_bytes),
        'manifest_bytes': len(manifest_bytes),
        'reservation_sha256': reservation_sha256 or digest(manifest_bytes),
        'protocol_sha256': protocol_sha256,
    }


def write_synthetic_publication(root, name, manifest, *, protocol_sha256,
                                reservation_sha256=None):
    raw = canonical_bytes(manifest)
    target = root / name
    target.write_bytes(raw)
    receipt = commit_receipt(
        name, raw, protocol_sha256=protocol_sha256,
        reservation_sha256=reservation_sha256)
    target.with_name(f'{name}.commit.json').write_bytes(canonical_bytes(receipt))
    return target


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
        'role': 'self_reservation', 'lineage_sha256': PROTOCOL_SHA256,
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


def fake_candidate(scene_id, slot, split):
    y = -0.7 + slot * 0.2
    layout = {
        'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': scene_id,
        'split': split, 'slot': slot,
        'rover_pose': [-1.0, float(y + 0.25), float(-0.2 + slot * 0.05)],
        'puck_xy': [-0.25, float(y)], 'goal_xy': [1.0, float(y)],
        'initial_qvel': 'all zeros',
    }
    return layout


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
        import numpy as np

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
        return reserve(directory, before, after, lineage_sha256=PROTOCOL_SHA256)

    def test_reservation_lineage_and_receipt_bind_the_frozen_protocol(self):
        on_policy, reserve = self.api('reserve_scene_roster')
        self.assertEqual(getattr(on_policy, 'PROTOCOL_SHA256', None), PROTOCOL_SHA256)
        snapshot = inventory_snapshot()
        wrong = 'a' * 64
        wrong_snapshot = copy.deepcopy(snapshot)
        wrong_snapshot['records'][-1]['lineage_sha256'] = wrong
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaisesRegex(ValueError, 'protocol'):
                reserve(root, wrong_snapshot, copy.deepcopy(wrong_snapshot),
                        lineage_sha256=wrong)
            self.assertEqual(list(root.iterdir()), [])

        with tempfile.TemporaryDirectory() as directory:
            result = self.reserve(Path(directory).resolve(), snapshot)
            manifest = json.loads(result['manifest_bytes'])
            receipt = json.loads(result['commit_bytes'])
            self.assertEqual(manifest['lineage_sha256'], PROTOCOL_SHA256)
            self.assertEqual(receipt['protocol_sha256'], PROTOCOL_SHA256)

    def test_reservation_version_rejects_boolean(self):
        on_policy = subject()
        with tempfile.TemporaryDirectory() as directory:
            result = self.reserve(Path(directory).resolve())
            manifest = json.loads(result['manifest_bytes'])
            manifest['version'] = True
            with self.assertRaisesRegex(ValueError, 'schema'):
                on_policy._read_reservation(canonical_bytes(manifest))

    def test_typed_inventory_reserves_exact_stable_self_lineage_atomically(self):
        on_policy, _ = self.api('reserve_scene_roster')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            real_link = os.link
            links = []

            def link(source, target, *arguments, **keywords):
                source, target = Path(source), Path(target)
                self.assertTrue(source.is_file())
                self.assertFalse(target.exists())
                links.append((source.name, target.name))
                real_link(source, target, *arguments, **keywords)

            with patch.object(on_policy.os, 'link', side_effect=link):
                result = self.reserve(root, snapshot, copy.deepcopy(snapshot))

            target = root / 'reservation.json'
            commit = root / 'reservation.json.commit.json'
            self.assertEqual(links, [
                ('.reservation.json.pending', 'reservation.json'),
                ('.reservation.json.commit.pending', 'reservation.json.commit.json'),
            ])
            self.assertEqual(set(result), {
                'manifest_path', 'manifest_bytes', 'manifest_sha256',
                'commit_path', 'commit_bytes', 'commit_sha256'})
            self.assertEqual(Path(result['manifest_path']), target)
            self.assertEqual(target.read_bytes(), result['manifest_bytes'])
            manifest = json.loads(result['manifest_bytes'])
            self.assertEqual(result['manifest_bytes'], canonical_bytes(manifest))
            self.assertEqual(result['manifest_sha256'], digest(result['manifest_bytes']))
            self.assertEqual(manifest['scene_ids'], list(RESERVED_IDS))
            self.assertEqual(manifest['lineage_sha256'], PROTOCOL_SHA256)
            self.assertEqual(manifest['inventory'], snapshot)
            self.assertEqual(manifest['inventory_before_sha256'], digest(snapshot))
            self.assertEqual(manifest['inventory_after_sha256'], digest(snapshot))
            self.assertEqual(manifest['occupied_scene_ids'], [6000])
            receipt = json.loads(result['commit_bytes'])
            self.assertEqual(receipt, commit_receipt(
                'reservation.json', result['manifest_bytes'],
                protocol_sha256=PROTOCOL_SHA256))
            self.assertEqual(commit.read_bytes(), result['commit_bytes'])
            self.assertEqual(result['commit_sha256'], digest(result['commit_bytes']))
            self.assertEqual(sorted(item.name for item in root.iterdir()),
                             ['reservation.json', 'reservation.json.commit.json'])
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
        extra_lineage['records'][0]['lineage_sha256'] = PROTOCOL_SHA256
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

    def test_prior_roster_and_each_identity_class_reject_duplicates(self):
        for field in ('scene_id', 'canonical_scene_sha256',
                      'scientific_initial_sha256', 'payload_sha256'):
            snapshot = inventory_snapshot()
            prior = snapshot['records'][2]['scenes'][0]
            duplicate = inventory_scene(6001, f'duplicate-{field}')
            duplicate[field] = prior[field]
            snapshot['records'][0]['scenes'].append(duplicate)
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, 'collision'):
                    self.reserve(Path(directory).resolve(), snapshot, copy.deepcopy(snapshot))
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

            real_link = os.link
            links = []

            def link(source, target, *arguments, **keywords):
                source, target = Path(source), Path(target)
                self.assertTrue(source.is_file())
                self.assertFalse(target.exists())
                links.append((source.name, target.name))
                real_link(source, target, *arguments, **keywords)

            with patch.object(on_policy, 'mint_layouts', side_effect=AssertionError(
                    'the reviewed real minter must remain uninvoked')), \
                    patch.object(on_policy.os, 'link', side_effect=link):
                result = stage(Path(scene_directory).resolve(), reservation['manifest_path'],
                               minter, inventory_after=copy.deepcopy(snapshot))

            expected_calls = [
                (scene_id, slot, 'on_policy_collection' if slot < 4
                 else 'on_policy_development')
                for slot, scene_id in enumerate(RESERVED_IDS)]
            self.assertEqual(calls, expected_calls)
            self.assertEqual(links, [
                ('.scene-manifest.json.pending', 'scene-manifest.json'),
                ('.scene-manifest.json.commit.pending',
                 'scene-manifest.json.commit.json'),
            ])
            target = Path(scene_directory) / 'scene-manifest.json'
            manifest_bytes = target.read_bytes()
            manifest = json.loads(manifest_bytes)
            self.assertEqual(manifest_bytes, canonical_bytes(manifest))
            self.assertEqual(manifest['scene_ids'], list(RESERVED_IDS))
            self.assertEqual([row['scene_id'] for row in manifest['scenes']],
                             list(RESERVED_IDS))
            self.assertEqual(result['manifest_sha256'], digest(manifest_bytes))
            self.assertEqual(Path(result['manifest_path']), target)
            self.assertEqual(json.loads(result['commit_bytes']), commit_receipt(
                'scene-manifest.json', manifest_bytes,
                protocol_sha256=PROTOCOL_SHA256,
                reservation_sha256=reservation['manifest_sha256']))
            self.assertEqual(Path(result['commit_path']),
                             target.with_name('scene-manifest.json.commit.json'))
            expected_scene_fields = {
                'scene_id', 'slot', 'split', 'canonical_scene_sha256',
                'scientific_initial_sha256', 'payload_sha256', 'layout'}
            self.assertTrue(all(set(row) == expected_scene_fields
                                for row in manifest['scenes']))
            projection_bytes = result['collection_projection_bytes']
            self.assertEqual(projection_bytes,
                             project(target, reservation_path=reservation['manifest_path'],
                                     audience='collection'))
            projection = json.loads(projection_bytes)
            self.assertEqual(projection_bytes, canonical_bytes(projection))
            self.assertEqual(set(projection), {'version', 'kind', 'scene_ids', 'scenes'})
            self.assertEqual(projection['scene_ids'], list(RESERVED_IDS[:4]))
            self.assertEqual([row['scene_id'] for row in projection['scenes']],
                             list(RESERVED_IDS[:4]))
            self.assertTrue(all(set(row) == expected_scene_fields
                                for row in projection['scenes']))
            self.assertNotIn(b'6120', projection_bytes)
            self.assertNotIn(b'on_policy_development', projection_bytes)
            self.assertNotIn(b'path', projection_bytes)
            self.assertNotIn(b'payload_bytes', projection_bytes)

            def assert_projection_safe(value):
                self.assertNotIsInstance(value, bytes)
                if type(value) is dict:
                    for key, child in value.items():
                        self.assertNotIn('path', key.lower())
                        self.assertNotEqual(key, 'payload_bytes')
                        assert_projection_safe(child)
                elif type(value) is list:
                    for child in value:
                        assert_projection_safe(child)
                elif type(value) is str:
                    self.assertNotIn('on_policy_development', value)

            assert_projection_safe(projection)
            for audience in ('development', 'held_out'):
                with self.subTest(audience=audience), self.assertRaises(ValueError):
                    project(target, reservation_path=reservation['manifest_path'],
                            audience=audience)

    def test_layout_derived_identities_and_all_collision_classes_fail_closed(self):
        on_policy, identities = self.api('scene_candidate_identities')
        _, stage = self.api('stage_scene_manifest')
        first = fake_candidate(RESERVED_IDS[0], 0, 'on_policy_collection')
        first_identities = identities(first)
        canonical_scene = {
            'version': 1, 'kind': 'puck-on-policy-canonical-scene-v1',
            'rover_pose': first['rover_pose'], 'puck_xy': first['puck_xy'],
            'goal_xy': first['goal_xy']}
        scientific_initial = canonical_scene | {
            'kind': 'puck-on-policy-scientific-initial-v1',
            'initial_qvel': 'all zeros'}
        self.assertEqual(first_identities, {
            'canonical_scene_sha256': digest(canonical_scene),
            'scientific_initial_sha256': digest(scientific_initial),
            'payload_sha256': digest(canonical_bytes(first)),
        })
        legacy_caller_markers = {
            'layout': first, 'canonical_scene': {'marker': 'changed'},
            'scientific_initial': {'marker': 'changed'},
            'payload': {'marker': 'changed'}}
        with self.assertRaises(ValueError):
            identities(legacy_caller_markers)

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
                    stage(Path(scene_directory).resolve(), reservation['manifest_path'],
                          fake_candidate, inventory_after=copy.deepcopy(snapshot))
                self.assertEqual(list(Path(scene_directory).iterdir()), [])

        def duplicate_physical_scene(scene_id, slot, split):
            row = fake_candidate(scene_id, slot, split)
            if scene_id == RESERVED_IDS[4]:
                for field in ('rover_pose', 'puck_xy', 'goal_xy', 'initial_qvel'):
                    row[field] = copy.deepcopy(first[field])
            return row

        def metadata_evasion(scene_id, slot, split):
            row = duplicate_physical_scene(scene_id, slot, split)
            if scene_id == RESERVED_IDS[4]:
                row['identity_marker'] = 'changed-to-evade-collision'
            return row

        for label, minter in (('physical duplicate', duplicate_physical_scene),
                              ('changed metadata', metadata_evasion)):
            snapshot = inventory_snapshot()
            with self.subTest(label=label), \
                    tempfile.TemporaryDirectory() as reservation_directory, \
                    tempfile.TemporaryDirectory() as scene_directory:
                reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
                with self.assertRaises((ValueError, RuntimeError)):
                    stage(Path(scene_directory).resolve(), reservation['manifest_path'],
                          minter, inventory_after=copy.deepcopy(snapshot))
                self.assertEqual(list(Path(scene_directory).iterdir()), [])

    def test_scene_manifest_reader_deeply_rejects_tamper_and_unbound_hashes(self):
        _, stage = self.api('stage_scene_manifest')
        _, project = self.api('collection_scene_projection')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as source_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            published = stage(Path(source_directory).resolve(), reservation['manifest_path'],
                              fake_candidate, inventory_after=copy.deepcopy(snapshot))
            original = json.loads(Path(published['manifest_path']).read_bytes())
            mutations = {}

            extra = copy.deepcopy(original); extra['scenes'].append(copy.deepcopy(extra['scenes'][-1]))
            mutations['extra scene'] = extra
            missing = copy.deepcopy(original); missing['scenes'].pop()
            mutations['missing scene'] = missing
            unbound = copy.deepcopy(original); unbound['scenes'][0]['payload_sha256'] = '0' * 64
            mutations['unbound payload hash'] = unbound
            path = copy.deepcopy(original); path['scenes'][0]['layout']['development_path'] = '/dev/scene'
            mutations['nested development path'] = path
            payload_bytes = copy.deepcopy(original); payload_bytes['scenes'][0]['payload_bytes'] = 'secret'
            mutations['payload bytes field'] = payload_bytes
            wrong_id = copy.deepcopy(original); wrong_id['scenes'][0]['scene_id'] = 6120
            mutations['wrong ordered ID'] = wrong_id
            lineage = copy.deepcopy(original); lineage['lineage_sha256'] = '1' * 64
            mutations['unbound lineage'] = lineage
            reservation_hash = copy.deepcopy(original); reservation_hash['reservation_sha256'] = '2' * 64
            mutations['unbound reservation'] = reservation_hash

            for label, manifest in mutations.items():
                with self.subTest(label=label), tempfile.TemporaryDirectory() as forged_directory:
                    target = write_synthetic_publication(
                        Path(forged_directory).resolve(), 'scene-manifest.json', manifest,
                        protocol_sha256=PROTOCOL_SHA256,
                        reservation_sha256=reservation['manifest_sha256'])
                    with self.assertRaises(ValueError):
                        project(target, reservation_path=reservation['manifest_path'],
                                audience='collection')

    def test_scene_manifest_reader_rechecks_self_consistent_prior_collision(self):
        on_policy, identities = self.api('scene_candidate_identities')
        _, stage = self.api('stage_scene_manifest')
        _, project = self.api('collection_scene_projection')
        forged_layout = fake_candidate(RESERVED_IDS[0], 0, 'on_policy_collection')
        for field in ('rover_pose', 'puck_xy', 'goal_xy'):
            forged_layout[field][1] += .0625
        forged_identities = identities(forged_layout)
        snapshot = inventory_snapshot()
        snapshot['records'][2]['scenes'][0]['canonical_scene_sha256'] = \
            forged_identities['canonical_scene_sha256']

        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as source_directory, \
                tempfile.TemporaryDirectory() as forged_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            published = stage(Path(source_directory).resolve(), reservation['manifest_path'],
                              fake_candidate, inventory_after=copy.deepcopy(snapshot))
            manifest = json.loads(Path(published['manifest_path']).read_bytes())
            manifest['scenes'][0]['layout'] = forged_layout
            manifest['scenes'][0].update(forged_identities)
            target = write_synthetic_publication(
                Path(forged_directory).resolve(), 'scene-manifest.json', manifest,
                protocol_sha256=PROTOCOL_SHA256,
                reservation_sha256=reservation['manifest_sha256'])
            with self.assertRaisesRegex(ValueError, 'collision'):
                project(target, reservation_path=reservation['manifest_path'],
                        audience='collection')

    def test_path_reader_requires_exact_positive_commit_receipt(self):
        _, stage = self.api('stage_scene_manifest')
        _, project = self.api('collection_scene_projection')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as source_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            published = stage(Path(source_directory).resolve(), reservation['manifest_path'],
                              fake_candidate, inventory_after=copy.deepcopy(snapshot))
            manifest_bytes = Path(published['manifest_path']).read_bytes()
            valid = commit_receipt(
                'scene-manifest.json', manifest_bytes,
                protocol_sha256=PROTOCOL_SHA256,
                reservation_sha256=reservation['manifest_sha256'])
            mutations = {'missing receipt': None, 'malformed receipt': b'{\n'}
            for label, field, value in (
                    ('extra field', 'extra', True),
                    ('wrong target', 'target', 'other.json'),
                    ('wrong manifest hash', 'manifest_sha256', '0' * 64),
                    ('wrong manifest size', 'manifest_bytes', len(manifest_bytes) + 1),
                    ('boolean manifest size', 'manifest_bytes', True),
                    ('wrong reservation', 'reservation_sha256', '1' * 64),
                    ('wrong protocol', 'protocol_sha256', '2' * 64)):
                receipt = copy.deepcopy(valid); receipt[field] = value
                mutations[label] = canonical_bytes(receipt)
            mutations['noncanonical receipt'] = json.dumps(
                valid, sort_keys=True, indent=2).encode('utf-8')

            for label, receipt_bytes in mutations.items():
                with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    target = root / 'scene-manifest.json'
                    target.write_bytes(manifest_bytes)
                    if receipt_bytes is not None:
                        target.with_name('scene-manifest.json.commit.json').write_bytes(
                            receipt_bytes)
                    with self.assertRaises(ValueError):
                        project(target, reservation_path=reservation['manifest_path'],
                                audience='collection')

            with tempfile.TemporaryDirectory() as directory, \
                    tempfile.TemporaryDirectory() as outside:
                root = Path(directory).resolve(); target = root / 'scene-manifest.json'
                target.write_bytes(manifest_bytes)
                external = Path(outside).resolve() / 'commit.json'
                external.write_bytes(canonical_bytes(valid))
                target.with_name('scene-manifest.json.commit.json').symlink_to(external)
                with self.assertRaises(ValueError):
                    project(target, reservation_path=reservation['manifest_path'],
                            audience='collection')

    def test_publication_reader_rejects_target_and_receipt_hardlink_replay(self):
        on_policy = subject()
        for victim_name in ('reservation.json', 'reservation.json.commit.json'):
            with self.subTest(victim=victim_name), \
                    tempfile.TemporaryDirectory() as directory, \
                    tempfile.TemporaryDirectory() as outside:
                root = Path(directory).resolve()
                result = self.reserve(root)
                target = Path(result['manifest_path'])
                victim = root / victim_name
                os.link(victim, Path(outside).resolve() / 'external-hardlink')
                with self.assertRaisesRegex(ValueError, 'linked'):
                    on_policy._read_published_reservation(target)

    def test_publication_reader_rejects_same_byte_file_and_parent_rebinding(self):
        on_policy = subject()
        real_path_open = Path.open
        real_os_open = os.open

        for victim_name in ('reservation.json', 'reservation.json.commit.json'):
            with self.subTest(victim=victim_name), \
                    tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                result = self.reserve(root)
                target = Path(result['manifest_path'])
                victim = root / victim_name
                replacement = root / f'{victim_name}.replacement'
                replacement.write_bytes(victim.read_bytes())
                raced = {'done': False}

                def race():
                    if not raced['done']:
                        raced['done'] = True
                        os.replace(replacement, victim)

                def path_open(path, *arguments, **keywords):
                    handle = real_path_open(path, *arguments, **keywords)
                    if Path(path) == victim:
                        race()
                    return handle

                def descriptor_open(path, *arguments, **keywords):
                    descriptor = real_os_open(path, *arguments, **keywords)
                    if Path(path).name == victim.name:
                        race()
                    return descriptor

                with patch.object(Path, 'open', new=path_open), \
                        patch.object(on_policy.os, 'open', side_effect=descriptor_open), \
                        self.assertRaisesRegex(ValueError, 'rebound'):
                    on_policy._read_published_reservation(target)
                self.assertTrue(raced['done'])

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            live = base / 'live'; live.mkdir()
            result = self.reserve(live)
            target = Path(result['manifest_path'])
            standby = base / 'standby'; standby.mkdir()
            for name in ('reservation.json', 'reservation.json.commit.json'):
                (standby / name).write_bytes((live / name).read_bytes())
            displaced = base / 'displaced'
            raced = {'done': False}

            def swap_parent():
                if not raced['done']:
                    raced['done'] = True
                    live.rename(displaced)
                    standby.rename(live)

            def path_open(path, *arguments, **keywords):
                handle = real_path_open(path, *arguments, **keywords)
                if Path(path).name == 'reservation.json':
                    swap_parent()
                return handle

            def descriptor_open(path, *arguments, **keywords):
                descriptor = real_os_open(path, *arguments, **keywords)
                if (keywords.get('dir_fd') is not None and
                        Path(path).name == 'reservation.json'):
                    swap_parent()
                return descriptor

            with patch.object(Path, 'open', new=path_open), \
                    patch.object(on_policy.os, 'open', side_effect=descriptor_open), \
                    self.assertRaisesRegex(ValueError, 'parent'):
                on_policy._read_published_reservation(target)
            self.assertTrue(raced['done'])

    def test_publication_reader_rechecks_blockers_after_final_secure_read(self):
        on_policy = subject()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            result = self.reserve(root)
            target = Path(result['manifest_path'])
            quarantine = root / '.reservation.json.quarantine'
            real_read = on_policy._read_exact_file
            reads = []

            def read_exact(*arguments, **keywords):
                raw = real_read(*arguments, **keywords)
                reads.append(Path(arguments[1]).name)
                if len(reads) == 4:
                    quarantine.write_bytes(b'synthetic-late-quarantine\n')
                return raw

            with patch.object(on_policy, '_read_exact_file', side_effect=read_exact), \
                    self.assertRaisesRegex(ValueError, 'changed'):
                on_policy._read_published_reservation(target)
            self.assertEqual(reads, [
                'reservation.json', 'reservation.json.commit.json',
                'reservation.json', 'reservation.json.commit.json'])
            self.assertTrue(quarantine.is_file())

    def test_preexisting_commit_paths_refuse_before_minting(self):
        _, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            for name in ('scene-manifest.json.commit.json',
                         '.scene-manifest.json.commit.pending'):
                with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve(); marker = root / name
                    marker.write_bytes(b'preexisting')
                    calls = []

                    def forbidden_minter(*arguments):
                        calls.append(arguments)
                        return fake_candidate(*arguments)

                    with self.assertRaises(ValueError):
                        stage(root, reservation['manifest_path'], forbidden_minter,
                              inventory_after=copy.deepcopy(snapshot))
                    self.assertEqual(calls, [])
                    self.assertEqual(list(root.iterdir()), [marker])

    def test_target_and_receipt_publication_never_overwrite_raced_destinations(self):
        on_policy, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        racer = b'synthetic-raced-destination\n'
        with tempfile.TemporaryDirectory() as reservation_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            for victim_name in ('scene-manifest.json',
                                'scene-manifest.json.commit.json'):
                with self.subTest(victim=victim_name), \
                        tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    victim = root / victim_name
                    real_replace = os.replace
                    real_link = os.link

                    def insert_racer(destination):
                        if Path(destination) == victim and not victim.exists():
                            victim.write_bytes(racer)

                    def replace(source, destination, *arguments, **keywords):
                        insert_racer(destination)
                        return real_replace(source, destination, *arguments, **keywords)

                    def link(source, destination, *arguments, **keywords):
                        insert_racer(destination)
                        return real_link(source, destination, *arguments, **keywords)

                    with patch.object(on_policy.os, 'replace', side_effect=replace), \
                            patch.object(on_policy.os, 'link', side_effect=link), \
                            self.assertRaises(FileExistsError):
                        stage(root, reservation['manifest_path'], fake_candidate,
                              inventory_after=copy.deepcopy(snapshot))
                    self.assertEqual(victim.read_bytes(), racer)
                    with self.assertRaises(ValueError):
                        on_policy._read_publication(
                            root / 'scene-manifest.json', 'scene-manifest.json')

    def test_quarantine_removal_is_the_final_publication_syscall(self):
        on_policy, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            root = Path(directory).resolve()
            events = []
            real_fsync_directory = on_policy._fsync_directory
            real_unlink = Path.unlink

            def fsync_directory(path):
                if Path(path) == root:
                    events.append(('fsync-directory', None))
                return real_fsync_directory(path)

            def unlink(path, *arguments, **keywords):
                if Path(path).parent == root:
                    events.append(('unlink', Path(path).name))
                return real_unlink(path, *arguments, **keywords)

            with patch.object(on_policy, '_fsync_directory', side_effect=fsync_directory), \
                    patch.object(Path, 'unlink', new=unlink):
                stage(root, reservation['manifest_path'], fake_candidate,
                      inventory_after=copy.deepcopy(snapshot))
            self.assertEqual(events[-1],
                             ('unlink', '.scene-manifest.json.quarantine'))

    def test_compounded_postcommit_failure_never_exposes_false_success(self):
        on_policy = subject()
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / 'reservation.json'
            commit = root / 'reservation.json.commit.json'
            commit_pending = root / '.reservation.json.commit.pending'
            quarantine = root / '.reservation.json.quarantine'
            real_fsync_directory = on_policy._fsync_directory
            real_replace = os.replace
            real_unlink = Path.unlink
            postcommit_faults = []

            def final_durability_failure(path):
                if target.exists() and commit.exists() and not quarantine.exists():
                    postcommit_faults.append('postcommit-fsync')
                    raise OSError('final durability failure')
                return real_fsync_directory(path)

            def receipt_demotion_failure(source, destination, *arguments, **keywords):
                if Path(source) == commit and Path(destination) == commit_pending:
                    raise OSError('receipt demotion failed')
                return real_replace(source, destination, *arguments, **keywords)

            def receipt_unlink_failure(path, *arguments, **keywords):
                if Path(path) == commit:
                    raise OSError('receipt unlink failed')
                return real_unlink(path, *arguments, **keywords)

            failed = False
            with patch.object(on_policy, '_fsync_directory',
                              side_effect=final_durability_failure), \
                    patch.object(on_policy.os, 'replace',
                                 side_effect=receipt_demotion_failure), \
                    patch.object(Path, 'unlink', new=receipt_unlink_failure), \
                    patch.object(on_policy, '_remove_failed_target', create=True,
                                 side_effect=OSError('target unlink failed')), \
                    patch.object(on_policy, '_retain_quarantine', create=True,
                                 side_effect=OSError('quarantine recreation failed')):
                try:
                    self.reserve(root, snapshot, copy.deepcopy(snapshot))
                except OSError:
                    failed = True

            if failed:
                self.assertTrue(postcommit_faults)
                with self.assertRaises(ValueError):
                    on_policy._read_published_reservation(target)
            else:
                self.assertEqual(postcommit_faults, [])
                raw, manifest = on_policy._read_published_reservation(target)
                self.assertEqual(raw, canonical_bytes(manifest))

    def test_commit_receipt_is_attempted_only_after_target_directory_fsync(self):
        on_policy, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory, \
                tempfile.TemporaryDirectory() as scene_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            root = Path(scene_directory).resolve()
            target = root / 'scene-manifest.json'
            events = []
            real_directory_fsync = on_policy._fsync_directory

            def directory_fsync(path):
                if target.exists() and 'target-directory-fsync' not in events:
                    events.append('target-directory-fsync')
                return real_directory_fsync(path)

            def write_receipt(path, raw):
                self.assertTrue(target.exists())
                self.assertIn('target-directory-fsync', events)
                events.append('receipt-write')
                with Path(path).open('xb') as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())

            with patch.object(on_policy, '_fsync_directory', side_effect=directory_fsync), \
                    patch.object(on_policy, '_write_commit_receipt', create=True,
                                 side_effect=write_receipt):
                stage(root, reservation['manifest_path'], fake_candidate,
                      inventory_after=copy.deepcopy(snapshot))
            self.assertIn('receipt-write', events)
            self.assertLess(events.index('target-directory-fsync'),
                            events.index('receipt-write'))

    def test_commit_receipt_write_fsync_publication_and_admission_fail_closed(self):
        on_policy, stage = self.api('stage_scene_manifest')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            real_link = os.link
            real_directory_fsync = on_policy._fsync_directory

            def partial_then_fsync_failure(path, raw):
                Path(path).write_bytes(raw[:8])
                raise OSError('commit receipt fsync')

            def receipt_link_failure(source, target, *arguments, **keywords):
                if Path(target).name == 'scene-manifest.json.commit.json':
                    raise OSError('commit receipt publication')
                return real_link(source, target, *arguments, **keywords)

            for label, context_factory in (
                    ('write', lambda: patch.object(
                        on_policy, '_write_commit_receipt', create=True,
                        side_effect=OSError('commit receipt write'))),
                    ('fsync', lambda: patch.object(
                        on_policy, '_write_commit_receipt', create=True,
                        side_effect=partial_then_fsync_failure)),
                    ('exclusive publication', lambda: patch.object(
                        on_policy.os, 'link', side_effect=receipt_link_failure)),
                    ('admission fsync', lambda: patch.object(
                        on_policy, '_fsync_directory', side_effect=lambda root: (
                            (_ for _ in ()).throw(OSError('commit receipt admission fsync'))
                            if (Path(root) / 'scene-manifest.json.commit.json').exists()
                            and (Path(root) / '.scene-manifest.json.quarantine').exists()
                            else real_directory_fsync(root))))):
                with self.subTest(label=label), tempfile.TemporaryDirectory() as directory, \
                        context_factory():
                    root = Path(directory).resolve()
                    with self.assertRaises(OSError):
                        stage(root, reservation['manifest_path'], fake_candidate,
                              inventory_after=copy.deepcopy(snapshot))
                    paths = on_policy._publication_paths(root, 'scene-manifest.json')
                    self.assertTrue(any((paths[name].exists() or paths[name].is_symlink())
                                        for name in ('pending', 'quarantine', 'commit_pending')))
                    with self.assertRaises(ValueError):
                        on_policy._read_publication(paths['target'], 'scene-manifest.json')

    def test_minter_layout_inventory_and_publication_failures_are_unreadable(self):
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
                    candidate['goal_xy'] = candidate['puck_xy'][:]
                return candidate

            changed = copy.deepcopy(snapshot)
            changed['records'][0]['identity_sha256'] = digest({'changed': 'after mint'})
            cases = (
                ('minter', exploding_minter, copy.deepcopy(snapshot), None),
                ('layout', invalid_layout_minter, copy.deepcopy(snapshot), None),
                ('inventory', fake_candidate, changed, None),
                ('fsync', fake_candidate, copy.deepcopy(snapshot), 'fsync'),
                ('directory fsync', fake_candidate, copy.deepcopy(snapshot), 'directory_fsync'),
                ('exclusive publication', fake_candidate, copy.deepcopy(snapshot), 'link'),
            )
            for label, minter, final_inventory, fault in cases:
                with self.subTest(label=label), tempfile.TemporaryDirectory() as scene_directory:
                    fsync_calls = []
                    real_fsync = os.fsync

                    def directory_fsync(file_descriptor):
                        fsync_calls.append(file_descriptor)
                        if len(fsync_calls) == 4:
                            raise OSError('directory fsync')
                        return real_fsync(file_descriptor)

                    context = (
                        patch.object(on_policy.os, 'fsync', side_effect=OSError('fsync'))
                        if fault == 'fsync' else
                        patch.object(on_policy.os, 'fsync', side_effect=directory_fsync)
                        if fault == 'directory_fsync' else
                        patch.object(on_policy.os, 'link', side_effect=OSError('link'))
                        if fault == 'link' else patch.object(
                            on_policy.os, 'link', wraps=os.link))
                    with context, self.assertRaises((ValueError, RuntimeError, OSError)):
                        root = Path(scene_directory).resolve()
                        stage(root, reservation['manifest_path'],
                              minter, inventory_after=final_inventory)
                    paths = on_policy._publication_paths(root, 'scene-manifest.json')
                    with self.assertRaises(ValueError):
                        on_policy._read_publication(paths['target'], 'scene-manifest.json')
                    if fault is None:
                        self.assertEqual(list(root.iterdir()), [])
                    else:
                        self.assertTrue(any(
                            paths[name].exists() or paths[name].is_symlink()
                            for name in ('pending', 'quarantine', 'commit_pending')))

    def test_publication_failures_retain_a_reader_visible_blocker(self):
        on_policy, stage = self.api('stage_scene_manifest')
        _, project = self.api('collection_scene_projection')
        snapshot = inventory_snapshot()
        with tempfile.TemporaryDirectory() as reservation_directory:
            reservation = self.reserve(Path(reservation_directory).resolve(), snapshot)
            real_fsync = os.fsync
            calls = []

            def fail_target_directory_fsync(file_descriptor):
                calls.append(file_descriptor)
                if len(calls) == 4:
                    raise OSError('target directory fsync failed')
                return real_fsync(file_descriptor)

            with tempfile.TemporaryDirectory() as scene_directory, \
                    patch.object(on_policy.os, 'fsync',
                                 side_effect=fail_target_directory_fsync):
                root = Path(scene_directory).resolve()
                target = root / 'scene-manifest.json'
                with self.assertRaises(OSError):
                    stage(root, reservation['manifest_path'], fake_candidate,
                          inventory_after=copy.deepcopy(snapshot))
                paths = on_policy._publication_paths(root, target.name)
                self.assertTrue(any(paths[name].exists() for name in
                                    ('pending', 'quarantine', 'commit_pending')))
                with self.assertRaises(ValueError):
                    project(target, reservation_path=reservation['manifest_path'],
                            audience='collection')

            real_unlink = Path.unlink
            with tempfile.TemporaryDirectory() as scene_directory:
                root = Path(scene_directory).resolve()
                target = root / 'scene-manifest.json'
                quarantine = root / '.scene-manifest.json.quarantine'

                def fail_final_commit(path, *arguments, **keywords):
                    if Path(path) == quarantine:
                        raise OSError('final quarantine removal failed')
                    return real_unlink(path, *arguments, **keywords)

                with patch.object(Path, 'unlink', new=fail_final_commit), \
                        self.assertRaises(OSError):
                    stage(root, reservation['manifest_path'], fake_candidate,
                          inventory_after=copy.deepcopy(snapshot))
                self.assertTrue(quarantine.exists())
                with self.assertRaisesRegex(ValueError, 'quarant'):
                    project(target, reservation_path=reservation['manifest_path'],
                            audience='collection')

            reservation_quarantine = Path(reservation['manifest_path']).with_name(
                '.reservation.json.quarantine')
            reservation_quarantine.write_bytes(b'indeterminate')
            minter_calls = []

            def forbidden_minter(*arguments):
                minter_calls.append(arguments)
                raise AssertionError('quarantined reservation reached minter')

            with tempfile.TemporaryDirectory() as scene_directory:
                with self.assertRaisesRegex(ValueError, 'quarant'):
                    stage(Path(scene_directory).resolve(), reservation['manifest_path'],
                          forbidden_minter, inventory_after=copy.deepcopy(snapshot))
                self.assertEqual(minter_calls, [])
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
                stage(alias, reservation['manifest_path'], fake_candidate,
                      inventory_after=copy.deepcopy(snapshot))
            self.assertEqual(list(real.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
