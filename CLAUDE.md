# CLAUDE.md - gitctx Development Guide

**Critical workflow guidance for Claude Code and developers working on gitctx.**

## 🚨 Context Loading Strategy

When working in gitctx, read the appropriate nested CLAUDE.md based on your task:

- **BDD/E2E Testing** → Read `tests/e2e/CLAUDE.md`
- **Unit Testing/TDD** → Read `tests/unit/CLAUDE.md`
- **Documentation** → Read `docs/CLAUDE.md` and subdirectories
- **Architecture** → Read `docs/architecture/CLAUDE.md`
- **Ticket Workflow** → Read `docs/tickets/CLAUDE.md`

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

### Workflow Steps

For each task in a story:

```bash
# 1. Complete the task implementation following BDD/TDD
# 2. Run all quality gates
uv run ruff check src tests && uv run ruff format src tests && uv run mypy src && uv run pytest

# 3. Update task file - mark status ✅ Complete, check all boxes, set Actual Hours
# 4. Update parent story file - increment progress %, update child task statuses
# 5. Get manual approval from user
# 6. Commit with format: feat(TASK-ID): description
# 7. Continue to next task
```

### Creating Pull Requests

When all tasks in a story are complete:

- **1 PR = 1 Story** - Create one PR per story (not per task)
- PR body mirrors the story ticket content exactly
- Use proper GitHub blob URLs for all file links (see [docs/tickets/CLAUDE.md](docs/tickets/CLAUDE.md#pr-workflow-and-github-links))
- All CI checks must pass before merge
- Push to branch named after story ID

See [PR Workflow section](docs/tickets/CLAUDE.md#pr-workflow-and-github-links) for detailed PR creation guidelines.

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
