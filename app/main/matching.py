"""
Модуль подбора профессий и вакансий по результатам профориентационного теста.

Основной пайплайн: process_career_test() принимает ответы пользователя,
рассчитывает совпадения с профессиями из БД по системе тегов (Климов,
интересы, стиль работы и т.д.), затем подтягивает релевантные вакансии
с учетом образования и опыта пользователя.
"""

import json
import logging

from flask import current_app

# Веса тегов для расчета процента совпадения профессии.
# Чем выше вес — тем сильнее влияние ответа на итоговый балл.
WEIGHTS = {
    'tag_specialty': 30,
    'tag_klimov': 20,
    'tag_role': 10,
    'tag_stress': 10,
    'tag_interests': 15,
    'tag_work_style': 10,
    'tag_environment': 5
}


def calculate_profession_score(user_answers, profession):
    """
    Рассчитывает балл совпадения пользователя с конкретной профессией.

    Сравнивает soft-теги ответов пользователя с тегами профессии из БД.
    Каждое точное совпадение добавляет вес из словаря WEIGHTS.

    Args:
        user_answers: dict с soft-тегами пользователя (tag_klimov, tag_role, ...).
        profession: dict-строка профессии из БД.

    Returns:
        int: суммарный балл совпадения (0–100).
    """
    score = 0

    tags = [
        'tag_specialty', 'tag_klimov', 'tag_role',
        'tag_stress', 'tag_interests', 'tag_work_style', 'tag_environment'
    ]

    for tag in tags:
        if user_answers.get(tag) and user_answers[tag] == profession.get(tag):
            score += WEIGHTS[tag]

    return score


def get_top_professions(conn, user_answers, limit=3):
    """
    Возвращает ТОП профессий из БД, отсортированных по баллу совпадения.

    Args:
        conn: sqlite3 соединение с БД.
        user_answers: полный dict ответов пользователя (содержит 'soft_tags').
        limit: максимальное количество профессий в результате.

    Returns:
        list[dict]: список профессий с добавленным полем 'match_score'.
    """
    professions = conn.execute(
        'SELECT id, name, category, description, image_path, '
        'tag_specialty, tag_klimov, tag_role, tag_stress, '
        'tag_interests, tag_work_style, tag_environment '
        'FROM professions WHERE status="published"'
    ).fetchall()

    scored_professions = []
    for p in professions:
        p_dict = dict(p)
        score = calculate_profession_score(user_answers.get('soft_tags', {}), p_dict)
        if score > 0:  # Только если есть хоть какое-то совпадение
            p_dict['match_score'] = score
            scored_professions.append(p_dict)

    scored_professions.sort(key=lambda x: x['match_score'], reverse=True)
    return scored_professions[:limit]


def process_career_test(user_payload, conn):
    """
    Главный пайплайн обработки результатов профориентационного теста.

    1. Находит ТОП-3 профессии по совпадению тегов.
    2. Сохраняет результат в таблицу career_test_results.
    3. Подтягивает релевантные вакансии с фильтрацией по образованию и опыту.

    Args:
        user_payload: dict с полными ответами пользователя (hard_tags, soft_tags).
        conn: sqlite3 соединение с БД.

    Returns:
        list[dict]: список профессий, каждая с полем 'vacancies' (list[dict]).
    """
    top_profs = get_top_professions(conn, user_payload, limit=3)

    top_profession_id = top_profs[0]['id'] if top_profs else None

    # Сохраняем результаты теста в БД для аналитики
    try:
        conn.execute(
            'INSERT INTO career_test_results (user_answers, top_profession_id) VALUES (?, ?)',
            (json.dumps(user_payload, ensure_ascii=False), top_profession_id)
        )
        conn.commit()
    except Exception as e:
        current_app.logger.error("Ошибка сохранения результатов теста: %s", e)

    # Подтягиваем вакансии для каждой из ТОП профессий
    try:
        from app.utils.vacancies import get_matching_vacancies
        all_vacs = conn.execute("SELECT * FROM dashboard_vacancies").fetchall()

        # Получаем данные образования и опыта из ответов пользователя
        hard_tags = user_payload.get('hard_tags', {})
        user_edu = hard_tags.get('education')
        user_exp = hard_tags.get('experience')

        for prof in top_profs:
            prof['vacancies'] = get_matching_vacancies(
                prof['name'],
                all_vacs,
                limit=3,
                user_edu=user_edu,
                user_exp=user_exp
            )
    except Exception as e:
        current_app.logger.error("Ошибка подбора вакансий для результатов теста: %s", e)
        for prof in top_profs:
            prof['vacancies'] = []

    return top_profs
