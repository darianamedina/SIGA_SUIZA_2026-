import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import create_engine
from alembic import context
import os
import sys

# Agregar el directorio app al path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configuración de Alembic
config = context.config

# Override DB URL desde variable de entorno
# Soporta: DB_URL directa, o DATABASE_URL (Railway), o componentes DB_*
db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")

_SSL_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres")

def _is_local_url(url: str) -> bool:
    """Detecta si la URL apunta a un host local (no requiere SSL)."""
    try:
        # Extraer host sin dependencias externas
        after_scheme = url.split("://", 1)[-1]
        host_part = after_scheme.split("@", 1)[-1]
        host = host_part.split(":", 1)[0].split("/", 1)[0].split("?", 1)[0]
        return host in _SSL_LOCAL_HOSTS
    except Exception:
        return False

def _normalize_sync_url(url: str) -> str:
    """Convierte cualquier scheme a postgresql+psycopg:// (psycopg3) y añade SSL si es remoto."""
    # Unificar scheme al dialecto sync instalado (psycopg3)
    for prefix in ("postgresql+asyncpg://", "postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = url.replace(prefix, "postgresql+psycopg://", 1)
            break
    # Añadir sslmode=require para hosts remotos si no viene explícito
    if "sslmode=" not in url and not _is_local_url(url):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

if not db_url:
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "john.007")
    host = os.getenv("DB_HOST", "host.docker.internal")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "siga_core")
    db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"

config.set_main_option("sqlalchemy.url", _normalize_sync_url(db_url))

# Interpretar el archivo de config para logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData target
from app.core.identity.models import Base
import app.core.registry.models
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode using sync engine."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()