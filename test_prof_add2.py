import app
from io import BytesIO

png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

application = app.create_app()
with application.test_client() as c:
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['is_admin'] = True

    data = {
        'name': 'Real Image Test 2',
        'code': '12.34.56',
        'category': 'it',
        'existing_main_image': '',
        'main_image': (BytesIO(png_data), 'my_test_upload2.png')
    }

    # Disable CSRF
    application.config['WTF_CSRF_ENABLED'] = False

    response = c.post('/admin/add_profession', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    with application.app_context():
        from app.db import get_db_connection
        conn = get_db_connection()
        prof = conn.execute("SELECT * FROM professions WHERE name='Real Image Test 2' ORDER BY id DESC").fetchone()
        if prof:
            print("Inserted profession image_path:", prof['image_path'])
        else:
            print("Row not found.")
            print(response.data.decode('utf-8'))
