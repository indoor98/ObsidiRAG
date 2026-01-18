"""
OpenAI Embedding을 사용하여 LanceDB에 인덱싱하는 모듈
"""

import os
import logging
from pathlib import Path
from typing import List, Optional
import lancedb
import pyarrow as pa
from openai import OpenAI
from src.config import OPEN_API_KEY

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPEN_API_KEY)

# LanceDB 테이블 이름
TABLE_NAME = "obsidirag_index"

# 임베딩 모델 설정
EMBEDDING_MODEL = "text-embedding-3-small"  # 또는 "text-embedding-3-large"
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small의 차원

# 청킹 설정
CHUNK_SIZE = 1000  # 토큰 수
CHUNK_OVERLAP = 200  # 오버랩 토큰 수


def get_lancedb_connection(db_path: str = "./data/lancedb") -> lancedb.DBConnection:
    """
    LanceDB 연결을 가져옵니다.
    
    Args:
        db_path: LanceDB 데이터베이스 경로
        
    Returns:
        LanceDB 연결 객체
    """
    os.makedirs(db_path, exist_ok=True)
    return lancedb.connect(db_path)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    텍스트를 청크로 나눕니다.
    
    Args:
        text: 청킹할 텍스트
        chunk_size: 각 청크의 최대 토큰 수
        overlap: 청크 간 오버랩 토큰 수
        
    Returns:
        텍스트 청크 리스트
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
    except ImportError:
        logger.warning("tiktoken not available, using simple character-based chunking")
        # tiktoken이 없으면 간단한 문자 기반 청킹
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    # tiktoken을 사용한 토큰 기반 청킹
    tokens = encoding.encode(text)
    chunks = []
    
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    return chunks


def read_file_content(file_path: str) -> Optional[str]:
    """
    파일 내용을 읽습니다.
    
    Args:
        file_path: 읽을 파일 경로
        
    Returns:
        파일 내용 문자열, 읽기 실패 시 None
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # 텍스트 파일만 처리
        if path.suffix.lower() in ['.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml', '.yml', '.csv']:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    OpenAI Embedding API를 사용하여 텍스트 리스트의 임베딩을 생성합니다.
    
    Args:
        texts: 임베딩을 생성할 텍스트 리스트
        
    Returns:
        임베딩 벡터 리스트
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        raise


def index_file(file_path: str, file_id: str, db_path: str = "./data/lancedb") -> bool:
    """
    단일 파일을 인덱싱합니다.
    
    Args:
        file_path: 인덱싱할 파일 경로
        file_id: 파일 ID (FileStatus.id)
        db_path: LanceDB 데이터베이스 경로
        
    Returns:
        성공 여부
    """
    try:
        # 파일 내용 읽기
        content = read_file_content(file_path)
        if not content:
            return False
        
        # 텍스트 청킹
        chunks = chunk_text(content)
        if not chunks:
            logger.warning(f"No chunks created for file: {file_path}")
            return False
        
        # 임베딩 생성
        embeddings = create_embeddings(chunks)
        
        # LanceDB에 저장
        db = get_lancedb_connection(db_path)
        
        # 테이블이 없으면 생성
        if TABLE_NAME not in db.table_names():
            schema = pa.schema([
                pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIMENSION)),
                pa.field("text", pa.string()),
                pa.field("file_id", pa.string()),
                pa.field("file_path", pa.string()),
                pa.field("chunk_index", pa.int32()),
            ])
            table = db.create_table(TABLE_NAME, schema=schema, mode="overwrite")
        else:
            table = db.open_table(TABLE_NAME)
        
        # 데이터 준비
        data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data.append({
                "vector": embedding,
                "text": chunk,
                "file_id": file_id,
                "file_path": file_path,
                "chunk_index": i,
            })
        
        # 테이블에 추가
        table.add(data)
        
        logger.info(f"Successfully indexed file: {file_path} ({len(chunks)} chunks)")
        return True
        
    except Exception as e:
        logger.error(f"Error indexing file {file_path}: {e}")
        return False


def index_files(file_paths: List[str], file_ids: Optional[List[str]] = None, db_path: str = "./data/lancedb") -> dict:
    """
    여러 파일을 인덱싱합니다.
    
    Args:
        file_paths: 인덱싱할 파일 경로 리스트
        file_ids: 파일 ID 리스트 (선택사항, file_paths와 같은 순서)
        db_path: LanceDB 데이터베이스 경로
        
    Returns:
        인덱싱 결과 딕셔너리 (성공/실패 개수)
    """
    if file_ids is None:
        file_ids = [str(i) for i in range(len(file_paths))]
    
    if len(file_paths) != len(file_ids):
        raise ValueError("file_paths and file_ids must have the same length")
    
    success_count = 0
    fail_count = 0
    failed_files = []
    
    for file_path, file_id in zip(file_paths, file_ids):
        if index_file(file_path, file_id, db_path):
            success_count += 1
        else:
            fail_count += 1
            failed_files.append(file_path)
    
    return {
        "total": len(file_paths),
        "success": success_count,
        "failed": fail_count,
        "failed_files": failed_files,
    }


def search_similar(query: str, limit: int = 10, db_path: str = "./data/lancedb") -> List[dict]:
    """
    유사한 텍스트를 검색합니다.
    
    Args:
        query: 검색 쿼리 텍스트
        limit: 반환할 최대 결과 수
        db_path: LanceDB 데이터베이스 경로
        
    Returns:
        검색 결과 리스트 (text, file_path, score 포함)
    """
    try:
        # 쿼리 임베딩 생성
        query_embedding = create_embeddings([query])[0]
        
        # LanceDB에서 검색
        db = get_lancedb_connection(db_path)
        
        if TABLE_NAME not in db.table_names():
            logger.warning("Index table does not exist")
            return []
        
        table = db.open_table(TABLE_NAME)
        
        # 벡터 검색
        results = table.search(query_embedding).limit(limit).to_pandas()
        
        # 결과 포맷팅
        search_results = []
        for _, row in results.iterrows():
            search_results.append({
                "text": row.get("text", ""),
                "file_path": row.get("file_path", ""),
                "file_id": row.get("file_id", ""),
                "chunk_index": row.get("chunk_index", 0),
                "score": row.get("_distance", 0.0) if "_distance" in row else 0.0,
            })
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return []


def delete_file_from_index(file_id: str, db_path: str = "./data/lancedb") -> bool:
    """
    인덱스에서 파일을 삭제합니다.
    
    Args:
        file_id: 삭제할 파일 ID
        db_path: LanceDB 데이터베이스 경로
        
    Returns:
        성공 여부
    """
    try:
        db = get_lancedb_connection(db_path)
        
        if TABLE_NAME not in db.table_names():
            logger.warning("Index table does not exist")
            return False
        
        table = db.open_table(TABLE_NAME)
        
        # file_id로 필터링하여 삭제
        # LanceDB의 delete는 where 조건을 사용
        try:
            table.delete(where=f"file_id = '{file_id}'")
        except TypeError:
            # 구버전 호환성: where 파라미터 없이 직접 조건 전달
            table.delete(f"file_id = '{file_id}'")
        
        logger.info(f"Successfully deleted file from index: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file from index {file_id}: {e}")
        return False
