@echo off
color 0B
cd ..

echo =========================================
echo  Fast Deploy to Server (via GitHub)
echo =========================================
echo.

rem 1. Stage files
echo [*] Staging files...
git add .

rem 2. Commit message
set /p msg="Enter commit message (or press Enter for 'auto update'): "
if "%msg%"=="" set msg="auto update"

rem 3. Commit
echo.
echo [*] Committing changes...
git commit -m "%msg%"

rem 4. Push to remote main
echo.
echo [*] Pushing to GitHub (origin main)...
git push origin HEAD:main

rem 5. Update server
echo.
echo [*] Triggering update on server...
ssh -t admincopp@178.20.47.20 "sudo bash /var/www/copp-newsite/deploy_scripts/update.sh"

echo.
echo =========================================
echo  Done! Code pushed and server updated.
echo =========================================
echo.
pause
