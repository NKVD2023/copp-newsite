import sqlite3
from app.main.matching import get_top_professions

conn = sqlite3.connect('coppdb.sqlite')
conn.row_factory = sqlite3.Row

user_payload = {
    "hard_tags": {"education": "edu:vo", "experience": "exp:0_1", "work_format": "work:remote"},
    "soft_tags": {
        "tag_interests": "interests:it",
        "tag_klimov": "klimov:man_tech",
        "tag_work_style": "work_style:team",
        "tag_environment": "env:office",
        "tag_role": "role:creator",
        "tag_stress": "stress:balanced"
    }
}
top = get_top_professions(conn, user_payload, limit=3)
print(top)
