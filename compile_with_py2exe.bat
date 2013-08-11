@ECHO OFF
REM see How-to in setup_py2exe.py
REM run from within the Printrun directory

setlocal EnableDelayedExpansion

for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "DEL=%%a"
)

where python

IF %ERRORLEVEL% NEQ 0 (
  Echo Python not in PATH. Trying to revert to C:\Python27\python.exe.
  If EXIST C:\Python22\python.exe (
    Echo Starting build with default path. This may take a moment...
    C:\Python27\python.exe setup_py2exe.py py2exe > compile_output.txt
    Echo Done. Check %CD%\compile_output.txt for build errors and missing packages.
  ) ELSE (
    Echo Python not found. Please enter the full path to python.exe:
    SET /p PythonPath="Python Path: "
    Echo Searching !PythonPath!...
    IF EXIST "!PythonPath!" (
      Echo.
      Echo Attempting to start build. This method is not guarnteed to work and may take a while. Check for output errors.
      Echo.
      Pause
      Echo.
      !PythonPath! setup_py2exe.py py2exe > compile_output.txt
      Echo.
      call :ColorText 04 "If there were no errors above" & Echo ^ check %CD%\compile_output.txt for build errors and missing packages.
    ) ELSE (
      Echo The Path "!PythonPath!" does not exist. Plase attempt a manual build.
    )
  )
) ELSE (
  Echo Starting build. This may take a moment...
  python setup_py2exe.py py2exe > compile_output.txt
  Echo Done. Check %CD%\compile_output.txt for build errors and missing packages.
)

pause

goto :eof

:ColorText
echo off
<nul set /p ".=%DEL%" > "%~2"
findstr /v /a:%1 /R "^$" "%~2" nul
del "%~2" > nul 2>&1
goto :eof

endlocal
