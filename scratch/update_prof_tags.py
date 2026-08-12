import sqlite3
import os
import sys

# Добавляем корневую папку в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import get_db_connection

def assign_tags(profession):
    name = profession['name'].lower()
    category = profession['category']
    desc = (profession['description'] or '').lower()
    
    tags = {
        'tag_specialty': 'spec:none',
        'tag_klimov': 'klimov:man_man',
        'tag_role': 'role:operator',
        'tag_stress': 'stress:balanced',
        'tag_interests': 'interests:none',
        'tag_work_style': 'work_style:team',
        'tag_environment': 'env:office'
    }
    
    # 1. Specialty (Профильное направление)
    if category in ['it', 'industry', 'transport', 'construction']:
        tags['tag_specialty'] = 'spec:tech'
    elif category in ['services', 'trade', 'management', 'finance', 'jurisprudence']:
        tags['tag_specialty'] = 'spec:econ'
    elif category in ['education', 'social', 'media', 'art', 'hospitality', 'security']:
        tags['tag_specialty'] = 'spec:humanitarian'
    elif category in ['medicine', 'agriculture']:
        tags['tag_specialty'] = 'spec:science'
    
    if any(k in name for k in ['програм', 'информ', 'систем', 'данн', 'разработ']):
        tags['tag_specialty'] = 'spec:tech'
    elif any(k in name for k in ['врач', 'мед', 'фарма', 'биол']):
        tags['tag_specialty'] = 'spec:science'
        
    # 2. Klimov (Предмет труда)
    if tags['tag_specialty'] == 'spec:tech':
        tags['tag_klimov'] = 'klimov:man_tech'
        if 'данн' in name or 'бух' in name or 'эконом' in name or 'учет' in name:
            tags['tag_klimov'] = 'klimov:man_sign'
    elif category in ['agriculture'] or 'ветеринар' in name or 'агрон' in name:
        tags['tag_klimov'] = 'klimov:man_nature'
    elif category in ['art', 'media'] or 'дизайн' in name or 'худож' in name or 'актер' in name:
        tags['tag_klimov'] = 'klimov:man_art'
    elif tags['tag_specialty'] == 'spec:econ':
        if category in ['finance', 'jurisprudence'] or any(k in name for k in ['бухгалтер', 'документ', 'архив']):
            tags['tag_klimov'] = 'klimov:man_sign'
        else:
            tags['tag_klimov'] = 'klimov:man_man'
    else:
        tags['tag_klimov'] = 'klimov:man_man'
        
    # 3. Role (Ролевая модель)
    if 'управ' in name or 'менеджер' in name or 'руковод' in name or 'директор' in name:
        tags['tag_role'] = 'role:manager'
    elif 'аналит' in name or 'исследова' in name or 'учен' in name or 'научн' in name:
        tags['tag_role'] = 'role:analyst'
    elif 'дизайн' in name or 'худож' in name or 'архитект' in name or 'сценарист' in name:
        tags['tag_role'] = 'role:creator'
    else:
        tags['tag_role'] = 'role:operator'
        
    # 4. Stress/Conditions
    if tags['tag_role'] == 'role:manager':
        tags['tag_stress'] = 'stress:responsibility'
    elif category in ['security', 'medicine'] or 'спасател' in name or 'полицей' in name:
        tags['tag_stress'] = 'stress:responsibility'
    elif category in ['transport', 'trade', 'services'] or tags['tag_role'] == 'role:creator':
        tags['tag_stress'] = 'stress:dynamic'
    elif 'бухгалтер' in name or 'архив' in name or 'сборщик' in name or 'оператор' in name:
        tags['tag_stress'] = 'stress:routine'
    else:
        tags['tag_stress'] = 'stress:balanced'

    # 5. Interests
    if category == 'it' or 'программист' in name or 'разработчик' in name:
        tags['tag_interests'] = 'interests:it'
    elif category in ['art', 'media'] or 'дизайн' in name or 'худож' in name:
        tags['tag_interests'] = 'interests:art'
    elif category in ['medicine', 'science'] or 'врач' in name or 'научн' in name:
        tags['tag_interests'] = 'interests:science'
    elif category in ['education', 'social'] or 'учитель' in name or 'помощ' in name:
        tags['tag_interests'] = 'interests:social'
    elif category in ['finance', 'management', 'trade'] or 'менеджер' in name or 'эконом' in name:
        tags['tag_interests'] = 'interests:finance'
    else:
        tags['tag_interests'] = 'interests:manual'

    # 6. Work Style
    if tags['tag_role'] in ['role:manager', 'role:operator'] and tags['tag_interests'] not in ['interests:it', 'interests:art']:
        tags['tag_work_style'] = 'work_style:team'
    elif tags['tag_interests'] in ['interests:it', 'interests:art', 'interests:science']:
        tags['tag_work_style'] = 'work_style:individual'
    else:
        tags['tag_work_style'] = 'work_style:team'

    # 7. Environment
    if category in ['it', 'finance', 'jurisprudence', 'media'] or 'бухгалтер' in name or 'оператор' in name:
        tags['tag_environment'] = 'env:office'
    elif category in ['transport', 'trade', 'services', 'security'] or 'курьер' in name or 'водитель' in name:
        tags['tag_environment'] = 'env:dynamic'
    elif category in ['construction', 'agriculture', 'industry'] or 'монтажник' in name or 'слесарь' in name:
        tags['tag_environment'] = 'env:physical'
    else:
        tags['tag_environment'] = 'env:office'

    return tags

def run():
    print("Connecting to DB...")
    # Так как запускаем из корня, БД будет браться из config
    # Сделаем прямой коннект на случай если context не поднят
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'coppdb.sqlite'))
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        conn.execute('ALTER TABLE professions ADD COLUMN tag_interests TEXT')
        conn.execute('ALTER TABLE professions ADD COLUMN tag_work_style TEXT')
        conn.execute('ALTER TABLE professions ADD COLUMN tag_environment TEXT')
    except sqlite3.OperationalError:
        pass
        
    professions = conn.execute('SELECT id, code, name, category, description FROM professions').fetchall()
    
    updated_count = 0
    for prof in professions:
        p_dict = dict(prof)
        tags = assign_tags(p_dict)
        
        conn.execute('''
            UPDATE professions 
            SET tag_specialty = ?, tag_klimov = ?, tag_role = ?, tag_stress = ?,
                tag_interests = ?, tag_work_style = ?, tag_environment = ?
            WHERE id = ?
        ''', (
            tags['tag_specialty'], tags['tag_klimov'], tags['tag_role'], tags['tag_stress'],
            tags['tag_interests'], tags['tag_work_style'], tags['tag_environment'],
            p_dict['id']
        ))
        updated_count += 1
        
    conn.commit()
    conn.close()
    
    print(f"Successfully updated tags for {updated_count} professions!")

if __name__ == '__main__':
    run()
