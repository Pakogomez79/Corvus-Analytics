@echo off
set PYTHONPATH=E:\APLICACIONES PROPIAS\Corvus-Analytics
cd /d E:\APLICACIONES PROPIAS\Corvus-Analytics
.venv\Scripts\python.exe tools\alter_alembic_version.py
.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade heads
echo --- migrations finished ---
echo s | .venv\Scripts\python.exe create_users.py
echo --- seed finished ---
.venv\Scripts\python.exe tools\check_seed.py
