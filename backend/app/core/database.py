"""
数据库连接与会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif settings.DATABASE_URL.startswith("postgresql"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

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
    事务由端点/服务层自行管理（显式 commit/rollback）。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库表 — 创建所有尚不存在的表（开发用）。

    生产环境（PostgreSQL）应使用 `alembic upgrade head` 替代此方法。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
