# 简介
这是一个json格式化app，采用pyside6开发

# 打包命令
## mac打包命令
`pyinstaller --windowed --name "JSON格式化" --strip --clean --icon=icon.icns --osx-bundle-identifier "com.lawliet.jsonformatter"  -y JsonFormatterApp.py`

## windows打包命令
`pyinstaller --windowed --name "JSON格式化" --strip --clean --icon=icon.ico -y JsonFormatterApp.py`

## linux打包命令
`pyinstaller --windowed --name "JSON格式化" --strip --clean --icon=icon.png -y JsonFormatterApp.py`


