# STORY-0001.1.1: CLI Framework Setup

**Parent Epic**: [EPIC-0001.1](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 3
**Progress**: ██████░░░░ 60%

## User Story

As a **developer**
I want **all gitctx commands available with mocked implementations**
So that **I can immediately test the interface and provide feedback before backend implementation**

## Acceptance Criteria

- [ ] Core commands (`index`, `search`, `config`, `clear`) are executable with mocked implementations
- [ ] Each command has comprehensive help text with examples
- [ ] Commands implement three output modes: Default (terse), Verbose (detailed), Quiet (silent)
- [ ] Default output matches TUI_GUIDE.md: git-like terse format (no panels/progress bars)
- [ ] Mock implementations demonstrate git history + HEAD behavior (search)
- [ ] Config command manages settings with in-memory storage (testing isolation)
- [ ] Error messages are clear, actionable, and include exit codes
- [ ] Invalid commands show helpful suggestions
- [ ] Missing arguments show usage instructions
- [ ] All BDD scenarios for CLI commands pass
- [ ] Platform-aware symbol rendering (Unicode for modern terminals, ASCII fallback for Windows cmd.exe)

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.1.1.1](TASK-0001.1.1.1.md) | Implement Index Command | ✅ Complete | 1 |
| [TASK-0001.1.1.2](TASK-0001.1.1.2.md) | Implement Search Command | ✅ Complete | 1 |
| [TASK-0001.1.1.3](TASK-0001.1.1.3.md) | Implement Config Command Structure | ✅ Complete | 2 |
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
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Each command module registers itself explicitly
from gitctx.cli import index, search, config, clear

index.register(app)
search.register(app)
config.register(app)
clear.register(app)
```

### Command Modules

Each command lives in its own module with a `register()` function for explicit registration:

```python
# src/gitctx/cli/index.py
import typer
from rich.console import Console

console = Console()

def register(app: typer.Typer) -> None:
    """Register the index command with the app."""
    app.command(name="index")(index_command)

def index_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reindexing"),
) -> None:
    """Index the repository for searching."""
    # Mock implementation - see TUI_GUIDE.md for output formats
```

**Why `register()` pattern?**
- **No circular imports** - Commands don't import `app` from main
- **Better testability** - Commands can be tested without full app initialization
- **Explicit control** - Clear registration flow in main.py
- **Dependency injection** - App passed in, not imported globally

### Mock Implementation Guidelines

Mock implementations MUST follow TUI_GUIDE.md output specifications:

**Default Mode (Terse)**:
```python
# Single-line output, git-like style
console.print("Indexed 5678 commits (1234 unique blobs) in 8.2s")
```

**Verbose Mode (Detailed)**:
```python
# Multi-line with detailed progress
console.print("→ Walking commit graph")
console.print("  Found 5678 commits")
console.print()
console.print("→ Extracting blobs")
console.print("  Total blob references: 4567")
console.print("  Unique blobs: 1234")
# etc...
```

**Quiet Mode (Silent)**:
```python
# No output on success, only errors
if not quiet:
    console.print(output)
```

**Key Principles**:
- Use `console.print()` directly, not Rich Panels or Tables
- Default = terse (one line)
- Verbose = multi-line with details
- Quiet = silent success
- Platform-aware symbols via Rich's automatic detection

## Dependencies

- `typer[all]` - Already installed
- `rich` - Already installed
- No new dependencies needed

## Success Metrics

- **Command Discovery**: Users can explore all commands via `--help`
- **Response Time**: All mock commands respond in <50ms
- **Error Clarity**: 100% of errors provide actionable next steps with correct exit codes
- **Output Compliance**: All output matches TUI_GUIDE.md specifications
- **Test Coverage**: Maintain >85% coverage
- **BDD Scenarios**: 10+ scenarios passing (up from 2)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mock outputs don't match TUI_GUIDE.md specs | Strict acceptance criteria requiring TUI_GUIDE.md compliance |
| Mock responses set wrong expectations | Demonstrate both git history and HEAD results in search mocks |
| Command interface changes after backend impl | BDD tests lock in the interface contract |
| Overly complex mocks slow development | Use simple console.print(), avoid Rich panels/tables |

## Notes

- This story establishes the complete CLI interface contract per TUI_GUIDE.md
- Mock implementations MUST be terse by default (git-like single-line output)
- Verbose mode demonstrates the detailed output users will see in production
- Focus on UX patterns that will persist: terse defaults, helpful errors, platform-aware symbols
- All error messages should be finalized here with proper exit codes
- Config command uses in-memory storage for testing isolation (no file I/O)

## Mock Behavior Boundaries

**What mocks SHOULD validate:**
- Git repository exists (check for `.git` directory)
- Required arguments are provided
- Flag combinations are valid

**What mocks SHOULD fake:**
- Actual git operations (commit walking, blob extraction)
- Embedding generation
- File I/O (no `.gitctx` directory creation)
- Network calls (no OpenAI API)

**Configuration storage:**
- Use in-memory dict, not actual YAML file
- This ensures test isolation and no side effects

## Git History Indexing - Technical Notes

### Core Design: Blob-Centric Indexing

**All content comes from git blobs** (content-addressed by SHA).

**Critical insight:** We index **blobs** (git's content storage), not "files".

**Deduplication:**
- Same blob SHA across commits = identical content = index ONCE
- Different blob SHA = different content = index separately
- Typical repos: 70% of files unchanged between commits
- Typical savings: 10-100x reduction in indexing cost

**Example:**
- Repository: 10,000 commits × 1,000 files = 10M "file instances"
- Unchanged rate: 70% → 3,000 unique blobs
- **Index 3,000 blobs (not 10M files) = 3,333x cost savings**

**Storage structure:**
```
.gitctx/
  blobs/
    abc123.safetensors      # Embeddings for blob abc123
  metadata/
    abc123.json             # All commits containing blob abc123
```

**Result Format** - ALL results show commit metadata:

Modern terminals:
```
src/auth.py:45:0.92 ● f9e8d7c (HEAD, 2025-10-02, Alice) "Add OAuth"
src/old.py:12:0.87   a1b2c3d (2024-09-15, Bob) "Add middleware"
```

Legacy Windows cmd.exe:
```
src/auth.py:45:0.92 [HEAD] f9e8d7c (2025-10-02, Alice) "Add OAuth"
src/old.py:12:0.87         a1b2c3d (2024-09-15, Bob) "Add middleware"
```

**HEAD Indicator**:
- Symbol: `●` (modern) or `[HEAD]` (legacy Windows)
- Shows which results are from current branch HEAD vs historical commits

**Implementation Notes**:
- Index entire git history as graph structure
- Each result includes: commit SHA, date, author, message
- Temporal search: "who wrote authentication logic" across all history
- See [TUI_GUIDE.md](../../../../TUI_GUIDE.md#result-attribution) for complete visual design

---

**Created**: 2025-10-01
**Last Updated**: 2025-10-03
