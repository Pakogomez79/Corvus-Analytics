import os
import pymysql
from dotenv import load_dotenv

def list_tables():
    load_dotenv()
    DB_HOST = os.getenv('DATABASE_HOST', 'localhost')
    DB_PORT = int(os.getenv('DATABASE_PORT', 3306))
    DB_USER = os.getenv('DATABASE_USER', 'root')
    DB_PASSWORD = os.getenv('DATABASE_PASSWORD', '')
    DB_NAME = os.getenv('DATABASE_NAME', 'xbrl_analytics')
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME, port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    rows = cur.fetchall()
    print('Tables:', [r[0] for r in rows])
    for t in ['permissions','role_permissions','user_permissions']:
        print(t, 'exists?', any(r[0]==t for r in rows))
    conn.close()

if __name__ == '__main__':
    list_tables()
