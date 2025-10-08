"""Protocol definitions for gitctx core components.

Protocols enable:
1. Type checking without inheritance
2. Duck typing with static verification
3. Future optimization (Python → Rust via PyO3)

All protocols use primitive types for FFI compatibility.
"""

from typing import Protocol

from gitctx.core.models import CodeChunk


class ChunkerProtocol(Protocol):
    """Protocol for code chunking - can be fulfilled by Python or Rust.

    Enables future optimization: Python implementation now, Rust implementation
    later via PyO3 bindings, without breaking changes to consuming code.

    Design principles:
    - Use primitive types (str, int) for FFI compatibility
    - Return dataclasses with primitive fields (CodeChunk)
    - No Path objects or complex types
    """

    def chunk_file(self, content: str, language: str, max_tokens: int = 1000) -> list[CodeChunk]:
        """Split file content into semantic chunks.

        Args:
            content: File content to chunk (str, not bytes)
            language: Programming language for language-aware splitting
                     (from detect_language_from_extension)
            max_tokens: Maximum tokens per chunk (embedding model specific)

        Returns:
            List of CodeChunk objects with metadata

        Examples:
            >>> chunker.chunk_file("def foo(): pass", "python", max_tokens=800)
            [CodeChunk(content="def foo(): pass", start_line=1, ...)]
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens (using cl100k_base encoding)

        Examples:
            >>> chunker.count_tokens("Hello world")
            2
        """
        ...
