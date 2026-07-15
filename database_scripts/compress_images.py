import os
import glob
from PIL import Image

# Путь к папке со статикой (где лежат загруженные картинки)
STATIC_DIR = os.path.join('app', 'static', 'uploads')
# Если нужно сжать вообще все картинки (включая дизайн), раскомментируйте строку ниже:
# STATIC_DIR = os.path.join('app', 'static')

def compress_to_webp(image_path, quality=80):
    """
    Конвертирует изображение в WebP и удаляет оригинал.
    """
    try:
        # Игнорируем файлы, которые уже webp или не картинки
        if not image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return False

        # Открываем изображение
        img = Image.open(image_path)
        
        # Формируем новое имя файла с расширением .webp
        file_name, _ = os.path.splitext(image_path)
        webp_path = file_name + '.webp'
        
        # Сохраняем в WebP
        img.save(webp_path, 'webp', quality=quality, optimize=True)
        
        # Проверяем, что новый файл успешно создался, и он не пустой
        if os.path.exists(webp_path) and os.path.getsize(webp_path) > 0:
            # Сравниваем размеры (WebP обычно сильно меньше)
            old_size = os.path.getsize(image_path)
            new_size = os.path.getsize(webp_path)
            
            # Удаляем оригинал (осторожно: убедитесь, что у вас есть бэкап!)
            os.remove(image_path)
            
            print(f"✅ Сжато: {os.path.basename(image_path)} "
                  f"({old_size // 1024} KB -> {new_size // 1024} KB)")
            return True
        else:
            print(f"❌ Ошибка при конвертации: {image_path}")
            return False

    except Exception as e:
        print(f"⚠️ Ошибка обработки {image_path}: {e}")
        return False

def main():
    print(f"🔍 Поиск изображений в папке: {STATIC_DIR}")
    
    # Ищем все jpg, jpeg и png рекурсивно
    search_patterns = [
        os.path.join(STATIC_DIR, '**', '*.jpg'),
        os.path.join(STATIC_DIR, '**', '*.jpeg'),
        os.path.join(STATIC_DIR, '**', '*.png')
    ]
    
    files_to_compress = []
    for pattern in search_patterns:
        files_to_compress.extend(glob.glob(pattern, recursive=True))
    
    if not files_to_compress:
        print("🤷‍♂️ Картинки для сжатия не найдены.")
        return

    print(f"📦 Найдено картинок: {len(files_to_compress)}")
    
    compressed_count = 0
    for file_path in files_to_compress:
        if compress_to_webp(file_path):
            compressed_count += 1
            
    print("-" * 30)
    print(f"🎉 Готово! Успешно сжато: {compressed_count} из {len(files_to_compress)}.")
    print("ВАЖНО: При добавлении новых новостей вам нужно будет прогнать этот скрипт еще раз.")

if __name__ == "__main__":
    main()
