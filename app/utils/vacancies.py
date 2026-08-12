"""
Модуль подбора вакансий по названию профессии.

Использует алгоритм сравнения «корней» слов (первые 5 символов) для нечеткого
сопоставления названий профессий и вакансий. Поддерживает фильтрацию по уровню
образования и опыту работы пользователя (гибридный подход: приоритизация +
визуальные бейджи несоответствия).
"""

import re


# Стоп-слова: слишком общие термины, которые дают ложные совпадения
# между несвязанными профессиями и вакансиями.
STOP_WORDS = {
    'и', 'по', 'на', 'в', 'с', 'для', 'от', 'до', 'из', 'за', 'к', 'об',
    'о', 'при', 'у', 'как', 'разряда', 'класс',
    'специалист', 'рабочий', 'мастер', 'инженер', 'заместитель',
    'эксплуатация', 'эксплуатации', 'отраслям', 'отрасли',
    'ремонту', 'ремонт', 'обслуживанию', 'обслуживание',
    'производства', 'производство', 'транспорте', 'технология',
    'строительство', 'организация', 'оператор', 'работ', 'монтаж',
    'дело', 'систем', 'система', 'видам', 'управления',
    'устройство', 'изделий', 'деятельность', 'сервис', 'сервиса'
}


def get_roots(text):
    """
    Извлекает набор «корней» из текста для нечеткого сравнения.

    Корень — первые 5 символов слова (для слов длиной >= 5) или целое слово
    (для слов длиной ровно 4). Слова из STOP_WORDS и короче 4 символов
    игнорируются.

    Args:
        text: строка для анализа (название профессии или вакансии).

    Returns:
        set: множество строковых корней.
    """
    if not text:
        return set()
    words = re.findall(r'[а-яА-ЯёЁa-zA-Z]+', text.lower())
    roots = set()
    for w in words:
        if w not in STOP_WORDS and len(w) >= 5:
            roots.add(w[:5])  # 5 букв — баланс между точностью и полнотой
        elif w not in STOP_WORDS and len(w) == 4:
            roots.add(w)
    return roots


def get_education_level(edu_string):
    """
    Преобразует текстовое описание образования из вакансии в числовой уровень.

    Шкала: 0 (не указано) → 1 (среднее) → 1.5 (курсы) → 2 (СПО) → 3 (высшее).

    Args:
        edu_string: строка из поля 'education' вакансии (API ТрудВсем).

    Returns:
        float: числовой уровень образования.
    """
    if not edu_string:
        return 0
    edu = edu_string.lower()
    if 'высшее' in edu:
        return 3
    if 'среднее профессиональное' in edu or 'спо' in edu or 'техникум' in edu or 'колледж' in edu:
        return 2
    if 'курсы' in edu or 'дополнительное' in edu:
        return 1.5
    return 1  # среднее или базовое


def get_user_edu_level(user_edu_tag):
    """
    Преобразует тег ответа пользователя об образовании в числовой уровень.

    Теги соответствуют вариантам ответа в career_test.html (вопрос 'education').

    Args:
        user_edu_tag: строка вида 'edu:vo', 'edu:spo', 'edu:courses', 'edu:basic'.

    Returns:
        float: числовой уровень образования пользователя.
    """
    if user_edu_tag == 'edu:vo':
        return 3
    if user_edu_tag == 'edu:spo':
        return 2
    if user_edu_tag == 'edu:courses':
        return 1.5
    if user_edu_tag == 'edu:basic':
        return 1
    return 3  # по умолчанию максимум, если тег не указан


def get_user_exp_years(user_exp_tag):
    """
    Преобразует тег ответа пользователя об опыте в числовое значение (лет).

    Возвращает верхнюю границу диапазона ответа. Используется для сравнения
    с полем experience_length вакансий (оператор <=).

    Args:
        user_exp_tag: строка вида 'exp:0_1', 'exp:1_3', 'exp:3_5', 'exp:5_plus'.

    Returns:
        int: максимальное количество лет опыта, соответствующее ответу.
    """
    if user_exp_tag == 'exp:0_1':
        return 0
    if user_exp_tag == 'exp:1_3':
        return 1
    if user_exp_tag == 'exp:3_5':
        return 3
    if user_exp_tag == 'exp:5_plus':
        return 5
    return 100  # по умолчанию максимум — не фильтровать


def _format_edu_badge(edu_raw):
    """
    Формирует краткий текст для бейджа несоответствия по образованию.

    Args:
        edu_raw: строка из поля 'education' вакансии.

    Returns:
        str: краткое название уровня образования для UI.
    """
    if not edu_raw:
        return "Образование"
    edu = edu_raw.lower()
    if 'высшее' in edu:
        return "Высшее"
    if 'среднее профессиональное' in edu or 'спо' in edu:
        return "СПО"
    return "Образование"


def get_matching_vacancies(prof_name, all_vacs, limit=6, user_edu=None, user_exp=None):
    """
    Подбирает вакансии по названию профессии с учетом квалификации пользователя.

    Алгоритм (гибридный подход):
    1. Сравнивает корни слов названия профессии и вакансии (базовый score).
    2. Если вакансия требует образование/опыт выше, чем у пользователя,
       начисляет штраф -15 баллов и формирует текст бейджа несоответствия.
    3. Сортирует по score (desc), возвращает top-N.
    4. Вакансии с бейджем всё равно могут попасть в выдачу (для заполнения
       карточек), но помечены визуальным предупреждением в UI.

    Args:
        prof_name: название профессии из атласа.
        all_vacs: список sqlite3.Row — все вакансии из dashboard_vacancies.
        limit: максимальное количество вакансий в результате.
        user_edu: тег образования пользователя (например, 'edu:spo').
        user_exp: тег опыта пользователя (например, 'exp:1_3').

    Returns:
        list[dict]: отсортированный список вакансий, каждая с полями
                    'match_score' (int) и 'mismatch_badge' (str | None).
    """
    prof_roots = get_roots(prof_name)
    user_edu_lvl = get_user_edu_level(user_edu)
    user_exp_max = get_user_exp_years(user_exp)

    scored_vacs = []
    for vac in all_vacs:
        # Конвертируем sqlite3.Row в dict для возможности добавления новых полей
        vac_dict = dict(vac)

        vac_name = vac_dict.get('vacancy_name') or ''
        vac_roots = get_roots(vac_name)

        # Считаем пересечение корней в названии (базовый вес)
        score = len(prof_roots.intersection(vac_roots)) * 10

        if score > 0:
            vac_edu_lvl = get_education_level(vac_dict.get('education'))
            vac_exp = vac_dict.get('experience_length') or 0

            mismatch_reasons = []

            # Проверяем образование: если вакансия требует уровень выше пользователя
            if vac_edu_lvl > user_edu_lvl:
                score -= 15
                mismatch_reasons.append(_format_edu_badge(vac_dict.get('education')))

            # Проверяем опыт: если вакансия требует больше лет, чем есть у пользователя
            if vac_exp > user_exp_max:
                score -= 15
                year_text = "лет"
                if vac_exp == 1:
                    year_text = "года"
                elif 2 <= vac_exp <= 4:
                    year_text = "лет"  # упрощенно
                mismatch_reasons.append(f"Опыт от {vac_exp} {year_text}")

            vac_dict['match_score'] = score
            vac_dict['mismatch_badge'] = " | ".join(mismatch_reasons) if mismatch_reasons else None
            scored_vacs.append(vac_dict)

    scored_vacs.sort(key=lambda x: x['match_score'], reverse=True)
    return scored_vacs[:limit]
