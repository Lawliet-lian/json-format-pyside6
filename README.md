# 简介
这是一个json格式化app，采用pyside6开发

# 打包命令
## mac打包arm命令-pyside6
```bash
pyinstaller --windowed --name "JSON格式化" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch arm64 \
  -y JsonFormatterApp.py
```

## mac打包intel命令-pyside6
```bash
pyinstaller --windowed --name "JSON格式化" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch x86_64 \
  -y JsonFormatterApp.py
```

## mac打包通用版命令-pyside6
```bash
pyinstaller --windowed --name "JSON格式化" --strip --clean \
  --icon=icon.icns \
  --osx-bundle-identifier "com.lawliet.jsonformatter" \
  --target-arch universal2 \
  -y JsonFormatterApp.py
```

## 使用虚拟环境
```bash
source venv/bin/activate
```


