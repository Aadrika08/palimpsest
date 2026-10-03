"""Byte fixtures only; no MuJoCo import, recorded assets, or native qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class PuckConstructionComparisonTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'scripts/puck_construction_compare.py'
        self.assertTrue(path.is_file(), 'fixed native comparison helper is missing')
        spec = importlib.util.spec_from_file_location('puck_construction_compare', path)
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
        self.contract = json.loads((ROOT / 'docs/plans/m6-puck-construction-v4.json').read_text())['native_data_comparison']
        self.fields = {name: (start, size) for name, start, size in self.contract['fields']}
        # This is an authored byte fixture, never a native model. Only its model
        # hash replaces the real model pin in this private test contract copy.
        model = b'\x01' + struct.pack('<QQ', 119881, 119881) + bytes(119881)
        self.contract['model_sha256'] = hashlib.sha256(model).hexdigest()
        data = bytearray(347881)
        data[0] = 1
        data[1:119899] = model
        for _, start, size in self.contract['fields']:
            struct.pack_into('<Q', data, start-8, size)
        for name, value in self.contract['dimensions'].items():
            struct.pack_into('<i', data, self.fields[name][0], value)
        for name, values in [('iM_rownnz', [1,2,3,4,5,6,7,7,7,8]),
                             ('iM_rowadr', [0,1,3,6,10,15,21,28,35,42])]:
            struct.pack_into('<10i', data, self.fields[name][0], *values)
        self.data = bytes(data)

    def compare(self, other, left=None):
        return self.helper.compare_native_data(self.data if left is None else left,
                                               other, self.contract)

    def changed(self, name, relative=0):
        other = bytearray(self.data)
        other[self.fields[name][0]+relative] ^= 1
        return bytes(other)

    def test_identical_fixture_and_exact_three_exclusions_without_mutation(self):
        self.assertTrue(self.compare(self.data)['raw_native_bytes_equal'])
        changed = bytearray(self.data)
        # Independent, hand-checked ABI offsets and sparse extent, not helper output.
        allowed = [(279971+i*16, 279979+i*16) for i in range(15)]
        allowed += [(331125+i*576+572, 331125+(i+1)*576) for i in range(6)]
        allowed += [(341489,341729), (342137,342617), (343025,343505)]
        for start, end in allowed:
            changed[start:end] = b'\x01' * (end-start)
        other = bytes(changed)
        result = self.compare(other)
        self.assertTrue(result['defined_native_bytes_equal'])
        self.assertFalse(result['raw_native_bytes_equal'])
        self.assertEqual(result['excluded_bytes'], 1344)
        self.assertEqual(result['compared_bytes'], 346537)
        self.assertEqual(result['different_excluded_bytes'], 1344)
        self.assertEqual(other, bytes(changed))
        self.assertEqual(result['raw_sha256'], [hashlib.sha256(self.data).hexdigest(), hashlib.sha256(other).hexdigest()])

    def test_rejects_changed_active_sparse_values_even_at_last_used_entry(self):
        for name, size in [('iM_colind',4), ('iM',8), ('iLD',8)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.compare(self.changed(name,49*size))

    def test_rejects_contact_fields_timer_counts_and_timer_padding(self):
        for name, relative in [('contact',0), ('contact',568), ('timer',8), ('timer',12)]:
            with self.subTest(name=name,relative=relative), self.assertRaises(ValueError):
                self.compare(self.changed(name,relative))

    def test_rejects_integration_state_and_other_cache_changes(self):
        for name in ('qpos','qvel','qacc_warmstart','ctrl','qfrc_applied','xfrc_applied','time','cacc'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.compare(self.changed(name))

    def test_rejects_truncation_extra_bytes_version_model_or_prefix_corruption(self):
        for value in (self.data[:-1], self.data+b'\0', b'\x02'+self.data[1:],
                      self.data[:42]+b'\x01'+self.data[43:]):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                self.compare(value)
        broken = bytearray(self.data)
        struct.pack_into('<Q', broken, self.fields['iM'][0]-8, 872)
        with self.assertRaises(ValueError): self.compare(bytes(broken), bytes(broken))

    def test_rejects_identical_invalid_dimensions_and_sparse_extents(self):
        for name, relative, value in [('ncon',0,7), ('nidof',0,11), ('nA',0,1),
                                      ('iM_rowadr',4,2), ('iM_rownnz',0,-1),
                                      ('iM_rownnz',36,69), ('iM_rownnz',36,7)]:
            broken = bytearray(self.data)
            struct.pack_into('<i', broken, self.fields[name][0]+relative, value)
            with self.subTest(name=name,value=value), self.assertRaises(ValueError):
                self.compare(bytes(broken),bytes(broken))

    def test_rejects_unsupported_abi_and_malformed_layout(self):
        with patch.object(self.helper.platform, 'machine', return_value='aarch64'):
            with self.assertRaises(ValueError): self.compare(self.data)
        self.contract['fields'][0][1] += 1
        with self.assertRaises(ValueError): self.compare(self.data)


if __name__ == '__main__':
    unittest.main()
