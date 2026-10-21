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
    [ -f "$target/.complete" ] && [ -f "$target/flashplayer.exe" ] && [ -f "$target/bin/boufbowl-client-1.9.6.swf" ]
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
        echo "Le telechargement de Boufbowl est incomplet ou endommage." >&2
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
            echo "Impossible de preparer Boufbowl dans $target." >&2
            exit 1
        fi
    fi
    rm -rf -- "$stage"
    trap - 0 INT TERM
fi
cd -- "$target"
exec ./jouer.sh
exit 1
__BOUFBOWL_PAYLOAD__
