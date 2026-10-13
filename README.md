# Boufbowl offline menus and tutorial on Linux

An Android APK and build instructions are available in [android/README.md](android/README.md).

## Requirements

Use Linux with Python 3, Wine, and X11 or XWayland. Adobe Flash Player 32 is
included in `bin/flashplayer_32_sa.exe`.

The server used here is a local HTTP asset server: it serves the SWF, videos,
sprites, sounds, and configuration files. Menus and tutorial logic run inside
the patched Flash client; they require no Boufbowl account or game server.

## Start server and client together

Run this from any directory:

```sh
/home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf/play.sh
```

The launcher starts the HTTP server on an available localhost port, then opens
the main menu in Flash Player under Wine. Keep the terminal open while
playing. Closing Flash Player stops the server automatically.

English is the default. To play in French:

```sh
/home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf/play.sh --lang fr
```

Supported language codes are `en`, `fr`, `de`, and `es`. Run the launcher again
to start a fresh offline session.

To enter the tutorial directly:

```sh
/home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf/play.sh --mode tutorial --lang en
```

## Browse the menus

The navigation strip at the upper right provides **Home**, **Teams**,
**Tutorial**, and **Quit**. Home returns to the main menu from any screen.

| Screen | How to open it | Offline behavior |
| --- | --- | --- |
| Main menu | Default startup or **Home** | Shows a local team and ten players. |
| Team selection | **Teams** | Browse three sample teams and two special-character teams; choose colors, an emblem, and a valid team name. |
| Team customization | **Customize the team** | Change the name, colors, and emblem; **OK** applies changes to the session. |
| New team | **New team** | Opens the original team builder with local customization options. |
| Player customization | Icons beside a player on Home | Explore appearance and composition; **OK** applies changes to the session. |
| Match setup | **Play** | Opens the original match setup menu. Starting a match explains that online play needs a game server. |
| Leaderboard | **Leaderboard** | Opens the original ranking menu with an empty offline list. |
| Tournaments | **Tournament** | Opens the original tournament menu with an empty offline list. |
| Options | Small gear at the upper right | Opens the original sound and options panel. |
| Tutorial | **Learn to play** or **Tutorial** | Plays the original interactive tutorial. |

Sample teams, player attributes, palettes, and customization credits are local
preview data. Edits last until the player closes; restarting resets them.
Use alphabetic player names of 4–30 characters: the original validator rejects
digits and names outside that length range.

## Unlocked characters

All 14 regular classes are available in both genders, together with all 18
special characters named by the client. Open a player's customization menu,
select a class on the left, then select a special character's starred portrait.
Class changes are also enabled in the appearance editor for this offline copy.
Click **OK**, then **Confirm**, to apply the choice to the current session.

To browse the whole special roster quickly, open **Teams** and advance to
**Offline Legends** (team 4/5) or **Offline Heroes** (team 5/5). These teams
contain all 18 special characters. Goultard is the fifth player in Offline
Legends; you can also select his starred portrait under the Iop class.

| Character ID | Special character (English client name) |
| --- | --- |
| 501 | Kriss Krass |
| 502 | Pita Smisse |
| 503 | Maud |
| 504 | The Masked Gobbowler |
| 505 | Goultard the Barbarian |
| 506 | Amalia Sheran Sharm |
| 507 | Miranda |
| 508 | Evangelyne |
| 509 | Ruel Stroud |
| 510 | Shosanne |
| 511 | Kabrok |
| 512 | Brumen Tinctorias |
| 513 | Count Harebourg |
| 514 | Pan Diego |
| 515 | Ironman |
| 516 | Jack Chaferton |
| 517 | Armand |
| 518 | Skunk |

Regular classes: Cra, Ecaflip, Eniripsa, Enutrof, Feca, Iop, Osamodas, Pandawa,
Rogue, Sacrier, Sadida, Sram, Xelor, and Masqueraider.

Special characters use their original illustrations in the editor and team
views. Their separate animated skin files were not included in the supplied
archive, so the small editor preview also uses the illustration and hides the
animation arrows. Regular characters retain their animated previews. Class
attributes and colors remain offline preview data. The machine-readable roster
is in [resources/offline_characters.json](resources/offline_characters.json).

## Start server and client separately

Use this when you want to keep the asset server running between client sessions.
You do not need these steps when using `play.sh`.

### Terminal 1: asset server

Serve the copy's root directory, which contains `bin/`, `assets/`, and `resources/`:

```sh
cd /home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf
python3 -m http.server 8765 --bind 127.0.0.1
```

Leave this terminal running. Asset requests appear in its output.

### Terminal 2: Flash client

Set up the same dedicated Wine environment used by the launcher and open the
SWF through the server:

```sh
cd /home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf/bin
export WINEPREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/boufbowl-tutorial/wine"
export WINEDEBUG=-all
mkdir -p "$(dirname "$WINEPREFIX")"
wine reg add 'HKCU\Software\Wine\Drivers' /v Graphics /d x11 /f
wine ./flashplayer_32_sa.exe 'http://127.0.0.1:8765/bin/boufbowl-client-1.9.6.swf?lang=en'
```

Change `lang=en` to `lang=fr`, `lang=de`, or `lang=es` as desired. Append
`&tuto=1` inside the quoted URL to start the tutorial directly. The Wine
registry setting selects X11/XWayland for this game's dedicated prefix.
The first run may take longer while Wine creates that prefix.

Close Flash Player to stop the client. In terminal 1, press **Ctrl+C** to stop
the server. You can leave the server running and repeat the last `wine` command
to start a fresh session.

## Tutorial controls

Click the green arrow to advance dialogue; some screens wait for speech or an
animation to finish before showing it. During exercises, drag a player's
icon to the indicated hexagon or character and click the gong to validate.
The orange cross leaves the tutorial and returns to Home. Completing the
tutorial also returns to Home. **Quit** in the navigation strip closes Flash
Player and lets the automatic launcher stop its asset server.

## Files and changes

This is a separate copy of `swf_sources/boufbowl_client`: the original archive
is untouched. The SWF defaults to English, bypasses online login, seeds local
menu data, and handles menu requests within the client. The copied configuration
disables Facebook and starts in 2D. All original tutorial videos, sprites,
sounds and artwork are retained.

## Logs and troubleshooting

The automatic launcher uses a dedicated Wine prefix at `$XDG_DATA_HOME/boufbowl-tutorial/wine`
(normally `~/.local/share/boufbowl-tutorial/wine`). Logs are in
`$XDG_STATE_HOME/boufbowl-tutorial` (normally `~/.local/state/boufbowl-tutorial`).
The launcher writes `wine.log` for player diagnostics and `http.log` for asset
requests. Manual mode shows diagnostics directly in the two terminals.

- **Blank client when opening a file:** launch through `play.sh` or use the HTTP
  URL above. Opening the SWF directly as a local file encounters Flash's
  local-file security restrictions.
- **Address already in use:** an asset server may already be running on port
  `8765`. Use it if it serves this copy, or choose another port, such as `8766`,
  in both the server command and the client URL. The automatic launcher chooses
  an available port itself.
- **Missing assets / HTTP 404:** start the manual server in `boufbowl_tutorial/`,
  rather than its `bin/` subdirectory. Keep the copied directory structure intact.
- **No player window:** run from a graphical Linux session with Wine and
  X11/XWayland available, then inspect `wine.log` or the manual terminal output.

## Rebuild the patched client

The patched SWF is already built. To rebuild using JPEXS FFDec 26.3.0 and Java:

```sh
cd /home/naciri_t/projects/Godot/BoufBowlExtraFiles/boufbowl_swf
python3 patches/rebuild.py --ffdec /path/to/ffdec.jar
```

The modified ActionScript classes are in `patches/`. `StartUpApplicationCommand`
seeds offline data and handles local menu requests; `ChannelPipeline` prevents
game-server connections. The customization commands apply edits locally, and
`TutorialFinishedCommand` returns to Home. `BoufbowlClient` displays uncaught
errors, `FlashVarsManager` supplies the default language, and `WelcomeView`
respects the disabled Facebook setting. The team selection view uses the sample
teams' names, and confirmation dialogs describe local session changes. The
copied sound configuration uses an available click sound in place of the
archive's missing `fleche_drop_01.mp3`. The rebuild reads the untouched
original SWF and replaces these classes using
[FFDec's script replacement command](https://github.com/jindrapetrik/jpexs-decompiler/wiki/Commandline-arguments).

The SWF is a binary containing compiled ActionScript 3 bytecode and embedded
assets. FFDec decompiles selected classes to `.as` source, recompiles the edited
source to bytecode, and replaces those classes in a new SWF. The `.as` files are
the readable patch sources; `rebuild.py` applies them to the original binary.

## Rendered verification

Checked in Adobe Flash Player 32 under Wine: Home, team selection, team and
player editors, saving colors and appearance, leaderboard, tournaments, match
setup, options, tutorial entry and return to Home, and quitting the player.
The automatic launcher exits successfully and stops its asset server on quit.
Both special-character teams render all 18 original illustrations. Goultard can
be selected and saved to the current team; switching between a special character
and a regular character restores the appropriate preview and animation controls.

Screenshots: [Home](evidence/home.png), [team selection](evidence/team-selection.png),
[player editor](evidence/player-editor.png), [options](evidence/options.png).
Character screenshots: [Goultard editor](evidence/goultard-editor.png),
[Goultard saved](evidence/goultard-saved.png), [heroes team](evidence/heroes-team.png).
