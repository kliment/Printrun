echo off
rem ************************************************************** 
rem *** This batch file will clean up all __pycache__ folders, ***
rem *** *.pyd files and left over gcoder_line files from       ***
rem *** previous builds. For Windows only.                     ***
rem ***                                                        ***
rem *** This is helpful when you switch between Python         ***
rem *** versions or you have problems with incompatible        ***
rem *** library files.                                         ***
rem ***                                                        ***
rem *** Don't forget to delete the virtual environment v3      ***
rem *** if you switch between Python versions.                 ***
rem ***                                                        ***
rem *** Author: DivingDuck, 2024-11-16, Status: working        ***
rem ************************************************************** 

echo *** Clean pip cache ***
if exist v3 (
   call v3\Scripts\activate
   echo *** Activate virtual environment v3 ***
   )

pip cache purge

echo *** Clean all __pycache__ folders ***

for /d /r . %%d in (__pycache__) do @if exist "%%d" echo "%%d" && rd /s/q "%%d"

if exist v3 (
   call v3\Scripts\deactivate
   echo *** Deactivate virtual environment v3 ***
   )

echo *** clean gcoder_line files ***   
if exist printrun\gcoder_line.c del printrun\gcoder_line.c && echo *** delete printrun\gcoder_line.c deleted ***
if exist printrun\gcoder_line.cp???-win_amd??.pyd del printrun\gcoder_line.cp???-win_amd??.pyd && echo *** printrun\gcoder_line.cp???-win_amd??.pyd deleted ***
if exist printrun\gcoder_line.cp???-win??.pyd del printrun\gcoder_line.cp???-win??.pyd && echo *** printrun\gcoder_line.cp???-win??.pyd deleted ***
if exist printrun\gcoder_line.cp??-win_amd??.pyd del printrun\gcoder_line.cp??-win_amd??.pyd && echo *** printrun\gcoder_line.cp??-win_amd??.pyd deleted ***
if exist printrun\gcoder_line.cp??-win??.pyd del printrun\gcoder_line.cp??-win??.pyd && echo *** printrun\gcoder_line.cp??-win??.pyd deleted ***
pause
