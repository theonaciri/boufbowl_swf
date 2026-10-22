# Inspect, export, and patch the binary

Use JDK 17 and FFDec 26.3.0 with the [build environment](BUILD.md#tools-and-inputs).
The SWF holds AS3 logic, UI, and embedded artwork. External animation, sound,
stadium, and video libraries also live under `assets/`.

## Find a function

Inventory classes, export their source, then search method names or distinctive
UI strings. Start from the preserved input; inspect the runnable SWF when
investigating an applied patch.

```sh
mkdir -p .local/reverse
swf_source=bin/base/boufbowl-client-1.9.6.swf
java -jar "$FFDEC_JAR" -dumpAS3 "$swf_source" > .local/reverse/classes.txt
rg 'FlashVarsManager|ScriptBuilder|Rules' .local/reverse/classes.txt

java -jar "$FFDEC_JAR" -export script .local/reverse/all "$swf_source"
rg -n 'function getValue|computeSkinId|ResolutionDoneMessage' .local/reverse/all/scripts
```

FFDec creates `scripts/com/.../ClassName.as`. For a known class, export only it:

```sh
as3_class=com.ankamagames.xgaming.utils.flashvars.FlashVarsManager
java -jar "$FFDEC_JAR" -selectclass "$as3_class"   -export script .local/reverse/one "$swf_source"
rg -n -A 35 'function getValue' .local/reverse/one/scripts
```

`-selectclass` also accepts comma-separated names, `com.example.+` for one
package, and `com.example.++` for a package and its descendants.
FFDec exports the containing AS3 script/class; the function source is inside it.

| Area | Starting point |
| --- | --- |
| Startup, toolbar, server bridge | `patches/StartUpApplicationCommand.as` and `ServerSupport.as.inc` |
| Saved options / launch parameters | `patches/OptionsView.as`, `OptionsMediator.as`, `FlashVarsManager.as` |
| Resolution entry and rendering | `patches/ComputeResolutionCommand.as`, `SceneController.as`, `UIController.as` |
| Movement previews | Export `com.ankamagames.boufbowl.client.match.strategic.model.Rules` |
| Network fields / message IDs | `protocol/client_contract.json` and `protocol/chat_contract.json` |
| Server outcomes → original animation tracks | `backend/turn_adapter.py` |
| Appearance and palettes | `patches/BoufbowlerSprite.as`, `tools/visual_assets.py`, `resources/palettes.json` |

Follow callers and their injected dependencies before changing a method.
The server computes outcomes; the client builds and plays resolution scenarios,
then acknowledges with `ResolutionDoneMessage`. A 2D run can acknowledge without
playing the 3D script.

The turn adapter reserves interaction time only on participants' tracks. Other
runners stretch their next step across that window, keeping their next action's
cell and arrival tick. `ScriptBuilder` also joins each interaction to the previous
outcome, so differing animation lengths cannot reorder actions. Field camera
effects keep game time advancing; fullscreen cinematics retain their pause.
Failed catches use the original `FxSprites.MISS` cloud without taking possession
or replacing the pass's link to its eventual catch or rebound.

## Patch one method through its class

Copy the exported class and edit the target method while preserving its package,
imports, signatures, constructors, and metadata:

```sh
cp .local/reverse/one/scripts/com/ankamagames/xgaming/utils/flashvars/FlashVarsManager.as \
  .local/reverse/FlashVarsManager.as
# Edit getValue() in .local/reverse/FlashVarsManager.as.
java -jar "$FFDEC_JAR" -replace "$swf_source" .local/reverse/patched.swf \
  "$as3_class" .local/reverse/FlashVarsManager.as

java -jar "$FFDEC_JAR" -selectclass "$as3_class" \
  -export script .local/reverse/check .local/reverse/patched.swf
rg -n -A 35 'function getValue' .local/reverse/check/scripts
```

Use a separate output SWF. Re-export to confirm the changed method and check
playback; decompilation/compilation can alter behavior or injection metadata.
To inspect bytecode instead of decompiled source:

```sh
java -jar "$FFDEC_JAR" -selectclass "$as3_class" -format script:pcode \
  -export script .local/reverse/pcode "$swf_source"
java -jar "$FFDEC_JAR" -help -replace
```

FFDec supports importing one AS3 P-code method body using its method-body index.
That index belongs to the exact input SWF; the source-class replacement above
does not take an index.

## Make the patch reproducible

1. For a new override, copy the class to `patches/ClassName.as`. For an existing
   override, edit that source instead of replacing it with a fresh decompile.
2. Add the fully qualified name to `classes` in `patches/rebuild.py`. The builder
   locates the file by its class basename.
3. Edit `.as.inc` templates or generators for generated startup/server code;
   files under `.local/` are temporary.
4. Run `python3 patches/rebuild.py --ffdec "$FFDEC_JAR"`, restart the client,
   and exercise the changed flow. Re-export the runnable SWF if needed.
5. Rebuild Android after shared changes. It collects shared `patches/*.as` and
   gives same-named files in `android/patches/` precedence.

Commit the readable patch/generator. The preserved base and generated runnable
SWF have distinct roles; generated clients, decompiles, and captures are ignored.

## Export embedded assets and protocol references

```sh
java -jar "$FFDEC_JAR" -export image,font,sound   .local/reverse/assets "$swf_source"
java -jar "$FFDEC_JAR" -export symbolClass \
  .local/reverse/symbols assets/artworks/cutscene-illustration.swf
```

For selected sprite frames, look up the character ID in the symbol-class export,
then use `-selectid ID -select ID:1-10 -zoom 4 -format sprite:png -export sprite`
with the output directory and library SWF. `tools/site_grid_icons.py` is a working
example. For rendered character poses and gameplay animations, use the
[website exporters](WEBSITE.md#export-characters-and-videos), which apply native
palettes and runtime animation logic.

Main libraries: `cutscene-boufbowler-repository.swf` contains character artwork;
`cutscene-illustration.swf` contains cinematic templates; `assets/sprites/bones/`
contains gameplay animations and `assets/sprites/skins/` their body pieces.
Normal skin IDs are class × 10 + gender; special IDs are 501–518. A portrait
does not prove the corresponding gameplay body exists.

The historical contract extractors require compatible original serializer source.
They can reject local extensions such as ClassOrderTarget's effect-delta field.
Preserve the tracked contracts and compare schema changes manually. The game
extractor writes its Markdown report to the ignored local export folder by default.
