#!/bin/bash

# ==============================================================================
# Скрипт быстрого обновления проекта COPP
# Использование: sudo bash update.sh
# Опции:  --no-restart   — обновить без перезапуска (редко нужно)
#         --hard         — полный сброс: git reset --hard (если конфликты)
# ==============================================================================

APP_DIR="/var/www/copp-newsite"
SERVICE_NAME="copp"

# ─── ЦВЕТА ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }
section() { echo -e "\n${CYAN}▶ $1${NC}"; }

# ─── АРГУМЕНТЫ ────────────────────────────────────────────────────────────────
NO_RESTART=false
HARD_RESET=false
for arg in "$@"; do
    case $arg in
        --no-restart) NO_RESTART=true ;;
        --hard)       HARD_RESET=true ;;
    esac
done

# ─── ПРОВЕРКА ROOT ────────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Запустите с правами root: sudo bash update.sh"
    exit 1
fi

if [ ! -d "$APP_DIR" ]; then
    error "Директория проекта $APP_DIR не найдена."
    error "Сначала выполните первоначальный деплой: sudo bash deploy.sh"
    exit 1
fi

START_TIME=$(date +%s)
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}   Обновление COPP — $(date '+%d.%m.%Y %H:%M')   ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"

# ─── 1. GIT PULL ──────────────────────────────────────────────────────────────
section "Получение обновлений с GitHub"
cd "$APP_DIR"

# Запоминаем текущий коммит чтобы потом показать что изменилось
OLD_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

if [ "$HARD_RESET" = true ]; then
    warn "Режим --hard: сбрасываю все локальные изменения..."
    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")
    git fetch origin
    git reset --hard "origin/$BRANCH"
else
    git pull
fi

NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    warn "Код уже актуален (коммит: $NEW_COMMIT). Обновлений нет."
    warn "Всё равно перезапускаю сервис..."
else
    info "Код обновлён: $OLD_COMMIT → $NEW_COMMIT"
    echo ""
    echo "  Изменённые файлы:"
    git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | sed 's/^/    /' || true
fi

# ─── 2. ЗАВИСИМОСТИ ───────────────────────────────────────────────────────────
section "Проверка зависимостей Python"

# Устанавливаем только если requirements.txt изменился с последнего pull
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | grep -q "requirements.txt"; then
    info "requirements.txt изменился — устанавливаю зависимости..."
    "$APP_DIR/venv/bin/pip" install -r requirements.txt --quiet
    info "Зависимости обновлены."
else
    info "requirements.txt не изменился — пропускаю установку зависимостей."
fi

# ─── 3. ПРАВА ДОСТУПА ─────────────────────────────────────────────────────────
section "Проверка прав доступа"
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod -R 775 "$APP_DIR/app/static/uploads" 2>/dev/null || true
chmod 664 "$APP_DIR/coppdb.sqlite" 2>/dev/null || true
info "Права расставлены."

# ─── 4. ПЕРЕЗАПУСК СЕРВИСА ────────────────────────────────────────────────────
if [ "$NO_RESTART" = false ]; then
    section "Перезапуск Gunicorn"
    systemctl restart "$SERVICE_NAME"

    # Даём секунду и проверяем статус
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "Сервис $SERVICE_NAME успешно перезапущен."
    else
        error "Сервис $SERVICE_NAME НЕ запустился! Последние логи:"
        journalctl -u "$SERVICE_NAME" --no-pager -n 25
        exit 1
    fi
else
    warn "Пропуск перезапуска (--no-restart)."
fi

# ─── 5. NGINX (только если изменились шаблоны или static) ─────────────────────
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" 2>/dev/null | grep -qE "^app/static/|^app/templates/"; then
    section "Перезагрузка Nginx (изменились шаблоны/статика)"
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        info "Nginx перезагружен."
    else
        warn "Конфиг Nginx содержит ошибки, не перезагружаю."
    fi
fi

# ─── ИТОГ ─────────────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Готово! Время обновления: ${ELAPSED}с${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "  Текущий коммит:  $NEW_COMMIT"
echo "  Статус сервиса:  $(systemctl is-active $SERVICE_NAME)"
echo ""
echo "  Полезные команды:"
echo "    sudo journalctl -u $SERVICE_NAME -f     # живые логи"
echo "    sudo tail -f /var/log/${SERVICE_NAME}_error.log  # ошибки"
echo ""
