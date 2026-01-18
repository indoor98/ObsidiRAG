from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.databases.database import get_db
from src.databases.file.models.file_status import FileStatus
from src.databases.file.models.file_status_enum import FileStatusEnum
from src.databases.file.crud import get_file_status
from src.databases.schemas.file_status import (
    FileStatusResponse,
    FileStatusStats,
    FileStatusSummary,
)
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/files", response_model=list[FileStatusResponse])
async def get_all_files(
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(100, ge=1, le=1000, description="반환할 최대 레코드 수"),
    db: AsyncSession = Depends(get_db),
):
    """
    추적 중인 모든 파일 목록을 조회합니다.
    
    - **skip**: 페이지네이션을 위한 건너뛸 레코드 수
    - **limit**: 반환할 최대 레코드 수 (최대 1000)

    """
    stmt = select(FileStatus).offset(skip).limit(limit)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileStatusResponse.model_validate(f) for f in files]


@router.get("/files/status/{status}", response_model=list[FileStatusResponse])
async def get_files_by_status(
    status: FileStatusEnum,
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(100, ge=1, le=1000, description="반환할 최대 레코드 수"),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 상태의 파일 목록을 조회합니다.
    
    - **status**: 파일 상태 (PENDING, MODIFIED, SYNCED, DELETED, ERROR)
    - **skip**: 페이지네이션을 위한 건너뛸 레코드 수
    - **limit**: 반환할 최대 레코드 수 (최대 1000)
    """
    stmt = (
        select(FileStatus)
        .where(FileStatus.status == status)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileStatusResponse.model_validate(f) for f in files]


@router.get("/files/{file_id}", response_model=FileStatusResponse)
async def get_file_by_id(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 파일의 상태를 조회합니다.
    
    - **file_id**: 파일 ID
    """
    file_status = await get_file_status(db, file_id)
    if not file_status:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")
    return FileStatusResponse.model_validate(file_status)


@router.get("/files/stats/summary", response_model=FileStatusSummary)
async def get_file_status_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    파일 상태별 통계를 조회합니다.
    
    모든 상태별 파일 개수를 반환합니다.
    """
    # 전체 개수
    total_stmt = select(func.count(FileStatus.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # 상태별 개수
    status_stmt = (
        select(FileStatus.status, func.count(FileStatus.id).label("count"))
        .group_by(FileStatus.status)
    )
    status_result = await db.execute(status_stmt)
    status_counts = status_result.all()

    by_status = [
        FileStatusStats(status=FileStatusEnum(row.status), count=row.count)
        for row in status_counts
    ]

    return FileStatusSummary(total=total, by_status=by_status)


@router.get("/files/stats/count", response_model=FileStatusStats)
async def get_file_count_by_status(
    status: FileStatusEnum = Query(..., description="조회할 파일 상태"),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 상태의 파일 개수를 조회합니다.
    
    - **status**: 파일 상태 (PENDING, MODIFIED, SYNCED, DELETED, ERROR)
    """
    stmt = (
        select(func.count(FileStatus.id))
        .where(FileStatus.status == status)
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0

    return FileStatusStats(status=status, count=count)