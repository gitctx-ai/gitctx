# STORY-0001.2.2: Blob Content Chunking

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 5
**Progress**: ████░░░░░░ 40% (2/5 tasks complete)

## User Story

As the indexing system (serving developers and AI agents)
I want to split blob content into semantically coherent, embeddable chunks
So that large files can be indexed within token limits while preserving context and enabling precise search result attribution

## Acceptance Criteria

- [ ] Chunks never exceed embedding model token limits (8191 for text-embedding-3-large)
- [ ] Chunks have configurable overlap (default 20%) to preserve semantic continuity
- [ ] Language-aware splitting respects code structure (functions, classes, paragraphs)
- [ ] Small blobs (<max_tokens) return single chunk without splitting
- [ ] Long lines (>max_tokens) split mid-line rather than failing
- [ ] Each chunk tracks position metadata (line numbers for search result attribution)
- [ ] Token counting uses tiktoken with cl100k_base encoding (consistent with OpenAI)
- [ ] Supports all major languages via LangChain RecursiveCharacterTextSplitter
- [ ] Protocol-based design enables future Rust optimization
- [ ] Metadata includes: blob_sha, chunk_index, language, start_line, end_line, token_count
- [ ] Invalid UTF-8 blobs are skipped with warning logged to WalkStats.errors (error type: 'invalid_encoding')

## BDD Scenarios

```gherkin
Feature: Blob Content Chunking

  Scenario: Chunk large Python file with overlap
    Given a Python blob with 5000 tokens
    And max_tokens configured as 800
    And chunk_overlap_ratio configured as 0.2
    When I chunk the blob
    Then I should get 7-8 chunks
    And each chunk should have ≤800 tokens
    And consecutive chunks should have ~20% content overlap
    And each chunk should have start_line and end_line metadata

  Scenario: Small blob returns single chunk
    Given a Python blob with 500 tokens
    And max_tokens configured as 800
    When I chunk the blob
    Then I should get exactly 1 chunk
    And the chunk should contain the entire blob content
    And chunk.start_line should be 1

  Scenario: Language-aware splitting preserves function boundaries
    Given a Python blob with 3 small functions totaling 1200 tokens
    And max_tokens configured as 800
    When I chunk the blob
    Then functions should not be split mid-body (best effort)
    And chunk boundaries should align with function boundaries when possible

  Scenario: Long single line handling
    Given a blob with one 2000-token line
    And max_tokens configured as 800
    When I chunk the blob
    Then the line should split into 3 chunks at character boundaries
    And each chunk should have ≤800 tokens
    And no data should be lost

  Scenario: Unicode and emoji support
    Given a blob containing Unicode and emoji characters
    When I count tokens
    Then tiktoken should handle non-ASCII correctly
    And chunking should not corrupt multibyte characters

  Scenario: Multiple language support
    Given blobs in Python, JavaScript, TypeScript, Go, Rust, Java, and Markdown
    When I chunk each blob
    Then each should use language-specific splitting rules from LangChain
    And metadata should indicate the detected language

  Scenario: Chunk metadata completeness
    Given a blob chunked into 5 pieces
    When I examine chunk metadata
    Then each chunk should have:
      | Field         | Type   | Example                |
      |---------------|--------|------------------------|
      | content       | str    | "def foo():\n  pass"   |
      | start_line    | int    | 42                     |
      | end_line      | int    | 58                     |
      | token_count   | int    | 156                    |
      | metadata      | dict   | {"language": "python"} |

  Scenario: Empty content handling
    Given an empty blob
    When I chunk the blob
    Then I should get an empty list []
    And no errors should be raised

  Scenario: Token limit compliance verification
    Given 100 random blobs of varying sizes
    And max_tokens configured as 800
    When I chunk all blobs
    Then 100% of chunks should have token_count ≤ 880 (allowing 10% tolerance)
```

## Child Tasks

**BDD/TDD Workflow**: BDD scenarios first, implement incrementally with each task, all scenarios pass at end

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.2.2.1](TASK-0001.2.2.1.md) | Write BDD scenarios for chunking behavior | ✅ | 3 | 0/9 scenarios (all failing) |
| [TASK-0001.2.2.2](TASK-0001.2.2.2.md) | Define protocols, models, and language detection (with tests) | ✅ | 3 | 1/9 scenarios passing |
| [TASK-0001.2.2.3](TASK-0001.2.2.3.md) | Implement LanguageAwareChunker with unit tests (TDD) and BDD scenarios | 🔵 | 10 | 7/9 scenarios passing |
| [TASK-0001.2.2.4](TASK-0001.2.2.4.md) | Integration with CommitWalker, configuration, and final BDD scenario | 🔵 | 4 | 9/9 scenarios passing ✅ |

**Total**: 20 hours = 5 story points

## Technical Design

### Protocol-Based Design

Follow protocol-based design pattern (from prototype) for future Rust optimization. Key patterns: dataclasses with primitive types only, Protocol classes for swappable implementations, factory functions for dependency injection:

```python
# src/gitctx/core/protocols.py (extend existing)

@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata.

    Design notes:
    - Simple dataclass for easy FFI serialization
    - All fields use primitive types (str, int, dict)
    - No Path objects (use strings for Rust compatibility)
    """
    content: str           # Chunk text content
    start_line: int        # Line number where chunk starts
    end_line: int          # Line number where chunk ends
    token_count: int       # Exact token count via tiktoken
    metadata: dict[str, Any]  # blob_sha, chunk_index, language, etc.


class ChunkerProtocol(Protocol):
    """Protocol for code chunking - can be fulfilled by Python or Rust.

    Enables future optimization: Python impl now, Rust impl later.
    """

    def chunk_file(
        self,
        content: str,
        language: str,
        max_tokens: int = 1000
    ) -> list[CodeChunk]:
        """Split file content into semantic chunks.

        Args:
            content: File content to chunk
            language: Programming language for language-aware splitting
            max_tokens: Maximum tokens per chunk

        Returns:
            List of CodeChunk objects with metadata
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        ...
```

### Language Detection

Simple extension-based detection provides 90%+ accuracy with zero dependencies:

```python
# src/gitctx/core/language_detection.py

from pathlib import Path

# Map file extensions to LangChain language identifiers
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "js",
    ".jsx": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "cpp",      # Default .h to C++
    ".cpp": "cpp",
    ".hpp": "hpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".html": "html",
    ".css": "css",
    ".md": "markdown",
    # Add more as needed (~30 total for 95% coverage)
}

def detect_language_from_extension(file_path: str) -> str:
    """Detect programming language from file extension.

    MVP approach: Simple extension mapping covers 90%+ of real-world files.
    Falls back to 'markdown' for unknown types (generic text splitting works fine).

    Future: Can upgrade to content-based detection if metrics show need.

    Args:
        file_path: Path to file

    Returns:
        Language identifier for LangChain RecursiveCharacterTextSplitter
    """
    ext = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "markdown")
```

**Design Rationale:**

- No external dependencies (Pygments, Linguist, etc.)
- 90%+ accuracy on common code files
- Explicit fallback behavior (markdown = generic splitting)
- Easy to test and maintain
- Can upgrade to content-based detection later if needed

### LangChain Integration

Use `RecursiveCharacterTextSplitter` with language-specific splitting:

```python
# src/gitctx/core/chunker.py

from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

class LanguageAwareChunker(ChunkerProtocol):
    """Code chunker using LangChain's language-aware text splitter.

    Implementation notes from prototype:
    - Uses RecursiveCharacterTextSplitter.from_language() for semantic coherence
    - Token counting via tiktoken for accuracy with OpenAI models
    - Cache splitters per language to avoid recreation overhead
    - Approximate chars-per-token ratio (3.5) for conservative chunking
    - Falls back to generic splitter for unsupported languages
    """

    def __init__(self, chunk_overlap_ratio: float = 0.2):
        """Initialize the chunker.

        Args:
            chunk_overlap_ratio: Overlap between chunks as ratio (0.2 = 20%)
        """
        # Use cl100k_base encoding (GPT-3.5-turbo, GPT-4, text-embedding-3-*)
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.chunk_overlap_ratio = chunk_overlap_ratio

        # No splitter caching needed: CLI spawns new process per invocation,
        # so in-memory cache would not persist across runs

        # Map language names to LangChain language codes
        self.language_map = {
            "python": "python",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "c++": "cpp",
            "c": "c",
            "c#": "csharp",
            "go": "go",
            "rust": "rust",
            "ruby": "ruby",
            "php": "php",
            "swift": "swift",
            "kotlin": "kotlin",
            "scala": "scala",
            "r": "r",
            "lua": "lua",
            "perl": "perl",
            "bash": "bash",
            "shell": "bash",
            "powershell": "powershell",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "markdown": "markdown",
        }

    def _create_splitter(
        self,
        language: str,
        max_tokens: int
    ) -> RecursiveCharacterTextSplitter:
        """Create a splitter for the given language.

        Args:
            language: Programming language (from detect_language_from_extension)
            max_tokens: Maximum tokens per chunk

        Returns:
            Configured text splitter
        """
        # Approximate characters per token for code (conservative estimate)
        #
        # Empirical data (OpenAI Community - character-to-token ratios):
        #   - Python: ~4.2 characters/token
        #   - JavaScript (minified): ~2.5 characters/token
        #   - Smalltalk: ~3.3-3.8 characters/token
        #   - General range: 2.5-4.2 characters/token
        #
        # Conservative estimate: 3.5 characters/token
        # - Middle of empirical range (avoids under-estimating token counts)
        # - Prevents exceeding max_tokens limit (chunking would fail if too aggressive)
        # - Trade-off: May create slightly smaller chunks than optimal (~15% smaller)
        # - Actual token counting via tiktoken provides precision after chunking
        #
        # Source: https://community.openai.com/t/rules-of-thumb-for-number-of-source-code-characters-to-tokens/622947
        # Note: LangChain RecursiveCharacterTextSplitter uses character counts; tiktoken validates after
        chunk_size = int(max_tokens * 3.5)
        chunk_overlap = int(chunk_size * self.chunk_overlap_ratio)

        # Use language-specific splitter (LangChain handles fallback)
        langchain_lang = self.language_map.get(language.lower())

        if langchain_lang:
            try:
                return RecursiveCharacterTextSplitter.from_language(
                    language=langchain_lang,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            except ValueError:
                # Language not supported by LangChain, use generic
                pass

        # Fallback to generic splitter
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk_file(
        self,
        content: str,
        language: str,
        max_tokens: int = 1000
    ) -> list[CodeChunk]:
        """Split file content into semantic chunks.

        Args:
            content: File content to chunk
            language: Programming language
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
            # Note: Line numbers are approximate when overlap > 0 due to chunk boundary ambiguity.
            # Accuracy: ±overlap_lines for chunks after first chunk. First chunk always exact.
            # This is acceptable for search result attribution (shows approximate location).
            current_line += int(lines_in_chunk * (1 - self.chunk_overlap_ratio))

        return chunks

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        return len(self.encoder.encode(text))


def create_chunker(chunk_overlap_ratio: float = 0.2) -> ChunkerProtocol:
    """Factory function to create a chunker.

    This allows easy swapping of implementations in the future
    (e.g., Rust implementation via PyO3).

    Args:
        chunk_overlap_ratio: Overlap between chunks as ratio

    Returns:
        Chunker instance implementing ChunkerProtocol
    """
    return LanguageAwareChunker(chunk_overlap_ratio)
```

### Integration with CommitWalker

The chunker sits between the walker and embedder:

```python
# Pipeline flow:
# 1. CommitWalker yields BlobRecord (sha, content: bytes, locations)
# 2. Chunker receives blob content, yields list[CodeChunk]
# 3. Embedder receives chunks, generates embeddings
# 4. Storage receives (blob_sha, chunk_index, embedding, metadata)

# Example orchestration (STORY-0001.2.4 will implement):
for blob_record in walker.walk():
    # Detect language from file extension (simple mapping, 90%+ accuracy)
    # See src/gitctx/core/language_detection.py for EXTENSION_TO_LANGUAGE mapping
    # Examples: .py → python, .js → js, .go → go
    # Unknown extensions fall back to 'markdown' (generic text splitting)
    file_path = blob_record.locations[0].file_path
    language = detect_language_from_extension(file_path)

    # Chunk the blob
    chunks = chunker.chunk_file(
        content=blob_record.content.decode("utf-8"),
        language=language,
        max_tokens=800  # Model-specific (text-embedding-3-large)
    )

    # Add blob_sha to chunk metadata
    for chunk in chunks:
        chunk.metadata["blob_sha"] = blob_record.sha

    # Pass chunks to embedder
    yield chunks
```

### Configuration Integration

Chunk parameters should be configurable via GitCtxSettings:

```python
# Extend GitCtxSettings (TASK-0001.2.2.3)
class IndexSettings(BaseModel):
    """Index configuration."""
    max_chunk_tokens: int = Field(
        default=800,
        description="Maximum tokens per chunk (model-specific)"
    )
    chunk_overlap_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=0.5,
        description="Overlap between chunks (0.0-0.5)"
    )
```

## Dependencies

### External Libraries

- `langchain-text-splitters>=0.3.0,<1.0` - Language-aware chunking (0.x API stability)
- `tiktoken>=0.8.0,<1.0` - Token counting for OpenAI (0.x API stability)

### Internal Dependencies

- **STORY-0001.2.1** (Commit Graph Walker) - Provides BlobRecord input ✅
- **STORY-0001.1.2** (Configuration System) - Provides GitCtxSettings ✅

### Downstream Consumers

- **STORY-0001.2.3** (OpenAI Embeddings) - Consumes chunks for embedding generation

## Pattern Reuse

From existing codebase analysis:

**Test Fixtures** (reuse these):

- `temp_git_repo` (tests/conftest.py) - Create test git repos
- `mock_clean_env` (tests/conftest.py) - Clean environment for tests

**Test Patterns** (follow these):

- AAA pattern: tests/unit/core/test_commit_walker.py (clear Arrange-Act-Assert)
- Parametrization: tests/unit/config/test_settings.py (test multiple languages)
- Factory pattern: tests/unit/conftest.py (reusable fixture factories)

**Source Patterns** (follow these):

- Protocol-based design: Enables future Rust optimization (see prototype)
- Factory functions: `create_chunker()` for easy swapping
- Dataclasses with primitive types: FFI-friendly (no Path objects)

**Anti-Patterns to Avoid** (from CLAUDE.md):

- ❌ No new abstractions when LangChain provides them
- ❌ No premature optimization (use LangChain until metrics show need)
- ❌ No reimplementing token counting (use tiktoken)

## Success Criteria

Story is complete when:

- ✅ All 5 tasks implemented and tested
- ✅ All 9 BDD scenarios pass
- ✅ Unit test coverage >90%
- ✅ Performance: 1000 chunks/second on typical code
- ✅ Memory: <50MB for 10K chunks
- ✅ Integration: Works with CommitWalker output
- ✅ Quality gates: ruff + mypy + pytest all pass
- ✅ Documentation: Protocol and implementation docstrings complete

## Performance Targets

- Chunking speed: >1000 chunks/second
- Memory usage: <50MB for 10K chunks in memory
- Token counting accuracy: ≤5% error vs tiktoken reference
- Language support: 20+ languages via LangChain

## Notes

- Follow the prototype in `/Users/bram/Code/codectl-ai/gitctx` closely
- LangChain RecursiveCharacterTextSplitter handles the hard work
- Protocol-based design enables future Rust optimization without breaking changes
- Token limits are embedding-model-specific (hardcode for text-embedding-3-large now)
- Overlap ratio of 0.2 (20%) balances context vs storage/cost

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
