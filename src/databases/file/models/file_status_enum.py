from enum import Enum


class FileStatusEnum(str, Enum):
    """
    파일 상태를 나타내는 Enum 클래스
    
    - PENDING: 파일이 생성되었지만 아직 처리되지 않음
    - MODIFIED: 파일이 수정됨
    - SYNCED: 파일이 동기화됨 (인덱싱 완료)
    - DELETED: 파일이 삭제됨
    - ERROR: 파일 처리 중 오류 발생
    """
    PENDING = "PENDING"
    MODIFIED = "MODIFIED"
    SYNCED = "SYNCED"
    DELETED = "DELETED"
    ERROR = "ERROR"
