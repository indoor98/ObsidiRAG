from src.databases.file.models.file_status import FileStatus
from src.databases.file.models.file_status_enum import FileStatusEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, insert, func

async def create_file_status(db: AsyncSession, file_status: FileStatus):
    stmt = insert(FileStatus).values(
        id=file_status.id,
        name=file_status.name,
        path=file_status.path,
        status=file_status.status
    )
    await db.execute(stmt)
    await db.commit()
    return file_status


async def get_file_status(db: AsyncSession, file_id: str):
    stmt = select(FileStatus).where(FileStatus.id == file_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_file_status(db: AsyncSession, file_id: str, new_status: FileStatusEnum | str):
    stmt = (
        update(FileStatus).
        where(FileStatus.id == file_id).
        values(status=new_status).
        execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()

async def delete_file_status(db: AsyncSession, file_id: str):
    stmt = delete(FileStatus).where(FileStatus.id == file_id)
    await db.execute(stmt)
    await db.commit()

async def list_all_file_statuses(db: AsyncSession):
    stmt = select(FileStatus)
    result = await db.execute(stmt)
    return result.scalars().all()

async def list_file_statuses_by_status(db: AsyncSession, status: FileStatusEnum | str):
    stmt = select(FileStatus).where(FileStatus.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()

async def count_file_statuses_by_status(db: AsyncSession, status: FileStatusEnum | str) -> int:
    stmt = select(func.count(FileStatus.id)).where(FileStatus.status == status)
    result = await db.execute(stmt)
    return result.scalar() or 0

async def bulk_update_file_statuses(db: AsyncSession, status_updates: dict):
    for file_id, new_status in status_updates.items():
        stmt = (
            update(FileStatus).
            where(FileStatus.id == file_id).
            values(status=new_status).
            execution_options(synchronize_session="fetch")
        )
        await db.execute(stmt)
    await db.commit()    

async def bulk_delete_file_statuses(db: AsyncSession, file_ids: list):
    stmt = delete(FileStatus).where(FileStatus.id.in_(file_ids))
    await db.execute(stmt)
    await db.commit()

async def get_file_status_by_path(db: AsyncSession, file_path: str):
    stmt = select(FileStatus).where(FileStatus.path == file_path)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def rename_file_status(db: AsyncSession, old_path: str, new_path: str):
    stmt = (
        update(FileStatus).
        where(FileStatus.path == old_path).
        values(path=new_path, name=new_path.split("/")[-1]).
        execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()   


async def list_file_statuses_by_name_pattern(db: AsyncSession, name_pattern: str):
    stmt = select(FileStatus).where(FileStatus.name.like(f"%{name_pattern}%"))
    result = await db.execute(stmt)
    return result.scalars().all()

async def delete_file_statuses_by_status(db: AsyncSession, status: FileStatusEnum | str):
    stmt = delete(FileStatus).where(FileStatus.status == status)
    await db.execute(stmt)
    await db.commit()

async def get_or_create_file_status(db: AsyncSession, file_status: FileStatus):
    existing = await get_file_status(db, file_status.id)
    if existing:
        return existing
    return await create_file_status(db, file_status)

async def update_file_status_name(db: AsyncSession, file_id: str, new_name: str):
    stmt = (
        update(FileStatus).
        where(FileStatus.id == file_id).
        values(name=new_name).
        execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()