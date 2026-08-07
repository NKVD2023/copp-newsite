from flask import render_template, request, jsonify
from app.main import bp
from app.db import get_db_connection
from app.main.matching import process_career_test

@bp.route('/career-test', methods=['GET'])
def career_test():
    """
    Страница опросника профориентации.
    """
    return render_template('career_test.html')

@bp.route('/career-test/submit', methods=['POST'])
def career_test_submit():
    """
    Принимает JSON с ответами пользователя, запускает алгоритм подбора
    профессий и вакансий, возвращает отрендеренный HTML-фрагмент результатов.
    """
    user_payload = request.get_json()
    if not user_payload:
        return jsonify({"error": "No data provided"}), 400
        
    conn = get_db_connection()
    try:
        results = process_career_test(user_payload, conn)
        return render_template('career_results_partial.html', results=results)
    finally:
        conn.close()
