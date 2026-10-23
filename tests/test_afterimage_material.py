"""Synthetic source selection; no model inference or renderer."""
import unittest
import numpy as np
import afterimage_material as material


def rows(count=3000):
    for i in range(count):
        episode, tick = divmod(i, 599)
        yield {'episode': episode, 'tick': tick,
               'simulation_time': np.array((tick + 1) * .02),
               'cam_left': np.full((128, 128, 3), i % 251, np.uint8),
               'cam_right': np.full((128, 128, 3), 255, np.uint8),
               'eyes': np.array([True, False])}


class SelectionTests(unittest.TestCase):
    def test_manual_driver_bounds_and_seeds(self):
        from test_choir_material import Engine
        for length, total in [(600, 3000), (599, 3594)]:
            engine = Engine(length)
            result = material.drive(engine)
            self.assertEqual(result['intervals'], total)
            self.assertEqual(engine.seeds, list(range(1, engine.episode + 1)))
        for engine in (Engine(1), Engine(4000), Engine(failed=True)):
            with self.assertRaises(ValueError): material.drive(engine)

    def test_left_eye_chronology_and_native_boundaries(self):
        frames, index = material.select(rows(3004))
        self.assertEqual(frames.shape, (600, 128, 128, 3))
        self.assertEqual(frames.dtype, np.uint8)
        self.assertEqual(index[-1]['source_interval'], 2995)
        self.assertEqual(index[-1]['presentation_seconds'], 59.9)
        self.assertEqual(index[120]['episode'], 1)
        self.assertEqual(index[120]['tick'], 1)
        self.assertEqual(index[120]['simulation_time_seconds'], .04)
        self.assertEqual(index[120]['eyes'], [True, False])
        for i, frame in enumerate(frames):
            self.assertTrue(np.all(frame == (i * 5) % 251))

    def test_rejects_short_gaps_reordering_wrong_images_and_bad_tail(self):
        with self.assertRaisesRegex(ValueError, '3000'): material.select(rows(2999))
        for field, value in [('tick', 7), ('episode', 7), ('simulation_time', np.array(1.)),
                             ('cam_left', np.zeros((1, 1, 3), np.uint8)),
                             ('cam_left', np.zeros((128, 128, 3), np.float32)),
                             ('eyes', np.array([1, 0]))]:
            def corrupt():
                for i, row in enumerate(rows(3004)):
                    if i == 3003: row[field] = value
                    yield row
            with self.assertRaises(ValueError): material.select(corrupt())

