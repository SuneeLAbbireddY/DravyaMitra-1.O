# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/mix_design_calculator_new.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/concrete_model.pkl', '.'),
        ('src/concrete_scaler.pkl', '.'),
    ],
    hiddenimports=[
        'sklearn.tree._utils',
        'sklearn.neighbors._partition_nodes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='concrete_calculator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'
) 