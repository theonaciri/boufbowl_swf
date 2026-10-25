#!/bin/sh
# One downloadable executable; game assets are extracted only on first launch.
set -eu
umask 077
if ! command -v wine >/dev/null 2>&1; then
    echo "Installez Wine avec la prise en charge 32 bits pour jouer." >&2
    exit 1
fi
cache=${XDG_CACHE_HOME:-"$HOME/.cache"}/boufbowl/player
revision='@REVISION@'
target=$cache/$revision
ready() {
    [ -f "$target/.complete" ] && [ -x "$target/BoufbowlUpdater" ] && [ -f "$target/update-client.json" ] && [ -f "$target/flashplayer.exe" ] && [ -f "$target/bin/boufbowl-client-1.9.6.swf" ]
}
if ! ready; then
    mkdir -p -- "$cache"
    stage=$(mktemp -d "$cache/.extract.XXXXXX")
    trap 'rm -rf -- "$stage"' 0
    trap 'exit 130' INT
    trap 'exit 143' TERM
    tail -n +@PAYLOAD_LINE@ -- "$0" > "$stage/payload.tar.gz"
    actual=$(sha256sum "$stage/payload.tar.gz")
    if [ "${actual%% *}" != "$revision" ]; then
        echo "Le telechargement de Boufbowl Fan est incomplet ou endommage." >&2
        exit 1
    fi
    tar -xzf "$stage/payload.tar.gz" -C "$stage"
    printf '%s\n' "$revision" > "$stage/Boufbowl/.complete"
    # Move an incomplete previous extraction aside before publishing the new one.
    if [ -e "$target" ] && ! ready; then
        mv -T -- "$target" "$stage/incomplete" || true
    fi
    # -T avoids nesting files into another launch's already prepared cache.
    if ! mv -T -- "$stage/Boufbowl" "$target"; then
        if ! ready; then
            echo "Impossible de preparer Boufbowl Fan dans $target." >&2
            exit 1
        fi
    fi
    rm -rf -- "$stage"
    trap - 0 INT TERM
fi
# Register the cached launcher with desktop environments after the first run.
# Shell executables do not have a portable embedded application icon.
data_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}
applications=$data_dir/applications
icons=$data_dir/icons/hicolor/256x256/apps
if mkdir -p -- "$applications" "$icons"; then
    cp -- "$target/icon.png" "$icons/boufbowl-fan.png"
    desktop_exec=$(printf '%s' "$target/BoufbowlUpdater" | sed 's/\\/\\\\/g; s/"/\\"/g; s/`/\\`/g; s/\$/\\$/g; s/%/%%/g')
    {
        printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Boufbowl Fan'
        printf 'Exec="%s"\n' "$desktop_exec"
        printf '%s\n' 'Icon=boufbowl-fan' 'Terminal=false' 'Categories=Game;'
    } > "$applications/boufbowl-fan.desktop"
fi
cd -- "$target"
exec ./BoufbowlUpdater
exit 1
__BOUFBOWL_PAYLOAD__
