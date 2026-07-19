import urllib.request
import json
import sqlite3
import re
import time
import os

STATUS_FILE = os.path.join('app', 'static', 'data', 'sync_status.json')

def update_status(status_dict):
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_dict, f, ensure_ascii=False)
    except Exception:
        pass

def extract_municipality(address_str):
    """
    Пытается извлечь название города/поселка из строки адреса.
    """
    if not address_str:
        return 'Республика Крым'
        
    parts = address_str.split(',')
    markers = ['г.', 'г ', 'город ', 'пгт.', 'пгт ', 'с.', 'с ', 'село ', 'р-н', 'район']
    for part in parts:
        part = part.strip()
        lower_part = part.lower()
        if lower_part in ['респ. крым', 'республика крым', 'крым респ', 'россия', 'рф', 'крым']:
            continue
        
        has_marker = any(m in lower_part for m in markers)
        if has_marker:
            # Очищаем префиксы для красоты
            clean_part = re.sub(r'^(г\.|г\s|с\.|с\s|пгт\.|пгт\s|город\s|село\s)', '', part, flags=re.IGNORECASE).strip()
            if clean_part:
                return clean_part
                
    return 'Республика Крым'

def run_trudvsem_sync(db_path):
    """
    Выкачивает вакансии из Работа в России (регион 91) и сохраняет в БД.
    """
    print("Начат процесс синхронизации с Работа в России (регион 91)...")
    update_status({"status": "running", "downloaded": 0, "total": 0, "pages": 0, "message": "Подготовка к скачиванию..."})
    base_url = "http://opendata.trudvsem.ru/api/v1/vacancies/region/91?limit=100&offset={}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dashboard_vacancies_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            vacancy_name TEXT,
            employer TEXT,
            municipality TEXT,
            salary INTEGER,
            jobs_count INTEGER,
            hard_skills TEXT,
            soft_skills TEXT,
            lat REAL,
            lng REAL,
            schedule TEXT,
            employment_type TEXT,
            education TEXT,
            requirements TEXT,
            duties TEXT,
            experience_length INTEGER,
            bonuses TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            source_link TEXT UNIQUE
        )
    ''')
    cursor.execute('DELETE FROM dashboard_vacancies_temp')
    
    offset = 0
    total_downloaded = 0
    seen_links = set()
    
    while True:
        url = base_url.format(offset)
        print(f"Скачивание страницы с offset {offset}...")
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            # Механизм повторных попыток
            max_retries = 3
            data = None
            for attempt in range(max_retries):
                try:
                    with urllib.request.urlopen(req, timeout=20) as response:
                        data = json.loads(response.read().decode('utf-8'))
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"Сбой соединения (попытка {attempt+1}/{max_retries}), ждем 2 сек...")
                    time.sleep(2)
                    
            results = data.get('results', {})
            vacancies = results.get('vacancies', [])
            
            if not vacancies:
                break
                
            for v_item in vacancies:
                vac = v_item.get('vacancy', {})
                
                job_name = vac.get('job-name', '')
                category = vac.get('category', {}).get('specialisation', 'Общее')
                employer = vac.get('company', {}).get('name', '')
                
                salary_min = vac.get('salary_min', 0)
                salary_max = vac.get('salary_max', 0)
                salary = salary_max if salary_max > 0 else salary_min
                
                jobs_count = vac.get('work_places', 1)
                
                addresses = vac.get('addresses', {}).get('address', [])
                location = ''
                lat, lng = 0.0, 0.0
                if addresses:
                    location = addresses[0].get('location', '')
                    try:
                        lat = float(addresses[0].get('lat', 0))
                        lng = float(addresses[0].get('lng', 0))
                    except (ValueError, TypeError):
                        pass
                        
                municipality = extract_municipality(location)
                
                requirements = vac.get('requirements', '')
                duties = vac.get('duty', '')
                education = vac.get('requirement', {}).get('education', '')
                experience_length = 0
                try:
                    experience_length = int(vac.get('requirement', {}).get('experience', 0))
                except (ValueError, TypeError):
                    pass
                
                raw_skills = vac.get('skills', [])
                hard_skills = ', '.join(raw_skills) if raw_skills else ''
                    
                schedule = vac.get('schedule', '')
                employment_type = 'Полная занятость' if vac.get('workPlaceType', {}).get('workPlaceOrdinary', True) else 'Особая занятость'
                
                contact_person = vac.get('contact_person', '')
                contact_phone = ''
                contact_list = vac.get('contact_list', [])
                if contact_list:
                    contact_phone = contact_list[0].get('contact_value', '')
                contact_email = vac.get('company', {}).get('email', '')
                
                source_link = vac.get('vac_url', '')
                
                if source_link in seen_links:
                    continue
                seen_links.add(source_link)
                
                cursor.execute('''
                    INSERT OR IGNORE INTO dashboard_vacancies_temp 
                    (category, vacancy_name, employer, municipality, salary, jobs_count, 
                     hard_skills, soft_skills, lat, lng, schedule, employment_type, education, requirements, duties, experience_length,
                     bonuses, contact_person, contact_phone, contact_email, source_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    category, job_name, employer, municipality, salary, jobs_count,
                    hard_skills, '', lat, lng, schedule, employment_type, education, requirements, duties, experience_length,
                    '', contact_person, contact_phone, contact_email, source_link
                ))
                total_downloaded += 1
            
            conn.commit()
                
            try:
                total_records = int(data.get('meta', {}).get('total', 0))
            except (ValueError, TypeError):
                total_records = 0
                    
            update_status({
                "status": "running",
                "downloaded": total_downloaded,
                "total": total_records,
                "pages": offset + 1,
                "message": f"Скачано {total_downloaded} вакансий (стр. {offset + 1})"
            })
            
            if len(vacancies) < 100 or (offset * 100 >= total_records and total_records > 0):
                break
            
            offset += 1
            time.sleep(0.5)
                
        except Exception as e:
            error_msg = f"Ошибка при скачивании offset {offset}: {str(e)}"
            print(error_msg)
            update_status({"status": "error", "message": error_msg})
            break
            
    if total_downloaded > 0:
        print(f"Скачано {total_downloaded} вакансий. Обновляем основную таблицу...")
        update_status({"status": "running", "downloaded": total_downloaded, "message": "Обновляем базу данных, строим индексы..."})
        
        cursor.execute('DROP TABLE IF EXISTS dashboard_vacancies')
        cursor.execute('''
            CREATE TABLE dashboard_vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                vacancy_name TEXT,
                employer TEXT,
                municipality TEXT,
                salary INTEGER,
                jobs_count INTEGER,
                hard_skills TEXT,
                soft_skills TEXT,
                lat REAL,
                lng REAL,
                schedule TEXT,
                employment_type TEXT,
                education TEXT,
                requirements TEXT,
                duties TEXT,
                experience_length INTEGER,
                bonuses TEXT,
                contact_person TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                source_link TEXT UNIQUE
            )
        ''')
        cursor.execute('''
            INSERT INTO dashboard_vacancies 
            (category, vacancy_name, employer, municipality, salary, jobs_count, 
             hard_skills, soft_skills, lat, lng, schedule, employment_type, education, requirements, duties, experience_length,
             bonuses, contact_person, contact_phone, contact_email, source_link)
            SELECT category, vacancy_name, employer, municipality, salary, jobs_count, 
             hard_skills, soft_skills, lat, lng, schedule, employment_type, education, requirements, duties, experience_length,
             bonuses, contact_person, contact_phone, contact_email, source_link
            FROM dashboard_vacancies_temp
        ''')
        conn.commit()
        
        # Создаем индексы для ускорения дашборда (так как записей много)
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dash_category ON dashboard_vacancies(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dash_municipality ON dashboard_vacancies(municipality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dash_employer ON dashboard_vacancies(employer)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dash_salary ON dashboard_vacancies(salary)')
        
        print("Синхронизация успешно завершена!")
        update_status({"status": "finished", "downloaded": total_downloaded, "message": "Синхронизация успешно завершена!"})
    else:
        print("Не удалось скачать вакансии. Основная таблица не изменена.")
        update_status({"status": "error", "message": "Не удалось скачать вакансии или их нет."})
        
    cursor.execute('DROP TABLE IF EXISTS dashboard_vacancies_temp')
    conn.commit()
    conn.close()
    if __name__ == '__main__':
    import os
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    db_path = os.path.join(basedir, 'coppdb.sqlite')
    run_trudvsem_sync(db_path)
