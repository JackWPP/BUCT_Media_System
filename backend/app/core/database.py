"""
数据库连接与会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# 创建异步数据库引擎
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建基类
Base = declarative_base()


async def get_db():
    """
    数据库会话依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库表

    1. create_all: 创建所有尚不存在的表
    2. _migrate_columns: 为已有表补齐新增列（SQLite 不支持 IF NOT EXISTS）
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_columns)


def _migrate_columns(conn):
    """
    给已有表添加缺失的列。

    SQLite 的 ALTER TABLE ADD COLUMN 如果列已存在会报错，
    所以用 try/except 逐条执行，跳过已存在的列。
    """
    import sqlite3

    migrations = [
        "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN sso_id VARCHAR(100)",
    ]

    for sql in migrations:
        try:
            conn.execute(text(sql))
        except Exception:
            # 列已存在，跳过
            pass
