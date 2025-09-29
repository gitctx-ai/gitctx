# gitctx Product Roadmap

## Executive Vision

### Problem Statement

Developers and AI coding agents fail to complete tasks effectively due to lack of project-specific context. Current tools either provide raw file search (grep/ag/rg) or simple semantic search without understanding the complete context needed for coding tasks.

### Solution

Build a focused, OpenAI-based context optimization engine with a git-like CLI interface. Use BDD/TDD to ensure quality from day one, with pytest-benchmark and LangSmith tracking metrics during development.

### Product Vision

**gitctx**: The intelligent context engine that understands your codebase like a senior developer, providing precisely the right context for any coding task.

### Success Metrics

See [success-metrics.md](success-metrics.md) for detailed KPIs and tracking.

## Development Philosophy

**Build the CLI first. Test everything. Ship working software continuously.**

1. **CLI-First Development**: Users can run commands immediately, even with mocked backends
2. **BDD for User Behavior**: Gherkin specifications define all user-facing features
3. **TDD for Implementation**: Unit tests written before code
4. **Continuous Evaluation**: Quality metrics integrated into test suite, not user commands

## Strategic Initiatives

### 🚀 Initiative 1: MVP Foundation

**Timeline**: Q4 2025 | **Status**: 📝 Planning

Build the core functionality users need to search their codebase intelligently.

**Details**: [INIT-0001](../tickets/initiatives/INIT-0001/)

**Epics**:

- EPIC-0001.1: CLI Foundation - 🔵 Not Started
- EPIC-0001.2: Real Indexing - 🔵 Not Started  
- EPIC-0001.3: Vector Search - 🔵 Not Started

**Key Deliverables:**

- ⬜ Complete CLI with all commands
- ⬜ OpenAI embedding generation
- ⬜ LanceDB vector search
- ⬜ Basic context assembly

**Success Criteria:**

```bash
pipx install gitctx
gitctx index
gitctx search "authentication"
# Returns relevant results in <2 seconds
```

### 🧠 Initiative 2: Intelligence Layer

**Timeline**: Q1 2026 | **Status**: 🔵 Not Started

Enhance search with AI-powered context optimization and intelligent reranking.

**Details**: [INIT-0002](../tickets/initiatives/INIT-0002/)

**Epics**:

- EPIC-0002.1: Context Assembly - 🔵 Not Started
- EPIC-0002.2: Performance Optimization - 🔵 Not Started
- EPIC-0002.3: Evaluation Framework - 🔵 Not Started

**Key Deliverables:**

- ⬜ Multi-source context aggregation
- ⬜ GPT-5-Codex reranking
- ⬜ Token budget management
- ⬜ Automated quality metrics with canonical test queries

### 📦 Initiative 3: Production Release

**Timeline**: Q2 2026 | **Status**: 🔵 Not Started

Harden the system for production use and public release.

**Details**: [INIT-0003](../tickets/initiatives/INIT-0003/)

**Epics**:

- EPIC-0003.1: Production Readiness - 🔵 Not Started
- EPIC-0003.2: Documentation & Onboarding - 🔵 Not Started
- EPIC-0003.3: Community Launch - 🔵 Not Started

**Key Deliverables:**

- ⬜ PyPI package publication
- ⬜ Comprehensive documentation
- ⬜ Community engagement plan
- ⬜ Support channels

### 🚀 Initiative 4: Advanced Features

**Timeline**: Q3 2026 | **Status**: 🔵 Not Started

Expand capabilities with multi-model support and enterprise features.

**Details**: [INIT-0004](../tickets/initiatives/INIT-0004/)

**Epics**:

- EPIC-0004.1: Multi-model Support - 🔵 Not Started
- EPIC-0004.2: Enterprise Features - 🔵 Not Started
- EPIC-0004.3: Plugin System - 🔵 Not Started

**Key Deliverables:**

- ⬜ Support for Anthropic, Google models
- ⬜ Team collaboration features
- ⬜ Plugin architecture
- ⬜ Custom embeddings

## Core Commands

The user-facing interface that drives all interactions:

```bash
gitctx index                     # Index the repository
gitctx search "query"            # Search with context assembly
gitctx config set key value      # Manage configuration
gitctx clear                     # Clear cache and embeddings
```

## Development Methodology

See [BDD/TDD Workflow](../../CLAUDE.md#the-development-cycle) in the root CLAUDE.md for the mandatory development process.

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Async, type hints, performance |
| CLI | Typer + Rich | Git-like interface |
| Testing | pytest, pytest-bdd, pytest-benchmark | Comprehensive testing |
| LLM | Langchain/LangGraph/LangSmith | Abstraction and observability |
| Embeddings | OpenAI text-embedding-3-large | Best quality for baseline |
| Storage | Safetensors | 5x smaller than JSON |
| Vector DB | LanceDB | SQL capabilities, embedded |
| Models | GPT-5-Codex | Code-optimized |

### Core Design Principles

1. **Future Rust Optimization Support via Protocol-Based Design**
2. **OpenAI Only, But Use Langchain/LangGraph/LangSmith Everywhere**
3. **LanceDB for Storage Universally**
4. **Embeddings Persist to Repo, Database Does Not**
5. **Git-Inspired Text User Interface Design**
6. **Optimize for Context Quality, Not Search Results**
7. **Language-Agnostic by Design**

## Distribution Strategy

**gitctx will be distributed exclusively via pipx for isolated installation:**

```bash
pipx install gitctx
```

This ensures:

- Clean isolation from system Python packages
- No dependency conflicts with user projects
- Easy uninstallation with `pipx uninstall gitctx`
- Automatic virtual environment management

**Note**: Direct `pip install` is not supported. The package will be published to PyPI but designed for pipx installation only.

## Quality Standards

See [success-metrics.md](success-metrics.md) for quality gates and performance targets.

## Version Planning

### v0.1.0 - MVP (Q4 2025)

- Basic indexing and search
- CLI foundation complete
- pipx installation working

### v0.2.0 - Intelligence (Q1 2026)

- Context assembly
- GPT-5-Codex reranking
- Performance optimizations

### v1.0.0 - Production (Q2 2026)

- Full test coverage
- Comprehensive documentation
- Community launch

### v2.0.0 - Advanced (Q3 2026)

- Multi-model support
- Plugin system
- Enterprise features

## Next Steps

1. ✅ Review initiative details in [tickets/initiatives/](../tickets/initiatives/)
2. 📊 Track progress in [success-metrics.md](success-metrics.md)
3. 🧪 Follow [BDD/TDD workflow](../../CLAUDE.md#the-development-cycle)

---

**Last Updated**: 2025-09-28  
**Status**: Planning Phase
