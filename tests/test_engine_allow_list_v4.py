"""Amendment 2: the Engine.open research-binding allow-list gains exactly NavigationBindingV4."""
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from palimpsest import (male_navigation_research as nav2, male_navigation_research_v4 as nav4, male_recovery_heldout,
                        male_recovery_research, male_research)
from palimpsest.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = '6666523'
HUNK = ["            if not admitted:",
        "                from .male_navigation_research_v4 import Binding as NavigationBindingV4",
        "                admitted = type(research_binding) is NavigationBindingV4",
        "                if admitted and (restore_snapshot is not None or replace_controller or memory_u is not None):",
        "                    raise ValueError('Navigation research permits only fresh roots')"]
TYPES = (male_research.Binding, male_recovery_research.Binding, male_recovery_heldout.Binding, nav2.Binding, nav4.Binding)


def make(cls): return object.__new__(cls)


class AllowList(unittest.TestCase):
    def open(self, binding, **kw):
        return Engine.open(ROOT, ROOT, ROOT/'unused', controller='male-original', research_binding=binding, **kw)

    def test_every_admitted_type_reaches_its_own_resolve_and_nothing_else_does(self):
        for cls in TYPES:
            with patch.object(cls, 'resolve', side_effect=RuntimeError('boundary')) as resolve, patch('palimpsest.records.RunWriter') as writer:
                with self.assertRaisesRegex(RuntimeError, 'boundary'): self.open(make(cls), expected_policy_identity={})
                self.assertEqual(resolve.call_count, 1); writer.assert_not_called()

    def test_subclasses_and_unknown_objects_are_refused_before_resolve(self):
        for cls in TYPES:
            sub = type('Sub', (cls,), {})
            with patch.object(cls, 'resolve') as resolve:
                with self.assertRaisesRegex(ValueError, 'unsupported trusted'): self.open(make(sub))
                resolve.assert_not_called()
        for other in ({}, object(), 'x'):
            with self.assertRaisesRegex(ValueError, 'unsupported trusted'): self.open(other)

    def test_navigation_types_refuse_non_fresh_roots_and_resolve_is_not_reached(self):
        for cls in (nav2.Binding, nav4.Binding):
            with patch.object(cls, 'resolve') as resolve:
                for kw in ({'restore_snapshot': {}}, {'replace_controller': True}, {'memory_u': {}}):
                    with self.assertRaises(ValueError): self.open(make(cls), **kw)
                resolve.assert_not_called()

    def test_engine_diff_against_the_pre_amendment_commit_is_exactly_the_declared_hunk(self):
        try:
            diff = subprocess.run(['git', 'diff', '--unified=0', BASE_COMMIT, '--', 'src/palimpsest/engine.py'], cwd=ROOT,
                                  capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('git history unavailable')
        lines = [l for l in diff.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        self.assertEqual(lines, ['+' + h for h in HUNK])


if __name__ == '__main__': unittest.main()
