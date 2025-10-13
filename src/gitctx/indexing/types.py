"""Data types for code chunking and embeddings."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata.

    Design notes:
    - Simple dataclass for easy FFI serialization (future Rust optimization)
    - All fields use primitive types (str, int, dict)
    - No Path objects (use strings for Rust compatibility)

    Attributes:
        content: Chunk text content
        start_line: Line number where chunk starts (1-indexed)
        end_line: Line number where chunk ends (inclusive)
        token_count: Exact token count via tiktoken
        metadata: Additional metadata (blob_sha, chunk_index, language, etc.)

    Examples:
        >>> chunk = CodeChunk(
        ...     content="def foo():\\n    pass",
        ...     start_line=10,
        ...     end_line=11,
        ...     token_count=8,
        ...     metadata={"language": "python", "chunk_index": 0}
        ... )
        >>> chunk.token_count
        8
    """

    content: str
    start_line: int
    end_line: int
    token_count: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Embedding:
    """Embedding vector and metadata for a code chunk.

    This dataclass represents the output from embedding generation
    (OpenAI API or local models), ready for storage in LanceDB.

    Attributes:
        vector: Embedding vector (list of floats, dimension depends on model)
        token_count: Number of tokens in the chunk
        model: Embedding model used (e.g., "text-embedding-3-large")
        cost_usd: Cost in USD for generating this embedding
        blob_sha: Blob SHA-1 hash this chunk came from
        chunk_index: Position within blob (0, 1, 2, ...)
        chunk_content: Raw code content that was embedded (optional)
        start_line: Line number where chunk starts (optional)
        end_line: Line number where chunk ends (optional)
        total_chunks: Total chunks for this blob (optional)
        language: Programming language (optional)
        api_token_count: Actual tokens used by API (optional, may differ from tiktoken estimate)
    """

    # Required fields
    vector: list[float]
    token_count: int
    model: str
    cost_usd: float
    blob_sha: str
    chunk_index: int

    # Optional fields
    chunk_content: str = ""
    start_line: int = 0
    end_line: int = 0
    total_chunks: int = 0
    language: str = ""
    api_token_count: int | None = None
