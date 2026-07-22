import app
application = app.create_app()
with application.test_client() as c:
    with c.session_transaction() as sess:
        sess['is_admin'] = True
    response = c.get('/admin/api/logs?page=1')
    print("GET /admin/api/logs")
    print(response.status_code)
    try:
        print(response.get_json()['total_pages'])
    except Exception as e:
        print("JSON Error:", e, response.data)
