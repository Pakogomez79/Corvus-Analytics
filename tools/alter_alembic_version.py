from sqlalchemy import text
from app.db import engine

with engine.begin() as conn:
    # Increase alembic_version.version_num length to accommodate long revision ids
    conn.exec_driver_sql("ALTER TABLE alembic_version MODIFY COLUMN version_num VARCHAR(255);")
    print('alembic_version.version_num altered to VARCHAR(255)')
