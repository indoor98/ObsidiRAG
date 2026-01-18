# engine & db session setup

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import DATABASE_URL
from src.databases.base import Base

engine = create_async_engine(DATABASE_URL, echo=False)
print(f"Connecting to database at {DATABASE_URL}")


async def init_db() -> None:
    """초기화: 비동기 엔진에서 메타데이터를 생성합니다.

    호출 시점: 애플리케이션 시작 시 한 번만 실행하세요.
    예: `await init_db()` 또는 스타트업 이벤트에서 호출.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session