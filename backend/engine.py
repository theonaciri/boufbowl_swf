"""Serialized subprocess bridge to the bundled Bun simulator worker."""
import json
import selectors
from pathlib import Path
import shutil
import subprocess
import threading

from backend.storage import ServiceError


class Engine:
    def __init__(self):
        root = Path(__file__).resolve().parent
        bundled = root / "runtime/bun"
        bun = str(bundled) if bundled.exists() else shutil.which("bun") or str(Path.home() / ".bun/bin/bun")
        worker = root / "build/engine.js"
        if not worker.exists():
            worker = root / "engine.ts"
        self.arguments = [bun, str(worker)]
        self.lock = threading.Lock()
        self.start()

    def start(self):
        self.process = subprocess.Popen(self.arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)

    def simulate(self, world, orders, turn, seed, rules, cpu=(False, True)):
        with self.lock:
            if self.process.poll() is not None:
                self.selector.close()
                self.process.stdin.close()
                self.process.stdout.close()
                self.start()
            request = {"world": world, "orders": orders, "turn": turn, "seed": seed, "rules": rules, "cpu": list(cpu)}
            try:
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as error:
                raise ServiceError("ENGINE_UNAVAILABLE", "Simulation worker exited") from error
            if not self.selector.select(timeout=30):
                self.process.kill()
                self.process.wait()
                raise ServiceError("ENGINE_TIMEOUT", "Simulation exceeded 30 seconds")
            line = self.process.stdout.readline()
            if not line:
                raise ServiceError("ENGINE_UNAVAILABLE", "Simulation worker exited")
            result = json.loads(line)
            if not result["ok"]:
                raise ServiceError("ORDER_REJECTED", result["error"])
            return result

    def close(self):
        self.selector.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()
