from app.db import SessionLocal
from app.models import FinancialStatement, CanonicalLine

db = SessionLocal()
try:
    stmts = db.query(FinancialStatement).all()
    print('FinancialStatements:', len(stmts))
    for s in stmts:
        print(s.id, s.code, s.name)
    lines = db.query(CanonicalLine).all()
    print('CanonicalLines:', len(lines))
    for l in lines[:50]:
        print(l.id, l.code, l.name, l.statement_id, l.parent_id)
finally:
    db.close()
