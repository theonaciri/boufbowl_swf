"""The Python and Bun build workers must share the same CPU budget."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import threading
import time
import unittest
from tools.build_parallel import available_cpus, build_budget, cpu_job, parallel


class BuildParallelTests(unittest.TestCase):
    def test_python_workers_respect_shared_budget(self):
        active = 0
        peak = 0
        lock = threading.Lock()
        def job(_):
            nonlocal active, peak
            with cpu_job():
                with lock:
                    active += 1
                    peak = max(peak, active)
                time.sleep(0.03)
                with lock:
                    active -= 1
        with build_budget(2):
            for _ in parallel(job, range(8), workers=8):
                pass
        self.assertEqual(peak, min(2, available_cpus()))
        self.assertEqual(active, 0)

    def test_bun_waits_for_python_to_release_the_shared_slot(self):
        bun = shutil.which('bun') or str(Path.home()/'.bun/bin/bun')
        if not Path(bun).is_file():
            self.skipTest('Bun unavailable')
        module = (Path(__file__).resolve().parent.parent/'tools/website/cpu-budget.mjs').as_uri()
        code = f'import {{cpuJob}} from {module!r}; console.log("ready"); await cpuJob(async()=>console.log("acquired"));'
        with build_budget(1):
            with cpu_job():
                process = subprocess.Popen([bun, '-e', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        self.assertEqual(executor.submit(process.stdout.readline).result(timeout=10).strip(), 'ready')
                    # The child has reached the budget request but cannot acquire yet.
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.wait(timeout=0.1)
                except BaseException:
                    process.kill()
                    process.communicate()
                    raise
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(stdout.strip(), 'acquired')
