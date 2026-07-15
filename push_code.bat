@echo off
chcp 65001 >nul
color 0B

echo =========================================
echo  Быстрая отправка кода на сервер (GitHub)
echo =========================================
echo.

:: 1. Проверяем статус
echo [*] Индексация файлов...
git add .

:: 2. Спрашиваем комментарий (если пустой — будет "auto update")
set /p msg="Введите что изменили (или просто нажмите Enter): "
if "%msg%"=="" set msg="auto update"

:: 3. Коммитим
echo.
echo [*] Сохранение изменений...
git commit -m "%msg%"

:: 4. Отправляем
echo.
echo [*] Отправка на GitHub...
git push origin develop

echo.
echo =========================================
echo  Готово! Код успешно отправлен.
echo =========================================
echo.
echo Чтобы обновить сервер, запустите там: sudo bash /var/www/copp-newsite/update.sh
echo.
pause
