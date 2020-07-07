rem AGe ** this batch is outdated, use pyinstall instead, need a bit more love somewhen later **
rem AGe, not needed for now: d:\python27\python.exe setup_win.py py2exe -v
rem AGe, not needed for now: py -3.7 setup_win.py py2exe -v
xcopy images dist\images\ /Y /E
xcopy locale dist\locale\ /Y /E
rem AGe,, not needed for now: xcopy Slic3r dist\Slic3r\ /Y /E
rem AGe, not needed for now: copy MSVCP90.DLL dist\ 
pause
