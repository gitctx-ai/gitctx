# CLAUDE.md - gitctx Development Guide

**Critical workflow guidance for Claude Code and developers working on gitctx.**

## 🚨 Context Loading Strategy

When working in gitctx, read the appropriate nested CLAUDE.md based on your task:

- **BDD/E2E Testing** → Read `tests/e2e/CLAUDE.md`
- **Unit Testing/TDD** → Read `tests/unit/CLAUDE.md`
- **Documentation** → Read `docs/CLAUDE.md` and subdirectories
- **Architecture** → Read `docs/architecture/CLAUDE.md`
- **Ticket Workflow** → Read `docs/tickets/CLAUDE.md`
- **Specialized Agents** → Read `.claude/agents/README.md` for agent composition patterns

## Core Development Workflow

Every feature follows **BDD/TDD development**:

```bash
1. 📝 BDD      - Write Gherkin scenario for user behavior
2. 🔴 RED      - Write failing unit tests
3. 🟢 GREEN    - Write minimal code to pass
4. 🔄 REFACTOR - Clean up code if needed
5. ✅ VERIFY   - Run ALL quality gates
6. 📦 INTEGRATE- Run BDD scenarios
7. 💾 COMMIT   - Commit with descriptive message
8. 🚀 PUSH     - Push and monitor CI until green
```

**For detailed workflow examples, see `tests/e2e/CLAUDE.md` and `tests/unit/CLAUDE.md`**

## Story-Driven Development Workflow

**All development work follows a strict story-driven approach:**

### Core Principles

1. **Never work ad-hoc** - Every change must be driven by a story/task ticket
2. **Branch name = Ticket ID** - Create branch matching ticket exactly (e.g., `STORY-0001.1.0`)
3. **1 Task = 1 Commit** - Each task gets exactly one commit after manual review/approval
4. **Manual approval gates** - Stop after each task for user review before committing
5. **Track progress continuously** - Update task and story files with each commit

### Task Breakdown Pattern (BDD/TDD)

**All stories follow proper BDD/TDD workflow with incremental test implementation:**

**Correct Pattern (typical 4-task structure):**

| Task | Focus | BDD Progress | Pattern |
|------|-------|--------------|---------|
| TASK-1 | Write ALL BDD scenarios | 0/N failing 🔴 | Define behavior upfront |
| TASK-2 | Protocols/models + tests + relevant BDD steps | 1-2/N passing 🟡 | Foundation with tests |
| TASK-3 | Core impl (TDD) + core BDD steps | 5-8/N passing 🟢 | Build incrementally |
| TASK-4 | Integration + final BDD step | N/N passing ✅ | Complete the picture |

**Key Principles:**

1. **BDD First (Task 1)**: Write ALL scenarios, all failing, defines "what" the system should do
2. **TDD Within Tasks**: Unit tests written BEFORE implementation in each task (red→green→refactor)
3. **BDD Incremental**: Each task implements its relevant BDD steps alongside implementation
4. **No "Tests at End"**: Tests are never a separate final task - they're integrated throughout

**Anti-Patterns to Avoid:**

- ❌ Separate "Write BDD tests" task at end (BDD should be incremental)
- ❌ Separate "Write unit tests" task (embed unit tests in implementation tasks)
- ❌ Tasks without test specifications
- ❌ BDD scenarios not tracked incrementally across tasks
- ❌ Missing "BDD Progress" column in task table

**Example Task Checklist (TASK-3 - Implementation with TDD + BDD):**

```markdown
### Unit Tests First (TDD - RED)
- [ ] Write failing test for feature X
- [ ] Write failing test for edge case Y
- [ ] Run tests - all fail ✓

### Implementation (GREEN)
- [ ] Implement feature X to pass tests
- [ ] Run tests - all pass ✓
- [ ] Refactor if needed

### BDD Implementation
- [ ] Implement BDD steps for Scenarios 2, 3, 4
- [ ] Run BDD tests - Scenarios 2-4 now pass ✓

### Verification
- [ ] All unit tests pass
- [ ] BDD scenarios 2-4 pass
- [ ] Code coverage >90%
```

**Story Table Format:**

```markdown
| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| TASK-1 | Write BDD scenarios | 🔵 | 3 | 0/9 (all failing) |
| TASK-2 | Protocols + tests | 🔵 | 3 | 1/9 passing |
| TASK-3 | Core impl (TDD) + BDD | 🔵 | 10 | 7/9 passing |
| TASK-4 | Integration + final BDD | 🔵 | 4 | 9/9 passing ✅ |
```

### Workflow Steps

For each task in a story:

```bash
# 1. Branch name tells you where to work: git checkout -b STORY-0001.1.1
# 2. Find your story: cd $(find docs/tickets -name "STORY-0001.1.1" -type d)
# 3. Complete the task implementation following BDD/TDD (tests first!)
# 4. Run all quality gates
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src && uv run pytest

# 5. Update task file - mark status ✅ Complete, check all boxes, set Actual Hours
# 6. Update parent story README.md - increment progress %, update child task statuses
# 7. Get manual approval from user
# 8. Commit with format: feat(TASK-ID): description
# 9. Continue to next task
```

### Story Quality & Progress Review

Use the `/review-story` slash command to validate story completeness and ensure ticket documentation matches implementation reality:

**When to Use:**

1. **Before Starting Work** - Validate story readiness

   ```bash
   git checkout -b STORY-0001.1.3
   /review-story

   # Validates:
   # - Story completeness (acceptance criteria, BDD scenarios, technical design)
   # - Hierarchy alignment (epic goals, prerequisites, no conflicts)
   # - Roadmap alignment (initiative objectives, design principles)
   # - Implementation readiness (concrete steps, file paths, examples)
   # - Specification clarity (no vague terms, quantified requirements)
   ```

2. **Mid-Work** - Validate newly added tasks align with story

   ```bash
   # After adding TASK-5, TASK-6 based on PR feedback
   /review-story

   # Validates quality + checks:
   # - New tasks align with original story scope
   # - Task additions documented in story
   # - No conflicts with completed work
   ```

3. **Before Creating PR** - Final quality check and ticket sync

   ```bash
   # All tasks complete
   /review-story

   # Validates quality + verifies:
   # - All ticket statuses match git commits
   # - Progress percentages accurate
   # - Parent epic/initiative updated
   # - Documentation matches reality
   ```

**What It Does:**

- **Quality Validation** (always): Scores story readiness (0-100%)
  - Detects vague/ambiguous specifications
  - Identifies missing documentation
  - Finds unquantified requirements
  - Suggests specific fixes with exact file edits

- **Ticket Sync** (if commits exist): Compares tickets vs git state
  - Detects task status mismatches
  - Finds undocumented task additions
  - Identifies progress inaccuracies
  - Proposes exact edits to sync tickets

- **Approval & Execution**: Shows proposed edits, gets approval, applies changes
  - User reviews exact OLD → NEW for each edit
  - Approves with "yes" or declines with "no"
  - Quality score improvement shown
  - Ticket accuracy restored

**Example Output:**

```markdown
# 📋 Story Review Report: STORY-0001.1.2
Quality Score: 85% (Ready with Minor Issues)
Ticket Sync: 2 discrepancies found

## Quality Issues (3)
1. Missing prerequisite documentation → Add to Dependencies
2. Vague acceptance criterion → Replace with measurable spec
3. Missing step definition plan → Add to TASK file

## Ticket Drift (2)
1. Undocumented task additions → Update story header
2. Epic progress outdated → Update epic README

## Proposed Edits (5 across 3 files)
[Shows exact OLD/NEW for each file]

Do you approve these file edits? (yes/no/modify)
```

**Best Practices:**

- Run before starting work to ensure story is unambiguous
- Run after adding tasks mid-work to validate coherence
- Run before PR to sync all documentation
- Approve edits to maintain ticket quality and accuracy
- Quality score 95%+ = ready for autonomous agent execution

### Creating Pull Requests

When all tasks in a story are complete:

- **1 PR = 1 Story** - Create one PR per story (not per task)
- PR body mirrors the story ticket content exactly
- Use proper GitHub blob URLs for all file links (see [docs/tickets/CLAUDE.md](docs/tickets/CLAUDE.md#pr-workflow-and-github-links))
- All CI checks must pass before merge
- Push to branch named after story ID

See [PR Workflow section](docs/tickets/CLAUDE.md#pr-workflow-and-github-links) for detailed PR creation guidelines.

### Responding to PR Review Comments

When addressing GitHub review comments (from humans or bots like GitHub Copilot):

**Workflow:**
1. Fix the code issue
2. Run quality gates
3. Commit with format: `fix(STORY-ID): Address review comment #N - description`
4. Push the fix
5. Reply to the comment explaining the fix
6. Resolve the comment thread

**Using Poe Tasks (Recommended):**

We provide poe tasks that automate the complex GitHub GraphQL API interactions:

```bash
# Complete workflow: find thread, reply, and resolve in one command
PR_NUMBER=4 COMMENT_ID=2404649657 REPLY_BODY="**Fixed** - Description of fix.

**Commit:** abc123" uv run poe pr-address-comment

# Find thread ID by comment ID (if you need it separately)
PR_NUMBER=4 COMMENT_ID=2404649657 uv run poe pr-find-thread

# Reply to an existing thread (manual workflow)
THREAD_ID="PRRT_xxx" BODY="Reply text" uv run poe pr-reply

# Resolve a thread (manual workflow)
THREAD_ID="PRRT_xxx" uv run poe pr-resolve
```

**Important Notes:**
- `pr-address-comment` automatically adds "On behalf of @username" footer using your `gh` authentication
- Always include commit hash in your reply body
- Test the fix locally before replying
- Some comments may need explanation rather than code changes (e.g., "code is correct as-is because...")
- The poe tasks handle proper escaping and GraphQL mutations for you

**Manual GraphQL Workflow (Advanced):**

If you need to use the GraphQL API directly instead of poe tasks:

<details>
<summary>Click to expand manual GraphQL examples</summary>

**Finding Review Thread IDs:**

```bash
gh api graphql -f query='
query {
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 30) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes {
              databaseId
              body
            }
          }
        }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.comments.nodes[0].body | contains("SEARCH_TEXT")) | {threadId: .id, isResolved}'
```

**Replying to Review Comments:**

```bash
gh api graphql -f query='
mutation {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: "THREAD_ID"
    body: "**Fixed** - Description of fix.\n\n**Commit:** abc123\n\n---\n*On behalf of @USERNAME*"
  }) {
    comment {
      id
    }
  }
}'
```

**Resolving Review Threads:**

```bash
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {
    threadId: "THREAD_ID"
  }) {
    thread {
      id
      isResolved
    }
  }
}'
```

</details>

## Branch Naming Conventions

Branches must be named identically to their corresponding tickets:

### Format
- `STORY-NNNN.N.N` - For story development
- `TASK-NNNN.N.N.N` - For individual tasks (if needed)
- `EPIC-NNNN.N` - For epic-level work
- `BUG-NNNN` - For bug fixes
- `INIT-NNNN` - For initiative-level changes

### Examples
```bash
# Create branch for a story
git checkout -b STORY-0001.1.0

# Create branch for a bug fix
git checkout -b BUG-0042

# Create branch for an epic
git checkout -b EPIC-0001.2
```

### Best Practices
- Branch name must exactly match the ticket ID
- Create branch before starting work on ticket
- Delete branch after merge to main
- Never reuse branch names

## Commit Message Standards

All commits must follow this format to maintain clear project history:

### Format
```
type(scope): description

[optional body]
[optional footer]
```

### Types
- `feat` - New feature or functionality
- `fix` - Bug fix
- `docs` - Documentation changes
- `test` - Test additions or modifications
- `refactor` - Code restructuring without behavior change
- `style` - Code formatting, whitespace, etc.
- `chore` - Maintenance tasks, dependencies, etc.

### Scope

**For ticket-driven work (the standard workflow):**

Use the **current task ID** as the scope when committing task completion:
- `TASK-NNNN.N.N.N` - Most commits (one per task)
- `STORY-NNNN.N.N` - Only for story-level changes without specific task
- `EPIC-NNNN.N` - For epic-level changes
- `BUG-NNNN` - For bug fixes

**For non-ticket work:**
- Component names: `cli`, `core`, `tests`, etc.

### Examples from Story-Driven Development

```bash
# Standard workflow: Each task gets one commit (STORY-0001.1.0 branch)
feat(TASK-0001.1.0.1): Create project structure with CLI foundation
feat(TASK-0001.1.0.2): Configure pyproject.toml with all tool settings
feat(TASK-0001.1.0.3): Set up comprehensive BDD/TDD framework with security isolation
feat(TASK-0001.1.0.4): Configure pre-commit hooks for code quality
feat(TASK-0001.1.0.5): Set up CI/CD pipeline with GitHub Actions

# Fix discovered during CI
fix(TASK-0001.1.0.5): Resolve CI failures on macOS and file size check

# Bug fix with ticket reference
fix(BUG-0042): Correct git isolation in E2E tests to prevent SSH key access

# General component work (no ticket)
feat(cli): Add --verbose flag to index command
chore(deps): Update pytest-bdd to v6.1.1 for better Gherkin support
```

### Best Practices
- Keep first line under 72 characters
- Use imperative mood ("Add" not "Added")
- Use TASK-ID scope for standard workflow (1 task = 1 commit)
- Branch name matches the story ID, commit scope matches the task ID
- Include "why" in body for complex changes
- Update task/story tracking files before each commit

## Repository Structure

Each directory has its own CLAUDE.md with context-appropriate guidelines:

- `tests/e2e/CLAUDE.md` - BDD testing, Gherkin scenarios, pytest-bdd
- `tests/unit/CLAUDE.md` - TDD practices, unit test patterns
- `docs/CLAUDE.md` - Documentation standards
- `docs/vision/CLAUDE.md` - Product vision and strategy
- `docs/tickets/CLAUDE.md` - Ticket hierarchy (INIT→EPIC→STORY→TASK)
- `docs/architecture/CLAUDE.md` - Technical design and ADRs

## 🚫 Absolute Rules

1. **NEVER run gitctx from the gitctx repository itself** - Use temporary/mock repos
2. **NEVER write code without tests first** - BDD for features, TDD for units
3. **NEVER commit with ANY failing tests** - The entire suite must pass
4. **NEVER skip or xfail tests** - Ask for help instead
5. **NEVER modify tests to match broken code** - Fix the code, not the test
6. **NEVER use `pip` directly** - Always use `uv` for package management
7. **NEVER create separate config files** - Everything in pyproject.toml

## Repository Etiquette

- **Package Manager**: Use `uv` (never `pip` directly)
- **Config**: Everything in `pyproject.toml`
- **Quality Gates**: `ruff check`, `ruff format`, `mypy`, `pytest`
- **Python Version**: 3.11+
- **Test Isolation**: Mock git config, env vars, and file paths

## Type Safety and mypy Configuration

### The Three-Tier mypy Override Policy

**Motivation**: Type safety prevents bugs and improves code maintainability. mypy overrides should be used strategically, not as a way to silence errors we don't want to fix.

#### Tier 1: External Dependencies (Always Acceptable)

Use `ignore_missing_imports = true` for third-party libraries without type stubs:

```toml
[[tool.mypy.overrides]]
module = "lancedb.*"
ignore_missing_imports = true
follow_imports = "skip"
```

**When to use**:
- Third-party library lacks `py.typed` marker
- No `@types/` package available on PyPI
- Not worth creating custom stubs

**No documentation required** - this is standard practice for untyped dependencies.

#### Tier 2: Temporary Overrides (Requires Documentation)

Use for legacy code being gradually typed. **MUST include inline documentation**:

```toml
[[tool.mypy.overrides]]
module = "gitctx.legacy_module"
warn_unused_ignores = false
disallow_any_unimported = false
# Reason: Complex Any types from untyped protobuf library, needs protocol wrappers
# Ticket: TASK-0001.5.2 (Add type-safe protocol layer)
# Target: 2025-Q2 (EPIC-0001.5 completion)
```

**Required documentation format**:
- **Reason**: Specific technical reason for the override (e.g., "Complex Any types from protobuf", "Legacy code with dynamic attrs")
- **Ticket**: Link to tracking ticket (TASK/STORY/EPIC ID) with brief description
- **Target**: Date or milestone for removal (e.g., "2025-Q2", "EPIC-0002 completion")

**Required actions**:
1. Add inline comment with Reason/Ticket/Target to `pyproject.toml`
2. Create tracking ticket if doesn't exist
3. Review in quarterly mypy audit (see below)
4. Remove override when fixed

**Quarterly Audit Process**:

```bash
# Review all overrides with Target dates
rg "Target:" pyproject.toml

# For each expired override:
# 1. Attempt to remove override and run mypy
uv run mypy src

# 2. If mypy fails, update Target date and Ticket with progress notes
# 3. If mypy passes, remove override entirely and commit
```

Schedule audits for: Q1 (March), Q2 (June), Q3 (September), Q4 (December)

#### Tier 3: Never Acceptable

❌ **NEVER silence errors in new code:**

```toml
# ❌ Bad: Hiding type errors instead of fixing them
[[tool.mypy.overrides]]
module = "gitctx.new_feature"
disallow_any_unimported = false
warn_unused_ignores = false
```

**If mypy fails on new code**: Fix the types, don't silence warnings!

**Common fixes**:
- **Missing return type**: Add `-> ReturnType` annotation
- **Missing parameter types**: Add `: ParamType` annotations
- **`Any` from untyped import**: Use `from typing import TYPE_CHECKING` + forward refs
- **Complex generic**: Simplify type or use `TypeVar` with bounds
- **Dynamic attributes**: Use `Protocol` or `@dataclass` instead of runtime `setattr()`

### New Module Checklist

When creating new Python modules, follow these type safety requirements:

1. ✅ Add full type annotations (all parameters, returns, class attributes)
2. ✅ Use `from __future__ import annotations` for forward reference support
3. ✅ Pass `uv run mypy src/gitctx/new_module.py` without any overrides
4. ✅ Avoid `Any` except for truly dynamic data (e.g., raw JSON, user input)
5. ✅ Use `Protocol` instead of weakening mypy settings
6. ✅ Add type stubs (`.pyi` files) only as last resort (prefer inline types)

### Protocol Pattern (Strongly Recommended)

Instead of disabling mypy for external types, define protocols:

```python
# ❌ Bad: Disable mypy for whole module
# In pyproject.toml: disallow_any_unimported = false

# ✅ Good: Define protocol for external type
from typing import Protocol
import numpy as np  # Untyped library

class ArrayLike(Protocol):
    """Type-safe interface for array-like objects."""
    shape: tuple[int, ...]

    def tolist(self) -> list[float]: ...
    def __len__(self) -> int: ...

def process_array(arr: ArrayLike) -> list[float]:
    """Process array with full type safety."""
    return arr.tolist()

# Works with numpy arrays, pandas Series, etc., but statically typed!
result = process_array(np.array([1.0, 2.0]))
```

**Benefits**:
- Full type safety without mypy overrides
- Documents expected interface
- Works with any compatible type (numpy, pandas, torch, etc.)
- Refactoring-safe (mypy catches breaking changes)

### Progressive Type Safety Strategy

**For new features** (post-INIT-0001):
- Start with strict mypy (no overrides except Tier 1)
- Use protocols for external types
- Aim for 100% type coverage

**For existing code**:
- Add Tier 2 overrides with documentation
- Fix during quarterly audits
- Prioritize hot paths and public APIs

**Measuring progress**:

```bash
# Count Tier 2 overrides (goal: reduce over time)
rg -c "Reason:" pyproject.toml

# Check mypy coverage (goal: increase over time)
uv run mypy src --html-report mypy-report
open mypy-report/index.html
```

Track mypy override count in each Epic's completion criteria.

### Common mypy Patterns

**Pattern 1: TYPE_CHECKING for circular imports**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gitctx.storage.lancedb_store import LanceDBStore  # Only for type checking

class QueryEmbedder:
    def __init__(self, store: LanceDBStore) -> None:  # Forward reference works!
        self.store = store
```

**Pattern 2: TypeVar for generic return types**

```python
from typing import TypeVar, Protocol

T = TypeVar("T", bound="Comparable")

class Comparable(Protocol):
    def __lt__(self, other: object) -> bool: ...

def max_value(items: list[T]) -> T:
    """Return max with proper type inference."""
    return max(items)

result = max_value([1, 2, 3])  # Type: int (inferred correctly!)
```

**Pattern 3: Literal for string enums**

```python
from typing import Literal

OutputMode = Literal["terse", "verbose", "mcp"]

def format_output(mode: OutputMode) -> str:
    """Type-safe output formatting."""
    if mode == "terse":
        return "..."
    # mypy catches typos: mode == "verbos" → error!
```

### Pre-commit Hook Enforcement

**Planned** (TASK-0001.X.X): Add automated validation:

```yaml
# .pre-commit-config.yaml
- id: check-mypy-overrides
  name: Verify mypy Tier 2 overrides have documentation
  entry: python scripts/check_mypy_overrides.py
  language: python
  pass_filenames: false
```

This script validates that all Tier 2 overrides have required Reason/Ticket/Target comments.

### Emergency Override Process

If you're blocked by mypy on critical work:

1. **First**, try the fixes above (Protocol, TYPE_CHECKING, TypeVar)
2. **If still blocked**, add Tier 2 override with full documentation
3. **Create ticket** immediately for fixing the type issue
4. **Set Target** within same EPIC or next quarter (whichever is sooner)
5. **Get approval** from tech lead in PR review

**Never commit undocumented overrides** - they create permanent tech debt.

## Quick Reference Commands

```bash
# Install with development dependencies
uv sync --all-extras

# BDD/TDD Development
uv run pytest tests/e2e/ -k "scenario"        # Run specific BDD scenario
uv run pytest tests/unit/module/test.py -v    # Run unit tests
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src && uv run pytest

# Testing
uv run pytest                                  # Run all tests
uv run pytest --cov=src/gitctx                # With coverage
uv run pytest -vvs -x                         # Debug mode

# Git Operations
git add . && git commit -m "feat: description"
gh run list --limit 1 && gh run watch <ID>
```

**For complete examples and detailed workflows, consult the nested CLAUDE.md files.**
