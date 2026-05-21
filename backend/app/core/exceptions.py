class NovaMindException(Exception):
    """Base exception for NovaMind"""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(NovaMindException):
    def __init__(self, file_id: str) -> None:
        super().__init__(f"Document not found: {file_id}", status_code=404)


class DuplicateFileError(NovaMindException):
    def __init__(self, file_hash: str) -> None:
        super().__init__(f"File already exists (hash={file_hash})", status_code=409)


class EmbeddingError(NovaMindException):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Embedding error: {detail}", status_code=502)


class LLMError(NovaMindException):
    def __init__(self, detail: str) -> None:
        super().__init__(f"LLM error: {detail}", status_code=502)
