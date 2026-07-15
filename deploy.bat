@echo off
color 0B

echo =========================================
echo  Fast Deploy to Server (via GitHub)
echo =========================================
echo.

echo [*] Uploading update script to server...
scp update.sh admincopp@178.20.47.20:/home/admincopp/update.sh

echo [*] Triggering update on server...
ssh -t admincopp@178.20.47.20 "sudo mv /home/admincopp/update.sh /var/www/copp-newsite/update.sh && sudo bash /var/www/copp-newsite/update.sh"

echo.
echo =========================================
echo  Done! Code pushed and server updated.
echo =========================================
echo.
pause
