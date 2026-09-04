# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


REPO_ROOT = Path(SPECPATH).resolve().parents[2]

a = Analysis(
    [str(REPO_ROOT / 'src' / 'core' / 'run.py')],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(REPO_ROOT / 'resource'), 'resource'),
        (str(REPO_ROOT / 'config'), 'config'),
    ],
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
    icon=[str(REPO_ROOT / 'build' / 'macos' / 'DigitMaid.icns')],
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
    icon=str(REPO_ROOT / 'build' / 'macos' / 'DigitMaid.icns'),
    bundle_identifier=None,
)
