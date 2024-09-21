rem Clearing dist...
rd /s /q "%cd%\dist"
md "%cd%\dist"

rem Building exe with nuitka...
python -m nuitka ^
    --onefile ^
    --output-dir="./dist" ^
    --windows-console-mode="disable" ^
    --windows-icon-from-ico="./bin/favicon.ico" ^
    --enable-plugin="tk-inter" ^
    --quiet ^
    --deployment ^
    Renderer.py

rem Cleaning build dirs...
rd /q /s "%cd%\dist\Renderer.build"
rd /q /s "%cd%\dist\Renderer.dist"
rd /q /s "%cd%\dist\Renderer.onefile-build"

rem Copying files...
md "%cd%\dist\bin"
copy "%cd%\bin\config.json" "%cd%\dist\bin\config.json"
copy "%cd%\bin\error.log" "%cd%\dist\bin\error.log"
copy "%cd%\bin\favicon.ico" "%cd%\dist\bin\favicon.ico"
copy "%cd%\bin\images.pickle" "%cd%\dist\bin\images.pickle"
copy "%cd%\README.md" "%cd%\dist\README.md"

rem Adding default dirs...
md "%cd%\dist\Renders"
type nul > "%cd%\dist\Renders\.del"
md "%cd%\dist\Sheets"
type nul > "%cd%\dist\Sheets\.del"
md "%cd%\dist\Textiles"
type nul > "%cd%\dist\Textiles\.del"

rem Done