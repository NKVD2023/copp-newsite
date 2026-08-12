import json
import sqlite3
from app.main.matching import get_top_professions

conn = sqlite3.connect('coppdb.sqlite')
conn.row_factory = sqlite3.Row

userAnswers = {"hard_tags": {"education": "edu:spo", "experience": "exp:0_1", "work_format": "work:field"}, "soft_tags": {"tag_interests": "interests:art", "tag_klimov": "klimov:man_sign", "tag_work_style": "work_style:team", "tag_environment": "env:physical", "tag_role": "role:operator", "tag_stress": "stress:dynamic"}}

top = get_top_professions(conn, userAnswers, limit=3)
print(top)
