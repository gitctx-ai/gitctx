# EPIC-0001.1: CLI Foundation

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🟡 In Progress
**Estimated**: 8 story points
**Progress**: ████████░░ 80% (8/10 story points estimated, 2 stories remaining)

## Overview

Build the complete command-line interface with all commands working against mocked implementations. This allows immediate user testing and establishes the interface contract before implementing the backend.

## Goals

- Users can run `gitctx` commands immediately
- All commands have proper help text and error handling  
- Git-like interface patterns established
- Configuration management working
- Progress indicators and formatting in place

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-0001.1.0](STORY-0001.1.0/README.md) | Development Environment Setup | ✅ Complete | 5 |
| [STORY-0001.1.1](STORY-0001.1.1/README.md) | CLI Framework Setup | ✅ Complete | 3 |
| STORY-0001.1.2 | (TBD - Next story) | 🔵 Not Started | TBD |

**Note**: STORY-0001.1.1 included all CLI commands (index, search, config, clear) as tasks within a single story, as they are tightly coupled for the CLI interface contract.

## BDD Specifications

See [tests/e2e/features/cli.feature](../../../../tests/e2e/features/cli.feature) for the complete BDD scenarios for this epic.

## Technical Design

### Command Structure

```python
# src/gitctx/cli/main.py
import typer
from rich.console import Console

app = typer.Typer(
    name="gitctx",
    help="Context optimization engine for coding workflows",
    add_completion=False,
)
console = Console()

@app.command()
def index(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Index the repository for searching."""
    # Mock implementation
    
@app.command()
def search(
    query: str,
    limit: int = typer.Option(10, "--limit", "-n"),
):
    """Search the indexed repository."""
    # Mock implementation

@app.command()
def config():
    """Manage configuration."""
    # Sub-commands for get/set/list
    
@app.command()
def clear(
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Clear cache and embeddings."""
    # Implementation
```

### Configuration Management

```python
# src/gitctx/cli/config.py
class Config:
    def __init__(self):
        self.path = Path.home() / ".gitctx" / "config.yml"
    
    def set(self, key: str, value: str):
        """Set a config value using dot notation."""
    
    def get(self, key: str) -> str:
        """Get a config value, checking env vars first."""
    
    def list(self) -> list[str]:
        """Get all config values, checking env vars first."""
```

## Dependencies

- `typer[all]` - CLI framework with completion
- `rich` - Terminal formatting and progress bars
- `pyyaml` - Configuration file management

## Success Criteria

1. **All commands executable** - Even with mocked implementations
2. **Git-like interface** - Consistent with git patterns
3. **Rich terminal output** - Progress bars, colors, formatting
4. **Configuration working** - API keys can be set and retrieved
5. **BDD tests passing** - All Gherkin scenarios pass

## Performance Targets

- CLI startup: <100ms
- Command response: <50ms for simple commands
- Help display: <20ms

## Notes

- This epic establishes the interface contract
- Mock implementations allow immediate user testing
- Focus on UX patterns that will persist through development
- All error messages and help text should be finalized here

## Completion Status

### Completed Stories

**STORY-0001.1.0: Development Environment Setup** (5 points)
- ✅ Project structure with pyproject.toml
- ✅ BDD/TDD framework (pytest-bdd, pytest-cov)
- ✅ Code quality tools (ruff, mypy)
- ✅ Pre-commit hooks
- ✅ GitHub Actions CI/CD

**STORY-0001.1.1: CLI Framework Setup** (3 points) - **Code Review: 9.5/10 (Production-Ready)**
- ✅ All 4 commands implemented (index, search, config, clear)
- ✅ Register pattern for clean architecture
- ✅ Terse output matching TUI_GUIDE.md (98% compliance)
- ✅ Error handling with quick start guide
- ✅ 78 tests passing, 98.82% coverage
- ✅ 13 BDD scenarios enabled
- ✅ Config "unset" via blank values (cleaner than separate command)
- ✅ Zero critical/major issues found in code review

**Total Progress**: 8/10 points estimated (80%)

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-04
