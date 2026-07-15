import sqlite3

def run_sql_console():
    db_name = 'coppdb.sqlite'
    print(f"=== Консоль SQL для базы: {db_name} ===")
    print("Вставьте ваш SQL-запрос.")
    print("Когда закончите, напишите RUN с новой строки и нажмите Enter для выполнения.")
    print("Для выхода напишите EXIT.\n")

    while True:
        lines = []
        print("SQL > ", end="")
        
        # Собираем многострочный ввод
        while True:
            try:
                line = input()
            except EOFError:
                break
                
            if line.strip().upper() == 'EXIT':
                print("Выход из консоли...")
                return
            if line.strip().upper() == 'RUN':
                break
                
            lines.append(line)

        sql_query = "\n".join(lines).strip()

        if not sql_query:
            continue

        # Выполняем запрос
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            # executescript отлично понимает комментарии /* ... */ и многострочность
            cursor.executescript(sql_query) 
            conn.commit()
            print("\n[УСПЕХ] Запрос успешно выполнен!\n")
        except sqlite3.Error as e:
            print(f"\n[ОШИБКА БД] {e}\n")
        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == '__main__':
    run_sql_console()