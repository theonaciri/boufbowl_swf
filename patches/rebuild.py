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
    "com.ankamagames.xgaming.audio.controller.AbstractTracksController",
    "com.ankamagames.xgaming.audio.controller.ConcurrentTracksManager",
    "com.ankamagames.boufbowl.ui.components.tooltip.Tooltip",
    "com.ankamagames.xgaming.ui.components.Slider",
    "com.ankamagames.boufbowl.client.ui.SliderTrack",
    "away3d.core.session.AbstractSession",
    "com.ankamagames.boufbowl.client.chat.ChatContextPart",
    "com.ankamagames.boufbowl.client.chat.view.ChatMediator",
    "com.ankamagames.boufbowl.ui.components.chat.ChannelButton",
    "org.swiftsuspenders.injectionpoints.ConstructorInjectionPoint",
    "com.ankamagames.jerakine.types.Uri",
    "com.ankamagames.jerakine.resources.adapters.impl.SwlAdapter",
    "com.ankamagames.xgaming.ui.components.FlashInstanceContainer",
    "com.ankamagames.boufbowl.resolution.display.camera.BoufbowlCamera",
    "com.ankamagames.boufbowl.client.match.controller.StopSpectatingCommand",
    "com.ankamagames.boufbowl.protocol.ClassOrderTarget",
    "com.ankamagames.boufbowl.client.match.resolution.interactions.ClassOrderBuffFunction",
    "com.ankamagames.boufbowl.client.match.resolution.interactions.ClassOrderDebuffFunction",
    "com.ankamagames.boufbowl.protocol.SigilBackground",
    "com.ankamagames.boufbowl.resolution.display.script.runner.AsvmTimeProvider",
    "com.ankamagames.boufbowl.resolution.display.script.runner.SceneController",
    "com.ankamagames.boufbowl.client.matchmaking.view.tournament.TournamentView",
    "com.ankamagames.boufbowl.resolution.display.script.runner.action.PlayPeriodAction",
    "com.ankamagames.boufbowl.client.match.strategic.model.FieldModel",
    "com.ankamagames.boufbowl.resolution.display.script.runner.action.PlayVersusAction",
    "com.ankamagames.boufbowl.resolution.display.script.runner.action.PlayMovieAction",
    "com.ankamagames.boufbowl.client.match.controller.PlayIntroductionCommand",
    "com.ankamagames.boufbowl.resolution.display.script.runner.UIController",
    "com.ankamagames.boufbowl.client.options.view.OptionsView",
    "com.ankamagames.boufbowl.client.options.view.OptionsMediator",
    "com.ankamagames.boufbowl.client.matchmaking.controller.DisplayMatchCreationTypeCommand",
    "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubColorSelectionModel",
    "com.ankamagames.boufbowl.client.chat.controller.contextmenu.ChatContextualMenuBuilder",
    "com.ankamagames.boufbowl.client.chat.controller.channel.ChatNameMenuOptionCommand",
    "com.ankamagames.boufbowl.client.match.controller.InitializeFieldCommand",
    "com.ankamagames.boufbowl.client.match.MatchContextPart",
    "com.ankamagames.boufbowl.client.chat.controller.command.ChatLocalCommand",
    "com.ankamagames.boufbowl.client.chat.controller.channel.ReceiveChannelsConfigurationCommand",
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
    "com.ankamagames.boufbowl.client.match.model.MatchModel",
]
replacements = []
for cls in classes:
    replacements.extend([cls, str(root / "patches" / (cls.rsplit(".", 1)[-1] + ".as"))])
with tempfile.TemporaryDirectory(prefix=".tutorial-build-", dir=root / "bin") as tmp:
    startup = Path(tmp) / "StartUpApplicationCommand.as"
    startup.write_text(startup_source((root / "patches/StartUpApplicationCommand.as").read_text(), config))
    replacements[2*classes.index("com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand")+1] = str(startup)
    flashvars = Path(tmp) / "FlashVarsManager.as"
    flashvars.write_text(flashvars_source((root / "patches/FlashVarsManager.as").read_text(), config))
    replacements[2*classes.index("com.ankamagames.xgaming.utils.flashvars.FlashVarsManager")+1] = str(flashvars)
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
