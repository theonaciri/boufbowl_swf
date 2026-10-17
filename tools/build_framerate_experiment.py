#!/usr/bin/env python3
"""Build a disposable SWF with an overridden Flash Stage frame rate."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "bin/boufbowl-client-1.9.6.swf"
CLIENT_CLASS = ROOT / "patches/BoufbowlClient.as"
CLASS_NAME = "com.ankamagames.boufbowl.BoufbowlClient"


def cached_tool(name: str) -> Path | None:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    candidates = {
        "ffdec": [
            cache / "boufbowl-flash-tools/ffdec-26.3.0/ffdec.jar",
            cache / "boufbowl-flash-tools/ffdec/ffdec.jar",
        ],
        "java": [cache / "boufbowl-flash-tools/jdk-17/jdk-17.0.20.1+1/bin/java"],
    }
    return next((path for path in candidates[name] if path.is_file()), None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=60, help="experimental Stage.frameRate (26–1000)")
    parser.add_argument("--ffdec", type=Path, help="FFDec JAR (or set FFDEC_JAR)")
    parser.add_argument("--java", type=Path, help="Java executable (or use java on PATH)")
    args = parser.parse_args()
    if not 25 <= args.fps <= 1000:
        parser.error("--fps must be between 25 and 1000")
    if not CLIENT.is_file() or not CLIENT_CLASS.is_file():
        parser.error("Build the regular desktop client first")
    ffdec = args.ffdec or (Path(os.environ["FFDEC_JAR"]).expanduser() if os.environ.get("FFDEC_JAR") else cached_tool("ffdec"))
    java = args.java or (Path(shutil.which("java")) if shutil.which("java") else cached_tool("java"))
    if ffdec is None or not ffdec.is_file():
        parser.error("FFDec JAR not found; pass --ffdec or set FFDEC_JAR")
    if java is None or not java.is_file():
        parser.error("Java not found; pass --java or add Java to PATH")

    fps = f"{args.fps:g}"
    source = CLIENT_CLASS.read_text(encoding="utf-8")
    marker = "addChild(new MainApp(this._uncaughtErrorsHandler,String(new embeddedVersionClass())));"
    if source.count(marker) != 1:
        parser.error("Expected one MainApp creation in BoufbowlClient.as")
    destination = ROOT / "bin" / f"boufbowl-client-1.9.6-{fps}fps.swf"
    with tempfile.TemporaryDirectory(prefix="boufbowl-frame-rate-") as directory:
        temporary = Path(directory)
        replacement = temporary / "BoufbowlClient.as"
        replacement.write_text(source.replace(marker, marker + f"\n         stage.frameRate = {fps};"), encoding="utf-8")
        output = temporary / destination.name
        subprocess.run(
            [str(java), "-jar", str(ffdec.resolve()), "-replace", str(CLIENT), str(output), CLASS_NAME, str(replacement)],
            check=True,
        )
        if not output.is_file():
            raise RuntimeError("FFDec completed without producing the experimental client")
        shutil.move(str(output), destination)
    print(f"Built {destination} with Stage.frameRate={fps} FPS")


if __name__ == "__main__":
    main()
