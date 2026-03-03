import re

from app import app, db
from models import Schedule

particles = ('에 ', '를 ', '을 ', '은 ', '는 ', '이 ', '가 ')
updated = 0

with app.app_context():
    rows = Schedule.query.filter(Schedule.title.isnot(None)).all()
    for row in rows:
        old = (row.title or '').strip()
        new = old

        changed = True
        while changed:
            changed = False
            for particle in particles:
                if new.startswith(particle):
                    new = new[len(particle):].strip()
                    changed = True

        if re.fullmatch(r'재고\s*조사', new):
            new = '재고조사'

        if new != old:
            row.title = new
            updated += 1

    db.session.commit()

print(f'updated={updated}')
