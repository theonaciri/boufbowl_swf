#!/usr/bin/env python3
"""Run inside xvfb-run to check original-client 3D fixture playback and capture it."""
import os
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--require-cinematic", action="store_true", help="Require and capture a successfully rendered full-screen cinematic")
    parser.add_argument("--require-celebration", help="Require a specific stadium goal animation to render")
    parser.add_argument("--capture-turns",action="store_true",help="Capture each original-client turn during playback")
    parser.add_argument("--timeout",type=float,default=80,help="Playback deadline in seconds")
    args = parser.parse_args()
    expected_fields = 2
    if args.fixture:
        expected_fields = sum(step["type"] == "FIELD_STATE" for step in json.loads(args.fixture.read_text())["steps"])
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("Run with xvfb-run -a -s '-screen 0 1280x800x24'")
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "boufbowl-tutorial"
    log = state / "mock.log"
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    offset = log.stat().st_size if log.exists() else 0
    trace = ""
    captured = False
    captured_turns = 0
    cinematic_captured = False
    celebration_captured = False
    with (evidence / "mock-launch.log").open("w") as launch_log:
        command = [sys.executable, str(ROOT / "play.py"), "--mode", "mock", "--scene-3d"]
        if args.fixture:
            command.extend(["--fixture", str(args.fixture.resolve())])
        game = subprocess.Popen(command,
                            cwd=ROOT, stdout=launch_log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if log.exists():
                    with log.open() as stream:
                        stream.seek(offset)
                        trace = stream.read()
                if args.require_cinematic and ("Cinematic unavailable:" in trace or "Movie unavailable:" in trace):
                    raise RuntimeError(trace)
                if args.require_cinematic and "Cinematic started:" in trace and not cinematic_captured:
                    time.sleep(.35)
                    subprocess.run(["import","-window","root",str(evidence/"mock-engine-cinematic.png")],check=True)
                    cinematic_captured=True
                count = trace.count("Playback script built")
                if args.capture_turns and count > captured_turns:
                    time.sleep(.5)
                    subprocess.run(["import","-window","root",str(evidence/("reference-turn-%02d.png" % count))],check=True)
                    captured_turns = count
                if "ERROR:" in trace:
                    raise RuntimeError(trace)
                if args.require_celebration and not celebration_captured and ("Cinematic started: " + args.require_celebration) in trace:
                    time.sleep(.35)
                    subprocess.run(["import", "-window", "root", str(evidence / "mock-stadium-celebration.png")], check=True)
                    celebration_captured = True
                if "Playback script built" in trace and not captured:
                    time.sleep(0.6)
                    subprocess.run(["import", "-window", "root", str(evidence / "mock-engine-playback.png")], check=True)
                    time.sleep(0.8)
                    subprocess.run(["import", "-window", "root", str(evidence / "mock-engine-movement.png")], check=True)
                    captured = True
                if "Incoming MATCH_END" in trace:
                    time.sleep(1)
                    subprocess.run(["import", "-window", "root", str(evidence / "mock-engine-result.png")], check=True)
                    break
                if game.poll() is not None:
                    raise RuntimeError("Client exited before fixture completion")
                time.sleep(0.2)
            else:
                raise RuntimeError("Fixture did not finish within " + str(args.timeout) + " seconds: " + trace)
            required = ("Playback mode 3D", "Playback script built", "Outgoing ResolutionDoneMessage", "Incoming MATCH_END")
            if any(event not in trace for event in required) or trace.count("Incoming FIELD_STATE") != expected_fields:
                raise RuntimeError("Incomplete playback trace: " + trace)
            if args.require_cinematic and (not cinematic_captured or "Cinematic finished" not in trace):
                raise RuntimeError("Cinematic did not render and finish: " + trace)
            if args.require_celebration and not celebration_captured:
                raise RuntimeError("Expected goal celebration did not render: " + args.require_celebration + "\n" + trace)
            (evidence / "mock-engine-trace.log").write_text(trace)
            print("Verified original-client 3D script, resolution acknowledgement, next field state and match end.")
        finally:
            data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            prefix = data / "boufbowl-tutorial/wine"
            wineserver = shutil.which("wineserver") or "/usr/lib/x86_64-linux-gnu/wine/wineserver"
            subprocess.run([wineserver, "-k"], env=dict(os.environ, WINEPREFIX=str(prefix)), check=False)
            try:
                game.wait(timeout=10)
            except subprocess.TimeoutExpired:
                game.terminate()
                game.wait(timeout=5)


if __name__ == "__main__":
    main()
