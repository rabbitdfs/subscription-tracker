from logging.config import fileConfig

from alembic import context

from app import models  # чтобы Alembic увидел все таблицы
from app.db import Base, engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
