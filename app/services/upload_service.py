import os
from flask import request
from app.utils.image_utils import save_image_as_webp

class UploadService:
    @staticmethod
    def handle_main_image(form_field='main_image', existing_field='existing_main_image', upload_folder='uploads'):
        """Handles upload of a main single image."""
        os.makedirs(os.path.join('app', 'static', upload_folder), exist_ok=True)
        main_image_path = request.form.get(existing_field, '')
        
        if form_field in request.files:
            file = request.files[form_field]
            if file and file.filename != '':
                filename = save_image_as_webp(file, os.path.join('app', 'static', upload_folder))
                if filename:
                    main_image_path = f"{upload_folder}/{filename}"
                    
        return main_image_path

    @staticmethod
    def handle_extra_images(form_field='extra_images', existing_field='existing_extra_images', upload_folder='uploads'):
        """Handles upload of multiple extra images."""
        os.makedirs(os.path.join('app', 'static', upload_folder), exist_ok=True)
        extra_images_paths = request.form.getlist(existing_field)
        
        if form_field in request.files:
            files = request.files.getlist(form_field)
            for file in files:
                if file and file.filename != '':
                    filename = save_image_as_webp(file, os.path.join('app', 'static', upload_folder))
                    if filename:
                        extra_images_paths.append(f"{upload_folder}/{filename}")
                        
        return ",".join(extra_images_paths)
