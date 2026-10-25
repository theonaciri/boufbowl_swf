#!/usr/bin/env python3
"""Rebuild the game SWF from the preserved base client or an explicit archive."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.game_config import DEFAULT_CONFIG, apply_resources, flashvars_source, load_config, startup_source
from tools.visual_assets import palette_item_source
from tools.media_fingerprints import logic_fingerprint, file_hash
import hashlib
from tools.build_tools import BuildError, ffdec_jar, java_binary
from tools.client_patches import client_patches
from tools.client_runtime_codegen import client_root_source

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ffdec", help="Path to ffdec.jar (defaults to FFDEC_JAR or the Boufbowl tool cache)")
parser.add_argument("--original", type=Path, help="Source SWF override (default: bin/base/boufbowl-client-1.9.6.swf)")
parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
try:
    args.ffdec = ffdec_jar(args.ffdec, download=True)
    java = java_binary()
except BuildError as error:
    parser.error(str(error))
original = args.original or root / "bin/base/boufbowl-client-1.9.6.swf"
if not original.is_file():
    parser.error("Client source missing; restore bin/base/boufbowl-client-1.9.6.swf or pass --original")
print("Rebuilding from", original, flush=True)
config = load_config(args.config)
config_source = args.config.read_bytes()
logic = logic_fingerprint(root, original, args.config)
palette_source = (root/"resources/palettes.json").read_bytes()
selected = client_patches(root)
classes = [patch.class_name for patch in selected]
replacements = []
for patch in selected:
    replacements.extend([patch.class_name, str(patch.source)])
with tempfile.TemporaryDirectory(prefix=".tutorial-build-", dir=root / "bin") as tmp:
    client_root = Path(tmp) / "BoufbowlClient.as"
    client_root.write_text(client_root_source((root / "patches/BoufbowlClient.as").read_text(), root))
    replacements[2*classes.index("com.ankamagames.boufbowl.BoufbowlClient")+1] = str(client_root)
    palette = Path(tmp) / "BoufbowlerPaletteItem.as"
    palette.write_text(palette_item_source((root / "patches/BoufbowlerPaletteItem.as").read_text()))
    replacements[2*classes.index("com.ankamagames.boufbowl.client.premiumservice.common.model.item.BoufbowlerPaletteItem")+1] = str(palette)
    startup = Path(tmp) / "StartUpApplicationCommand.as"
    startup.write_text(startup_source((root / "patches/StartUpApplicationCommand.as").read_text(), config))
    replacements[2*classes.index("com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand")+1] = str(startup)
    flashvars = Path(tmp) / "FlashVarsManager.as"
    flashvars.write_text(flashvars_source((root / "patches/FlashVarsManager.as").read_text(), config))
    replacements[2*classes.index("com.ankamagames.xgaming.utils.flashvars.FlashVarsManager")+1] = str(flashvars)
    output = Path(tmp) / "boufbowl-client-1.9.6.swf"
    subprocess.run([
        str(java), "-jar", str(args.ffdec.resolve()), "-replace", str(original), str(output),
        *replacements,
    ], check=True, timeout=600)
    if args.config.read_bytes() != config_source or (root/"resources/palettes.json").read_bytes() != palette_source:
        raise RuntimeError("Configuration changed during compilation; rebuild with the updated file")
    output.replace(root / "bin" / output.name)
receipt = root/".local/game-build.json"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps({"client": file_hash(root/"bin/boufbowl-client-1.9.6.swf"), "logic": logic,
                               "palette": hashlib.sha256(palette_source).hexdigest()})+"\n")
apply_resources(root / "resources", config)
print("Rebuilt", root / "bin/boufbowl-client-1.9.6.swf")
