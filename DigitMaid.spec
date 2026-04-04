# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


PROJECT_ROOT = Path.cwd()


a = Analysis(
    [str(PROJECT_ROOT / 'src' / 'core' / 'run.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / 'resource'), 'resource'),
        (str(PROJECT_ROOT / 'src' / 'function' / 'apps.yaml'), 'src/function'),
        (str(PROJECT_ROOT / 'src' / 'input' / 'dialog_style.yaml'), 'src/input'),
        (str(PROJECT_ROOT / 'src' / 'ui' / 'pet_animations.yaml'), 'src/ui'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DigitMaid',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(PROJECT_ROOT / 'icon.ico')],
)
