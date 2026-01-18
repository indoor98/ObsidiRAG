from src.databases.base import Base
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from src.databases.file.models.file_status_enum import FileStatusEnum


class FileStatus(Base):
    __tablename__ = 'file_status'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[FileStatusEnum] = mapped_column(
        SQLEnum(FileStatusEnum),
        default=FileStatusEnum.PENDING,
        nullable=False
    )