import os
from fpdf import FPDF
from flask import current_app

class PDF(FPDF):
    pass

def format_date_ru(date_input):
    """Форматирует дату из YYYY-MM-DD в DD.MM.YYYY. Безопасен для дат, уже представленных в DD.MM.YYYY."""
    if not date_input:
        return ""
    try:
        date_str = str(date_input).split(' ')[0].strip()
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                return f"{int(parts[2]):02d}.{int(parts[1]):02d}.{parts[0]}"
        elif '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{int(parts[2]):02d}.{int(parts[1]):02d}.{parts[0]}"
            return date_str
        return date_str
    except Exception:
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


MONTHS_GENITIVE = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

def format_date_quote_words(date_input):
    """Форматирует дату YYYY-MM-DD или DD.MM.YYYY в «DD» месяца YYYY г."""
    if not date_input:
        return '«___» ___________ 20__ г.'
    try:
        s = str(date_input).split(' ')[0].strip()
        if '-' in s:
            parts = [int(x) for x in s.split('-')]
            y, m, d = parts[0], parts[1], parts[2]
        elif '.' in s:
            parts = [int(x) for x in s.split('.')]
            d, m, y = parts[0], parts[1], parts[2]
        else:
            return s
        m_str = MONTHS_GENITIVE.get(m, '')
        return f'«{d:02d}» {m_str} {y} г.'
    except Exception:
        return str(date_input)


def _get_watermark_path():
    """Возвращает путь к полупрозрачному водяному знаку герба колледжа (создаёт при отсутствии)."""
    wm_path = os.path.join(current_app.root_path, 'static', 'img', 'ркиг_watermark.png')
    if not os.path.exists(wm_path):
        orig_logo = os.path.join(current_app.root_path, 'static', 'img', 'ркиг.png')
        if os.path.exists(orig_logo):
            try:
                from PIL import Image
                im = Image.open(orig_logo).convert('RGBA')
                r, g, b, a = im.split()
                a = a.point(lambda p: int(p * 0.08))
                wm = Image.merge('RGBA', (r, g, b, a))
                wm.save(wm_path)
            except Exception:
                return None
    return wm_path if os.path.exists(wm_path) else None


def _render_study_cert_page(pdf, request_data):
    """Отрисовывает одну страницу официальной справки об обучении."""
    pdf.add_page()
    
    # --- 1. Фоновый водяной знак (герб колледжа по центру листа) ---
    wm_path = _get_watermark_path()
    if wm_path:
        pdf.image(wm_path, x=45, y=95, w=120)

    # --- 2. Логотип колледжа (слева) ---
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'ркиг.png')
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=32, y=17, w=44)
    
    # --- Шапка министерства и колледжа (правее) ---
    header_x = 100
    header_w = 92
    pdf.set_font("TimesNewRoman", size=10)
    header_lines = [
        "Министерство образования,",
        "науки и молодёжи",
        "Республики Крым",
        "Государственное бюджетное",
        "профессиональное образовательное",
        "учреждение Республики Крым",
        "«Романовский колледж индустрии",
        "гостеприимства»",
        "295000 г. Симферополь ул. Дыбенко, 14",
        "тел. 27-00-38, 27-42-18",
        "E-mail: 043@crimeaedu.ru"
    ]
    pdf.set_y(15)
    for line in header_lines:
        pdf.set_x(header_x)
        pdf.cell(header_w, 4.3, txt=line, ln=1, align='C')
        
    cert_num = request_data.get('cert_number') or ''
    cert_date_val = request_data.get('cert_date')
    cert_date_str = format_date_quote_words(cert_date_val) if cert_date_val else '«___» ___________ 20__ г.'
    if cert_num:
        out_line = f"№ {cert_num} от {cert_date_str}"
    else:
        out_line = f"№ _____ / _____ от {cert_date_str}"
        
    pdf.set_x(header_x)
    pdf.cell(header_w, 6, txt=out_line, ln=1, align='C')
    
    # --- Заголовок ---
    pdf.ln(12)
    pdf.set_font("TimesNewRoman", "B", size=14)
    pdf.cell(0, 8, txt="С П Р А В К А", ln=1, align='C')
    pdf.ln(5)
    
    # --- Основной текст ---
    pdf.set_font("TimesNewRoman", size=12)
    
    fio = (request_data.get('fio') or '').strip()
    birth_date = format_date_ru(request_data.get('birth_date') or '')
    duration = (request_data.get('study_duration') or '').strip()
    
    start_date = format_date_quote_words(request_data.get('study_period_start')) if request_data.get('study_period_start') else '«___» ___________ 20__ г.'
    end_date = format_date_quote_words(request_data.get('study_period_end')) if request_data.get('study_period_end') else '«___» ___________ 20__ г.'
    specialty = (request_data.get('specialty') or '').strip()
    
    if request_data.get('is_state_support'):
        state_support = "находится на полном гособеспечении"
    else:
        state_support = "не находится на полном гособеспечении"
        
    funding_type_val = request_data.get('funding_type', 'budget')
    if funding_type_val == 'contract':
        funding_str = "коммерческая форма обучения"
    elif funding_type_val == 'budget':
        funding_str = "бюджетная форма обучения"
    else:
        funding_str = str(funding_type_val)
        
    order_num = request_data.get('order_number') or '___'
    order_dt = format_date_ru(request_data.get('order_date')) if request_data.get('order_date') else '__.__.20__ г.'
    if order_dt and not order_dt.endswith('г.') and not order_dt.endswith('г'):
        order_dt += ' г.'
        
    # Строка 1: Дана + ФИО, дата рождения (отступ 1.25 см только для первой строки "Дана")
    pdf.set_x(20 + 12.5)
    pdf.cell(14, 7, txt="Дана", ln=0, align='L')
    pdf.set_font("TimesNewRoman", "B", size=12)
    pdf.cell(0, 7, txt=f"{fio}, {birth_date}", border='B', ln=1, align='L')
    pdf.set_font("TimesNewRoman", size=12)
    pdf.ln(3)
    
    end_date_clean = end_date.rstrip('.') + '.'
    order_dt_clean = order_dt.rstrip('.') + '.'

    # Текст справки без абзацных отступов (ровно по левому краю)
    p1 = (
        f"в том, что он (она) действительно является обучающимся(ейся) Государственного "
        f"бюджетного профессионального образовательного учреждения Республики Крым "
        f"«Романовский колледж индустрии гостеприимства», срок обучения **{duration}** с **{start_date}** по **{end_date_clean}**"
    )
    pdf.multi_cell(0, 6.5, txt=p1, align='J', markdown=True)
    pdf.ln(2)
    
    p2 = "По основным образовательным программам по **очной форме обучения**."
    pdf.multi_cell(0, 6.5, txt=p2, align='J', markdown=True)
    pdf.ln(2)
    
    p3 = f"Обучается по специальности **«{specialty}»**, {state_support}, **{funding_str}**."
    pdf.multi_cell(0, 6.5, txt=p3, align='J', markdown=True)
    pdf.ln(2)
    
    p4 = f"Зачислен(а) приказом **№ {order_num}** от **{order_dt_clean}**"
    pdf.multi_cell(0, 6.5, txt=p4, align='J', markdown=True)
    pdf.ln(2)
    
    p5 = "Лицензия на осуществление образовательной деятельности № 0679 от 15 августа 2016 г. серия 82Л01 № 0000711."
    pdf.multi_cell(0, 6.5, txt=p5, align='J', markdown=True)
    pdf.ln(2)
    
    p6 = "Справка дана для предъявления по месту требования."
    pdf.multi_cell(0, 6.5, txt=p6, align='J', markdown=True)
    
    # Отступ перед блоком подписей
    pdf.ln(18)
    
    director_title = request_data.get('director_title') or 'Директор'
    director_name = request_data.get('director_name') or 'М.И. Пальчук'
    head_teacher_title = request_data.get('head_teacher_title') or 'И.о. зав. учебной частью'
    head_teacher_name = request_data.get('head_teacher_name') or 'В.А. Чупахина'
    
    col1_w = 60
    col2_w = 55
    col3_w = 55
    
    # Первая строка подписи: Руководитель (с линией для подписи)
    pdf.cell(col1_w, 8, txt=director_title, ln=0, align='L')
    sig_x = pdf.get_x()
    sig_y = pdf.get_y()
    pdf.line(sig_x + 3, sig_y + 6.5, sig_x + col2_w - 3, sig_y + 6.5)
    pdf.cell(col2_w, 8, txt='', ln=0)
    pdf.cell(col3_w, 8, txt=director_name, ln=1, align='R')
    
    pdf.ln(5)
    # Вторая строка подписи: Зав. учебной частью (с линией для подписи)
    pdf.cell(col1_w, 8, txt=head_teacher_title, ln=0, align='L')
    sig_x = pdf.get_x()
    sig_y = pdf.get_y()
    pdf.line(sig_x + 3, sig_y + 6.5, sig_x + col2_w - 3, sig_y + 6.5)
    pdf.cell(col2_w, 8, txt='', ln=0)
    pdf.cell(col3_w, 8, txt=head_teacher_name, ln=1, align='R')


def generate_study_certificate_pdf(request_data, output_path):
    """
    Генерирует официальную справку об обучении студента в колледже (РКИГ).
    При необходимости генерирует несколько одинаковых листов (copies_count).
    """
    pdf = PDF(orientation='P', unit='mm', format='A4')
    
    font_reg_path = os.path.join(current_app.root_path, 'static', 'fonts', 'LiberationSerif-Regular.ttf')
    font_bold_path = os.path.join(current_app.root_path, 'static', 'fonts', 'LiberationSerif-Bold.ttf')
    
    pdf.add_font("TimesNewRoman", "", font_reg_path, uni=True)
    pdf.add_font("TimesNewRoman", "B", font_bold_path, uni=True)
    pdf.add_font("TimesNewRoman", "I", font_reg_path, uni=True)
    pdf.add_font("TimesNewRoman", "BI", font_bold_path, uni=True)
    
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.set_top_margin(15)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    try:
        copies = int(request_data.get('copies_count') or 1)
        if copies < 1:
            copies = 1
        elif copies > 10:
            copies = 10
    except (ValueError, TypeError):
        copies = 1

    for _ in range(copies):
        _render_study_cert_page(pdf, request_data)

    pdf.output(output_path)
    return output_path

