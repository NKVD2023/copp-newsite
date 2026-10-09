import os
from werkzeug.utils import secure_filename

def save_image_as_webp(file, upload_folder, quality=80, add_uuid=False):
    """
    Сохраняет загруженный файл. Если это картинка (jpg/png), 
    конвертирует в WebP и сохраняет. Возвращает итоговое имя файла.
    """
    if not file or file.filename == '':
        return None
        
    os.makedirs(upload_folder, exist_ok=True)
    
    orig_ext = os.path.splitext(file.filename)[1].lower()
    filename = secure_filename(file.filename)
    
    # Если имя файла состояло только из русских букв, secure_filename вернет пустоту или только расширение
    if not filename or filename == orig_ext.strip('.') or filename.startswith('.'):
        import uuid
        filename = f"image_{uuid.uuid4().hex[:8]}{orig_ext}"
        
    if add_uuid:
        import uuid
        filename = f"{uuid.uuid4().hex}_{filename}"
        
    basename, ext = os.path.splitext(filename)
    if not ext:
        ext = orig_ext
        filename += ext
    
    if ext.lower() not in ['.png', '.jpg', '.jpeg']:
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filename
        
    try:
        from PIL import Image, ImageOps
        # Если загружаемый файл в памяти или во временном файле
        img = Image.open(file.stream)
        
        # Исправляем ориентацию фотографии по EXIF (актуально для смартфонов)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
            
        # Автоматическое пропорциональное уменьшение гигантских фото (например, 48MP с телефона)
        # Для веб-новостей максимального разрешения 1920x1920 более чем достаточно
        max_dim = 1920
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
        # Корректная обработка цветовых пространств
        if img.mode in ('RGBA', 'LA'):
            # WebP отлично поддерживает альфа-канал
            pass
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        webp_filename = f"{basename}.webp"
        filepath = os.path.join(upload_folder, webp_filename)
        
        # Сохраняем в WebP с method=4 (быстрое и качественное сжатие без долгого exhaustive search)
        img.save(filepath, 'webp', quality=quality, method=4)
        return webp_filename
    except Exception as e:
        print(f"Ошибка при конвертации в WebP: {e}")
        # Если не получилось (например, битый файл) - просто сохраняем оригинал
        try:
            file.stream.seek(0)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            return filename
        except Exception as save_err:
            print(f"Ошибка сохранения оригинального файла: {save_err}")
            return None
