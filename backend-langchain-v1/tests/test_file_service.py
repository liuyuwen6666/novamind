import pytest
from app.services.file_service import FileService

def test_split_text():
    service = FileService()
    # 模拟 1000 字符的长文本
    long_text = "人工智能" * 250
    chunks = service.split_text(long_text, chunk_size=100, chunk_overlap=20)
    
    assert len(chunks) > 0
    # 验证每个切片不超过限制范围
    for chunk in chunks:
        assert len(chunk.page_content) <= 120
