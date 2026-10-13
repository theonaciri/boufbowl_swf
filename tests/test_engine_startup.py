import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from backend.engine import Engine
from backend.storage import ServiceError
from tools.game_config import ROOT


class EngineStartupTests(unittest.TestCase):
    def test_missing_worker_reports_update_instead_of_importing_sibling_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ServiceError, 'Update the checkout'):
                Engine(worker=Path(directory)/'missing.js')

    def test_missing_runtime_reports_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ServiceError, 'Bun is required'):
                Engine(runtime=str(Path(directory)/'missing-bun'))

    def test_startup_errors_include_worker_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            worker=Path(directory)/'broken.py'
            worker.write_text('import sys\nsys.stderr.write("Cannot load required module\\n")\n')
            with self.assertRaisesRegex(ServiceError, 'Cannot load required module'):
                Engine(runtime=sys.executable,worker=worker)

    def test_checkout_worker_runs_without_sibling_source(self):
        runtime=shutil.which('bun') or str(Path.home()/'.bun/bin/bun')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'backend',root/'backend',ignore=shutil.ignore_patterns('__pycache__','engine.ts','runtime'))
            record=json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())
            (root/'input.json').write_text(json.dumps(record))
            script='''import json,sys
sys.path.insert(0,sys.argv[1])
from backend.engine import Engine
record=json.load(open(sys.argv[1]+"/input.json"))
engine=Engine(runtime=sys.argv[2])
try:
 result=engine.simulate(record["initial"],record["orders"],1,12345,{},(False,False))
 assert result["ok"] and result["result"]["final_state_hash"]==record["result"]["final_state_hash"]
finally: engine.close()
'''
            result=subprocess.run([sys.executable,'-I','-c',script,str(root),runtime],cwd=root,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__': unittest.main()
