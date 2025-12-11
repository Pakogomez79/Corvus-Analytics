from sqlalchemy import inspect
from app.db import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
for t in ['permissions','role_permissions','user_permissions']:
    print(t, 'exists?', t in tables)
