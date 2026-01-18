from pydantic import BaseModel
from src.databases.file.models.file_status_enum import FileStatusEnum

class FileStatusResponse(BaseModel):
    """파일 상태 응답 스키마"""
    id: str
    name: str
    path: str
    status: FileStatusEnum

    class Config:
        from_attributes = True  # SQLAlchemy 모델에서 자동 변환

class FileStatusStats(BaseModel):
    """파일 상태별 통계 스키마"""
    status: FileStatusEnum
    count: int

class FileStatusSummary(BaseModel):
    """파일 상태 요약 스키마"""
    total: int
    by_status: list[FileStatusStats]
