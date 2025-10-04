# gitctx TUI Design Guide

**Philosophy**: Terse for humans, structured for machines (search only)
**Inspired by**: git, gh CLI, Claude Code, modern agentic tools
**Target User**: Professional developers in human/AI collaborative workflows
**Priority**: Speed, clarity, LLM-friendly search output, contextual help, temporal context

---

## Design Principles

1. **Terse by Default** - Minimal output on success, like git (experts don't need celebration)
2. **Helpful When Needed** - Tips on first-run and errors only (not intrusive)
3. **Search is LLM-First** - `--mcp` flag on search outputs structured markdown for AI consumption
4. **Professional Tone** - Assume competence, provide precision
5. **Progressive Disclosure** - Quiet → Default → Verbose (and MCP for search)

---

## Output Modes

### For Most Commands (INDEX, CONFIG, CLEAR)

**Default**: Terse, single-line success messages (git-like)
**Verbose**: Multi-line progress, detailed statistics
**Quiet**: Suppress all output except errors

### For SEARCH Command Only

**Default**: Terse human-readable results
**Verbose**: Code context previews
**MCP**: Structured markdown optimized for LLM consumption

**Why Markdown for MCP Mode:**

- Native LLM format (no parsing needed)
- Preserves syntax highlighting and code structure
- Human-readable fallback
- Richer semantic context (headers, lists, code blocks)
- Efficient token usage
- AI agents can consume search results directly in their context

---

## Visual System

### Color Palette

```
Success:  Green (ANSI 32)
Error:    Red (ANSI 31)
Warning:  Yellow (ANSI 33)
Tip:      Blue (ANSI 34)
Dim:      Gray (ANSI 90)
```

### Symbol Set

Symbols with automatic fallback for legacy Windows cmd.exe:

```
Primary (Modern Terminals)      Fallback (Legacy Windows)
✓  Success                       [OK] Success
✗  Error                         [X]  Error
⚠️  Warning                       [!]  Warning
💡 Tip                            [i]  Tip
→  Next step                     ->   Next step
●  HEAD commit                   [HEAD] Current branch HEAD
```

### Typography

- **Bold**: Commands, important values
- **Dim**: Secondary info, metadata
- **Plain**: Default text
- **No panels**: Simple text and boxes only

### Layout Rules

- Single-line output preferred (default mode)
- Multi-line for errors and verbose
- Simple boxes for tips (not elaborate panels)
- Markdown structure for MCP mode

---

## Platform Compatibility

### Supported Platforms

- **macOS**: Full Unicode support, all features work
- **Linux**: Full Unicode support, all features work
- **Windows Terminal**: Full Unicode support, emoji, all features work
- **PowerShell 7+**: Full Unicode support with Windows Terminal
- **Windows cmd.exe (legacy)**: Graceful degradation to ASCII alternatives

### Automatic Detection

gitctx uses the Python Rich library which automatically detects terminal capabilities:

**Modern terminals** (Windows Terminal, macOS Terminal, Linux terminals):
- ANSI colors (truecolor)
- Unicode box drawing characters
- Unicode symbols (✓ ✗ ⚠️ 💡 →)
- Emoji support

**Legacy Windows cmd.exe**:
- ANSI colors (8 colors on Windows 10+)
- ASCII box drawing (if TrueType font not available)
- ASCII symbol fallbacks ([OK] [X] [!] [i] ->)
- No emoji (replaced with ASCII equivalents)

### Box Drawing Characters

Tip boxes use Unicode box drawing characters with automatic fallback:

**Modern terminals:**
```
┌─ 💡 Tip ──────────────────────┐
│ This is a helpful tip message │
└────────────────────────────────┘
```

**Legacy cmd.exe fallback:**
```
+-- [i] Tip -------------------+
| This is a helpful tip message |
+-------------------------------+
```

### Font Recommendations

For best results on Windows, use TrueType fonts:
- **Recommended**: Cascadia Mono, Cascadia Code, DejaVu Sans Mono
- **Avoid**: Raster fonts, Lucida Console (limited Unicode support)

### Encoding Notes

- **Windows Terminal**: UTF-8 by default
- **cmd.exe**: May require `chcp 65001` for full UTF-8 (not recommended globally)
- **Rich library**: Handles encoding automatically with `Console.encoding`

---

## Result Attribution

**All indexed content comes from git blobs** (content-addressed by SHA).

**gitctx never indexes uncommitted changes** - you must commit before searching.

**Deduplication:** Same content appearing in multiple commits is indexed only once, then tracked across all commits containing it. This provides 10-100x cost savings.

All results show full commit metadata with HEAD indicator:

**Modern terminals:**
```
src/auth.py:45:0.92 ● f9e8d7c (HEAD, 2025-10-02, Alice) "Add OAuth support"
src/old.py:12:0.87    a1b2c3d (2024-09-15, Bob) "Add middleware auth"
```

**Legacy Windows cmd.exe:**
```
src/auth.py:45:0.92 [HEAD] f9e8d7c (2025-10-02, Alice) "Add OAuth support"
src/old.py:12:0.87          a1b2c3d (2024-09-15, Bob) "Add middleware auth"
```

- **●** or **[HEAD]** indicates result is from current branch HEAD
- Results without indicator are from historical commits

---

## Command Specifications

### INDEX Command

#### Flags

```bash
-v, --verbose       Show detailed progress
-f, --force         Force reindexing
-q, --quiet         Suppress all output except errors
    --resume        Resume interrupted indexing
```

#### Happy Path: Default

```bash
$ gitctx index
Indexed 5678 commits (1234 unique blobs) in 8.2s
```

#### Happy Path: Default (First Run - Show Tip)

```bash
$ gitctx index
Indexed 5678 commits (1234 unique blobs) in 8.2s

┌─ 💡 Tip ──────────────────────────────────────┐
│ Commit your changes before indexing - gitctx  │
│ only searches committed files, not working    │
│ directory changes.                            │
└───────────────────────────────────────────────┘

Next: gitctx search "your query"
```

#### Happy Path: Verbose

```bash
$ gitctx index --verbose

→ Walking commit graph
  Found 5678 commits

→ Extracting blobs
  Total blob references: 4567
  Unique blobs: 1234
  Deduplication: 73% savings

→ Generating embeddings
  Processing blobs: abc123, def456, ...

→ Saving index
  Blobs: ~/.gitctx/blobs/ (45.2 MB)
  Metadata: ~/.gitctx/metadata/ (2.1 MB)

✓ Indexed 5678 commits (1234 unique blobs) in 8.2s

Statistics:
  Commits:      5678
  Unique blobs: 1234
  Total refs:   4567
  Dedup rate:   73%
  Chunks:       3456
  Size:         47.3 MB
```

#### Happy Path: Quiet

```bash
$ gitctx index --quiet
(no output on success, exit code 0)
```

#### Happy Path: Force Reindex

```bash
$ gitctx index --force
Cleared existing index (47.3 MB)
Indexed 5678 commits (1234 unique blobs) in 8.2s
```

#### Happy Path: Resume

```bash
$ gitctx index --resume
Resuming from commit 2345/5678 (blob 456/1234)
Indexed 3333 commits (778 unique blobs) in 4.1s
```

#### Error: Not in Git Repo

```bash
$ gitctx index

✗ Error: not a git repository

gitctx requires a git repository. To fix:

  1. Create a repository:
     git init

  2. Or clone one:
     git clone <url>

  3. Then run:
     gitctx index
```

#### Error: No API Key

```bash
$ gitctx index

✗ Error: OPENAI_API_KEY not set

Set your API key:

  1. Config file (recommended):
     gitctx config set api_keys.openai sk-...

  2. Environment variable:
     export OPENAI_API_KEY=sk-...

  3. Command line:
     OPENAI_API_KEY=sk-... gitctx index

Get your key: https://platform.openai.com/api-keys
```

#### Error: Rate Limit

```bash
$ gitctx index
⠋ Indexing... 5.2s
⚠️  Rate limit exceeded (60/min)

Progress saved: commit 2345/5678 (blob 456/1234)

Resume with: gitctx index --resume
```

#### Error: Network Failure

```bash
$ gitctx index
⠋ Indexing... 8.1s

✗ Error: network error at commit 2345/5678 (blob 456/1234)

Failed to connect to OpenAI API.

Possible causes:
  • No internet connection
  • OpenAI service outage
  • Firewall blocking requests

Progress saved. Resume with:
  gitctx index --resume

Check status: https://status.openai.com/
```

#### Error: Disk Full

```bash
$ gitctx index

✗ Error: disk full

Need:  169 MB
Have:  42 MB
Short: 127 MB

To free space:

  1. Clear gitctx cache:
     gitctx clear

  2. Check disk usage:
     du -sh ~/.gitctx

  3. Then retry:
     gitctx index
```

#### Error: Interrupted (Ctrl+C)

```bash
$ gitctx index
⠋ Indexing... 8.3s
^C
Interrupted at commit 2345/5678 (blob 456/1234)

Progress saved. Resume with:
  gitctx index --resume
```

#### Warning: Large Repository

```bash
$ gitctx index

⚠️  Large repository: 125432 files

Estimated:
  Time:  ~45 minutes
  Cost:  ~$15.00
  Calls: ~150000 API requests

This is a one-time cost. Updates will be faster.

Continue? [y/N] y

⠋ Indexing... 0.1s
(continues...)
```

---

### SEARCH Command

#### Flags

```bash
-n, --limit N      Max results (default: 10)
-v, --verbose      Show code context
    --mcp          Output structured markdown (MCP mode)
```

#### Happy Path: Default

```bash
$ gitctx search "authentication"
src/auth/login.py:45:0.92 ● f9e8d7c (HEAD, 2025-10-02, Alice) "Add OAuth support"
src/auth/middleware.py:12:0.87 a1b2c3d (2024-09-15, Bob) "Add middleware auth"
docs/authentication.md:34:0.85 ● e4f5g6h (HEAD, 2025-10-02, Alice) "Update auth docs"
tests/test_auth.py:78:0.76 ● f9e8d7c (HEAD, 2025-10-02, Alice) "Add OAuth support"

4 results in 0.23s
```

**Note**: Results with `●` are from current branch HEAD. Results without are from historical commits.

#### Happy Path: Verbose

```bash
$ gitctx search "authentication" --verbose

src/auth/login.py:45-67 (0.92) ● f9e8d7c (HEAD, 2025-10-02, Alice)
─────────────────────────────────────────────────────────────────
Message: Add OAuth support

45: def authenticate_user(username: str, password: str) -> User:
46:     """Authenticate user with credentials."""
47:     user = get_user_by_username(username)
48:     if not user:
49:         return None
50:     if not verify_password(password, user.hashed_password):
51:         return None
52:     return user

src/auth/middleware.py:12-25 (0.87) a1b2c3d (2024-09-15, Bob)
──────────────────────────────────────────────────────────────
Message: Add middleware auth

12: class AuthenticationMiddleware:
13:     def __init__(self, app):
14:         self.app = app
15:     async def __call__(self, scope, receive, send):
16:         if scope["type"] == "http":
17:             headers = dict(scope["headers"])

docs/authentication.md:34-41 (0.85) ● e4f5g6h (HEAD, 2025-10-02, Alice)
────────────────────────────────────────────────────────────────────────
Message: Update auth docs

34: ## Authentication Flow
35:
36: 1. User submits credentials to `/api/login`
37: 2. Server validates against database
38: 3. If valid, JWT token generated (24h expiry)

tests/test_auth.py:78-92 (0.76) ● f9e8d7c (HEAD, 2025-10-02, Alice)
────────────────────────────────────────────────────────────────────
Message: Add OAuth support

78: def test_login_with_valid_credentials():
79:     """Test successful authentication."""
80:     response = client.post("/api/login", json={
81:         "username": "testuser",
82:         "password": "testpass123"

4 results in 0.23s
```

#### Happy Path: MCP Mode (Machine-Optimized)

```bash
gitctx search "authentication" --mcp
```

**Output (Structured Markdown):**

````markdown
---
status: success
command: search
query: authentication
results_count: 4
duration_seconds: 0.23
timestamp: 2025-10-02T14:35:42Z
version: 0.1.0
---

# Search Results: "authentication"

## Summary

- **Query**: `authentication`
- **Results**: 4 matches
- **Duration**: 0.23s
- **Chunks searched**: 5678

## Results

### 1. src/auth/login.py:45-67 (Score: 0.92)

**Source**: Current file

**Context**: User authentication function

```python
def authenticate_user(username: str, password: str) -> User:
    """Authenticate user with credentials."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
```

**Metadata**:
- File: `src/auth/login.py`
- Lines: 45-67
- Relevance: 0.92
- Type: function_definition
- Language: python
- Tokens: 234

---

### 2. src/auth/middleware.py:12-25 (Score: 0.87)

**Source**: Historical commit
**Commit**: a1b2c3d
**Author**: Alice <alice@example.com>
**Date**: 2024-09-15
**Message**: Add middleware auth

**Context**: HTTP authentication middleware class

```python
class AuthenticationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            auth_header = headers.get(b"authorization")
            if auth_header:
                token = self.extract_token(auth_header)
                scope["user"] = await self.validate_token(token)
```

**Metadata**:
- File: `src/auth/middleware.py`
- Lines: 12-25
- Relevance: 0.87
- Type: class_definition
- Language: python
- Tokens: 312

---

### 3. docs/authentication.md:34-41 (Score: 0.85)

**Source**: Current file

**Context**: Authentication flow documentation

```markdown
## Authentication Flow

1. User submits credentials to `/api/login`
2. Server validates against database
3. If valid, JWT token generated (24h expiry)
4. Token returned in response body
5. Client includes token in Authorization header
6. Middleware validates token on each request
```

**Metadata**:
- File: `docs/authentication.md`
- Lines: 34-41
- Relevance: 0.85
- Type: documentation
- Language: markdown
- Tokens: 156

---

### 4. tests/test_auth.py:78-92 (Score: 0.76)

**Source**: Current file

**Context**: Authentication test case

```python
def test_login_with_valid_credentials():
    """Test successful authentication."""
    response = client.post("/api/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
```

**Metadata**:
- File: `tests/test_auth.py`
- Lines: 78-92
- Relevance: 0.76
- Type: test_function
- Language: python
- Tokens: 198

---

## Search Metadata

```json
{
  "query": "authentication",
  "results_count": 4,
  "total_chunks_searched": 5678,
  "duration_ms": 230,
  "model": "text-embedding-3-large",
  "top_score": 0.92,
  "avg_score": 0.85,
  "min_score": 0.76,
  "threshold": 0.7
}
```
````

#### Happy Path: Limit Results

```bash
$ gitctx search "authentication" --limit 2
src/auth/login.py:45:0.92 ● f9e8d7c (HEAD, 2025-10-02, Alice) "Add OAuth support"
src/auth/middleware.py:12:0.87 a1b2c3d (2024-09-15, Bob) "Add middleware auth"

2 of 4 results in 0.23s
```

#### Error: No Index ```bash

$ gitctx search "authentication"

✗ Error: no index found

Run: gitctx index

```

#### Error: No Index (MCP)
````markdown
---
status: error
command: search
error_code: no_index
exit_code: 8
timestamp: 2025-10-02T14:32:15Z
version: 0.1.0
---

# Search Operation: Error

## Error Details

- **Error**: No index found
- **Code**: `no_index`
- **Exit Code**: 8

## Resolution

You need to index your repository before searching.

```bash
gitctx index
```

This is a one-time setup that takes a few minutes.

## Additional Information

- Indexing creates semantic embeddings of your code
- Cost: ~$0.10 per 1,000 files (one-time)
- Time: ~30 seconds per 1,000 files

````

#### Error: Missing Query ```bash
$ gitctx search

✗ Error: missing argument: QUERY

Usage: gitctx search <QUERY> [OPTIONS]

Example:
  gitctx search "authentication logic"
```

#### Error: Zero Results ```bash
$ gitctx search "nonexistent"
0 results in 0.12s
```

#### Error: Zero Results (MCP)
````markdown
---
status: success
command: search
query: nonexistent
results_count: 0
duration_seconds: 0.12
timestamp: 2025-10-02T14:32:15Z
version: 0.1.0
---

# Search Results: "nonexistent"

## Summary

- **Query**: `nonexistent`
- **Results**: 0 matches
- **Duration**: 0.12s
- **Chunks searched**: 5678

## Suggestions

- Try broader search terms
- Check spelling
- Use related keywords
- Try natural language: "how does X work"

If you recently added files, reindex:

```bash
gitctx index
```
````

#### Error: Query Too Long ```bash

$ gitctx search "$(cat huge_file.txt)"

✗ Error: query exceeds 8000 tokens (got 9234)

Use a shorter, more focused query.

```

#### Error: Corrupted Index

```bash
$ gitctx search "authentication"

✗ Error: index corrupted

Fix with:
  gitctx clear && gitctx index
```

---

### CONFIG Command

#### Subcommands

```bash
gitctx config set <key> <value>
gitctx config get <key>
gitctx config list
gitctx config unset <key>
```

#### Happy Path: Set

```bash
$ gitctx config set api_keys.openai sk-proj-abc123
set api_keys.openai
```

#### Happy Path: Get
```bash
$ gitctx config get api_keys.openai
sk-...abc
```

#### Happy Path: List

```bash
$ gitctx config list
api_keys.openai=sk-...abc
search.limit=10
search.rerank=true
index.chunk_size=1000
model.embedding=text-embedding-3-large
```

#### Happy Path: Unset

```bash
$ gitctx config unset api_keys.openai
unset api_keys.openai
```

#### Error: Invalid Key

```bash
$ gitctx config set invalid.key value

✗ Error: unknown key 'invalid.key'

Valid keys: gitctx config list --help
```

#### Error: Invalid Value Type

```bash
$ gitctx config set search.limit abc

✗ Error: invalid value for search.limit

Expected: integer (1-100)
Got:      "abc"

Example:
  gitctx config set search.limit 10
```

#### Error: Permission Denied

```bash
$ gitctx config set api_keys.openai sk-123

✗ Error: permission denied: ~/.gitctx/config.yml

Fix permissions:
  chmod 644 ~/.gitctx/config.yml
```

---

### CLEAR Command

#### Flags

```bash
-f, --force        Skip confirmation
-d, --database     Clear database only
-e, --embeddings   Clear embeddings only
-a, --all          Clear everything (default)
    --dry-run      Show what would be cleared
```

#### Happy Path: Default

```bash
$ gitctx clear

This will clear:
  database (68.3 MB)
  embeddings (191.2 MB)
  cache (12.4 MB)

Total: 271.9 MB

Continue? [y/N] y

Cleared 271.9 MB in 0.3s
```

#### Happy Path: Force

```bash
$ gitctx clear --force
Cleared 271.9 MB in 0.3s
```

#### Happy Path: Database Only

```bash
$ gitctx clear --database
Clear database (68.3 MB)? [y/N] y
Cleared database (68.3 MB) in 0.1s
```

#### Happy Path: Dry Run

```bash
$ gitctx clear --dry-run

Would clear:
  database (68.3 MB)
  embeddings (191.2 MB)
  cache (12.4 MB)

Total: 271.9 MB
```

#### Happy Path: User Cancels

```bash
$ gitctx clear

This will clear:
  database (68.3 MB)
  embeddings (191.2 MB)
  cache (12.4 MB)

Total: 271.9 MB

Continue? [y/N] n

Cancelled
```

#### Happy Path: Nothing to Clear

```bash
$ gitctx clear
Nothing to clear
```

#### Error: Permission Denied

```bash
$ gitctx clear --force

✗ Error: permission denied: ~/.gitctx/index.db

Fix permissions:
  chmod 644 ~/.gitctx/index.db
```

#### Error: Files in Use ```bash

$ gitctx clear --force

✗ Error: index.db is locked (in use by another process)

Close other gitctx processes and retry.

```

#### Error: Partial Failure ```bash
$ gitctx clear --force

Cleared database (68.3 MB)
✗ Error: permission denied: ~/.gitctx/embeddings/

Partial: 1 of 3 items cleared
```

---

## Behavioral Rules

### TTY Detection

```python
import sys

if sys.stdout.isatty():
    # Interactive terminal
    allow_prompts = True
    use_spinner = True  # Only for >5s operations
    show_tips = check_first_run()  # First-run only
else:
    # Pipe or redirect
    allow_prompts = False  # Require --force
    use_spinner = False
    show_tips = False
```

### MCP Mode Detection (Search Command Only)

```python
def is_mcp_mode(args) -> bool:
    """Check if MCP output mode is requested (search command only)."""
    return hasattr(args, 'mcp') and args.mcp

# Usage in search command
if is_mcp_mode(args):
    output_search_markdown_mcp(results)
else:
    output_search_human(results)
```

### First-Run Detection

```python
from pathlib import Path

def is_first_run(command: str) -> bool:
    """Detect if this is user's first time running command."""
    marker_file = Path.home() / ".gitctx" / f".{command}_run"

    if not marker_file.exists():
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.touch()
        return True
    return False

# Usage: Show tips only on first run
if is_first_run("index"):
    show_tip_box("gitctx creates semantic embeddings...")
```

### Progress Indicators

```python
# Only show spinner for operations >5 seconds
# No progress bars - use spinner with elapsed time
# Format: ⠋ Action... 12.3s

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

def with_spinner(message: str, min_duration: float = 5.0):
    """Show spinner only if operation takes >5s."""
    start = time.time()

    def check_and_show():
        if time.time() - start > min_duration:
            # Start spinner
            pass

    # ... spinner logic
```

### Confirmation Prompts

```python
# Always default to No [y/N]
# Always allow --force to skip
# Never prompt in non-TTY

def confirm(message: str, force: bool = False) -> bool:
    if force or not sys.stdout.isatty():
        return True

    response = input(f"{message} [y/N] ").strip().lower()
    return response in ('y', 'yes')
```

### Error Messages

```python
# Format: error: <brief description>
# Optional details with numbered steps
# Keep it terse but helpful

def error(message: str, steps: list[str] = None):
    print(f"✗ Error: {message}", file=sys.stderr)

    if steps:
        print("\nTo fix:\n")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        print()

    sys.exit(get_exit_code(message))
```

### MCP Output Format (Search Command)

```python
def output_search_mcp(query: str, results: list[SearchResult], metadata: dict):
    """Output structured markdown for MCP consumption (search only)."""

    # Frontmatter with search metadata
    frontmatter = {
        "status": "success",
        "command": "search",
        "query": query,
        "results_count": len(results),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "0.1.0",
    }

    # Add additional metadata
    frontmatter.update(metadata)

    # Build markdown
    md = ["---"]
    for key, value in frontmatter.items():
        md.append(f"{key}: {value}")
    md.append("---\n")

    # Add structured content
    md.append(f"# Search Results: \"{query}\"\n")
    md.append(render_search_results_markdown(results, metadata))

    print("\n".join(md))
```

### Exit Codes

```
0   Success
1   General error
2   Usage error (wrong arguments)
3   Not in git repo
4   No API key
5   Network error
6   Permission denied
7   Disk full
8   Index not found
130 Interrupted (Ctrl+C)
```

---

## Flag Naming Conventions

### Standard Flags (All Commands)

```bash
-h, --help         Show help
-v, --verbose      Detailed output
-q, --quiet        Suppress output
    --version      Show version
```

### Command-Specific Flags

```bash
# INDEX
-f, --force        Force reindex
    --resume       Resume interrupted

# SEARCH
-n, --limit N      Result limit
    --mcp          Structured markdown output for AI consumption

# CONFIG
(no command flags, only subcommands)

# CLEAR
-f, --force        Skip confirmation
-d, --database     Database only
-e, --embeddings   Embeddings only
-a, --all          Everything
    --dry-run      Preview only
```

---

## Implementation Guidelines

### Typer Configuration

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="gitctx",
    help="Context optimization engine for coding workflows",
    add_completion=False,
    rich_markup_mode="markdown",
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
    no_args_is_help=False,
)

# Rich Console with automatic platform detection
console = Console(
    highlight=False,
    soft_wrap=True,
    force_terminal=False,
    legacy_windows=None,  # Auto-detect (default)
)
```

### Platform-Aware Symbol Selection

```python
# Symbol selection based on terminal capability
# Rich's legacy_windows auto-detects Windows cmd.exe vs modern terminals
if console.legacy_windows:
    # Legacy Windows cmd.exe fallback
    SYMBOLS = {
        "success": "[OK]",
        "error": "[X]",
        "warning": "[!]",
        "tip": "[i]",
        "arrow": "->",
    }
else:
    # Modern terminals (Windows Terminal, macOS, Linux)
    SYMBOLS = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠️",
        "tip": "💡",
        "arrow": "→",
    }

# Usage in code
def show_success(message: str):
    """Show success message with platform-appropriate symbol."""
    console.print(f"[green]{SYMBOLS['success']}[/green] {message}")

def show_error(message: str):
    """Show error message with platform-appropriate symbol."""
    console.print(f"[red]{SYMBOLS['error']}[/red] Error: {message}", file=sys.stderr)
```

### MCP Markdown Schema

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class MCPFrontmatter:
    """Frontmatter metadata for MCP output."""
    status: Literal["success", "error"]
    command: str
    timestamp: str  # ISO 8601 format
    version: str
    # Command-specific fields added dynamically

@dataclass
class SearchResult:
    """Structure for a single search result in MCP mode."""
    file: str
    line_start: int
    line_end: int
    score: float
    code: str
    context: str
    language: str
    type: str  # function, class, documentation, etc.
    tokens: int
```

### Markdown Rendering Helpers

```python
def render_search_result_mcp(result: SearchResult, rank: int) -> str:
    """Render a search result as structured markdown."""

    md = [
        f"### {rank}. {result.file}:{result.line_start}-{result.line_end} (Score: {result.score:.2f})",
        "",
        f"**Context**: {result.context}",
        "",
        f"```{result.language}",
        result.code,
        "```",
        "",
        "**Metadata**:",
        f"- File: `{result.file}`",
        f"- Lines: {result.line_start}-{result.line_end}",
        f"- Relevance: {result.score:.2f}",
        f"- Type: {result.type}",
        f"- Language: {result.language}",
        f"- Tokens: {result.tokens}",
        "",
        "---",
        "",
    ]

    return "\n".join(md)
```

### Tips System

```python
from rich.panel import Panel
from rich.box import ROUNDED, ASCII

TIPS = {
    "index": "Commit your changes before indexing - gitctx only searches committed files, not working directory changes.",
    "search": "Use natural language queries for better results. Try 'how does X work' instead of just 'X'.",
    "config": "API keys are stored securely and masked in all output.",
}

def show_tip(command: str):
    """Show tip box for command (first-run only) with platform-aware formatting."""
    if not is_first_run(command):
        return

    tip = TIPS.get(command)
    if not tip:
        return

    # Use Rich Panel for automatic platform compatibility
    # ROUNDED box for modern terminals, ASCII for legacy Windows
    box_style = ASCII if console.legacy_windows else ROUNDED
    tip_icon = SYMBOLS["tip"]

    panel = Panel(
        tip,
        title=f"{tip_icon} Tip",
        title_align="left",
        box=box_style,
        border_style="blue",
        expand=False,
    )

    console.print()
    console.print(panel)
    console.print()
```

---

## Example Workflows

### Workflow 1: Human Developer (Default Mode)

```bash
# First time indexing - sees tip
$ gitctx index
Indexed 1234 files in 12.3s

┌─ 💡 Tip ──────────────────────────────────────┐
│ gitctx creates semantic embeddings for smart  │
│ search. Updates track file changes auto.      │
└───────────────────────────────────────────────┘

Next: gitctx search "your query"

# Searching - terse output
$ gitctx search "authentication"
src/auth/login.py:45:0.92
src/auth/middleware.py:12:0.87
docs/authentication.md:34:0.85
tests/test_auth.py:78:0.76

4 results in 0.23s

# Want more detail
$ gitctx search "authentication" --verbose
(shows code context)

# Error case - helpful
$ gitctx search "auth" --limit 999

✗ Error: invalid value for --limit

Expected: integer (1-100)
Got:      999

Example:
  gitctx search "auth" --limit 50
```

### Workflow 2: AI Agent (MCP Mode)

```bash
# Claude Code or other AI agent running gitctx

$ gitctx search "authentication logic" --mcp

# Returns structured markdown with:
# - Frontmatter metadata (parseable)
# - Clear section headers
# - Code blocks with syntax hints
# - Metadata for each result
# - Relevance scores
# - File/line information
# - Token counts for context management

# Agent can:
# 1. Parse frontmatter for status/metadata
# 2. Extract code blocks directly
# 3. Use relevance scores for ranking
# 4. Respect token budgets
# 5. Navigate to exact file:line locations
```

### Workflow 3: CI/CD Pipeline

```bash
# CI script using gitctx

# Index in quiet mode (no output)
gitctx index --quiet

# Search for TODOs in MCP mode, parse results
results=$(gitctx search "TODO FIXME" --mcp)

# Parse markdown frontmatter to check result count
result_count=$(echo "$results" | grep "^results_count:" | cut -d: -f2)

if [ "$result_count" -gt 0 ]; then
    echo "Found $result_count TODOs/FIXMEs"
    exit 1
fi
```

### Workflow 4: Agentic Coding Assistant

```python
# Cursor, Continue, or other agentic tool

def search_codebase(query: str) -> List[CodeChunk]:
    """Search codebase using gitctx MCP output."""

    # Run gitctx in MCP mode
    result = subprocess.run(
        ["gitctx", "search", query, "--mcp"],
        capture_output=True,
        text=True,
    )

    # Parse markdown output
    # Frontmatter gives us metadata
    # Each section is a result with code
    markdown = result.stdout

    # Extract frontmatter
    metadata = parse_frontmatter(markdown)

    # Extract code chunks
    chunks = extract_code_blocks(markdown)

    # Now we have:
    # - Relevance scores
    # - File locations
    # - Code context
    # - Token counts
    # All in LLM-friendly format!

    return chunks
```

---

## Summary

**BLEND Design System** is for:

- ✅ Professional developers who value speed
- ✅ Human/AI collaborative workflows
- ✅ Agentic coding assistants (Claude Code, Cursor, etc.)
- ✅ CI/CD automation and scripting
- ✅ Users who want terse defaults with help when needed

**Key Characteristics**:

- Terse, git-like output by default (MINIMAL)
- Helpful tips on first-run and errors only (GUIDED)
- LLM-first structured markdown output (`--mcp` flag)
- Progressive disclosure (quiet → default → verbose → mcp)
- Professional tone, assumes competence

**Unique Features**:

- **MCP mode for search only** - `--mcp` flag provides LLM-optimized output where it matters
- **Markdown over JSON** for MCP output (LLM-native format)
- **Structured frontmatter** for metadata (machine-parseable)
- **Code blocks preserved** with syntax information
- **Token counts** for context budget management
- **First-run tips** only (not annoying for repeated use)
- **TTY detection** for smart defaults

**Trade-offs**:

- ⚠️  Tips only shown once (might miss them)
- ⚠️  MCP search output is verbose (but LLM-optimized)
- ✅ Best of both worlds (terse + helpful + machine-friendly for search)

**Best for**: Modern development teams using agentic coding tools, CI/CD integration, developers who want git-like terseness with smart contextual help, and any workflow mixing human and AI interaction.

---

## Comparison Matrix

| Feature | MINIMAL | GUIDED | RICH | **BLEND** |
|---------|---------|--------|------|-----------|
| **Terseness** | ✓✓✓ | ✓ | - | ✓✓✓ |
| **Helpfulness** | - | ✓✓✓ | ✓✓ | ✓✓ (contextual) |
| **Visual Polish** | - | ✓ | ✓✓✓ | ✓ |
| **Speed** | ✓✓✓ | ✓✓ | ✓ | ✓✓✓ |
| **LLM-Friendly** | ✓ | - | - | ✓✓✓ |
| **First-Run UX** | - | ✓✓✓ | ✓✓ | ✓✓ |
| **Expert-Friendly** | ✓✓✓ | ✓ | - | ✓✓✓ |
| **MCP Support** | - | - | - | ✓✓✓ |
| **Scriptable** | ✓✓✓ | ✓✓ | ✓ | ✓✓✓ |
| **Beautiful** | - | ✓ | ✓✓✓ | ✓ |

**Legend**: ✓✓✓ Excellent | ✓✓ Good | ✓ Fair | - Poor/None
