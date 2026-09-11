import sys
from app import create_app
from app.services.pdf_generator import generate_income_certificate_pdf
from datetime import datetime

app = create_app()
with app.app_context():
    data = {
        'fio': 'Иванова Ивана Ивановича',
        'group_number': '3ПК1',
        'birth_date': '2005-10-15',
        'study_period_start': '23',
        'study_period_end': '27',
        'phone': '+7 (978) 123-45-67',
        'income_period_start': '2024-01-01',
        'income_period_end': '2024-06-30',
        'created_at': datetime.now()
    }
    generate_income_certificate_pdf(data, 'test.pdf')
    print("PDF generated successfully")
