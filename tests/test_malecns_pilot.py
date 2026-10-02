"""Offline extraction contract checks; these fixtures are not anatomical evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('extract_malecns_pilot',
    Path(__file__).parents[1] / 'scripts/extract_malecns_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class ExtractionTests(unittest.TestCase):
    def responses(self):
        return [(['input_nodes','edges'], [[1,2]]), (['bodyId'], [[3]]),
            (['edges'], [[2]]), (['pre','post','weight'], [[3,12781,20],[3,556329,25]]),
            (['bodyId','type','instance','somaSide','status'],
                [[3,None,None,None,'Traced'],[12781,'DNge104','DNge104_R','R','Traced'],
                 [556329,'DNge104','DNge104_L','L','Traced']]),
            (['edges','weight'], [[5,50]]), (['edges','weight'], [[6,60]])]

    def run_fixture(self, responses):
        class Response:
            status = 200
            def __init__(self, columns, rows):
                self.body = json.dumps({'columns':columns,'data':rows}).encode()
            def read(self, limit):
                return self.body[:limit]
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pilot.urllib.request, 'urlopen', side_effect=[Response(*r) for r in responses]) as request:
                report = pilot.extract(Path(directory) / 'new')
            return report, request.call_count

    def test_complete_fixture_records_directed_graph_and_cut_boundary(self):
        report, calls = self.run_fixture(self.responses())
        self.assertEqual((report['status'],report['nodes'],report['edges'],calls), ('extracted',3,2,7))
        self.assertEqual(report['retained_weight'],45)
        self.assertEqual(report['boundary']['incoming'],{'edges':5,'weight':50})
        self.assertFalse(report['r3_complete'])

    def test_oversized_and_inconsistent_queries_stop_before_publication(self):
        report, calls = self.run_fixture([(['input_nodes','edges'],[[300,300]])])
        self.assertEqual((report['status'],calls),('failed',1))
        self.assertNotIn('graph_sha256',report)
        responses = self.responses()
        responses[3] = (['pre','post','weight'], [[3,12781,20],[3,556329,1]])
        report, calls = self.run_fixture(responses)
        self.assertEqual((report['status'],calls),('failed',4))
        self.assertIn('contradicts',report['error']['message'])


if __name__ == '__main__':
    unittest.main()
