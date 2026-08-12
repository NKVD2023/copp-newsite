import json

payload_str = '{"hard_tags": {"education": "edu:spo", "experience": "exp:0_1", "work_format": "work:field"}, "soft_tags": {"tag_interests": "interests:art", "tag_klimov": "klimov:man_sign", "tag_work_style": "work_style:team", "tag_environment": "env:physical", "tag_role": "role:operator", "tag_stress": "stress:dynamic"}}'
userAnswers = json.loads(payload_str)
print(userAnswers.get('soft_tags'))
