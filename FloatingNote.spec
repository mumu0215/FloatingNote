# -*- mode: python ; coding: utf-8 -*-
# onedir package: FloatingNote.exe MUST sit next to _internal/

a = Analysis(
    ['app_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/app.ico', 'assets'),
        ('assets/app.png', 'assets'),
    ],
    hiddenimports=[
        'src.main',
        'src.storage',
        'src.autostart',
        'src.paths',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.IcoImagePlugin',
        'PIL.PngImagePlugin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # unused GUI / science stacks
        'gi',
        'gtk',
        'PySide2',
        'PySide6',
        'PyQt5',
        'PyQt6',
        'matplotlib',
        'numpy',
        'scipy',
        # non-Windows pystray backends (shrink analysis; avoids flaky 3.13 dis bugs)
        'pystray._darwin',
        'pystray._gtk',
        'pystray._appindicator',
        'pystray._xorg',
        'pystray._dummy',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FloatingNote',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FloatingNote',
)
