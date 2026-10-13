#!/usr/bin/env python3
"""Rebuild the offline menu/tutorial SWF from the untouched archive."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.game_config import DEFAULT_CONFIG, apply_resources, flashvars_source, load_config, startup_source

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ffdec", type=Path, required=True, help="Path to ffdec.jar")
parser.add_argument("--original", type=Path, help="Path to the untouched original client SWF")
parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
original = args.original or root.parent / "swf_sources/boufbowl_client/bin/boufbowl-client-1.9.6.swf"
config = load_config(args.config)
config_source = args.config.read_bytes()
classes = [
    "com.ankamagames.boufbowl.BoufbowlClient",
    "com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand",
    "com.ankamagames.xgaming.utils.flashvars.FlashVarsManager",
    "com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline",
    "com.ankamagames.boufbowl.client.tutorial.controller.TutorialFinishedCommand",
    "com.ankamagames.boufbowl.client.matchmaking.view.WelcomeView",
    "com.ankamagames.boufbowl.client.clubselection.view.ClubSelectionView",
    "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.SendClubCustomisationChangeCommand",
    "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller.SendBoufbowlerCustomisationChangeCommand",
    "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.ClubCustomisationConfirmCommand",
    "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller.BoufbowlerCustomisationConfirmCommand",
    "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model.BoufbowlerEditionModel",
    "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorSpriteHolderView",
    "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorView",
    "com.ankamagames.boufbowl.client.match.resolution.controller.ComputeResolutionCommand",
    "com.ankamagames.boufbowl.resolution.display.animation.BoufbowlerSprite",
    "com.ankamagames.boufbowl.client.clubselection.controller.PredefinedClubsCommand",
    "com.ankamagames.boufbowl.client.match.strategic.view.ClassOrderTextComputer",
]
replacements = []
for cls in classes:
    replacements.extend([cls, str(root / "patches" / (cls.rsplit(".", 1)[-1] + ".as"))])
with tempfile.TemporaryDirectory(prefix=".tutorial-build-", dir=root / "bin") as tmp:
    startup = Path(tmp) / "StartUpApplicationCommand.as"
    startup.write_text(startup_source((root / "patches/StartUpApplicationCommand.as").read_text(), config))
    replacements[3] = str(startup)
    flashvars = Path(tmp) / "FlashVarsManager.as"
    flashvars.write_text(flashvars_source((root / "patches/FlashVarsManager.as").read_text(), config))
    replacements[5] = str(flashvars)
    output = Path(tmp) / "boufbowl-client-1.9.6.swf"
    subprocess.run([
        "java", "-jar", str(args.ffdec.resolve()), "-replace", str(original), str(output),
        *replacements,
    ], check=True, timeout=120)
    if args.config.read_bytes() != config_source:
        raise RuntimeError("Configuration changed during compilation; rebuild with the updated file")
    output.replace(root / "bin" / output.name)
apply_resources(root / "resources", config)
print("Rebuilt", root / "bin/boufbowl-client-1.9.6.swf")
