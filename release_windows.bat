echo off
cls

rem *************************************************************************
rem ****************  ---> New batch file starts here <---  *****************
rem **                                                                     **
rem **  This batch will compile automated via command line an executable   **
rem **  Pronterface file for Windows 10.                                   **
rem **                                                                     **
rem **  Steps that are automated:                                          **
rem **                                                                     **
rem **  1. clean up previous compilations (directory .\dist)               **
rem **  2. check for virtual environment called v3 and generate it, if     **
rem **     not available (start from scratch)                              **
rem **  3. install all needed additional modules via pip                   **
rem **  4. check for outdated modules that need to be updated and          **
rem **     update them                                                     **
rem **  5. Check if virtual environment needs an update and do it          **
rem **  6. check for existing variants of gcoder_line.cp??-win_amd??.pyd   **
rem **     and delete them (to prevent errors and incompatibilities)       **
rem **  7. compile Pronterface.exe                                         **
rem **  8. copy localization files to .\dist                               **
rem **  9. go to directory .\dist, list files and ends the activity        **
rem **                                                                     **
rem **  Steps, you need to do manually before running this batch:          **
rem **                                                                     **
rem **  1. install python 3.7.9                                            **
rem **     https://www.python.org/downloads/release/python-378/            **
rem **  2. install C-compiler environment                                  **
rem **     https://wiki.python.org/moin/WindowsCompilers                   **
rem **  3. check for latest repository updates at:                         **
rem **     http://github.com/kliment/Printrun.git                          **
rem **                                                                     **
rem **  Author: DivingDuck, 2021-01-06, Status: working                    **
rem **                                                                     **
rem *************************************************************************
rem *************************************************************************

echo **************************************************
echo ****** Delete files and directory of .\dist ******
echo **************************************************
if exist dist (
   DEL /F/Q/S dist > NUL
   RMDIR /Q/S dist
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
   py -3.7 -m venv v3

   echo *********************************************
   echo ****** Activate virtual environment v3 ******
   echo *********************************************
   call v3\Scripts\activate

   pip install --upgrade pip
   pip install --upgrade setuptools

   pip install wheel
   
   echo **********************************
   echo ****** install requirements ******
   echo **********************************
   pip install -r requirements.txt
   pip install cython
   echo ***********************
   echo ****** additions ******
   echo ***********************
   pip install simplejson
   
   rem echo *******************************
   rem echo ****** pyinstaller 4 dev ******
   rem echo *******************************
   rem pyinstaller v3.6 don't work with Windows 10  pip install pyinstaller
   rem update 2020-12-13: there is a new version available v4.1. 
   rem Looks like we don't need this fix any longer
   REM pip uninstall pyinstaller
   REM pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
   pip install pyinstaller
   pip install pypiwin32
   pip install polygon3
   )

echo ********************************************
echo ****** upgrade virtual environment v3 ******
echo ********************************************
pip install --upgrade virtualenv

echo ****************************************************
echo ****** check for and update outdated modules  ******
echo ****************************************************
for /F "skip=2 delims= " %%i in ('pip list --outdated') do pip install --upgrade %%i

rem echo ****************************************************************************************
rem echo ****** --->> Hotfix AGe: solve numpy 1.19.4 problem for x64 windows runtime error ******
rem echo ****************************************************************************************
rem numpy v1.19.4 create an python RuntimeError: The current Numpy installation fails to pass a 
rem sanity check due to a bug in the windows runtime. See this issue for more information:
rem https://tinyurl.com/y3dm3h86
rem Temporary workaround is to install 1.19.3 instead.
rem --> ToDo: Need to be checked in 2021 January again
rem update 2021-01-06: There is a new version available
rem --> Solved with version 1.19.5
rem pip uninstall numpy
rem pip install numpy==1.19.3

echo ******************************************************************
echo ****** Compile G-Code parser gcoder_line.cp37-win_amd64.pyd ******
echo ******************************************************************
rem For safety reasons delete existing version first to prevent errors
if exist printrun\gcoder_line.cp??-win_amd??.pyd (
   del printrun\gcoder_line.cp??-win_amd??.pyd
   echo ********************************************************************************
   echo ****** found versions of printrun\gcoder_line.cp??-win_amd??.pyd, deleted ******
   echo ********************************************************************************
   )
python setup.py build_ext --inplace

echo ****************************************
echo ****** Collect all data for build ******
echo ****************************************
pyi-makespec -F --add-data images/*;images --add-data *.png;. --add-data *.ico;. -w -i pronterface.ico pronterface.py

echo *******************************
echo ****** Build Pronterface ******
echo *******************************
pyinstaller --clean pronterface.spec -y

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