echo off
cls
rem AGe ** this batch is outdated, use pyinstall instead, need a bit more love somewhen later **
rem AGe ** here starts the old batch **
rem AGe, not needed for now: d:\python27\python.exe setup_win.py py2exe -v
rem AGe, not needed for now: py -3.7 setup_win.py py2exe -v
rem AGe obsolete: xcopy images dist\images\ /Y /E
rem AGe xcopy locale dist\locale\ /Y /E
rem AGe, not needed for now: xcopy Slic3r dist\Slic3r\ /Y /E
rem AGe, not needed for now: copy MSVCP90.DLL dist\ 
rem AGe: pause

rem AGe **** Check's , ToDo's and what ever else... ****
rem AGe
rem AGe             **** ---> !! Requirements bevore starting this batch: !! <--- ****
rem AGe, manually?: **           install python 3.7.8                               **
rem AGe, manually?: **           install C-compiler environment                     **
rem AGe             **           https://wiki.python.org/moin/WindowsCompilers      **
rem AGe
rem AGe ? install git
rem AGe ? git clone http://github.com/kliment/Printrun.git
rem AGe ? git pull
rem AGe ? check if Python 3.7.x is installed and up to date
rem AGe ? check if C-Comiler is installed and up to date
rem AGe ?? maybe add a tool like curl for downloading and processing 
rem AGe   installations of not pip installations (python 3.7.x,
rem AGe   c-compiler and git) --> not jet but maybe later as fully 
rem AGe   automated process ...
rem AGe ? check for outdated python modules and update them automated
rem AGe ? maybe a option for deleting an existing virtual environment 
rem AGe   (start from real scratch), compilations,__pycache__ etc. 
rem AGe   and delete them in general, or maybe delete everything 
rem AGe   except original git repository files
rem AGe ? generate new pot catalog file automated and with cleanup
rem AGE   --> not jet but maybe later


rem *************************************************************************
rem ****************  ---> New batch file starts here <---  *****************
rem **                                                                     **
rem **  This batch will compile automated via commandline an executable    **
rem **  Pronterface file for Windows 10.                                   **
rem **                                                                     **
rem **  Steps that are automated:                                          **
rem **                                                                     **
rem **  1. clean up previous compilations (directory dist)                 **
rem **  2. check for virtual environment called v3 and generate it, if     **
rem **     not availabe (start from scratch)                               **
rem **  3. install all needed additional moduls via pip                    **
rem **  4. check for outdated moduls that need to be updated and           **
rem **     wait for keystroke                                              **
rem **  5. Check if virtual environment need an update and do it           ** 
rem **  6. check for existing variants of gcoder_line.cp??-win_amd??.pyd   **
rem **     and delete them (to prevent errors and incompatibilities)       **
rem **  7. compile Pronterface.exe                                         **
rem **  8. copy localisation files to dist                                 **
rem **  9. go to directory \dist, list files and ends the activity         **
rem **                                                                     **
rem **  Steps, you need to do manually bevore running this batch:          **
rem **                                                                     **
rem **  1. install python 3.7.8                                            **
rem **     https://www.python.org/downloads/release/python-378/            **
rem **  2. install C-compiler environment                                  **
rem **     https://wiki.python.org/moin/WindowsCompilers                   **
rem **  3. check for latest repository updates at:                         **
rem **     http://github.com/kliment/Printrun.git                          **
rem **                                                                     **
rem **  Author: DivingDuck, 2020-07-09, Status: working, but not finishd   **
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
   echo ****** No virtual environment named v3 avaliable                ******
   echo ****** Will create first a new virtual environment with name v3 ******
   echo **********************************************************************
   
   rem AGe need check of correct version!!!
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
   rem AGe  **** my additions
   pip install simplejson
   
   rem AGe move before requirements as needed after installation: pip install wheel
   echo *******************************
   echo ****** pyinstaller 4 dev ******
   echo *******************************
   rem AGe, pyinstaller v3.6 don't work with Windows 10  pip install pyinstaller
   pip uninstall pyinstaller
   pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip

   pip install pypiwin32
   pip install polygon3

   echo ************************************
   echo ****** list outdated modules  ******
   echo ************************************
   rem AGe it shouldn't happen, but just in case ....
   pip list --outdated
   pause
   rem AGe exit /b
   )

echo ********************************************
echo ****** upgrate virtual environment v3 ******
echo ********************************************
pip install --upgrade virtualenv

echo ************************************
echo ****** list outdated modules  ******
echo ************************************
pip list --outdated
rem AGe check for actual env needed?
pause
echo ******************************************************************
echo ****** Compile G-Code parser gcoder_line.cp37-win_amd64.pyd ******
echo ******************************************************************
rem AGe for safty reasons delete existing version first to prevent errors
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
echo ****** You will find Pronterface and localisations here: ******
echo ***************************************************************
cd dist
dir .
pause
echo on