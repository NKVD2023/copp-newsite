import app
from io import BytesIO

png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

application = app.create_app()
with application.test_client() as c:
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['is_admin'] = True

    # Assume we're editing profession with ID 75
    data = {
        'name': 'Test Prof (Edited)',
        'code': '11.11.11',
        'category': 'it',
        'existing_main_image': '',
        'main_image': (BytesIO(png_data), 'test_edit_upload.png')
    }

    application.config['WTF_CSRF_ENABLED'] = False
    response = c.post('/admin/edit_profession/75', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    with application.app_context():
        from app.db import get_db_connection
        conn = get_db_connection()
        prof = conn.execute("SELECT * FROM professions WHERE id=75").fetchone()
        print("Edited profession image_path:", prof['image_path'])
