d:\python27\python.exe setup_win.py py2exe -v
xcopy images dist\images\ /Y /E
xcopy locale dist\locale\ /Y /E
xcopy Slic3r dist\Slic3r\ /Y /E
copy MSVCP90.DLL dist\
pause
