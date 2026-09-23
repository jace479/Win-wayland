@echo off
setlocal
echo ========================================================
echo Setting up Visual Studio 2022 MSVC x64 Environment...
echo ========================================================
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to initialize vcvars64.bat
    exit /b %ERRORLEVEL%
)

cd /d "%~dp0build"
echo.
echo ========================================================
echo Configuring CMake...
echo ========================================================
cmake -G "Visual Studio 17 2022" -A x64 -DCMAKE_PREFIX_PATH="C:\Users\jace.zorn\Qt\6.8.2\msvc2022_64" ..
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed.
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo Building kwin_win (Release)...
echo ========================================================
cmake --build . --config Release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed.
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo [SUCCESS] kwin_win.exe compiled successfully!
echo ========================================================
exit /b 0
