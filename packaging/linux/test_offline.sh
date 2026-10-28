#!/bin/bash
# Внутри Docker --network none, без монтирования исходников и Python.
set -euo pipefail
if command -v python3 || command -v python || command -v uv; then
    echo 'В тестовом образе неожиданно установлен Python/uv' >&2
    exit 1
fi
if [ "$(wc -l < /proc/net/route)" -ne 1 ]; then
    echo 'Ожидался контейнер без сетевых маршрутов' >&2
    exit 1
fi
export QT_QPA_PLATFORM=xcb APPIMAGE_EXTRACT_AND_RUN=1 LANG=C.UTF-8
export XDG_DATA_HOME=/tmp/cyberlab-data XDG_CONFIG_HOME=/tmp/cyberlab-config
export XDG_CACHE_HOME=/tmp/cyberlab-cache DISPLAY=:91
Xvfb :91 -screen 0 1600x1000x24 > /artifacts/offline-xvfb.log 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT
for attempt in $(seq 1 20); do
    if [ -S /tmp/.X11-unix/X91 ]; then break; fi
    sleep 1
done
/artifacts/CyberLab-x86_64.AppImage --smoke-test /artifacts/linux-isolated-offline-smoke.json
cat /artifacts/linux-isolated-offline-smoke.json
