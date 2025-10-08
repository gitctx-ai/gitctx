# EPIC-0001.2: Real Indexing Implementation

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🟡 In Progress
**Estimated**: 26 story points
**Progress**: ████████░░ 85% (22/26 story points complete)

## Overview

Replace the mock indexing from EPIC-0001.1 with actual functionality that scans files, chunks text, generates embeddings via OpenAI, and stores them using safetensors binary format.

## Goals

- Walk commit graph and extract blobs from commit trees
- Deduplicate blobs by SHA (same content indexed once)
- Track blob → commit relationships for result attribution
- Chunk blob content intelligently for embedding
- Generate embeddings via OpenAI text-embedding-3-large
- Store embeddings with blob_sha as primary key (safetensors)
- Track costs and provide accurate progress

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-0001.2.1](STORY-0001.2.1/README.md) | Commit Graph Walker with Blob Deduplication | ✅ Complete | 10 |
| [STORY-0001.2.2](STORY-0001.2.2/README.md) | Blob Content Chunking | ✅ Complete | 5 |
| [STORY-0001.2.3](STORY-0001.2.3/README.md) | OpenAI Embedding Generation | 🔵 Not Started | 5 |
| [STORY-0001.2.4](STORY-0001.2.4/README.md) | LanceDB Denormalized Storage | 🔵 Not Started | 3 |
| [STORY-0001.2.5](STORY-0001.2.5/README.md) | Progress Tracking and Cost Estimation | 🔵 Not Started | 3 |

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
    Given a repository with 10 commits
    And 5 unique blobs across those commits
    When I run "gitctx index"
    Then the output should show "Indexed 10 commits (5 unique blobs)"
    And 5 .safetensors files should be created in .gitctx/blobs/
    And metadata should track blob→commit relationships

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

### Commit Walker

```python
# src/gitctx/core/commit_walker.py
from pathlib import Path
from typing import Set, Dict, List, Iterator, Tuple
from dataclasses import dataclass, asdict
import pygit2

@dataclass
class CommitRef:
    """Reference to a commit containing a blob."""
    commit_sha: str
    path: str
    author: str
    date: int
    message: str
    is_head: bool

@dataclass
class Blob:
    """Git blob with content."""
    sha: str
    content: bytes

class CommitWalker:
    """Walk commit graph extracting unique blobs with deduplication."""

    def __init__(self, repo_path: Path):
        self.repo = pygit2.Repository(repo_path)
        self.seen_blobs: Set[str] = set()
        self.blob_commits: Dict[str, List[CommitRef]] = {}

    def walk(self) -> Iterator[Blob]:
        """Walk commits, yield unique blobs, track all commit refs."""
        for commit in self.repo.walk(self.repo.head.target):
            for blob_sha, path in self._extract_blobs(commit.tree):
                # Track this commit reference
                if blob_sha not in self.blob_commits:
                    self.blob_commits[blob_sha] = []

                self.blob_commits[blob_sha].append(CommitRef(
                    commit_sha=commit.hex,
                    path=path,
                    author=commit.author.name,
                    date=commit.commit_time,
                    message=commit.message,
                    is_head=(commit.hex == self.repo.head.target.hex)
                ))

                # Yield blob content if first occurrence
                if blob_sha not in self.seen_blobs:
                    blob = self.repo[blob_sha]
                    yield Blob(sha=blob_sha, content=blob.data)
                    self.seen_blobs.add(blob_sha)

    def _extract_blobs(self, tree) -> Iterator[Tuple[str, str]]:
        """Recursively extract (blob_sha, path) from tree."""
        # Walk tree recursively
        # Yield (blob.hex, path) for each blob
        # Skip binary files, respect size limits
        pass
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

### Blob Store

```python
# src/gitctx/storage/blob_store.py
from safetensors.numpy import save_file, load_file
import numpy as np
import json
from pathlib import Path
from typing import List

class BlobStore:
    """Store embeddings and metadata for git blobs."""

    def __init__(self, cache_dir: Path):
        self.blobs_dir = cache_dir / "blobs"
        self.metadata_dir = cache_dir / "metadata"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def store_blob(
        self,
        blob_sha: str,
        embeddings: List[np.ndarray],
        commit_refs: List[CommitRef]
    ):
        """Store blob embeddings and commit metadata."""
        # Store embeddings
        embeddings_dict = {
            f"chunk_{i}": emb
            for i, emb in enumerate(embeddings)
        }
        metadata = {
            "model": "text-embedding-3-large",
            "dimensions": "3072",
            "blob_sha": blob_sha,
            "chunks": str(len(embeddings))
        }
        save_file(
            embeddings_dict,
            self.blobs_dir / f"{blob_sha}.safetensors",
            metadata=metadata
        )

        # Store commit references
        refs_data = {
            "blob_sha": blob_sha,
            "occurrences": [asdict(ref) for ref in commit_refs]
        }
        (self.metadata_dir / f"{blob_sha}.json").write_text(
            json.dumps(refs_data, indent=2)
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

- Index 100 commits in <60 seconds
- Deduplication: Skip 70%+ of blobs (typical unchanged rate)
- Storage <0.05x of source code size (5% due to deduplication)
- Memory usage <500MB during indexing
- Cost <$0.0001 per unique blob average

## Architectural Constraint: Committed Files Only

**Decision**: gitctx indexes ONLY committed files, never working directory changes.

**Rationale**:
- Temporal context: Every result traceable to exact commit with metadata
- Reproducibility: Search results are stable, tied to git history
- Collaboration: Team sees same results for same commits
- Simplicity: No tracking of uncommitted changes

**Implementation**:
- Index HEAD commit + full git history
- Working directory changes are invisible to gitctx
- Users must commit before indexing new/changed files

**User Impact**:
- **Workflow change**: "Commit to search" (not "save to search")
- **Benefit**: Results include who/when/why context from commit metadata
- **Trade-off**: Must commit more frequently during development

## Architecture: Blob-Centric Indexing

**gitctx indexes git blobs, not "files".**

Git stores content as **blobs** (content-addressed by SHA-256). Same blob SHA across commits = identical content.

**Key principle:** Index each unique blob once, track all commits containing it.

**Example deduplication:**
- 10,000 commits × 1,000 files = 10M "file instances"
- 70% unchanged = 3,000 unique blobs
- **Index 3,000 blobs (not 10M), save 3,333x cost**

See implementation in STORY-0001.2.1 (Commit Graph Walker).

## Notes

- This epic makes indexing real and functional
- Focus on reliability over speed initially
- Cost tracking is critical for user trust
- Incremental indexing sets foundation for future features

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-03
