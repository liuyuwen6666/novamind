import hashlib


def compute_md5(data: bytes) -> str:
    """计算文件 MD5，用于去重"""
    return hashlib.md5(data).hexdigest()
