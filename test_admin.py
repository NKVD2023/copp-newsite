import app
application = app.create_app()
with application.test_client() as c:
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['is_admin'] = True
    response = c.get('/admin/')
    print("GET /admin/")
    print(response.status_code)
    if response.status_code == 500:
        print(response.data.decode('utf-8'))
