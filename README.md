# 简介
这是一个json格式化app，采用pyside6开发

# 打包命令
## mac打包arm命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch arm64 \
  -y json_formatter_app.py
```

## mac打包intel命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch x86_64 \
  -y json_formatter_app.py
```

## mac打包通用版命令-pyside6
```bash
pyinstaller --windowed --name "JSON工具" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch universal2 \
  -y json_formatter_app.py
```

```
# 修改spec文件
app = BUNDLE(
    coll,
    name='JSON工具.app',
    icon='icon.icns',
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


