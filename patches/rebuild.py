#!/usr/bin/env python3
"""Rebuild the offline menu/tutorial SWF from the untouched archive."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ffdec", type=Path, required=True, help="Path to ffdec.jar")
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
original = root.parent / "swf_sources/boufbowl_client/bin/boufbowl-client-1.9.6.swf"
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
]
replacements = []
for cls in classes:
    replacements.extend([cls, str(root / "patches" / (cls.rsplit(".", 1)[-1] + ".as"))])
with tempfile.TemporaryDirectory(prefix=".tutorial-build-", dir=root / "bin") as tmp:
    output = Path(tmp) / original.name
    subprocess.run([
        "java", "-jar", str(args.ffdec.resolve()), "-replace", str(original), str(output),
        *replacements,
    ], check=True, timeout=120)
    output.replace(root / "bin" / original.name)
print("Rebuilt", root / "bin" / original.name)
