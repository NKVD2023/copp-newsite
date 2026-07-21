import sqlite3
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Статистика вакансий (Работа в России)")
    parser.add_argument('--sync', action='store_true', help="Принудительно запустить синхронизацию перед выводом")
    args = parser.parse_args()

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'coppdb.sqlite')
    
    # Спрашиваем пользователя, если не передан флаг --sync
    do_sync = args.sync
    if not do_sync:
        ans = input("Загрузить свежие данные с портала «Работа в России» перед выводом статистики? (y/n) [n]: ")
        if ans.lower() in ('y', 'yes', 'д', 'да'):
            do_sync = True

    if do_sync:
        print("\n⏳ Запуск обновления базы данных... Это может занять около минуты.")
        # Подключаем функцию синхронизации из проекта
        try:
            from app.utils.trudvsem_sync import run_trudvsem_sync
            run_trudvsem_sync(db_path)
            print("✅ Синхронизация завершена.\n")
        except ImportError as e:
            print(f"[!] Ошибка импорта модуля синхронизации: {e}")
            print("Убедитесь, что вы находитесь в корне проекта.\n")

    if not os.path.exists(db_path):
        print(f"[*] База данных не найдена: {db_path}")
        print("Убедитесь, что вы запускаете скрипт из корневой папки проекта.")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем наличие таблицы
        cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='dashboard_vacancies'")
        if cursor.fetchone()[0] == 0:
            print("[!] Таблица 'dashboard_vacancies' не существует. Запустите синхронизацию данных.")
            sys.exit(1)

        # Общее количество вакансий и рабочих мест
        cursor.execute("SELECT COUNT(*), SUM(jobs_count) FROM dashboard_vacancies")
        total_vacancies, total_jobs = cursor.fetchone()
        
        if total_vacancies == 0:
            print("[!] Таблица вакансий пуста. Запустите синхронизацию.")
            sys.exit(0)
            
        print("\n" + "="*70)
        print(" СТАТИСТИКА «РАБОТА В РОССИИ» (РЕСПУБЛИКА КРЫМ) ")
        print("="*70)
        print(f" Всего вакансий (уникальных карточек): {total_vacancies}")
        print(f" Всего рабочих мест (доступных позиций): {total_jobs or 0}")
        print("-" * 70)
        
        # Средняя и максимальная зарплата
        cursor.execute("SELECT AVG(salary), MAX(salary) FROM dashboard_vacancies WHERE salary > 0")
        avg_salary, max_salary = cursor.fetchone()
        
        # Медианная зарплата (аналогично SQL-запросу на сайте)
        cursor.execute("""
            SELECT AVG(salary) as median_salary
            FROM (
                SELECT salary,
                       ROW_NUMBER() OVER (ORDER BY salary) as rn,
                       COUNT(*) OVER ()                    as cnt
                FROM dashboard_vacancies 
                WHERE salary IS NOT NULL AND salary > 0
            )
            WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
        """)
        median_row = cursor.fetchone()
        median_salary = median_row[0] if median_row else None

        if median_salary:
            print(f" Медианная предлагаемая зарплата:    {int(median_salary):,.0f} руб.".replace(',', ' '))
        if avg_salary:
            print(f" Средняя предлагаемая зарплата:      {avg_salary:,.0f} руб.".replace(',', ' '))
        if max_salary:
            print(f" Максимальная предлагаемая зарплата: {max_salary:,.0f} руб.".replace(',', ' '))
            
        print("-" * 70)
        print(" ТОП-5 МУНИЦИПАЛИТЕТОВ ПО КОЛИЧЕСТВУ ВАКАНСИЙ:")
        cursor.execute('''
            SELECT municipality, COUNT(*) as cnt 
            FROM dashboard_vacancies 
            WHERE municipality IS NOT NULL AND municipality != 'None' AND municipality != ''
            GROUP BY municipality 
            ORDER BY cnt DESC 
            LIMIT 5
        ''')
        for idx, row in enumerate(cursor.fetchall(), 1):
            print(f"  {idx}. {row['municipality']:<35} — {row['cnt']} шт.")
            
        print("-" * 70)
        print(" ТОП-5 РАБОТОДАТЕЛЕЙ ПО КОЛИЧЕСТВУ ВАКАНСИЙ:")
        cursor.execute('''
            SELECT employer, COUNT(*) as cnt 
            FROM dashboard_vacancies 
            WHERE employer IS NOT NULL AND employer != 'None' AND employer != ''
            GROUP BY employer 
            ORDER BY cnt DESC 
            LIMIT 5
        ''')
        for idx, row in enumerate(cursor.fetchall(), 1):
            employer_name = row['employer']
            if len(employer_name) > 45:
                employer_name = employer_name[:42] + '...'
            print(f"  {idx}. {employer_name:<45} — {row['cnt']} шт.")

        print("-" * 70)
        print(" ГРАФИК РАБОТЫ (распределение):")
        cursor.execute('''
            SELECT schedule, COUNT(*) as cnt 
            FROM dashboard_vacancies 
            WHERE schedule IS NOT NULL AND schedule != 'None' AND schedule != ''
            GROUP BY schedule 
            ORDER BY cnt DESC
        ''')
        for row in cursor.fetchall():
            print(f"  • {row['schedule']:<30} — {row['cnt']} шт.")
            
        print("-" * 70)
        print(" ТРЕБУЕМЫЙ ОПЫТ РАБОТЫ:")
        cursor.execute('''
            SELECT experience_length, COUNT(*) as cnt 
            FROM dashboard_vacancies 
            GROUP BY experience_length 
            ORDER BY cnt DESC
        ''')
        for row in cursor.fetchall():
            exp = row['experience_length']
            label = f"От {exp} лет" if exp else "Без опыта"
            print(f"  • {label:<30} — {row['cnt']} шт.")

        print("="*70 + "\n")
        
    except sqlite3.Error as e:
        print(f"[!] Ошибка при работе с базой данных: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    main()
