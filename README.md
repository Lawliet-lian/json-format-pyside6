# 简介
这是一个json格式化app，采用pyside6开发

## mac 应用图标尺寸约定

本仓库后续制作或调整 macOS 打包图标时，以 Xcode 26.3 的应用图标为尺寸基准。该基准来自本机 `Xcode26.3.app/Contents/Resources/Xcode.icns` 的实际测量，不代表所有 macOS 图标必须使用相同比例。

- 图标使用正方形透明画布，提供最大 1024 × 1024 像素的图像，并生成包含多种尺寸的 `.icns` 文件。
- 以不透明度大于等于 50% 的像素计算可见范围，图案宽度和高度各占画布的 **80.47%**。换算为 1024 × 1024 画布，约为 **824 × 824 像素**，居中放置。
- 打包后以安装到 macOS 的实际应用为准，与 Xcode 在 Launchpad 或 Finder 中并排检查。透明边缘、阴影和图案形状会影响视觉观感，测量比例一致后仍需检查实际显示。

# 打包命令
## mac打包arm命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon-dark.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch arm64 \
  -y json_formatter_app.py
```

## mac打包intel命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon-dark.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch x86_64 \
  -y json_formatter_app.py
```

## mac打包通用版命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon-dark.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch universal2 \
  -y json_formatter_app.py
```

```
# 修改spec文件
app = BUNDLE(
    coll,
    name='JSON工具.app',
    icon='icon-dark.icns',
    bundle_identifier='com.lawliet.jsonformatter',
    info_plist={
        'CFBundleShortVersionString': '2.0.5',
        'CFBundleVersion': '2.0.5',
    },
)

# 打包，可以打出mac版本号
pyinstaller -y JSON工具.spec
```

## 使用虚拟环境
```bash
source venv/bin/activate
```


