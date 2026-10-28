#!/bin/bash
# Запускается внутри dbus-run-session и xvfb-run. Проверяет настоящий WM.
set -euo pipefail
desktop=$1
image=$(realpath "$2")
report=$(realpath -m "$3")
mkdir -p "$(dirname "$report")"
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export APPIMAGE_EXTRACT_AND_RUN=1
export XDG_RUNTIME_DIR
XDG_RUNTIME_DIR=$(mktemp -d)
chmod 700 "$XDG_RUNTIME_DIR"
case "$desktop" in
    kde)
        export XDG_CURRENT_DESKTOP=KDE
        kwin_x11 --replace --no-global-shortcuts >"${report%.json}-wm.log" 2>&1 &
        ;;
    gnome)
        export XDG_CURRENT_DESKTOP=GNOME
        gnome-shell --x11 --replace --sm-disable >"${report%.json}-wm.log" 2>&1 &
        ;;
    *) exit 2 ;;
esac
wm=$!
trap 'kill "$wm" 2>/dev/null || true; rm -rf "$XDG_RUNTIME_DIR"' EXIT
ready=false
for attempt in $(seq 1 30); do
    if ! kill -0 "$wm" 2>/dev/null; then
        cat "${report%.json}-wm.log"
        echo "Window manager exited before the application started" >&2
        exit 1
    fi
    property=$(xprop -root _NET_SUPPORTING_WM_CHECK)
    if [[ "$property" == *"window id"* ]]; then
        id=${property##* }
        name=$(xprop -id "$id" _NET_WM_NAME)
        if [[ "$desktop:$name" == kde:*KWin* || "$desktop:$name" == gnome:*GNOME* ]]; then
            echo "$name" | tee "${report%.json}-wm.txt"
            ready=true
            break
        fi
    fi
    sleep 1
done
if [[ "$ready" != true ]]; then
    cat "${report%.json}-wm.log"
    echo "Requested window manager did not acquire the display" >&2
    exit 1
fi
python3 scripts/verify_desktop.py "$image" --report "$report"
kill -0 "$wm"
