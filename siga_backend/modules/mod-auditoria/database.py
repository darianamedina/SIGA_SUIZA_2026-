import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Auditoría vive en el schema core (siga_suiza_2026) al igual que identidades y auth
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "siga_suiza_2026")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SSL para BDs remotas (Railway, etc.); sin SSL en hosts locales
import ssl as _ssl_mod
_SSL_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "host.docker.internal", "postgres")

def _db_url_is_local(url: str) -> bool:
    try:
        after = url.split("://", 1)[-1]
        host_part = after.split("@", 1)[-1]
        host = host_part.split(":", 1)[0].split("/", 1)[0].split("?", 1)[0]
        return host in _SSL_LOCAL_HOSTS
    except Exception:
        return False

_ssl_ctx = _ssl_mod.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl_mod.CERT_NONE
_connect_args = {"ssl": _ssl_ctx} if not _db_url_is_local(DATABASE_URL) else {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
