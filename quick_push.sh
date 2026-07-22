#!/bin/bash

# Если при запуске не указать комментарий, скрипт сгенерирует его автоматически с текущей датой
COMMIT_MSG="${1:-Auto-update: $(date '+%Y-%m-%d %H:%M:%S')}"

echo "➤ Подготовка файлов (git add .)"
git add .

echo "➤ Создание коммита (git commit)"
git commit -m "$COMMIT_MSG"

echo "➤ Отправка изменений (git push)"
git push origin main

echo "➤ Обновление на сервере (через SSH)"
ssh -t site "cd /var/www/copp-newsite && sudo ./update.sh"

echo "✅ Успешно выполнено!"
