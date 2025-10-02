# EPIC-0001.2: Real Indexing Implementation

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🔵 Not Started  
**Estimated**: 21 story points  
**Progress**: ░░░░░░░░░░ 0%

## Overview

Replace the mock indexing from EPIC-0001.1 with actual functionality that scans files, chunks text, generates embeddings via OpenAI, and stores them using safetensors binary format.

## Goals

- Scan repository files respecting .gitignore
- Chunk files intelligently for embedding
- Generate embeddings via OpenAI text-embedding-3-large
- Store embeddings in safetensors format for 5x space savings
- Track costs and provide accurate progress

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-0001.2.1](.././active/STORY-0001.2.1.md) | Git-Aware File Scanner | 🔵 Not Started | 5 |
| [STORY-0001.2.2](.././active/STORY-0001.2.2.md) | Language-Agnostic Code Chunking | 🔵 Not Started | 5 |
| [STORY-0001.2.3](.././active/STORY-0001.2.3.md) | OpenAI Embedding Generation | 🔵 Not Started | 5 |
| [STORY-0001.2.4](.././active/STORY-0001.2.4.md) | Safetensors Storage Implementation | 🔵 Not Started | 3 |
| [STORY-0001.2.5](.././active/STORY-0001.2.5.md) | Progress Tracking and Cost Estimation | 🔵 Not Started | 3 |

## BDD Specifications

```gherkin
# tests/e2e/features/indexing.feature

Feature: Repository Indexing
  As a developer
  I want to index my repository
  So that I can search through my codebase

  Background:
    Given OpenAI API key is configured

  Scenario: Index a small repository
    Given a repository with 10 Python files
    When I run "gitctx index"
    Then the output should show progress
    And embeddings should be created in .gitctx/embeddings/
    And files should have .safetensors extension
    And manifest.json should be created

  Scenario: Respect gitignore rules
    Given a repository with node_modules directory
    And .gitignore contains "node_modules/"
    When I run "gitctx index"
    Then files in node_modules should not be indexed
    And the output should show correct file count

  Scenario: Handle large files
    Given a repository with a 10MB file
    When I run "gitctx index"
    Then the large file should be chunked appropriately
    And chunks should have overlapping content
    And each chunk should respect token limits

  Scenario: Track indexing costs
    Given a repository with 50 files
    When I run "gitctx index"
    Then the output should show token count
    And the output should show estimated cost
    And the final cost should be displayed

  Scenario: Resume interrupted indexing
    Given a partially indexed repository
    When I run "gitctx index"
    Then only new files should be processed
    And existing embeddings should be preserved
```

## Technical Design

### File Scanner

```python
# src/gitctx/core/scanner.py
from pathlib import Path
from gitignore_parser import parse_gitignore

class FileScanner:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.gitignore = self._load_gitignore()
    
    def scan(self) -> List[Path]:
        """Scan repository for indexable files."""
        files = []
        for path in self.repo_path.rglob("*"):
            if self._should_index(path):
                files.append(path)
        return files
    
    def _should_index(self, path: Path) -> bool:
        # Check gitignore
        # Check if binary
        # Check file size
        return True
```

### Chunker

```python
# src/gitctx/core/chunker.py
import tiktoken

class Chunker:
    def __init__(self, max_tokens: int = 800, overlap: int = 100):
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.encoder = tiktoken.encoding_for_model("gpt-4")
    
    def chunk_file(self, content: str, file_path: Path) -> List[Chunk]:
        """Split file into overlapping chunks."""
        chunks = []
        lines = content.split('\n')
        # Implement smart chunking with overlap
        return chunks
```

### Embedding Generator

```python
# src/gitctx/core/embedder.py
from langchain.embeddings import OpenAIEmbeddings

class Embedder:
    def __init__(self, api_key: str):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=api_key
        )
        self.cost_tracker = CostTracker()
    
    async def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Generate embeddings with batching and cost tracking."""
        # Batch requests
        # Track costs
        # Handle rate limits
        return embeddings
```

### Safetensors Storage

```python
# src/gitctx/storage/safetensors_cache.py
from safetensors.numpy import save_file, load_file
import numpy as np

class EmbeddingCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.vectors_dir = cache_dir / "vectors"
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
    
    def store(self, blob_hash: str, embeddings: List[np.ndarray]):
        """Store embeddings in safetensors format."""
        embeddings_dict = {
            f"chunk_{i}": emb 
            for i, emb in enumerate(embeddings)
        }
        metadata = {
            "model": "text-embedding-3-large",
            "dimensions": "3072",
            "blob_hash": blob_hash,
            "chunks": str(len(embeddings))
        }
        save_file(
            embeddings_dict,
            self.vectors_dir / f"{blob_hash}.safetensors",
            metadata=metadata
        )
```

## Dependencies

- `tiktoken` - Token counting for chunks
- `gitignore-parser` - Parse .gitignore rules
- `langchain` - OpenAI integration
- `safetensors` - Binary embedding storage
- `numpy` - Array manipulation

## Success Criteria

1. **Accurate file scanning** - Respects .gitignore, skips binaries
2. **Smart chunking** - Respects token limits with overlap
3. **Reliable embedding generation** - Handles errors, tracks costs
4. **Efficient storage** - 5x smaller than JSON
5. **Resume capability** - Can continue after interruption

## Performance Targets

- Index 100 files in <60 seconds
- Storage <0.2x of source code size
- Memory usage <500MB during indexing
- Cost <$0.001 per file average

## Notes

- This epic makes indexing real and functional
- Focus on reliability over speed initially
- Cost tracking is critical for user trust
- Incremental indexing sets foundation for future features

---

**Created**: 2025-09-28  
**Last Updated**: 2025-09-28
