class NovaMindException(Exception):
    """NovaMind 全局异常基类"""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(NovaMindException):
    def __init__(self, file_id: str) -> None:
        super().__init__(f"未找到相关文件: {file_id}", status_code=404)


class DuplicateFileError(NovaMindException):
    def __init__(self, file_hash: str) -> None:
        super().__init__(f"文件已存在，请勿重复上传 (哈希为 {file_hash})", status_code=409)


class EmbeddingError(NovaMindException):
    def __init__(self, detail: str) -> None:
        super().__init__(f"向量生成失败: {detail}", status_code=502)


class LLMError(NovaMindException):
    def __init__(self, detail: str) -> None:
        super().__init__(f"大模型调用失败: {detail}", status_code=502)
