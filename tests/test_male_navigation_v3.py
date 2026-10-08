"""Pure matched-budget schedule checks; no corpus, Torch, MuJoCo, or simulator."""
from dataclasses import FrozenInstanceError
import hashlib
import json
import sys
import unittest

try:
    from palimpsest import male_matched_budget as budget
except ImportError as error:  # RED until Task 1's module exists.
    budget = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


OLD_ROWS = (277, 182, 315, 245, 199, 265, 243, 257, 67, 67)
AUGMENTED_ROWS = OLD_ROWS + (600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186)
OLD_REMAINDER = (212, 140, 242, 188, 153, 203, 186, 197, 51, 51)
AUGMENTED_REMAINDER = (111, 73, 127, 99, 80, 107, 98, 103, 27, 27, 242, 195,
                       200, 242, 79, 242, 241, 98, 80, 241, 111, 75)
OLD_PRESENTATIONS = (6029, 3962, 6857, 5333, 4332, 5768, 5289, 5594, 1458, 1458)
AUGMENTED_PRESENTATIONS = (1773, 1165, 2017, 1569, 1274, 1697, 1556, 1645, 429,
                           429, 3842, 3105, 3176, 3842, 1255, 3842, 3841, 1556,
                           1268, 3841, 1767, 1191)


class MatchedBudgetSchedule(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(budget, f"missing pure scheduler: {IMPORT_ERROR}")

    def sources(self, rows):
        return tuple(budget.SourceIdentity(
            run_id=f"{index + 1:032x}", episode=0,
            feature_target_sha256=f"{index + 1:064x}", rows=count)
            for index, count in enumerate(rows))

    def exposures(self, schedule):
        counts = [[0] * source.rows for source in schedule.sources]
        for update in schedule.updates:
            self.assertEqual(sum(piece.stop - piece.start for piece in update.fragments),
                             schedule.rows_per_update)
            for piece in update.fragments:
                for row in range(piece.start, piece.stop):
                    counts[piece.source_index][row] += 1
        return tuple(tuple(source) for source in counts)

    def test_frozen_arms_match_real_row_and_update_budgets(self):
        cases = (
            (OLD_ROWS, 21, 1623, OLD_REMAINDER, OLD_PRESENTATIONS),
            (AUGMENTED_ROWS, 6, 2898, AUGMENTED_REMAINDER, AUGMENTED_PRESENTATIONS),
        )
        schedules = []
        for rows, sweeps, remainder, allocations, presentations in cases:
            schedule = budget.build_schedule(self.sources(rows), seed=10)
            schedules.append(schedule)
            self.assertEqual((schedule.presentations, schedule.rows_per_update), (46080, 32))
            self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (sweeps, remainder))
            self.assertEqual(schedule.remainder_allocations, allocations)
            self.assertEqual(schedule.source_presentations, presentations)
            self.assertEqual(len(schedule.updates), 1440)
            observed = self.exposures(schedule)
            for index, counts in enumerate(observed):
                self.assertEqual(set(counts), {sweeps, sweeps + 1})
                self.assertEqual(counts.count(sweeps + 1), allocations[index])
                self.assertEqual(sum(counts), presentations[index])
            self.assertEqual(sum(map(sum, observed)), 46080)
        self.assertEqual(schedules[0].remainder_starts,
                         schedules[1].remainder_starts[:len(OLD_ROWS)])

    def test_fragments_mark_source_resets_update_continuations_and_wraps(self):
        sources = self.sources((1, 31, 32, 33))
        schedule = budget.build_schedule(sources, seed=6, presentations=104,
                                         rows_per_update=8)
        self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (1, 7))
        self.assertEqual(schedule.remainder_allocations, (0, 2, 2, 3))
        self.assertEqual(schedule.remainder_starts, (0, 30, 9, 3))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.fragments),
            ((0, 0, 1, True), (1, 0, 31, True), (2, 0, 32, True),
             (3, 0, 33, True), (1, 30, 31, True), (1, 0, 1, True),
             (2, 9, 11, True), (3, 3, 6, True)))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.updates[0].fragments),
            ((0, 0, 1, True), (1, 0, 7, True)))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.updates[1].fragments),
            ((1, 7, 15, False),))
        replay = budget.build_schedule(sources, seed=6, presentations=104,
                                       rows_per_update=8)
        self.assertEqual(schedule.canonical_bytes(), replay.canonical_bytes())
        self.assertEqual(schedule.sha256,
                         hashlib.sha256(schedule.canonical_bytes()).hexdigest())
        self.assertNotEqual(schedule.canonical_bytes(), budget.build_schedule(
            sources, seed=7, presentations=104, rows_per_update=8).canonical_bytes())
        self.assertEqual(json.loads(schedule.canonical_bytes())["protocol_id"],
                         "M7-NAV-V3-MATCHED-BUDGET-1")
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("mujoco", sys.modules)

    def test_hamilton_ties_and_invalid_inputs_fail_closed(self):
        tie = budget.build_schedule(self.sources((1, 1, 1)), seed=0,
                                    presentations=4, rows_per_update=2)
        self.assertEqual(tie.remainder_allocations, (1, 0, 0))
        with self.assertRaises(FrozenInstanceError):
            tie.seed = 1
        source = self.sources((2,))[0]
        for operation in (
            lambda: budget.build_schedule((), seed=0, presentations=2, rows_per_update=2),
            lambda: budget.build_schedule((source, source), seed=0, presentations=4,
                                          rows_per_update=2),
            lambda: budget.build_schedule([source], seed=0, presentations=2,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=True, presentations=2,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0, presentations=3,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0,
                                          presentations=sys.maxsize + 1,
                                          rows_per_update=1),
            lambda: budget.SourceIdentity("not-hex", 0, "0" * 64, 1),
            lambda: budget.SourceIdentity("0" * 32, 0, "0" * 64, True),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()


if __name__ == "__main__":
    unittest.main()
