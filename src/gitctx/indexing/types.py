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


@dataclass
class SearchResult:
    """Search result from vector/hybrid search with metadata and scores.

    This dataclass represents a single search result returned from vector store
    search operations (LanceDB, Qdrant, etc.), combining chunk content, git metadata,
    and relevance scores.

    Design notes:
    - Simple dataclass for easy FFI serialization (future Rust optimization)
    - All fields use primitive types (str, int, float, bool) for Rust compatibility
    - Score fields are optional (float | None) for backward compatibility
    - Includes both keyword (BM25) and semantic (vector) score breakdowns

    Attributes:
        # Core chunk fields
        chunk_content: Chunk text content
        file_path: File path relative to repository root
        distance: Cosine distance from query vector (0-∞, lower = more similar)
            For BM25-only matches without vector component: inf (infinite distance)
        commit_sha: Git commit SHA (40-character hex string)
        token_count: Exact token count for this chunk
        blob_sha: Git blob SHA (40-character hex string)
        chunk_index: Position within blob (0, 1, 2, ...)
        start_line: Line number where chunk starts (1-indexed)
        end_line: Line number where chunk ends (inclusive)
        total_chunks: Total number of chunks for this blob
        language: Programming language (from file extension detection)

        # Git metadata fields
        author_name: Commit author name
        author_email: Commit author email
        commit_date: Commit timestamp (ISO8601 format)
        commit_message: Commit message (first line)
        is_head: True if chunk exists in HEAD tree
        is_merge: True if chunk comes from a merge commit

        # Score breakdown fields (NEW in STORY-0001.4.1 for hybrid search)
        # Note: LanceDB stores scores in internal fields (_distance, _score, _relevance_score)
        # but SearchResult uses public API naming without underscores
        bm25_score: BM25 keyword matching score (mapped from LanceDB _score field)
            (higher = better match, None if not available)
        vector_score: Cosine similarity computed as 1.0 - distance
            (0-1 range, -inf for BM25-only matches, None if not available)
        hybrid_score: RRF combined score (mapped from LanceDB _relevance_score field)
            (0-1 range, higher = more relevant, None if not available)

    Examples:
        >>> result = SearchResult(
        ...     chunk_content="def authenticate(user): pass",
        ...     file_path="src/auth.py",
        ...     distance=0.15,
        ...     commit_sha="abc123" * 6 + "ab12",
        ...     token_count=50,
        ...     blob_sha="def456" * 6 + "de45",
        ...     chunk_index=0,
        ...     start_line=1,
        ...     end_line=10,
        ...     total_chunks=1,
        ...     language="python",
        ...     author_name="Alice",
        ...     author_email="alice@example.com",
        ...     commit_date="2025-01-15T10:30:00Z",
        ...     commit_message="feat: add auth",
        ...     is_head=True,
        ...     is_merge=False,
        ...     bm25_score=0.85,
        ...     vector_score=0.92,
        ...     hybrid_score=0.88
        ... )
        >>> result.hybrid_score
        0.88
    """

    # Core chunk fields
    chunk_content: str
    file_path: str
    distance: float
    commit_sha: str
    token_count: int
    blob_sha: str
    chunk_index: int
    start_line: int
    end_line: int
    total_chunks: int
    language: str

    # Git metadata fields
    author_name: str
    author_email: str
    commit_date: str
    commit_message: str
    is_head: bool
    is_merge: bool

    # Score breakdown fields (optional for backward compatibility)
    bm25_score: float | None = None
    vector_score: float | None = None
    hybrid_score: float | None = None
