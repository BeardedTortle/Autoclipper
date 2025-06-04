@echo off
set "video=%~1"
set "script_dir=%~dp0"
cd /d "%script_dir%"
"C:\Users\theke\AppData\Local\Programs\Python\Python311\python.exe" process_tarkov_raid.py "%video%"
pause
