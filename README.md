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

# Search for relevant code
gitctx search "authentication logic"
```

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

- 🔵 CLI Foundation (not started)
- 🔵 Real Indexing (not started)
- 🔵 Vector Search (not started)

See [initiatives](docs/tickets/initiatives/) for detailed progress.

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

## License

MIT

---
