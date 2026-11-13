import base64, io, json, math, unittest
import numpy as np
from lab.core import astar, clean
from lab import dataset

class CoreTests(unittest.TestCase):

    def test_astar_routes_around_wall(self):
        path = astar([0, 0], [4, 4], [[2, y] for y in range(4)], 5)
        self.assertEqual(path[-1], [4, 4])
        self.assertTrue(all((p[0] != 2 or p[1] == 4 for p in path)))

    def test_astar_impossible(self):
        self.assertEqual(astar([0, 0], [2, 2], [[1, y] for y in range(3)], 3), [])

    def test_json_serialization(self):
        self.assertEqual(clean({'a': np.int64(2), 'b': float('nan')}), {'a': 2, 'b': None})

class ForensicsTests(unittest.TestCase):

    def test_known_defects_found(self):
        e = dataset.Engine()
        types = {x['type'] for x in e.state['findings']}
        self.assertTrue({'duplicates', 'entity_overlap', 'prediction_time_unavailable'} <= types)

    def test_correction_removes_unavailable(self):
        e = dataset.Engine()
        r = e.evaluate({})
        self.assertNotIn('post_event_result', r['corrected']['features'])
        self.assertLess(r['corrected']['accuracy'], r['original']['accuracy'])

    def test_target_validation(self):
        with self.assertRaises(ValueError):
            dataset.Engine().configure({'target': 'missing'})
