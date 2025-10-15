# gitctx

[![CI](https://github.com/gitctx-ai/gitctx/actions/workflows/ci.yml/badge.svg)](https://github.com/gitctx-ai/gitctx/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gitctx-ai/gitctx/branch/main/graph/badge.svg)](https://codecov.io/gh/gitctx-ai/gitctx)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-latest-green.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

git native context enhancement for agentic coding.

## What is gitctx?

gitctx provides precisely the right context for any coding task, helping developers and AI coding agents complete tasks effectively with full project-specific understanding.

## Installation

```bash
# Coming soon via pipx
pipx install gitctx
```

## Quick Start

```bash
# Configure your OpenAI API key
gitctx config set api_keys.openai "sk-..."

# Index your repository
gitctx index

# Search for relevant code (default: terse format)
gitctx search "authentication logic"
# Output: src/auth.py:45:0.92 ● f9e8d7c (2025-10-02, Alice) "Add OAuth support"

# Show code context (verbose format)
gitctx search "authentication" --verbose

# Machine-readable output for AI tools
gitctx search "authentication" --mcp
```

## Output Formats

gitctx provides three output formats optimized for different contexts:

### Terse (Default)
One-line format for quick scanning:
```bash
gitctx search "authentication logic"
# src/auth.py:45:0.92 ● f9e8d7c (2025-10-02, Alice) "Add OAuth support"
# src/middleware.py:23:0.85   a1b2c3d (2025-09-15, Bob) "JWT validation"
```

### Verbose
Multi-line format with syntax-highlighted code blocks:
```bash
gitctx search "authentication" --verbose
# Shows full code context with line numbers and commit metadata
```

### MCP (Model Context Protocol)
Structured markdown with YAML frontmatter for AI tools:
```bash
gitctx search "authentication" --mcp
# Outputs machine-readable format optimized for LLM consumption
```

## Context Engineering

gitctx is designed for **context engineering** - results are meant for AI prompts (Claude, GPT, etc.). Quality matters more than quantity.

**Semantic Similarity Filtering** (default: 0.5):
```bash
# High precision (only best matches)
gitctx search "auth" --min-similarity 0.7

# Balanced quality (default)
gitctx search "auth"

# High recall (include marginal results)
gitctx search "auth" --min-similarity 0.3
```

**Similarity Scoring:**
- 0.7-1.0: Highly relevant (excellent for AI context)
- 0.5-0.7: Moderately relevant (good context quality)
- 0.3-0.5: Vaguely related (marginal value)
- Below 0.3: Filtered by default (noise)

## Documentation

This project follows a comprehensive documentation-driven development approach:

### For Contributors

- **[CLAUDE.md](CLAUDE.md)** - Critical workflow guidance for BDD/TDD development
- **[Development Process](docs/tickets/CLAUDE.md)** - Ticket hierarchy and workflow
- **[Testing Guidelines](tests/)** - BDD scenarios and unit test patterns

### Project Organization

- **[Vision & Roadmap](docs/vision/ROADMAP.md)** - Strategic initiatives and planning
- **[Current Progress](docs/tickets/initiatives/)** - Active development tracking
- **[Architecture](docs/architecture/CLAUDE.md)** - Technical design documentation

## CLAUDE.md Hierarchy

This project uses Claude Code (claude.ai/code) and maintains CLAUDE.md files throughout the codebase as single sources of truth:

```bash
CLAUDE.md                        # Root - BDD/TDD workflow
├── tests/e2e/CLAUDE.md          # E2E testing with pytest-bdd
├── tests/unit/CLAUDE.md         # Unit testing patterns
├── docs/CLAUDE.md               # Documentation standards
├── docs/vision/CLAUDE.md        # Vision documentation
├── docs/tickets/CLAUDE.md       # Development tickets
└── docs/architecture/CLAUDE.md  # Technical standards
```

## Project Status

Currently implementing **INIT-0001: MVP Foundation** (Q4 2025)

**EPIC-0001.1: CLI Foundation** ✅ Complete (10/10 story points)
- ✅ Development Environment Setup (STORY-0001.1.0) - 5 points
- ✅ CLI Framework Setup (STORY-0001.1.1) - 3 points

**EPIC-0001.2: Real Indexing** ✅ Complete (31/31 story points)
- ✅ Commit Graph Walker (STORY-0001.2.1) - 10 points
- ✅ Blob Chunking (STORY-0001.2.2) - 5 points
- ✅ OpenAI Embeddings (STORY-0001.2.3) - 8 points
- ✅ LanceDB Vector Storage (STORY-0001.2.4) - 3 points
- ✅ Progress Tracking (STORY-0001.2.5) - 5 points

**EPIC-0001.3: Vector Search** 🟡 In Progress (10/13 story points complete)
- ✅ Query Embedding Generation (STORY-0001.3.1) - 4 points
- ✅ Vector Similarity Search (STORY-0001.3.2) - 6 points
- 🟢 Result Formatting & Output (STORY-0001.3.3) - 3 points [PR #23 pending merge]

**Next Up:**
- 🔵 EPIC-0001.4: Performance Optimization
- 🔵 EPIC-0001.5: Incremental Updates

See [ROADMAP](docs/vision/ROADMAP.md) for detailed progress.

## Development

```bash
# Install with development dependencies
uv sync --all-extras

# Run tests (BDD + TDD)
uv run pytest

# Run quality checks
uv run ruff check src tests
uv run mypy src
```

## Project Management with GitStory

This project uses [GitStory](https://github.com/gitstory-ai/gitstory), a git-native project management framework designed for AI agent-driven development. GitStory provides:

- **Hierarchical Planning** - INIT → EPIC → STORY → TASK structure in markdown
- **Perfect Traceability** - Every commit links to tasks, documentation lives in git
- **Agent-Optimized Specs** - Quality scores ensure concrete, testable requirements
- **Story-Driven Workflow** - 1 story = 1 branch = 1 PR, with BDD/TDD throughout

All development work follows structured tickets in [docs/tickets/](docs/tickets/). See [GitStory's README](https://github.com/gitstory-ai/gitstory) for the complete workflow and philosophy.

## License

MIT

---
