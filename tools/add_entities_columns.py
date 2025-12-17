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

if DB_TYPE != "mysql":
    raise SystemExit("This helper currently supports only MySQL")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    # get existing columns
    res = conn.execute(sqlalchemy.text("SHOW COLUMNS FROM entities"))
    existing = {r[0] for r in res.fetchall()}

    to_add = []
    if 'code' not in existing:
        to_add.append("ADD COLUMN `code` VARCHAR(100) NULL")
    if 'delegatura' not in existing:
        to_add.append("ADD COLUMN `delegatura` VARCHAR(255) NULL")
    if 'short_name' not in existing:
        to_add.append("ADD COLUMN `short_name` VARCHAR(255) NULL")

    if to_add:
        stmt = "ALTER TABLE entities " + ", ".join(to_add)
        try:
            conn.execute(sqlalchemy.text(stmt))
            print('Executed:', stmt)
        except Exception as e:
            print('Failed to execute:', stmt, e)
    else:
        print('No columns to add; all present')

    # show resulting columns
    try:
        res2 = conn.execute(sqlalchemy.text("SHOW COLUMNS FROM entities"))
        print('\nentities columns after changes:')
        for r in res2.fetchall():
            print(r)
    except Exception as e:
        print('error listing columns:', e)
