# System-wide Constants and Enums
from enum import Enum

class IntentType(str, Enum):
    COMPARISON = "comparison"
    LOOKUP = "lookup"
    CALCULATION = "calculation"
    GENERAL = "general"

class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NO_EVIDENCE = "No Evidence"
    ERROR = "Error"

class HILTTaskStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"

# Default Model & RAG parameters
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIM = 384
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64
MAX_CONTEXT_TOKENS = 4000
HIGH_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.40
