import os
from flask import request, current_app
from app.utils.image_utils import save_image_as_webp

class UploadService:
    @staticmethod
    def _get_target_dir(upload_folder):
        base_dir = (current_app.static_folder if current_app else None) or os.path.join(os.getcwd(), 'app', 'static')
        target_dir = os.path.join(base_dir, upload_folder)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    @staticmethod
    def handle_main_image(form_field='main_image', existing_field='existing_main_image', upload_folder='uploads'):
        """Handles upload of a main single image."""
        target_dir = UploadService._get_target_dir(upload_folder)
        main_image_path = request.form.get(existing_field, '')
        
        if form_field in request.files:
            file = request.files[form_field]
            if file and file.filename != '':
                filename = save_image_as_webp(file, target_dir)
                if filename:
                    main_image_path = f"{upload_folder}/{filename}"
                    
        return main_image_path

    @staticmethod
    def handle_extra_images(form_field='extra_images', existing_field='existing_extra_images', upload_folder='uploads'):
        """Handles upload of multiple extra images."""
        target_dir = UploadService._get_target_dir(upload_folder)
        extra_images_paths = request.form.getlist(existing_field)
        
        if form_field in request.files:
            files = request.files.getlist(form_field)
            for file in files:
                if file and file.filename != '':
                    filename = save_image_as_webp(file, target_dir)
                    if filename:
                        extra_images_paths.append(f"{upload_folder}/{filename}")
                        
        return ",".join(extra_images_paths)
