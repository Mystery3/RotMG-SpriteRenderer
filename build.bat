rem requires pyinstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --exclude-module IO ^
    --exclude-module Rendering ^
    --exclude-module UI ^
    --icon ./bin/favicon.ico ^
    Renderer.py 

move "%cd%\dist\Renderer.exe" "%cd%"
rd "%cd%\dist"
rd /s /q "%cd%\build"
del "%cd%\.gitignore"
del "%cd%\Renderer.py"
del "%cd%\Renderer.spec"

md "%cd%\Renders"
md "%cd%\Textiles"
md "%cd%\Sheets"

del "%cd%\build.bat"