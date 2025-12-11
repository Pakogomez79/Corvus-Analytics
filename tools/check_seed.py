from sqlalchemy import text
from app.db import engine

with engine.begin() as conn:
    tables = ['permissions','role_permissions','user_permissions','roles','user_roles','users']
    for t in tables:
        try:
            row = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {t}").first()
            count = row[0] if row else 0
        except Exception as e:
            count = f'ERROR: {e}'
        print(f"{t}: {count}")

    print('\nSample permissions:')
    try:
        rows = conn.exec_driver_sql("SELECT id, name FROM permissions LIMIT 20").fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print('Error fetching permissions:', e)
