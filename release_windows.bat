echo off
cls

rem ************************************************************************************
rem *********************  ---> New batch file starts here <---  ***********************
rem **                                                                                **
rem **  This batch will compile automated via command line an executable              **
rem **  Pronterface, Pronsole and Plater file for Windows 10.                         **
rem **                                                                                **
rem **  Steps that are automated:                                                     **
rem **                                                                                **
rem **   1. Clean up previous compilations (directory .\dist)                         **
rem **   2. Check for virtual environment called v3 and generate it, if               **
rem **      not available (start from scratch)                                        **
rem **   3. Install all needed additional modules via pip                             **
rem **   4. Check for outdated modules that need to be updated and                    **
rem **      update them                                                               **
rem **   5. Check if virtual environment needs an update and do it                    **
rem **   6. Check for existing variants of gcoder_line.cp??-win_amd??.pyd             **
rem **      and delete them (to prevent errors and incompatibilities)                 **
rem **   7. Compile Pronterface.exe                                                   **
rem **   8. Compile Pronsole.exe                                                      **
rem **   9. Copy localization files to .\dist                                         **
rem **  10. Go to directory .\dist, list files and ends the activity                  **
rem **                                                                                **
rem **  Steps, you need to do manually before running this batch:                     **
rem **                                                                                **
rem **  1. Install python 64-bit (3.10.x 64-bit is actually preferred                 **
rem **     and standard version for Windows 10)                                       **
rem **     https://www.python.org/downloads/release                                   **
rem **     In case you use an other Python version: Check line 77 to 82 and adjust    **
rem **     the parameter accordingly to build your virtual environment.               **
rem **  2. Install C-compiler environment                                             **
rem **     https://wiki.python.org/moin/WindowsCompilers                              **
rem **     (Microsoft Visual Studio 2022 Community version is proofed to work fine)   **
rem **  3. Check for latest repository updates at:                                    **
rem **     http://github.com/kliment/Printrun.git                                     **
rem **  4. It is recommended to delete an existing virtual environment (v3) when you  **
rem **     switch between -x32/-x64 or different Python versions. There is a second   **
rem **     batch script called CleanCacheFiles.bat available for cleaning             **
rem **     former compiling- and __pycache__ artifacts . Run it as often you need.    **
rem **  																			  **
rem **  Remark: Plater stand alone application is experimental only. GUI code need an **
rem **          update for closing plater window and running processes. For now you   **
rem **          need to terminate the process manually via Task manager.			  **
rem **                                                                                **
rem **  Author: DivingDuck, 2024-11-16, Status: working                               **
rem **                                                                                **
rem ************************************************************************************
rem ************************************************************************************

echo **************************************************
echo ****** Delete files and directory of .\dist ******
echo **************************************************
if exist dist (
   DEL /F/Q/S dist > NUL
   RMDIR /Q/S dist
   )
echo ***************************************************
echo ****** Delete files and directory of .\build ******
echo ***************************************************
if exist build (
   DEL /F/Q/S build > NUL
   RMDIR /Q/S build
   )   
echo *********************************************
echo ****** Activate virtual environment v3 ******
echo *********************************************
if exist v3 (
   call v3\Scripts\activate
   ) else (

   echo **********************************************************************
   echo ****** No virtual environment named v3 available                ******
   echo ****** Will create first a new virtual environment with name v3 ******
   echo **********************************************************************
   rem Select your Python version below. Remove 'rem' before 'rem py -3.x ...'
   rem for your Python version of choice and add 'rem' for all other versions.
   rem Attention: 
   rem Minimum version for wxPython is >= 4.2.1. With this version
   rem Python x64 (version 3.8 up to 3.12) and 
   rem Python x86 (version 3.9 up to 3.12) is supported.

   rem py -3.8 -m venv v3
   rem py -3.9-32 -m venv v3
   rem py -3.9 -m venv v3
   rem py -3.10-32 -m venv v3
   rem py -3.10 -m venv v3
   rem py -3.11-32 -m venv v3
   rem py -3.11 -m venv v3
   rem py -3.12-32 -m venv v3
   rem py -3.12 -m venv v3
   
   rem Attention: Python 3.13 support is experimental, no 3D view available for now.
   rem py -3.13-32 -m venv v3
   py -3.13 -m venv v3
   
   echo *********************************************
   echo ****** Activate virtual environment v3 ******
   echo *********************************************
   call v3\Scripts\activate

   py -m pip install --upgrade pip
   pip install --upgrade setuptools

   pip install wheel
   
   echo **********************************
   echo ****** install requirements ******
   echo **********************************
   pip install cython
   pip install -r requirements.txt
   
   echo ***********************
   echo ****** additions ******
   echo ***********************
   pip install simplejson
   pip install pyinstaller
   pip install pypiwin32
   pip install polygon3
   pip install pytest
   )

echo ********************************************
echo ****** upgrade virtual environment v3 ******
echo ********************************************
pip install --upgrade virtualenv
 
echo ********************************************************
echo ****** check for outdated modules and update them ******
echo ********************************************************
for /F "skip=2 delims= " %%i in ('pip list --outdated') do py -m pip install --upgrade %%i


echo *************************************************************************
echo ****** pyglet workaround, needs to be below 2.0 (isn't compatible) ******
echo *************************************************************************
rem # 2022-11-01
pip uninstall pyglet -y
pip install pyglet==1.5.29

rem echo **************************************************************************
rem echo ****** pillow workaround, needs to be below 10.0 (isn't compatible) ******
rem echo **************************************************************************
rem # 2023-12-15
rem building wxPython 4.2.1 for x86 needs pillow <10.0
rem *** pip uninstall pillow -y
rem *** pip install pillow==9.5.0

echo ******************************************************************
echo ****** Compile G-Code parser gcoder_line.cp??-win_amd??.pyd ******
echo ******************************************************************
rem Delete existing versions first to prevent errors and incompatibilities
if exist printrun\gcoder_line.cp??-win_amd??.pyd (
   del printrun\gcoder_line.cp??-win_amd??.pyd
   echo ********************************************************************************
   echo ****** found versions of printrun\gcoder_line.cp??-win_amd??.pyd, deleted ******
   echo ********************************************************************************
   )
rem In addition check for 3 digit Python versions
if exist printrun\gcoder_line.cp???-win_amd??.pyd (
   del printrun\gcoder_line.cp???-win_amd??.pyd
   echo ***********************************************************************++*********
   echo ****** found versions of printrun\gcoder_line.cp???-win_amd??.pyd, deleted ******
   echo **********************************************************************************
   )

python setup.py build_ext --inplace

echo ****************************************
echo ****** Collect all data for build ******
echo ****************************************

pyi-makespec -F --name "Pronterface" --add-data images/*;images --add-data *.png;. --add-data *.ico;. -w -i pronterface.ico pronterface.py
pyi-makespec -F --name "Pronsole" --add-data images/*;images --add-data *.png;. --add-data *.ico;. -c -i pronsole.ico pronsole.py
rem Plater stand alone application is experimental only (See remark).
pyi-makespec -F --name "Plater" --add-data images/*;images --add-data *.png;. --add-data *.ico;. -w -i plater.ico plater.py

echo ***************************************************************
echo ****** Build Pronterface, Pronsole and Plater executables *****
echo ***************************************************************
echo
echo ** Build Pronterface executable **
pyinstaller --clean Pronterface.spec -y
echo 
echo ** Build Pronsole executable **
pyinstaller --clean Pronsole.spec -y
echo 
echo ** Build Plater executable **
rem Plater stand alone application is experimental only (See remark).
pyinstaller --clean Plater.spec -y


echo ********************************
echo ****** Add language files ******
echo ********************************
xcopy locale dist\locale\ /Y /E

echo ***************************************************************
echo ******                Batch finalizes                    ******
echo ******                                                   ******
echo ******    Happy printing with Pronterface for Windows!   ******
echo ******                                                   ******
echo ****** You will find Pronterface and localizations here: ******
echo ***************************************************************
cd dist
dir .
pause
echo on