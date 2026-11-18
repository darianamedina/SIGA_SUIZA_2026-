from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
import os
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, JSON, Boolean

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
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

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class TimeStampedMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BaseModel(Base, TimeStampedMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)

class OutboxEvent(BaseModel):
    __tablename__ = "outbox_events"
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    published = Column(Boolean, default=False, index=True)

engine = create_async_engine(DATABASE_URL, echo=True, connect_args=_connect_args)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        print("Tablas creadas/verificadas")
    except Exception as e:
        print(f"init_db: tablas ya existen o error menor: {e}")