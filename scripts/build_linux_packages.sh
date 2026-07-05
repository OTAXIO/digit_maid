#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

REPO_ROOT="$(pwd)"
APP_NAME="DigitMaid"
PACKAGE_NAME="digitmaid"
ICON_PNG="resource/wisdel/皮肤素材/维什戴尔大人.png"
BUILD_DIR="build/linux"
DIST_DIR="dist"
APP_DIST_DIR="$DIST_DIR/$APP_NAME"
PACKAGE_ROOT="$BUILD_DIR/package-root"
PACKAGE_ROOT_ABS="$REPO_ROOT/$PACKAGE_ROOT"
RPM_TOPDIR="$BUILD_DIR/rpmbuild"

RAW_VERSION="${DM_VERSION:-${GITHUB_REF_NAME:-0.1.0}}"
VERSION="$(printf '%s' "$RAW_VERSION" | sed -E 's/^v//; s/[^0-9A-Za-z.+~]/./g')"
if [[ -z "$VERSION" ]]; then
  VERSION="0.1.0"
fi

PYTHON_EXE="${DM_PYTHON:-python3}"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)
    DEB_ARCH="amd64"
    RPM_ARCH="x86_64"
    ;;
  aarch64|arm64)
    DEB_ARCH="arm64"
    RPM_ARCH="aarch64"
    ;;
  *)
    DEB_ARCH="$ARCH"
    RPM_ARCH="$ARCH"
    ;;
esac

echo "[1/6] Installing Python build dependencies"
"$PYTHON_EXE" -m pip install -r requirements.txt pyinstaller==6.16.0

echo "[2/6] Building Linux app bundle"
"$PYTHON_EXE" -m PyInstaller --noconfirm --clean DigitMaid.linux.spec

if [[ ! -x "$APP_DIST_DIR/$APP_NAME" ]]; then
  echo "Build finished but $APP_DIST_DIR/$APP_NAME was not found."
  exit 1
fi

echo "[3/6] Staging package root"
rm -rf "$PACKAGE_ROOT" "$RPM_TOPDIR"
mkdir -p \
  "$PACKAGE_ROOT/opt/$PACKAGE_NAME" \
  "$PACKAGE_ROOT/usr/bin" \
  "$PACKAGE_ROOT/usr/share/applications" \
  "$PACKAGE_ROOT/usr/share/pixmaps" \
  "$PACKAGE_ROOT/DEBIAN"

cp -a "$APP_DIST_DIR/." "$PACKAGE_ROOT/opt/$PACKAGE_NAME/"
cp "$ICON_PNG" "$PACKAGE_ROOT/usr/share/pixmaps/$PACKAGE_NAME.png"

cat > "$PACKAGE_ROOT/usr/bin/$PACKAGE_NAME" <<'EOF'
#!/usr/bin/env bash
exec /opt/digitmaid/DigitMaid "$@"
EOF
chmod 0755 "$PACKAGE_ROOT/usr/bin/$PACKAGE_NAME"

cat > "$PACKAGE_ROOT/usr/share/applications/$PACKAGE_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DigitMaid
Comment=Virtual desktop maid assistant
Exec=$PACKAGE_NAME
Icon=$PACKAGE_NAME
Terminal=false
Categories=Utility;
StartupNotify=false
EOF

find "$PACKAGE_ROOT/opt/$PACKAGE_NAME" -type d -exec chmod 0755 {} \;
find "$PACKAGE_ROOT/opt/$PACKAGE_NAME" -type f -exec chmod 0644 {} \;
chmod 0755 "$PACKAGE_ROOT/opt/$PACKAGE_NAME/$APP_NAME"

echo "[4/6] Building .deb"
cat > "$PACKAGE_ROOT/DEBIAN/control" <<EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Maintainer: DigitMaid Maintainers <noreply@example.com>
Depends: libxcb-cursor0, libxkbcommon-x11-0, libxcb-xinerama0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libgl1
Description: DigitMaid virtual desktop assistant
 DigitMaid is a PyQt-based desktop companion with menus, reminders, screenshots, and app shortcuts.
EOF

mkdir -p "$DIST_DIR"
dpkg-deb --root-owner-group --build "$PACKAGE_ROOT" "$DIST_DIR/${APP_NAME}-linux-${RPM_ARCH}.deb"

echo "[5/6] Building .rpm"
mkdir -p "$RPM_TOPDIR/BUILD" "$RPM_TOPDIR/BUILDROOT" "$RPM_TOPDIR/RPMS" "$RPM_TOPDIR/SOURCES" "$RPM_TOPDIR/SPECS" "$RPM_TOPDIR/SRPMS"
cat > "$RPM_TOPDIR/SPECS/$PACKAGE_NAME.spec" <<EOF
Name:           $PACKAGE_NAME
Version:        $VERSION
Release:        1%{?dist}
Summary:        DigitMaid virtual desktop assistant
License:        Unknown
URL:            https://github.com
AutoReqProv:    no

%description
DigitMaid is a PyQt-based desktop companion with menus, reminders, screenshots, and app shortcuts.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a "$PACKAGE_ROOT_ABS"/opt %{buildroot}/
cp -a "$PACKAGE_ROOT_ABS"/usr %{buildroot}/

%files
/opt/$PACKAGE_NAME
/usr/bin/$PACKAGE_NAME
/usr/share/applications/$PACKAGE_NAME.desktop
/usr/share/pixmaps/$PACKAGE_NAME.png
EOF

rpmbuild -bb "$RPM_TOPDIR/SPECS/$PACKAGE_NAME.spec" --define "_topdir $REPO_ROOT/$RPM_TOPDIR"
RPM_PATH="$(find "$RPM_TOPDIR/RPMS" -type f -name '*.rpm' | head -n 1)"
if [[ -z "$RPM_PATH" ]]; then
  echo "RPM build finished but no .rpm was found."
  exit 1
fi
cp "$RPM_PATH" "$DIST_DIR/${APP_NAME}-linux-${RPM_ARCH}.rpm"

echo "[6/6] Done"
echo "DEB: $DIST_DIR/${APP_NAME}-linux-${RPM_ARCH}.deb"
echo "RPM: $DIST_DIR/${APP_NAME}-linux-${RPM_ARCH}.rpm"
