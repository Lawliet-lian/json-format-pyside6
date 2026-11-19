# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['json_formatter_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='JSON格式化',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon-dark.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='JSON格式化',
)
app = BUNDLE(
    coll,
    name='JSON格式化.app',
    icon='icon-dark.icns',
    bundle_identifier='com.lawliet.jsonformatter',
    # macOS Finder 和“显示简介”里的版本号来自 Info.plist。
    # 如果这里不显式写入版本字段，某些构建结果会显示默认值 0.0.0。
    info_plist={
        'CFBundleShortVersionString': '2.0.5',
        'CFBundleVersion': '2.0.5',
    },
)
