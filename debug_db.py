# debug_db.py
from app.database import SessionLocal
from app.models import User

db = SessionLocal()
for u in db.query(User).all():
    print(f"login='{u.login}', password='{u.password}'")
db.close()
