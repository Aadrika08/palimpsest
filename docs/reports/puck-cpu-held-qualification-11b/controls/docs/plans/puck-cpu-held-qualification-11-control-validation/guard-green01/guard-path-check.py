"""Exercise the guard's real history read without executing its other checks."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest

TEMPLATE=Path(sys.argv.pop(1))

class HistoryPathCheck(unittest.TestCase):
    def test_reads_history_below_root_before_validating_records(self):
        source=TEMPLATE.read_text().replace('@CONTROL@','0'*40).replace('@COUNT@','0')
        self.assertNotIn('@',source)
        tree=ast.parse(source,filename=str(TEMPLATE))
        compile(tree,str(TEMPLATE),'exec')
        reads=[node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='before' for target in node.targets)]
        self.assertEqual(len(reads),1)
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-guard-path-') as directory:
            root=Path(directory)
            (root/'fixture-control-validation').mkdir()
            (root/'fixture-control-validation/historical-before-admission.json').write_text('{"raw_run_files":[],"historical_absent_paths":["runs/future"]}\n')
            namespace=dict(ROOT=root,BASE='fixture',json=json)
            try:
                exec(compile(ast.Module(body=reads,type_ignores=[]),str(TEMPLATE),'exec'),namespace)
            except Exception as error:
                self.fail('guard failed to read fixture history: '+type(error).__name__+': '+str(error))
            self.assertEqual(namespace['before'],{'raw_run_files':[],'historical_absent_paths':['runs/future']})

if __name__=='__main__':unittest.main(verbosity=2)
