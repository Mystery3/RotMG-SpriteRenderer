rem requires pyinstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --icon ./bin/favicon.ico ^
    Renderer.py 

rem pyinstaller cleanup
move "%cd%\dist\Renderer.exe" "%cd%"
rd "%cd%\dist"
rd /s /q "%cd%\build"
rd /s /q "%cd%\bin\modules"
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