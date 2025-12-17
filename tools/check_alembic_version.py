from dotenv import load_dotenv
import os
import sqlalchemy

load_dotenv()
DB_TYPE = os.getenv("DATABASE_TYPE", "mysql")
DB_USER = os.getenv("DATABASE_USER", "root")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "Pako280279*")
DB_HOST = os.getenv("DATABASE_HOST", "localhost")
DB_PORT = os.getenv("DATABASE_PORT", "3306")
DB_NAME = os.getenv("DATABASE_NAME", "xbrl_analytics")

if DB_TYPE == "mysql":
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise SystemExit("Unsupported DB type for this check")

engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    try:
        res = conn.execute(sqlalchemy.text("SELECT * FROM alembic_version"))
        rows = res.fetchall()
        if not rows:
            print('no rows in alembic_version')
        else:
            for r in rows:
                print('alembic_version row:', r)
    except Exception as e:
        print('error querying alembic_version:', e)

    # Inspect entities table columns
    try:
        cols = conn.execute(sqlalchemy.text("SHOW COLUMNS FROM entities"))
        print('\nentities columns:')
        for c in cols.fetchall():
            print(c)
    except Exception as e:
        print('error inspecting entities table:', e)
