# EPIC-0001.1: CLI Foundation

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: ✅ Complete
**Estimated**: 10 story points
**Progress**: ██████████ 100% (10/10 story points - all stories complete)

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
| [STORY-0001.1.2](STORY-0001.1.2/README.md) | Real Configuration Management | ✅ Complete | 5 |

**Note**: STORY-0001.1.1 implemented all CLI commands with mock/in-memory configuration. STORY-0001.1.2 replaces the mock config with real Pydantic Settings-based persistent configuration.

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

**STORY-0001.1.1**: Mock implementation (in-memory dict)
```python
# src/gitctx/cli/config.py (mock)
_config_store: dict[str, Any] = {}  # In-memory for testing
```

**STORY-0001.1.2**: Real implementation (Pydantic Settings)
```python
# src/gitctx/core/config.py
from pydantic_settings import BaseSettings

class GitCtxSettings(BaseSettings):
    """Type-safe configuration with multi-source loading.

    Precedence: OPENAI_API_KEY > GITCTX_* env vars > YAML > defaults
    """
    api_keys: ApiKeys
    search: SearchSettings
    index: IndexSettings
    model: ModelSettings

    model_config = SettingsConfigDict(
        yaml_file="~/.gitctx/config.yml",
        env_prefix="GITCTX_",
    )
```

## Dependencies

- `typer[all]` - CLI framework with completion
- `rich` - Terminal formatting and progress bars
- `pyyaml` - Configuration file management
- `pydantic>=2.11.0` - Type validation (STORY-0001.1.2)
- `pydantic-settings[yaml]>=2.11.0` - Config management (STORY-0001.1.2)

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

**STORY-0001.1.2: Real Configuration Management** (5 points) - **Complete**
- ✅ Pydantic Settings-based configuration
- ✅ Three-tier precedence: `OPENAI_API_KEY` > `GITCTX_*` > YAML
- ✅ Type validation and SecretStr masking
- ✅ Persistent storage at `~/.gitctx/config.yml`
- ✅ Source indicators in output
- ✅ Backward compatible with STORY-0001.1.1 CLI interface
- ✅ 19 BDD scenarios passing, 94.55% coverage
- ✅ Windows CI integration complete

**Total Progress**: 10/10 points complete (100%) - All stories complete

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-05
