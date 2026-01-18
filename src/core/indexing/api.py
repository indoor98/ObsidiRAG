from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from src.databases.database import get_db
from src.databases.file.crud import get_file_status_by_path, update_file_status
from src.databases.file.models.file_status_enum import FileStatusEnum
from src.core.indexing.index import index_files, search_similar, delete_file_from_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/indexing", tags=["indexing"])


@router.post("/run")
async def run_indexing(
    paths: List[str] = Body(..., description="인덱싱할 파일 경로 리스트"),
    db: AsyncSession = Depends(get_db),
):
    """
    파일들을 인덱싱합니다.
    
    - **paths**: 인덱싱할 파일 경로 리스트
    """
    if not paths:
        raise HTTPException(status_code=400, detail="No file paths provided")
    
    # 파일 경로로부터 file_id 조회
    file_ids = []
    valid_paths = []
    
    for path in paths:
        file_status = await get_file_status_by_path(db, path)
        if file_status:
            file_ids.append(file_status.id)
            valid_paths.append(path)
        else:
            logger.warning(f"File status not found for path: {path}")
    
    if not valid_paths:
        raise HTTPException(status_code=404, detail="No valid files found for indexing")
    
    # 인덱싱 실행
    try:
        result = index_files(valid_paths, file_ids)
        
        # 성공한 파일들의 상태를 SYNCED로 업데이트
        for path, file_id in zip(valid_paths, file_ids):
            if path in result.get("failed_files", []):
                # 실패한 파일은 ERROR 상태로
                await update_file_status(db, file_id, FileStatusEnum.ERROR)
            else:
                # 성공한 파일은 SYNCED 상태로
                await update_file_status(db, file_id, FileStatusEnum.SYNCED)
        
        return {
            "status": "completed",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        # 모든 파일을 ERROR 상태로 업데이트
        for file_id in file_ids:
            try:
                await update_file_status(db, file_id, FileStatusEnum.ERROR)
            except Exception:
                pass
        
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.post("/search")
async def search_index(
    query: str = Body(..., description="검색 쿼리"),
    limit: int = Body(10, description="반환할 최대 결과 수"),
):
    """
    인덱스에서 유사한 텍스트를 검색합니다.
    
    - **query**: 검색 쿼리 텍스트
    - **limit**: 반환할 최대 결과 수
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        results = search_similar(query, limit=limit)
        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.delete("/file/{file_id}")
async def delete_indexed_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    인덱스에서 파일을 삭제합니다.
    
    - **file_id**: 삭제할 파일 ID
    """
    try:
        from src.databases.file.crud import get_file_status
        
        success = delete_file_from_index(file_id)
        if success:
            # 파일 상태를 PENDING으로 변경 (재인덱싱 가능하도록)
            file_status = await get_file_status(db, file_id)
            if file_status:
                await update_file_status(db, file_id, FileStatusEnum.PENDING)
            return {"status": "deleted", "file_id": file_id}
        else:
            raise HTTPException(status_code=404, detail="File not found in index")
    except Exception as e:
        logger.error(f"Error deleting file from index: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
