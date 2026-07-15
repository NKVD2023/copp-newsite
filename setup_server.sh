#!/bin/bash
# ==============================================================================
# setup_server.sh — Первичная настройка сервера (БЕЗ GIT)
# Код берется из папки /var/www/copp-newsite, куда он был загружен через bat-файл
# ==============================================================================

set -euo pipefail

APP_DIR="/var/www/copp-newsite"
APP_USER="www-data"
DOMAIN="copp82.ru 178.20.47.20"

echo "=== 1. Проверка директории ==="
if [ ! -d "$APP_DIR" ]; then
    echo "Ошибка: Директория $APP_DIR не найдена."
    echo "Сначала загрузите файлы через deploy_direct.bat с вашего ПК!"
    exit 1
fi

echo "=== 2. Настройка виртуального окружения ==="
cd "$APP_DIR"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip nginx

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Устанавливаем зависимости
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
else
    echo "Предупреждение: requirements.txt не найден!"
fi
pip install gunicorn python-dotenv Pillow pandas openpyxl --quiet

echo "=== 3. Настройка логов ==="
sudo touch /var/log/copp_error.log /var/log/copp_access.log
sudo chown www-data:www-data /var/log/copp_error.log /var/log/copp_access.log

echo "=== 4. Настройка прав ==="
sudo chown -R $APP_USER:$APP_USER "$APP_DIR"
sudo chmod -R 755 "$APP_DIR"

echo "=== 5. Настройка Systemd (Gunicorn) ==="
cat <<EOF | sudo tee /etc/systemd/system/copp.service
[Unit]
Description=Gunicorn instance — COPP site
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind unix:$APP_DIR/copp.sock -m 007 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable copp
sudo systemctl restart copp

echo "=== 6. Настройка Nginx ==="
# Учитываем, что сертификаты уже лежат в /home/admincopp/srt/
cat <<EOF | sudo tee /etc/nginx/sites-available/copp
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /home/admincopp/srt/_.copp82.ru_certificate.txt;
    ssl_certificate_key /home/admincopp/srt/_.copp82.ru_private.txt;
    ssl_trusted_certificate /home/admincopp/srt/_.copp82.ru_rootCA.txt;

    access_log /var/log/copp_access.log;
    error_log /var/log/copp_error.log;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/copp.sock;
    }

    location /static/ {
        alias $APP_DIR/app/static/;
        expires 30d;
    }

    location /media/ {
        alias $APP_DIR/app/media/;
        expires 30d;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/copp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "========================================="
echo " Готово! Сервер развернут из локального кода."
echo "========================================="
