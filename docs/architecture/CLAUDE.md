# CLAUDE.md - Architecture Documentation Guidelines for docs/architecture/

This document defines standards for technical architecture documentation in gitctx.

## 🚨 Architecture Philosophy

**Document decisions, not just designs.**

Architecture documentation should:

1. Capture the "why" behind technical decisions
2. Provide clear system understanding
3. Enable future maintainers
4. Record decision history

## Directory Structure

```bash
docs/architecture/
├── CLAUDE.md           # This file - architecture guidelines
├── decisions/          # Architecture Decision Records (ADRs)
│   ├── ADR-001-vector-database-selection.md
│   └── ADR-002-embedding-model-choice.md
└── diagrams/          # System diagrams
    ├── system-overview.md
    └── data-flow.md
```

## Architecture Decision Records (ADRs)

### ADR Template

```markdown
# ADR-NNN: [Decision Title]

**Date**: 2025-01-15
**Status**: Accepted | Proposed | Deprecated | Superseded
**Deciders**: [List of people]

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision Drivers
- Driver 1 (e.g., performance requirements)
- Driver 2 (e.g., cost constraints)
- Driver 3 (e.g., team expertise)

## Considered Options
1. Option A
2. Option B
3. Option C

## Decision Outcome
Chosen option: "Option B", because [justification]

### Positive Consequences
- Good thing 1
- Good thing 2

### Negative Consequences
- Trade-off 1
- Trade-off 2

## Pros and Cons of the Options

### Option A: [Name]
- ✅ Good, because [reason]
- ✅ Good, because [reason]
- ❌ Bad, because [reason]

### Option B: [Name]
- ✅ Good, because [reason]
- ❌ Bad, because [reason]

## Links
- [Related ADR](ADR-NNN.md)
- [Epic that required this](../tickets/initiatives/INIT-NNNN/epics/EPIC-NNNN.N.md)
```

### ADR Best Practices

1. **Immutable**: Once accepted, never modify - supersede instead
2. **Numbered**: Sequential numbering (ADR-001, ADR-002)
3. **Linked**: Reference related ADRs and tickets
4. **Concise**: One decision per ADR
5. **Timely**: Write when decision is made, not later

### ADR Status Flow

```bash
Proposed → Accepted → Superseded by ADR-NNN
    ↓                      ↓
Rejected              Deprecated
```

## System Diagrams

### Diagram Types

#### 1. System Overview

High-level architecture showing major components:

```markdown
# System Overview

## Components
​```mermaid
graph TB
    CLI[CLI Interface]
    Scanner[File Scanner]
    Chunker[Text Chunker]
    Embedder[Embedder]
    VectorDB[Vector DB]
    Search[Search Engine]
    
    CLI --> Scanner
    Scanner --> Chunker
    Chunker --> Embedder
    Embedder --> VectorDB
    CLI --> Search
    Search --> VectorDB
​```

## Component Descriptions
- **CLI**: Typer-based command interface
- **Scanner**: Git-aware file discovery
- **Chunker**: Token-aware text splitting
...
```

#### 2. Data Flow Diagrams

Show how data moves through the system:

```markdown
# Indexing Data Flow

​```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Scanner
    participant Chunker
    participant Embedder
    participant Storage
    
    User->>CLI: gitctx index
    CLI->>Scanner: Scan repository
    Scanner->>CLI: File list
    loop For each file
        CLI->>Chunker: Split file
        Chunker->>CLI: Chunks
        CLI->>Embedder: Generate embeddings
        Embedder->>CLI: Vectors
        CLI->>Storage: Store vectors
    end
    CLI->>User: Index complete
​```
```

#### 3. Component Diagrams

Detail internal structure:

```markdown
# Search Component Architecture

​```mermaid
classDiagram
    class SearchEngine {
        +search(query: str)
        +rerank(results: List)
        -generate_embedding(text: str)
    }
    
    class VectorStore {
        +query(vector: List)
        +add(vector: List)
        -index: Index
    }
    
    class Reranker {
        +score(query: str, result: str)
        -llm: LLM
    }
    
    SearchEngine --> VectorStore
    SearchEngine --> Reranker
​```
```

### Diagram Standards

1. **Tool**: Use Mermaid for all diagrams (renders in GitHub/GitLab)
2. **Scope**: One concept per diagram
3. **Labels**: Clear, descriptive labels
4. **Direction**: Top-to-bottom or left-to-right flow
5. **Legend**: Include legend for symbols if needed

## Technical Design Documents

### Design Document Template

```markdown
# [Component] Design

## Overview
[One paragraph summary]

## Requirements
- Functional requirement 1
- Non-functional requirement 1
- Constraint 1

## Design

### Architecture
[High-level architecture]

### API Design
​```python
class ComponentName:
    def method_one(self, param: Type) -> ReturnType:
        """Method description."""
        pass
​```

### Data Model
​```python
@dataclass
class DataStructure:
    field1: Type
    field2: Type
​```

## Implementation Plan
1. Phase 1: [Description]
2. Phase 2: [Description]

## Testing Strategy
- Unit tests: [Approach]
- Integration tests: [Approach]
- Performance tests: [Approach]

## Security Considerations
- Consideration 1
- Consideration 2

## Performance Considerations
- Metric: Target
- Optimization: Approach
```

## API Documentation

### API Documentation Standards

```markdown
# API Reference

## Module: gitctx.search

### Class: SearchEngine

​```python
class SearchEngine:
    """
    Vector-based search engine for code repositories.
    
    Attributes:
        vector_store: Vector database connection
        embedder: Embedding generator
        reranker: Optional result reranker
    """
    
    def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for relevant code chunks.
        
        Args:
            query: Search query text
            limit: Maximum results to return
            threshold: Minimum relevance score
            
        Returns:
            List of SearchResult objects, ranked by relevance
            
        Raises:
            SearchError: If search fails
            ValueError: If invalid parameters
            
        Example:
            >>> engine = SearchEngine()
            >>> results = engine.search("authentication", limit=5)
            >>> for result in results:
            ...     print(f"{result.file}:{result.line}")
        """
​```
```

### API Documentation Rules

1. **Docstrings**: Every public class/method
2. **Type Hints**: All parameters and returns
3. **Examples**: Include usage examples
4. **Exceptions**: Document all exceptions
5. **Threading**: Note thread safety

## Technology Stack Documentation

### Stack Overview

```markdown
# Technology Stack

## Core Technologies

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Language | Python | 3.11+ | Async, types, performance |
| CLI | Typer | 0.9+ | Modern, type-safe |
| Embeddings | OpenAI | latest | Best quality |
| Vector DB | LanceDB | 0.5+ | Embedded, fast |
| Storage | Safetensors | latest | 5x compression |

## Dependencies

### Production
- typer[all]: CLI framework
- openai: Embedding generation
- lancedb: Vector storage
- safetensors: Embedding storage

### Development
- pytest: Testing framework
- mypy: Type checking
- ruff: Linting and formatting
```

## Performance Documentation

### Performance Requirements

```markdown
# Performance Requirements

## Targets

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Search latency | <2s | 1.8s | ✅ |
| Index speed | >100 files/min | 120 | ✅ |
| Memory usage | <500MB | 450MB | ✅ |
| Startup time | <100ms | 95ms | ✅ |

## Benchmarks

### Search Performance
​```python
@pytest.mark.benchmark
def test_search_performance(benchmark):
    engine = SearchEngine()
    result = benchmark(engine.search, "query")
    assert benchmark.stats['mean'] < 2.0
​```

## Optimization Strategies
1. Caching frequent queries
2. Batch embedding generation
3. Index optimization
```

## Security Documentation

### Security Considerations

```markdown
# Security

## API Key Management
- Never commit keys
- Use environment variables
- Mask in logs and output

## Data Privacy
- No telemetry without consent
- Local storage only
- Respect .gitignore

## Input Validation
- Sanitize file paths
- Validate query length
- Prevent injection
```

## Deployment Documentation

### Deployment Architecture

```markdown
# Deployment

## Distribution
- PyPI package via pipx
- No direct pip install
- Isolated environment

## Configuration
- ~/.gitctx/config.yml
- Environment variables
- No system-wide config

## Updates
- Semantic versioning
- Backward compatibility
- Migration scripts
```

## Documentation Standards

### Writing Technical Documentation

1. **Audience**: Assume technical reader
2. **Completeness**: Self-contained documents
3. **Examples**: Include code examples
4. **Diagrams**: Visual when helpful
5. **Updates**: Keep synchronized with code

### Documentation Review

Before committing architecture docs:

- [ ] Follows templates
- [ ] Includes diagrams where helpful
- [ ] Has code examples
- [ ] Links to related documents
- [ ] Technically accurate

## Resources

- [ADR GitHub](https://adr.github.io/)
- [C4 Model](https://c4model.com/)
- [Mermaid Diagrams](https://mermaid-js.github.io/)
- [System Design Primer](https://github.com/donnemartin/system-design-primer)
