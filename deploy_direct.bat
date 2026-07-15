@echo off

echo =========================================
echo  Direct Upload to Server (Bypass Git)
echo =========================================
echo.

echo [*] Packing files (excluding __pycache__ and venv)...
tar --exclude="__pycache__" --exclude=".git" --exclude="venv" -czf upload.tar.gz app run.py wsgi.py config.py requirements.txt deploy.sh update.sh .env coppdb.sqlite

echo [*] Preparing server...
ssh admincopp@178.20.47.20 "mkdir -p ~/site_upload"

echo [*] Uploading files...
scp upload.tar.gz admincopp@178.20.47.20:~/site_upload/

echo.
echo [*] Installing files and restarting service...
ssh -t admincopp@178.20.47.20 "sudo mkdir -p /var/www/copp-newsite && sudo tar -xzf ~/site_upload/upload.tar.gz -C /var/www/copp-newsite/ && sudo chown -R www-data:www-data /var/www/copp-newsite && sudo systemctl restart copp"

echo [*] Cleaning up...
del upload.tar.gz
ssh admincopp@178.20.47.20 "rm ~/site_upload/upload.tar.gz"

echo.
echo =========================================
echo  Done! The site is updated.
echo =========================================
pause
