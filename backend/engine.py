"""Serialized subprocess bridge to the bundled Bun simulator worker."""
import json
import os
import selectors
from pathlib import Path
import shutil
import subprocess
import threading
import tempfile

from backend.storage import ServiceError


class Engine:
    def __init__(self, runtime=None, worker=None):
        root = Path(__file__).resolve().parent
        bundled = root / "runtime/bun"
        bun = runtime or (str(bundled) if bundled.exists() else shutil.which("bun") or str(Path.home() / ".bun/bin/bun"))
        worker = Path(worker) if worker else root / "build/engine.js"
        if not worker.is_file():
            raise ServiceError("WORKER_MISSING", "Compiled worker backend/build/engine.js is missing. Update the checkout; no Flash rebuild is required.")
        if not shutil.which(bun) and not Path(bun).is_file():
            raise ServiceError("RUNTIME_MISSING", "Bun is required for matches. Install Bun, or use the Linux package with its bundled runtime.")
        self.arguments = [bun, str(worker)]
        self.lock = threading.Lock()
        self.start()

    def start(self):
        self.errors = tempfile.TemporaryFile(mode="w+t")
        try:
            self.process = subprocess.Popen(self.arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=self.errors, text=True, bufsize=1,
                                            env=dict(os.environ, BOUFBOWL_WORKER_HANDSHAKE="1"))
        except OSError as error:
            self.errors.close()
            raise ServiceError("ENGINE_STARTUP", f"Cannot launch simulation runtime: {error}") from error
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        if not self.selector.select(timeout=10):
            self.close()
            raise ServiceError("ENGINE_STARTUP", "Simulation worker did not become ready within 10 seconds")
        line = self.process.stdout.readline()
        try:
            ready = json.loads(line).get("ready") is True
        except (ValueError, AttributeError):
            ready = False
        if not ready:
            detail = self.error_detail()
            self.close()
            raise ServiceError("ENGINE_STARTUP", "Simulation worker failed to start" + detail)

    def error_detail(self):
        self.errors.seek(0)
        detail = self.errors.read()[-4096:].strip()
        return ": " + detail if detail else ""

    def simulate(self, world, orders, turn, seed, rules, cpu=(False, True)):
        with self.lock:
            if self.process.poll() is not None:
                self.selector.close()
                self.process.stdin.close()
                self.process.stdout.close()
                self.errors.close()
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
                raise ServiceError("ENGINE_UNAVAILABLE", "Simulation worker exited" + self.error_detail())
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
        self.errors.close()
