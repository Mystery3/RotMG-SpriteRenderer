rem requires pyinstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --exclude-module IO ^
    --exclude-module Rendering ^
    --exclude-module UI ^
    --icon ./bin/favicon.ico ^
    Renderer.py 

rem pyinstaller cleanup
move "%cd%\dist\Renderer.exe" "%cd%"
rd "%cd%\dist"
rd /s /q "%cd%\build"
del "%cd%\Renderer.py"
del "%cd%\Renderer.spec"

rem git cleanup
del "%cd%\.gitignore"
del "%cd%\LICENSE"
del "%cd%\README.md"

rem default folders
md "%cd%\Renders"
md "%cd%\Textiles"
md "%cd%\Sheets"

rem self cleanup
del "%cd%\build.bat"