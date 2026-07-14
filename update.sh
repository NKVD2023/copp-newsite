#!/bin/bash

# ==============================================================================
# update.sh — Быстрое обновление сайта COPP (git pull + restart)
# Использование: sudo bash update.sh [--hard] [--no-restart]
#
#   --hard        Сбросить локальные изменения и полностью стянуть с GitHub
#   --no-restart  Обновить файлы без перезапуска Gunicorn
# ==============================================================================

APP_DIR="/var/www/copp-newsite"
APP_USER="www-data"
SERVICE_NAME="copp"

# ─── ЦВЕТА ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
section() { echo -e "\n${CYAN}▶ $*${NC}"; }

# ─── АРГУМЕНТЫ ────────────────────────────────────────────────────────────────
NO_RESTART=false
HARD_RESET=false
for arg in "$@"; do
    case $arg in
        --no-restart) NO_RESTART=true ;;
        --hard)       HARD_RESET=true ;;
    esac
done

# ─── ПРОВЕРКИ ─────────────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Запустите с правами root: sudo bash update.sh"
    exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
    error "Директория проекта не найдена: $APP_DIR"
    error "Сначала выполните первичный деплой: sudo bash deploy.sh"
    exit 1
fi

START_TIME=$(date +%s)
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Обновление COPP — $(date '+%d.%m.%Y %H:%M')${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"

# ─── 1. GIT PULL ──────────────────────────────────────────────────────────────
section "1/4  Получение обновлений с GitHub"
cd "$APP_DIR"

# Фикс ошибки "fatal: detected dubious ownership" (если запускаем через sudo)
git config --global --add safe.directory "$APP_DIR"

OLD_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

if [ "$HARD_RESET" = true ]; then
    warn "Режим --hard: сбрасываю все локальные изменения..."
    git fetch origin
    git reset --hard origin/main
    git clean -fd
else
    # Сервер всегда работает на ветке main (продакшн)
    git fetch origin
    git checkout main 2>/dev/null || true
    git pull origin main
fi

NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    warn "Код уже актуален (коммит: $NEW_COMMIT). Новых изменений нет."
else
    info "Код обновлён: $OLD_COMMIT → $NEW_COMMIT"
    echo ""
    echo "  Изменённые файлы:"
    git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | sed 's/^/    ► /' || true
fi

# Страховка: создаём wsgi.py если он вдруг пропал
if [ ! -f "$APP_DIR/wsgi.py" ]; then
    warn "wsgi.py не найден — создаю..."
    cat > "$APP_DIR/wsgi.py" << 'WSGIEOF'
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
WSGIEOF
    info "wsgi.py создан."
fi

# ─── 2. ЗАВИСИМОСТИ ───────────────────────────────────────────────────────────
section "2/4  Зависимости Python"

# Устанавливаем только если requirements.txt изменился
if [ "$OLD_COMMIT" != "$NEW_COMMIT" ] && \
   git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | grep -q "requirements.txt"; then
    info "requirements.txt изменился — устанавливаю..."
    "$APP_DIR/venv/bin/pip" install --upgrade pip --quiet
    "$APP_DIR/venv/bin/pip" install -r requirements.txt --quiet
    "$APP_DIR/venv/bin/pip" install gunicorn python-dotenv --quiet
    info "Зависимости обновлены."
else
    info "requirements.txt не изменился — пропускаю установку."
fi

# ─── 3. ПРАВА ДОСТУПА ─────────────────────────────────────────────────────────
section "3/4  Права доступа"

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod 664 "$APP_DIR/coppdb.sqlite" 2>/dev/null || true
chmod -R 775 "$APP_DIR/app/static/uploads" 2>/dev/null || true

# Убеждаемся что файлы логов существуют и принадлежат www-data
touch /var/log/${SERVICE_NAME}_error.log /var/log/${SERVICE_NAME}_access.log
chown "$APP_USER":"$APP_USER" /var/log/${SERVICE_NAME}_error.log /var/log/${SERVICE_NAME}_access.log

info "Права расставлены."

# ─── 4. ПЕРЕЗАПУСК ────────────────────────────────────────────────────────────
section "4/4  Перезапуск сервисов"

if [ "$NO_RESTART" = false ]; then
    systemctl restart "$SERVICE_NAME"
    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "Gunicorn перезапущен успешно."
    else
        error "Gunicorn НЕ запустился! Логи:"
        journalctl -u "$SERVICE_NAME" --no-pager -n 30
        exit 1
    fi

    # Перезагружаем Nginx только если изменились шаблоны или статика
    if [ "$OLD_COMMIT" != "$NEW_COMMIT" ] && \
       git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | grep -qE "^app/static/|^app/templates/"; then
        if nginx -t 2>/dev/null; then
            systemctl reload nginx
            info "Nginx перезагружен (изменились шаблоны/статика)."
        fi
    fi
else
    warn "Перезапуск пропущен (--no-restart)."
fi

# ─── ИТОГ ─────────────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Готово! Время: ${ELAPSED}с  |  Коммит: $NEW_COMMIT${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
ACTIVE=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "unknown")
echo "  Статус сервиса: $ACTIVE"
echo ""
echo "  Полезные команды:"
echo "    sudo journalctl -u $SERVICE_NAME -f            # живые логи"
echo "    sudo tail -f /var/log/${SERVICE_NAME}_error.log   # ошибки Flask"
echo ""
