from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base  # 👈 AGREGAR declarative_base aquí
from sqlalchemy import MetaData
from ..config import settings
import ssl

# Metadata específica de Identity (separada del Core)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# SSL para BDs remotas (Railway, etc.); sin SSL en hosts locales
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
connect_args = {"ssl": _ssl_ctx} if not settings.db_host_is_local else {}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300
)

# Session local para Identity
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_identity_db():
    """Dependencia de base de datos para Identity"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()