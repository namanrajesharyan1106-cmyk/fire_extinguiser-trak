import os
import re

auth_file = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\schemas\auth.py'
user_file = r'c:\Users\naman\OneDrive\Desktop\firesafetyexting\backend\app\schemas\user.py'

validator_code = '''
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[@$!%*?&#]", v):
        raise ValueError("Password must contain at least one special character")
    return v
'''

with open(auth_file, 'r', encoding='utf-8') as f:
    auth_content = f.read()
if 'def validate_password' not in auth_content:
    auth_content = auth_content.replace('from pydantic import BaseModel, ConfigDict', validator_code)
    auth_content = auth_content.replace('    new_password: str', '    new_password: str\n\n    @field_validator("new_password")\n    def check_password(cls, v):\n        return validate_password(v)')
    with open(auth_file, 'w', encoding='utf-8') as f:
        f.write(auth_content)

with open(user_file, 'r', encoding='utf-8') as f:
    user_content = f.read()
if 'def validate_password' not in user_content:
    user_content = user_content.replace('from pydantic import BaseModel, ConfigDict', validator_code)
    user_content = user_content.replace('    password: str', '    password: str\n\n    @field_validator("password")\n    def check_password(cls, v):\n        return validate_password(v)')
    with open(user_file, 'w', encoding='utf-8') as f:
        f.write(user_content)

print("Updated password validators")
