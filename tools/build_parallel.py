"""CPU-aware jobs with one shared budget across build subprocesses."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import subprocess
import threading
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4


def available_cpus():
    """Respect CPU affinity and Linux container quotas, not just host CPU count."""
    count = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    try:
        groups = Path('/proc/self/cgroup').read_text().splitlines()
        unified = next(line.split(':', 2)[2] for line in groups if line.startswith('0::'))
        directory = (Path('/sys/fs/cgroup')/unified.lstrip('/')).resolve()
        # Container mounts can expose the current cgroup as their filesystem root.
        if not directory.is_relative_to('/sys/fs/cgroup') or not directory.exists():
            directory = Path('/sys/fs/cgroup')
        while directory.is_relative_to('/sys/fs/cgroup'):
            cpu_max = directory/'cpu.max'
            if cpu_max.is_file():
                quota, period = cpu_max.read_text().split()
                if quota != 'max':
                    count = min(count, max(1, math.ceil(int(quota)/int(period))))
            directory = directory.parent
    except (OSError, ValueError, StopIteration):
        pass
    # Some systems expose cgroup v1 CPU controllers instead of cpu.max.
    try:
        for line in Path('/proc/self/cgroup').read_text().splitlines():
            _, controllers, group = line.split(':', 2)
            if 'cpu' not in controllers.split(','):
                continue
            for mount in (Path('/sys/fs/cgroup/cpu'), Path('/sys/fs/cgroup/cpu,cpuacct')):
                if not mount.is_dir():
                    continue
                directory = (mount/group.lstrip('/')).resolve()
                if not directory.is_relative_to(mount) or not directory.exists():
                    directory = mount
                while directory.is_relative_to(mount):
                    try:
                        quota = int((directory/'cpu.cfs_quota_us').read_text())
                        period = int((directory/'cpu.cfs_period_us').read_text())
                        if quota > 0:
                            count = min(count, max(1, math.ceil(quota/period)))
                    except (OSError, ValueError):
                        pass
                    directory = directory.parent
    except (OSError, ValueError):
        pass
    override = os.environ.get('BOUFBOWL_BUILD_CPUS')
    if override:
        requested = int(override)
        if requested < 1:
            raise ValueError('BOUFBOWL_BUILD_CPUS must be positive')
        count = min(count, requested)
    return max(1, count)


_local_lock = threading.Lock()
_local_budget = None


@contextmanager
def cpu_job():
    """Reserve one CPU job, including when this process belongs to another build."""
    address = os.environ.get('BOUFBOWL_BUILD_BUDGET')
    if address:
        opener = build_opener(ProxyHandler({}))
        with opener.open(address+f'/acquire?pid={os.getpid()}', timeout=86400) as response:
            token = json.load(response)['token']
        try:
            yield
        finally:
            with opener.open(Request(address+'/release', data=token.encode()), timeout=30):
                pass
    else:
        global _local_budget
        with _local_lock:
            if _local_budget is None:
                _local_budget = threading.BoundedSemaphore(available_cpus())
        with _local_budget:
            yield


@contextmanager
def build_budget(cpus=None):
    """Share a dynamically allocated job budget with all nested Python/Bun tools."""
    if os.environ.get('BOUFBOWL_BUILD_BUDGET'):
        yield
        return
    limit = min(cpus or available_cpus(), available_cpus())
    condition = threading.Condition()
    active = {}
    closed = False
    secret = uuid4().hex

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path != '/'+secret+'/acquire':
                self.send_error(404)
                return
            try:
                pid = int(parse_qs(parsed.query)['pid'][0])
                if pid < 1:
                    raise ValueError('Invalid PID')
            except (KeyError, ValueError):
                self.send_error(400)
                return
            with condition:
                while not closed:
                    # Recover permits if an encoder/browser process crashed.
                    for token, owner in list(active.items()):
                        try:
                            os.kill(owner, 0)
                        except ProcessLookupError:
                            active.pop(token, None)
                        except PermissionError:
                            pass
                    if len(active) < limit:
                        break
                    condition.wait(timeout=1)
                if closed:
                    self.send_error(503)
                    return
                token = uuid4().hex
                active[token] = pid
            payload = json.dumps({'token': token}).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                with condition:
                    active.pop(token, None)
                    condition.notify_all()

        def do_POST(self):
            if self.path != '/'+secret+'/release':
                self.send_error(404)
                return
            size = int(self.headers.get('Content-Length', 0))
            if size != 32:
                self.send_error(400)
                return
            with condition:
                active.pop(self.rfile.read(size).decode('ascii'), None)
                condition.notify_all()
            self.send_response(204)
            self.end_headers()

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 1024

    server = Server(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    old_cpus = os.environ.get('BOUFBOWL_BUILD_CPUS')
    os.environ['BOUFBOWL_BUILD_CPUS'] = str(limit)
    os.environ['BOUFBOWL_BUILD_BUDGET'] = f'http://127.0.0.1:{server.server_port}/{secret}'
    print(f'Build CPU budget: {limit} concurrent jobs', flush=True)
    try:
        yield
    finally:
        with condition:
            closed = True
            condition.notify_all()
        server.shutdown()
        server.server_close()
        thread.join()
        os.environ.pop('BOUFBOWL_BUILD_BUDGET', None)
        if old_cpus is None:
            os.environ.pop('BOUFBOWL_BUILD_CPUS', None)
        else:
            os.environ['BOUFBOWL_BUILD_CPUS'] = old_cpus


def parallel(function, items, workers=None):
    """Yield results as they finish; serialize manifest/cache writes in the caller."""
    items = list(items)
    if not items:
        return
    with ThreadPoolExecutor(max_workers=min(workers or available_cpus(), len(items))) as executor:
        futures = [executor.submit(function, item) for item in items]
        try:
            for future in as_completed(futures):
                yield future.result()
        except BaseException:
            for future in futures:
                future.cancel()
            raise


def cpu_run(command, **kwargs):
    """Run a single-threaded encoder/compiler inside the shared CPU budget."""
    command = [str(part) for part in command]
    name = Path(command[0]).name
    if name == 'ffmpeg':
        command[1:1] = ['-threads', '1', '-filter_threads', '1', '-filter_complex_threads', '1']
        # Output codecs have their own thread setting, separate from input decoding.
        command[-1:-1] = ['-threads', '1']
    elif name == 'avifenc':
        if '--jobs' in command:
            command[command.index('--jobs')+1] = '1'
        else:
            command[1:1] = ['--jobs', '1']
    elif name in ('java', 'java.exe'):
        command.insert(1, '-XX:ActiveProcessorCount=1')
    with cpu_job():
        return subprocess.run(command, **kwargs)
