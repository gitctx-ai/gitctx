"""Language-aware code chunking using LangChain and tiktoken.

This module implements the ChunkerProtocol using:
- LangChain's RecursiveCharacterTextSplitter for language-aware splitting
- tiktoken for accurate token counting (cl100k_base encoding)

Design notes:
- Protocol-based for future Rust optimization via PyO3
- Uses primitive types only (str, int, dict) for FFI compatibility
- Conservative 3.5 chars-per-token ratio (validated by tests)
- No splitter caching needed (CLI spawns new process per run)
"""

from typing import TYPE_CHECKING, Any

import tiktoken

if TYPE_CHECKING:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
else:
    # Runtime import - mypy can't follow this due to ignore_missing_imports
    from langchain_text_splitters import RecursiveCharacterTextSplitter

from gitctx.core.language_detection import get_langchain_language
from gitctx.core.models import CodeChunk
from gitctx.core.protocols import ChunkerProtocol


class LanguageAwareChunker:
    """Code chunker using LangChain's language-aware text splitter.

    Implements ChunkerProtocol for compatibility with future Rust implementation.

    Attributes:
        encoder: tiktoken encoder (cl100k_base) for token counting
        chunk_overlap_ratio: Overlap between chunks as ratio (0.2 = 20%)
    """

    def __init__(self, chunk_overlap_ratio: float = 0.2):
        """Initialize the chunker.

        Args:
            chunk_overlap_ratio: Overlap between chunks as ratio (0.2 = 20%)
        """
        # Use cl100k_base encoding (GPT-3.5-turbo, GPT-4, text-embedding-3-*)
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.chunk_overlap_ratio = chunk_overlap_ratio

    def _create_splitter(self, language: str, max_tokens: int) -> Any:
        """Create a splitter for the given language.

        Args:
            language: Programming language (from detect_language_from_extension)
            max_tokens: Maximum tokens per chunk

        Returns:
            Configured text splitter (language-specific or generic)
        """
        # Conservative chars-per-token estimate (validated by test_token_ratio.py)
        # Empirical range: 2.5-4.2 characters/token
        # Using 2.5 (lower bound) prevents exceeding max_tokens
        # This is conservative but ensures chunks never exceed token limits
        chunk_size = int(max_tokens * 2.5)
        chunk_overlap = int(chunk_size * self.chunk_overlap_ratio)

        # Try language-specific splitter
        langchain_lang = get_langchain_language(language)

        if langchain_lang:
            try:
                return RecursiveCharacterTextSplitter.from_language(
                    language=langchain_lang,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            except ValueError:
                # Language not supported by LangChain, fall through to generic
                pass

        # Fallback to generic splitter
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk_file(self, content: str, language: str, max_tokens: int = 1000) -> list[CodeChunk]:
        """Split file content into semantic chunks.

        Args:
            content: File content to chunk (str, not bytes)
            language: Programming language for language-aware splitting
            max_tokens: Maximum tokens per chunk (default: 1000)

        Returns:
            List of CodeChunk objects with metadata
        """
        if not content:
            return []

        # Create appropriate splitter
        splitter = self._create_splitter(language, max_tokens)

        # Split the content
        texts = splitter.split_text(content)

        # Convert to CodeChunk objects
        chunks: list[CodeChunk] = []
        current_line = 1

        for chunk_index, text in enumerate(texts):
            # Count lines in this chunk
            lines_in_chunk = text.count("\n") + 1

            chunk = CodeChunk(
                content=text,
                start_line=current_line,
                end_line=current_line + lines_in_chunk - 1,
                token_count=self.count_tokens(text),
                metadata={
                    "chunk_index": chunk_index,
                    "language": language,
                    "max_tokens": max_tokens,
                    "overlap_ratio": self.chunk_overlap_ratio,
                },
            )
            chunks.append(chunk)

            # Update line counter (approximate due to overlap)
            # Line numbers approximate when overlap > 0 (±overlap_lines accuracy)
            # Acceptable for search result attribution
            current_line += int(lines_in_chunk * (1 - self.chunk_overlap_ratio))

        return chunks

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens (using cl100k_base encoding)
        """
        return len(self.encoder.encode(text))


def create_chunker(chunk_overlap_ratio: float = 0.2) -> ChunkerProtocol:
    """Factory function to create a chunker.

    This allows easy swapping of implementations in the future
    (e.g., Rust implementation via PyO3).

    Args:
        chunk_overlap_ratio: Overlap between chunks as ratio (0.0-0.5)

    Returns:
        Chunker instance implementing ChunkerProtocol
    """
    return LanguageAwareChunker(chunk_overlap_ratio)
