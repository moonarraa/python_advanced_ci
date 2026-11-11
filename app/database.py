import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cookbook.db")

engine = create_async_engine(DATABASE_URL)
# expire_on_commit=False — после commit объекты остаются доступны для чтения
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """Зависимость FastAPI: отдельная сессия на каждый запрос."""
    async with async_session() as session:
        yield session
