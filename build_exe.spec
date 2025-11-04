# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# 收集tables的数据文件和动态库
tables_datas = collect_data_files('tables')
tables_binaries = collect_dynamic_libs('tables')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        ('parser_core/dll_parser/stdf_ctype.dll', 'parser_core/dll_parser'),
        # visual.pyd已移除，使用Python fallback实现
    ] + tables_binaries,
    datas=[
        ('icon_swf.ico', '.'),
        ('ui_component/ui_resource/source', 'ui_component/ui_resource/source'),
    ] + tables_datas,
    hiddenimports=[
        'PySide2.QtCore',
        'PySide2.QtGui',
        'PySide2.QtWidgets',
        'PySide2.QtPrintSupport',
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.dockarea',
        'pyqtgraph.parametertree',
        'Semi_ATE.STDF',
        'pandas',
        'numpy',
        'tables',
        'tables.nodes',
        'tables.parameters',
        'tables.hdf5extension',
        'numexpr',
        'prettytable',
        'xlsxwriter',
        'loguru',
        'colorama',
        'var_language',
        'subprocess',
        'multiprocessing',
        'multiprocessing.Process',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'PIL',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='STDF_Analysis',
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
    icon='icon_swf.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='STDF_Analysis',
)