@echo off
rem Gets the newest Miasma: Rebirth build from GitHub. Close Godot first.
rem Matches GitHub exactly: Godot's own rewrites of .import/.uid files are thrown away, so a pull never fails on them.
cd /d "%~dp0"
echo Getting the newest build...
git fetch origin
if errorlevel 1 goto fail
git reset --hard origin/master
if errorlevel 1 goto fail
echo.
git log -1 --format="Now on: %%h  %%s"
echo Open the project in Godot 4.7.2; it re-imports anything new the first time.
pause
exit /b 0
:fail
echo.
echo Something went wrong - copy the message above to Claude.
pause
exit /b 1
