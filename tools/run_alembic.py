from alembic.config import Config
from alembic import command

cfg = Config("alembic.ini")
command.upgrade(cfg, "heads")
print('Alembic upgrade heads completed')
