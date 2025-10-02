# STORY-0001.1.1: CLI Framework Setup

**Parent Epic**: [EPIC-0001.1](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 3
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a **developer**
I want **all gitctx commands available with mocked implementations**
So that **I can immediately test the interface and provide feedback before backend implementation**

## Acceptance Criteria

- [ ] All core commands (`index`, `search`, `config`, `clear`) are executable
- [ ] Each command has comprehensive help text with examples
- [ ] Commands provide mock responses demonstrating expected behavior
- [ ] Error messages are clear and actionable
- [ ] Output uses Rich formatting for better terminal UX
- [ ] Invalid commands show helpful suggestions
- [ ] Missing arguments show usage instructions
- [ ] All BDD scenarios for CLI commands pass

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.1.1.1](TASK-0001.1.1.1.md) | Implement Index Command | 🔵 Not Started | 1 |
| [TASK-0001.1.1.2](TASK-0001.1.1.2.md) | Implement Search Command | 🔵 Not Started | 1 |
| [TASK-0001.1.1.3](TASK-0001.1.1.3.md) | Implement Config Command Structure | 🔵 Not Started | 2 |
| [TASK-0001.1.1.4](TASK-0001.1.1.4.md) | Implement Clear Command | 🔵 Not Started | 1 |
| [TASK-0001.1.1.5](TASK-0001.1.1.5.md) | Add Error Handling & Validation | 🔵 Not Started | 2 |

## BDD Specifications

See [tests/e2e/features/cli.feature](../../../../tests/e2e/features/cli.feature) for the BDD scenarios this story will enable.

Currently commented scenarios to enable:

- Index command help
- Search command help
- Clear command help
- Configure API key
- Display configuration
- Environment variable override
- Invalid command
- Missing required arguments

## Technical Design

### Command Architecture

```python
# src/gitctx/cli/main.py
app = typer.Typer(
    name="gitctx",
    help="Context optimization engine for coding workflows",
    add_completion=False,
    rich_markup_mode="rich",  # Enable Rich formatting
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Each command module registers itself
from gitctx.cli import index, search, config, clear

index.register(app)
search.register(app)
config.register(app)
clear.register(app)
```

### Command Modules

Each command lives in its own module with a `register()` function:

```python
# src/gitctx/cli/index.py
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def register(app: typer.Typer) -> None:
    """Register the index command."""
    app.command()(index_command)

def index_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reindexing"),
) -> None:
    """Index the repository for searching."""
    # Mock implementation
```

### Mock Implementations

Mock implementations should demonstrate the expected UX:

```python
# Index command mock
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console,
) as progress:
    task = progress.add_task("Indexing repository...", total=100)
    # Simulate work
    progress.update(task, completed=100)

console.print("[green]✓[/green] Repository indexed successfully")
console.print("  Files: 1,234")
console.print("  Chunks: 5,678")
console.print("  Embeddings: 5,678")
```

## Dependencies

- `typer[all]` - Already installed
- `rich` - Already installed
- No new dependencies needed

## Success Metrics

- **Command Discovery**: Users can explore all commands via `--help`
- **Response Time**: All mock commands respond in <50ms
- **Error Clarity**: 100% of errors provide actionable next steps
- **Test Coverage**: Maintain >85% coverage
- **BDD Scenarios**: 14+ scenarios passing (up from 2)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mock responses set wrong expectations | Clear "mock" indicators in output |
| Command interface changes after backend impl | BDD tests lock in the interface contract |
| Users confused by non-functional commands | Help text clearly states "mock implementation" |

## Notes

- This story establishes the complete CLI interface contract
- Mock implementations allow immediate user testing
- Focus on UX patterns that will persist through development
- All error messages and help text should be finalized here
- Rich formatting should make the CLI feel polished even with mocks

---

**Created**: 2025-10-01
**Last Updated**: 2025-10-01
