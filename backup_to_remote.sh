#!/bin/bash

# ==============================================================================
# Скрипт автоматического резервного копирования на удаленный сервер через SSH
# ==============================================================================

# Настройки путей (обновите при необходимости)
PROJECT_DIR="/home/copp-admin/copp-newsite"
BACKUP_DIR="/tmp/copp_backups"
DB_FILE="coppdb.sqlite"
UPLOADS_DIR="app/static/uploads"

# Настройки удаленного сервера (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ ЭТИ ДАННЫЕ)
REMOTE_USER="backupuser"
REMOTE_HOST="192.168.1.100"
REMOTE_PORT="22"
REMOTE_DIR="/var/backups/copp-site"

# Формирование имени файла
DATE=$(date +"%d-%m-%Y_%H-%M")
ARCHIVE_NAME="copp-site-$DATE.zip"
ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"

mkdir -p "$BACKUP_DIR"

# Переход в директорию проекта, чтобы пути внутри архива были правильными
cd "$PROJECT_DIR" || exit 1

echo "[$(date +"%Y-%m-%d %H:%M:%S")] Начинаем создание архива $ARCHIVE_NAME..."

# Создаем архив (добавляем БД в корень архива)
zip -q "$ARCHIVE_PATH" "$DB_FILE"

# Переходим в папку со статикой, чтобы папка uploads тоже лежала в корне архива
cd "$PROJECT_DIR/app/static" || exit 1
zip -q -r "$ARCHIVE_PATH" "uploads"

if [ $? -eq 0 ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Архив успешно создан. Отправка на удаленный сервер..."
    
    # Отправка файла через SCP. Для работы без пароля нужен SSH ключ.
    scp -P "$REMOTE_PORT" "$ARCHIVE_PATH" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"
    
    if [ $? -eq 0 ]; then
        echo "[$(date +"%Y-%m-%d %H:%M:%S")] Бекап успешно отправлен на $REMOTE_HOST!"
        # Удаляем локальный архив, чтобы не забивать место
        rm "$ARCHIVE_PATH"
    else
        echo "[$(date +"%Y-%m-%d %H:%M:%S")] ОШИБКА: Не удалось отправить файл на удаленный сервер."
        exit 1
    fi
else
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] ОШИБКА: Не удалось создать локальный архив."
    exit 1
fi
