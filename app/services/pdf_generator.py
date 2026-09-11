import os
from fpdf import FPDF
from flask import current_app

class PDF(FPDF):
    pass

def format_date_ru(date_input):
    """Форматирует дату из YYYY-MM-DD в DD.MM.YYYY"""
    if not date_input:
        return ""
    try:
        date_str = str(date_input).split(' ')[0] # Отрезаем время если есть
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return date_str
    except:
        return str(date_input)

def generate_income_certificate_pdf(request_data, output_path):
    """
    Генерирует PDF-файл заявления на основе данных из БД и сохраняет по указанному пути.
    request_data - это словарь или sqlite3.Row с данными заявки.
    """
    pdf = PDF()
    
    # Подключаем кириллические шрифты (Times New Roman analog)
    font_reg_path = os.path.join(current_app.root_path, 'static', 'fonts', 'LiberationSerif-Regular.ttf')
    font_bold_path = os.path.join(current_app.root_path, 'static', 'fonts', 'LiberationSerif-Bold.ttf')
    
    pdf.add_font("TimesNewRoman", "", font_reg_path, uni=True)
    pdf.add_font("TimesNewRoman", "B", font_bold_path, uni=True)
    
    pdf.add_page()
    
    # --- Вставка логотипа ---
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'ркиг.png')
    if os.path.exists(logo_path):
        # x, y, w
        pdf.image(logo_path, x=20, y=20, w=45)
    
    # --- Шапка (справа) ---
    pdf.set_font("TimesNewRoman", size=14)
    # Сдвигаем Y на уровень начала шапки
    pdf.set_xy(105, 20)
    pdf.cell(90, 7, txt="Директору ГБПОУ РК «РКИГ»", ln=1, align='L')
    pdf.set_x(105)
    pdf.cell(90, 7, txt="Пальчук М. И.", ln=1, align='L')
    
    pdf.ln(5)
    pdf.set_x(105)
    pdf.cell(10, 7, txt="от", ln=0, align='L')
    pdf.cell(80, 7, txt=request_data['fio'], border='B', ln=1, align='C')
    
    pdf.set_x(105)
    pdf.cell(22, 7, txt="группа №", ln=0, align='L')
    pdf.cell(68, 7, txt=request_data['group_number'], border='B', ln=1, align='C')
    
    pdf.set_x(105)
    pdf.cell(35, 7, txt="дата рождения", ln=0, align='L')
    dob = format_date_ru(request_data['birth_date'])
    pdf.cell(55, 7, txt=dob, border='B', ln=1, align='C')
    
    pdf.set_x(105)
    pdf.cell(38, 7, txt="период обучения:", ln=0, align='L')
    txt_period = f"с 01.09.{request_data['study_period_start']} г. по 30.06.{request_data['study_period_end']} г."
    pdf.cell(52, 7, txt=txt_period, border='B', ln=1, align='C')
    
    pdf.set_x(105)
    pdf.cell(20, 7, txt="телефон", ln=0, align='L')
    pdf.cell(70, 7, txt=request_data['phone'], border='B', ln=1, align='C')
    
    # --- Заголовок ---
    pdf.ln(25) # Отступ после шапки
    pdf.set_font("TimesNewRoman", "B", size=14)
    pdf.cell(0, 10, txt="Заявление", ln=1, align='C')
    
    # --- Основной текст ---
    pdf.set_font("TimesNewRoman", size=14)
    pdf.ln(5)
    
    import json
    
    # Текст с отступом (абзацем)
    pdf.set_x(30)
    pdf.cell(0, 8, txt="Прошу Вас предоставить мне справку о доходах за следующие периоды:", ln=1, align='L')
    
    # Пытаемся распарсить JSON периодов
    periods = []
    if request_data.get('income_periods'):
        try:
            periods = json.loads(request_data['income_periods'])
        except:
            pass
            
    # Если JSON пуст или не распарсился, используем старые поля для обратной совместимости
    if not periods and request_data.get('income_period_start') and request_data.get('income_period_end'):
        periods = [
            {"start": request_data['income_period_start'], "end": request_data['income_period_end']}
        ]
        
    for p in periods:
        d_start = format_date_ru(p['start'])
        d_end = format_date_ru(p['end'])
        
        pdf.set_x(40)
        pdf.cell(10, 8, txt="с", ln=0, align='L')
        pdf.cell(40, 8, txt=d_start, border='B', ln=0, align='C')
        
        pdf.cell(10, 8, txt=" по ", ln=0, align='C')
        pdf.cell(40, 8, txt=d_end, border='B', ln=1, align='C')
    
    pdf.ln(5)
    pdf.set_x(30)
    pdf.cell(0, 8, txt="Справка предоставляется по месту требования.", ln=1, align='L')
    
    # --- Дата в левом нижнем углу ---
    pdf.ln(25)
    
    # Форматируем дату подачи
    created_at_date = format_date_ru(request_data['created_at'])
            
    pdf.set_x(20)
    pdf.cell(15, 8, txt="Дата", ln=0)
    pdf.cell(40, 8, txt=created_at_date, border='B', ln=0, align='C')
    
    # Сохраняем
    pdf.output(output_path)
    return output_path
