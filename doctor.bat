@echo off
setlocal
title Misa's AI Paper - doctor
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo   Misa's AI Paper Processing Project - startup check
echo   Made by Misa
echo   ------------------------------------------------
echo.

echo [1/5] current folder
echo       %CD%
echo.

echo [2/5] python
where python >nul 2>&1
if errorlevel 1 (
  echo       python : NOT FOUND on PATH
  where py >nul 2>&1
  if errorlevel 1 (
    echo       py     : NOT FOUND either
  ) else (
    py -3 --version
  )
) else (
  python --version
)
echo.

echo [3/5] import test
python -c "import misa; print('        ok:', misa.__project__, 'v' + misa.__release__)" 2>&1
if errorlevel 1 echo        FAILED - the misa package is not importable from here
echo.

echo [4/5] port 8765
netstat -ano | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
  echo        free
) else (
  echo        IN USE - another process is holding port 8765
  netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"
)
echo.

echo [5/5] files
for %%f in (start.bat pyproject.toml README.md misa\__init__.py misa\web\static\index.html) do (
  if exist "%%f" (echo        ok   %%f) else (echo        MISSING  %%f)
)
echo.
echo   If steps 2-5 all look fine, run start.bat again.
echo.
pause
