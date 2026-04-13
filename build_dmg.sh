#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="DigitMaid"
ICON_PNG="resource/wisdel/皮肤素材/维什戴尔大人.png"
BUILD_DIR="build/macos"
ICONSET_DIR="$BUILD_DIR/${APP_NAME}.iconset"
ICNS_PATH="$BUILD_DIR/${APP_NAME}.icns"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}.dmg"

PYTHON_EXE="${DM_PYTHON:-}"
if [[ -z "$PYTHON_EXE" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON_EXE=".venv/bin/python"
  else
    PYTHON_EXE="python3"
  fi
fi

for cmd in sips iconutil hdiutil; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd"
    exit 1
  fi
done

if [[ ! -f "$ICON_PNG" ]]; then
  echo "Icon source not found: $ICON_PNG"
  exit 1
fi

echo "[1/5] Generating .icns from $ICON_PNG"
mkdir -p "$BUILD_DIR"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

sips -z 16 16   "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32   "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32   "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64   "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"

echo "[2/5] Installing dependencies"
"$PYTHON_EXE" -m pip install -r requirements.txt pyinstaller==6.16.0

echo "[3/5] Building macOS app with icon"
"$PYTHON_EXE" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ICNS_PATH" \
  --add-data "resource:resource" \
  --add-data "src/function/apps.yaml:src/function" \
  --add-data "src/input/dialog_style.yaml:src/input" \
  --add-data "src/ui/maid_animations.yaml:src/ui" \
  src/core/run.py

echo "[4/5] Packing DMG"
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

echo "[5/5] Done"
echo "App: $APP_PATH"
echo "DMG: $DMG_PATH"
