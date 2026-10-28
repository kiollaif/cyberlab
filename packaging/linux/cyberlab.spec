Name: cyberlab
Version: 0.1.0
Release: alt0.1
Summary: Interactive cybersecurity learning laboratory
License: Proprietary
Group: Education
URL: https://github.com/kiollaif/cyberlab
Source0: CyberLab-linux-bundle.tar.gz
Source1: cyberlab.desktop
Source2: cyberlab.png
ExclusiveArch: x86_64
AutoReqProv: no
Requires: glibc-core >= 2.35
Requires: libX11, libEGL, libGL, libfontconfig, libdbus, libxcb
Requires: libxkbcommon, libxkbcommon-x11, libxcbutil-cursor

# Python и Qt уже в пакете. Их бинарные файлы нельзя повторно strip-ить.
%set_strip_method none
%define debug_package %{nil}

%description
CYBERLAB is an offline educational simulator with decision history,
alternative branches and an optional online mentor. This RPM is an
ALT p11 candidate; ALT Education must be tested separately.

%prep
%setup -q -n CyberLab

%build
# Приложение уже собрано PyInstaller на Ubuntu 22.04 (glibc 2.35).

%install
mkdir -p %buildroot/opt/cyberlab %buildroot/usr/bin
cp -a . %buildroot/opt/cyberlab/
ln -s /opt/cyberlab/CyberLab %buildroot/usr/bin/cyberlab
install -Dm644 %SOURCE1 %buildroot/usr/share/applications/cyberlab.desktop
install -Dm644 %SOURCE2 %buildroot/usr/share/icons/hicolor/256x256/apps/cyberlab.png

%files
/opt/cyberlab
/usr/bin/cyberlab
/usr/share/applications/cyberlab.desktop
/usr/share/icons/hicolor/256x256/apps/cyberlab.png
