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
        from PIL import Image
        # Если загружаемый файл в памяти - открываем его
        img = Image.open(file.stream)
        
        # Конвертация RGBA (png с прозрачностью) в RGB, если нужно, 
        # но WebP отлично поддерживает RGBA, так что просто сохраняем
        
        webp_filename = f"{basename}.webp"
        filepath = os.path.join(upload_folder, webp_filename)
        
        img.save(filepath, 'webp', quality=quality, optimize=True)
        return webp_filename
    except Exception as e:
        print(f"Ошибка при конвертации в WebP: {e}")
        # Если не получилось (например, битый файл) - просто сохраняем оригинал
        file.stream.seek(0)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filename
