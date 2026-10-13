# Boufbowl for Linux

The .deb and tar archive include the compiled original Flash client, assets,
Flash Player, Python/SQLite replacement backend, Bun runtime and launcher.
Default startup runs persistent local matches. A graphical X11/XWayland session
is required.

Ubuntu dependencies:

```sh
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install python3 wine wine32:i386
sudo apt install ./linux/build/BoufbowlOffline-linux-amd64.deb
```

Launch **Boufbowl Offline** from the application menu, or run
`/opt/boufbowl-offline/play.sh`. Alternatively extract
`build/BoufbowlOffline-linux.tar.gz` and run its `play.sh`. **Play** on the toolbar
starts a CPU match or resumes a checkpoint. Use the original Play menu for
nickname challenges. `--mode tutorial` opens the tutorial; `--mode menus` opens
the session preview. `--lang fr` selects French.

Shared backend:

```sh
python3 -m backend.server --host 0.0.0.0 --port 9900
./play.sh --server-url http://SERVER_ADDRESS:9900 --profile Alice
```

For device sessions, backup/restore and recorded replays, see
[backend operation](../docs/backend-operation.md).

Rebuild from the preserved original 1.9.6 SWF:

```sh
python3 patches/rebuild.py --ffdec /path/ffdec.jar --original /path/original.swf
python3 linux/build.py
```

A source checkout needs Bun installed in addition to Python/Wine. Run `./play.sh`
directly; its compiled client and worker are included. No sibling project or SDK
is needed for playback. Packaging uses the included worker by default.

Rebuilding the Flash client needs Java and FFDec. Rebuilding the simulation worker
uses `python3 linux/build.py --rebuild-worker` and the sibling `boufbowl_server`
source. Packaging needs Python, dpkg-deb and Bun; the resulting package bundles
Bun. Readable changes remain in `patches/`.
