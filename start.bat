@echo off
setlocal
title Misa's AI Paper Processing Project
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem This file is intentionally ASCII-only: cmd.exe parses .bat files with the
rem system code page, and non-ASCII text can split commands apart.

set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
  set "PY=py -3"
  where py >nul 2>&1
  if errorlevel 1 (
    echo.
    echo   [ERROR] Python 3.10+ was not found on PATH.
    echo   Install it from https://www.python.org/downloads/
    echo   and tick "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
  )
)

%PY% -c "import misa" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   [ERROR] Cannot import the "misa" package.
  echo   Run this file from the project folder:
  echo     D:\project\misa-ai-paper
  echo.
  pause
  exit /b 1
)

echo.
echo   Misa's AI Paper Processing Project   v0.1
echo   Made by Misa
echo   --------------------------------------------
echo   Starting the local web UI...
echo.

%PY% -m misa serve --open

echo.
echo   Server stopped.
echo   If the browser did not open, visit: http://127.0.0.1:8765
echo.
pause
exit /b 0
