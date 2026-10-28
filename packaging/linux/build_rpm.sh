#!/bin/bash
# Только внутри официального контейнера alt:p11. Это НЕ Альт Образование.
set -euo pipefail
cd /work
mkdir -p /work/dist/rpm
log=/work/dist/rpm/build.log
report_error() {
    result=$?
    message=$(tail -c 2800 "$log")
    message=${message//%/%25}
    message=${message//$'\r'/%0D}
    message=${message//$'\n'/%0A}
    echo "::error title=ALT RPM::exit=$result $message"
    exit "$result"
}
trap report_error ERR
# Для x86_64-сборки не скачиваем индексы 32-битного репозитория. Ограничиваем
# ожидание зеркала, чтобы сетевая ошибка не держала сборку десятки минут.
sed -i '/^[^#].*x86_64-i586/d; s@http://@https://@g' /etc/apt/sources.list.d/*.list
printf '%s\n' 'Acquire::http::Timeout "20";' 'Acquire::https::Timeout "20";' \
    'Acquire::Retries "1";' > /etc/apt/apt.conf.d/99cyberlab-network
apt-get update 2>&1 | tee "$log"
apt-get install -y rpm-build python3 tar gzip coreutils binutils shadow-utils \
    xorg-xvfb xauth fonts-ttf-dejavu libGL libEGL libfontconfig libdbus \
    libX11 libxcb libxkbcommon libxkbcommon-x11 libxcbutil-cursor 2>&1 | tee -a "$log"
top=/work/build/rpm
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} /work/dist/rpm
cp downloads/CyberLab-linux-bundle.tar.gz "$top/SOURCES/"
cp packaging/linux/cyberlab.desktop "$top/SOURCES/"
cp src/cyberlab/resources/cyberlab.png "$top/SOURCES/"
cp packaging/linux/cyberlab.spec "$top/SPECS/"
# Политика ALT запрещает rpmbuild от root. Root нужен только для apt и установки
# тестового пакета; сама сборка идёт от отдельного непривилегированного пользователя.
useradd --create-home --shell /bin/bash cyberlab-builder
chown -R cyberlab-builder:cyberlab-builder "$top"
su -s /bin/bash cyberlab-builder -c \
    "rpmbuild --define '_topdir $top' --target x86_64 -bb '$top/SPECS/cyberlab.spec'" \
    2>&1 | tee -a "$log"
package=$(find "$top/RPMS" -name 'cyberlab-*.rpm' -type f | head -1)
test -n "$package"
rpm -ivh "$package"
test -f /usr/share/applications/cyberlab.desktop
test -f /usr/share/icons/hicolor/256x256/apps/cyberlab.png
Xvfb :95 -screen 0 1600x1000x24 > /work/dist/rpm/xvfb.log 2>&1 &
xserver=$!
trap 'kill "$xserver" 2>/dev/null || true' EXIT
export DISPLAY=:95 QT_QPA_PLATFORM=xcb
for attempt in $(seq 1 30); do
    if [ -S /tmp/.X11-unix/X95 ]; then break; fi
    sleep 1
done
python3 scripts/verify_desktop.py /usr/bin/cyberlab --report /work/dist/rpm/alt-p11-smoke.json
rpm -q --requires cyberlab > /work/dist/rpm/rpm-requires.txt
cat /etc/os-release > /work/dist/rpm/tested-system.txt
rpm -e cyberlab
test ! -e /usr/bin/cyberlab
test ! -e /usr/share/applications/cyberlab.desktop
cp "$package" /work/dist/rpm/CyberLab-alt-p11-unverified.rpm
printf '%s\n' \
    'Кандидат RPM: проверен только в ALT Container p11, не в Альт Образование.' \
    'Не переименовывать в CyberLab.rpm и не объявлять совместимым до проверки' \
    'на установленной Альт Образование с KDE/GNOME и её менеджером пакетов.' \
    > /work/dist/rpm/UNVERIFIED-ALT-EDUCATION.txt
cd /work/dist/rpm
sha256sum CyberLab-alt-p11-unverified.rpm > SHA256SUMS.txt
