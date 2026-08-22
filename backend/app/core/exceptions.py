from fastapi import HTTPException, status

class FinExplainException(Exception):
    """Base exception for FinExplain backend."""
    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)

class ProductNotFoundError(HTTPException):
    def __init__(self, product_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found."
        )

class DocumentNotFoundError(HTTPException):
    def __init__(self, document_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

class RetrievalError(FinExplainException):
    """Raised when hybrid retrieval fails."""
    pass

class LLMGenerationError(FinExplainException):
    """Raised when Gemini LLM generation fails."""
    pass

class IngestionError(FinExplainException):
    """Raised when document ingestion or parsing fails."""
    pass
