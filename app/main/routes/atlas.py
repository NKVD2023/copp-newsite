from flask import render_template, abort, current_app, session
from app.main import bp
from app.db import get_db_connection

@bp.route('/atlas')
def atlas():
    """
    Страница атласа профессий.
    Colleges загружаются из app-level кэша (один раз за жизнь процесса).
    """
    conn = get_db_connection()
    professions = conn.execute(
        "SELECT * FROM professions WHERE status = 'published' ORDER BY code ASC, name ASC"
    ).fetchall()

    colleges = current_app.get_colleges()
    return render_template('atlas.html', professions=professions, colleges=colleges)


@bp.route('/atlas/<int:prof_id>')
def profession_detail(prof_id):
    """
    Детальная страница профессии из Атласа.
    Colleges загружаются из app-level кэша.
    """
    import json

    conn = get_db_connection()
    prof = conn.execute('SELECT * FROM professions WHERE id = ?', (prof_id,)).fetchone()

    if not prof or (prof['status'] != 'published' and not session.get('is_admin')):
        abort(404)

    colleges = current_app.get_colleges()

    # Нормализация для поиска (игнорируем тип кавычек, двойные пробелы, регистр)
    import re
    def norm_s(s):
        if not s: return ""
        return re.sub(r'["\'«»]', '', s).replace('  ', ' ').strip().lower()

    colleges_with_links = []
    inst_val = prof['institutions']
    if inst_val:
        val = inst_val.strip()
        if val.startswith('[') and val.endswith(']'):
            try:
                selected_colleges = json.loads(val)
                for name in selected_colleges:
                    url = next((c['url'] for c in colleges if norm_s(c['name']) == norm_s(name)), None)
                    colleges_with_links.append({'name': name, 'url': url})
            except Exception:
                pass
        elif ',' in val:
            for part in val.split(','):
                part = part.strip()
                if not part: continue
                url = next((c['url'] for c in colleges if norm_s(c['name']) == norm_s(part)), None)
                colleges_with_links.append({'name': part, 'url': url})
        else:
            # Сплошной текст без запятых. Ищем известные колледжи как подстроки.
            norm_val = norm_s(val)
            for c in colleges:
                if norm_s(c['name']) in norm_val:
                    colleges_with_links.append({'name': c['name'], 'url': c['url']})
            if not colleges_with_links:
                colleges_with_links.append({'name': val, 'url': None})

    # Маппинг категорий профессий на категории вакансий
    VACANCY_CATEGORY_MAP = {
        'it': ['Информационные технологии, телекоммуникации, связь'],
        'medicine': ['Здравоохранение и социальное обеспечение'],
        'education': ['Образование, наука'],
        'construction': ['Строительство, ремонт, стройматериалы, недвижимость', 'ЖКХ, эксплуатация'],
        'transport': ['Транспорт, автобизнес, логистика, склад, ВЭД'],
        'industry': ['Производство', 'Машиностроение', 'Пищевая промышленность', 'Легкая промышленность', 'Добывающая промышленность', 'Химическая, нефтехимическая, топливная промышленность'],
        'agriculture': ['Сельское хозяйство, экология, ветеринария'],
        'service': ['Услуги населению, сервисное обслуживание', 'Туризм, гостиницы, рестораны', 'Продажи, закупки, снабжение, торговля'],
        'other': []
    }

    prof_cat = prof['category'] or 'other'
    
    # Получаем все вакансии, так как категории на ТрудВсем могут не совпадать с нашими
    query = "SELECT * FROM dashboard_vacancies"
    all_vacs = conn.execute(query).fetchall()

    # Алгоритм "умного" подбора по корням слов
    import re
    stop_words = {
        'и', 'по', 'на', 'в', 'с', 'для', 'от', 'до', 'из', 'за', 'к', 'об', 'о', 'при', 'у', 'как', 'разряда', 'класс',
        'специалист', 'рабочий', 'мастер', 'инженер', 'заместитель', 'эксплуатация', 'эксплуатации', 'отраслям', 'отрасли',
        'ремонту', 'ремонт', 'обслуживанию', 'обслуживание', 'производства', 'производство', 'транспорте', 'технология',
        'строительство', 'организация', 'оператор', 'работ', 'монтаж', 'дело', 'систем', 'система', 'видам', 'управления',
        'устройство', 'изделий', 'деятельность', 'сервис', 'сервиса'
    }
    
    def get_roots(text):
        if not text:
            return set()
        words = re.findall(r'[а-яА-ЯёЁa-zA-Z]+', text.lower())
        roots = set()
        for w in words:
            if w not in stop_words and len(w) >= 5:
                roots.add(w[:5]) # 5 букв отсеивает ложные срабатывания
            elif w not in stop_words and len(w) == 4:
                roots.add(w)
        return roots
    
    prof_roots = get_roots(prof['name'])
    
    # Расширяем поиск: добавляем синонимы из категории, если корней мало
    # Но для максимальной точности будем опираться именно на корни названия профессии.

    scored_vacs = []
    for vac in all_vacs:
        vac_name = vac['vacancy_name'] or ''
        vac_duties = vac['duties'] or ''
        vac_roots = get_roots(vac_name)
        
        # Считаем пересечение корней в названии
        score = len(prof_roots.intersection(vac_roots)) * 10
        
        # Дополнительный балл, если корень есть в обязанностях
        duties_lower = vac_duties.lower()
        for root in prof_roots:
            if root in duties_lower:
                score += 1
        
        if score > 0:
            scored_vacs.append((score, vac))

    # Сортируем: сначала по совпадениям (score), затем по зарплате
    scored_vacs.sort(key=lambda x: (x[0], x[1]['salary'] or 0), reverse=True)
    
    # Берем ТОП-6 ТОЛЬКО подходящих
    related_vacancies = [item[1] for item in scored_vacs[:6]]

    # Чтобы передать колледжи
    return render_template('profession_detail.html', prof=prof, colleges=colleges_with_links, related_vacancies=related_vacancies)
