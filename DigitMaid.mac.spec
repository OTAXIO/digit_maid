# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/core/run.py'],
    pathex=[],
    binaries=[],
    datas=[('resource', 'resource'), ('src/function/apps.yaml', 'src/function'), ('src/input/dialog_style.yaml', 'src/input'), ('src/ui/maid_animations.yaml', 'src/ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DigitMaid',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['build/macos/DigitMaid.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DigitMaid',
)
app = BUNDLE(
    coll,
    name='DigitMaid.app',
    icon='build/macos/DigitMaid.icns',
    bundle_identifier=None,
)
