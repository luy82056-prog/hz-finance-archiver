@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "LOG=%~dp0build_installer.log"
break > "%LOG%"

call :log ========================================
call :log HZ Finance Archiver Windows Setup Builder
call :log ========================================
call :log Current folder: %CD%
call :log.

echo %CD% | findstr /I "\\Temp\\ \\Temporary Internet Files\\ \\7z" >nul
if not errorlevel 1 (
  call :log [WARNING] You may be running this from inside a zip preview or temporary folder.
  call :log Please extract the whole zip to Desktop first, then double-click this file again.
  call :finish 1
)

if not exist "finance_ocr_app\\app.py" (
  call :log [ERROR] Missing finance_ocr_app\\app.py.
  call :log Please extract the whole folder before running this file.
  call :finish 1
)

where py >> "%LOG%" 2>&1
if errorlevel 1 (
  call :log [ERROR] Python Launcher was not found.
  call :log Install Python 3.10+ and check "Add python.exe to PATH".
  call :log https://www.python.org/downloads/windows/
  call :finish 1
)

if not exist ".venv\\Scripts\\python.exe" (
  call :log Creating local Python environment...
  py -3 -m venv .venv >> "%LOG%" 2>&1
  if errorlevel 1 call :finish 1
)

call :log Installing Python dependencies...
".venv\\Scripts\\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 call :finish 1
".venv\\Scripts\\python.exe" -m pip install -r requirements.txt pyinstaller >> "%LOG%" 2>&1
if errorlevel 1 call :finish 1

call :log Building Windows application...
".venv\\Scripts\\pyinstaller.exe" --clean --noconfirm packaging\\finance_ocr_archiver_windows.spec >> "%LOG%" 2>&1
if errorlevel 1 call :finish 1

set "ISCC="
where ISCC.exe >> "%LOG%" 2>&1
if not errorlevel 1 (
  for /f "delims=" %%I in ('where ISCC.exe') do (
    if not defined ISCC set "ISCC=%%I"
  )
)

if not defined ISCC (
  if exist "%ProgramFiles(x86)%\\Inno Setup 6\\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\\Inno Setup 6\\ISCC.exe"
)

if not defined ISCC (
  call :log [ERROR] Inno Setup 6 was not found.
  call :log Install it, then run this file again:
  call :log https://jrsoftware.org/isdl.php
  call :log.
  call :log App EXE was generated here:
  call :log dist\\HZ财务归档器-Windows\\HZ财务归档器.exe
  call :finish 1
)

call :log Building Setup.exe with Inno Setup...
"%ISCC%" packaging\\hz_finance_archiver.iss >> "%LOG%" 2>&1
if errorlevel 1 call :finish 1

call :log.
call :log SUCCESS.
call :log Final installer:
call :log installer_output\\HZ财务归档器-Windows安装包.exe
call :finish 0

:log
echo %*
echo %*>> "%LOG%"
exit /b 0

:finish
set "CODE=%~1"
call :log.
if "%CODE%"=="0" (
  call :log Done. You can send the generated installer EXE to other Windows users.
) else (
  call :log Failed. Full log is saved at:
  call :log %LOG%
)
call :log.
echo Press any key to close this window...
pause >nul
exit /b %CODE%

