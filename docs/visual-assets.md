# Stadium textures and customization palettes

`resources/stadium_art.json` selects a surface for each stadium. Farmstead keeps
its original texture. Eight court atlases were imported from the neighboring
`boufbowl/assets/courts` directory and converted losslessly from WebP to PNG for
Flash/AIR. The manifest records source paths and SHA-256 hashes; runtime builds
need only the copies included here. Source archives remain unchanged.

| Stadium | Surface |
| --- | --- |
| Farmstead | Original prairie pitch |
| Brakmar | Brakmar |
| Beach | Sand |
| Bonta | Grass |
| Frigost | Clouds |
| Kara | Kara |
| Forest | Meadow |
| Ballotin | Wabbits |
| Pixel | Prairies atlas |

These are configurable visual themes, not recovered original 3D stadium models.
All variants retain the available Farmstead geometry and scenery. In particular,
Clouds for Frigost and Prairies for Pixel are selected substitutes. Choosing a
texture changes appearance only; stadium balance remains in `game_config.json`.
The recovered 2D strategic backgrounds remain embedded in the original client.

`tools/visual_assets.py` generates compatible COLLADA variants during resource
preparation. Atlas regions select the field without resizing or repainting the
original artwork. Only UV indices used exclusively by ground triangles change;
scenery UVs remain intact. Away3D uses one shared texture-path base, so each
variant keeps its texture dependencies in a local `images/` folder. Its parser
also appends UV sources without rebasing indices, so adding a second UV source
would silently sample the wrong atlas region.

Edit `resources/palettes.json` to adjust club and character colors. There are 11
club palettes, with 10 colors in the standard palette. The shared class/hero
choices include 16 hair colors, 10 eye colors and 10 skin tones. Three additional
character palettes—Pastel, Vivid and Natural—are available to every class and
special character. Original palette IDs remain valid. Choices are free and saved
through the existing customization service; animation fallback still uses Cra.

The original color grid supports at most 16 colors per list; the fixed club editor
layout fits 10 without clipping. Palette validation
rejects longer lists, invalid RGB hex values and duplicate IDs. Both desktop and
Android startup code read the same catalog at build time. Additional character
palette names are inserted into all four client languages without changing the
rest of the recovered language file. Repeated resource preparation is safe.

Rebuild after editing palette colors:

```sh
python3 patches/rebuild.py --ffdec /path/ffdec.jar --original /path/original.swf
python3 linux/build.py
python3 android/build.py --air-sdk /path/AIRSDK --ffdec /path/ffdec.jar --jdk /path/jdk-17
```

Validation covers both platform palette catalogs, repeatable translations,
texture dependencies and unchanged scenery UVs. Native Brakmar replay confirms
that the surface renders and resolution completes; character customization
shows the expanded color choices. Android is package-verified, not device-tested.
