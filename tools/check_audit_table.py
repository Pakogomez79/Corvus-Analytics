from app.db import engine

with engine.begin() as conn:
    try:
        rows = conn.exec_driver_sql("SHOW TABLES LIKE 'audit_logs'").fetchall()
        if rows:
            print('audit_logs table exists')
        else:
            print('audit_logs table NOT found')
    except Exception as e:
        print('error checking table:', e)
